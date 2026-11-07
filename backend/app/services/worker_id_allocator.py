"""雪花 ID 机器位分配器：用跨进程文件锁保证同一 (datacenter, worker) 唯一（Q29）。

为什么需要：``snowflake.py`` 的 ``_snowflake`` 是进程内单例，若所有进程都用
配置里固定的 worker_id（默认 1），uvicorn 多 worker 或多台后端实例会在同一
毫秒生成完全相同的雪花 ID，直接造成主键冲突。

方案：进程启动时在**系统临时目录**（``tempfile.gettempdir()``，绝不写项目目录）
按编号抢占锁文件 ``pos_snowflake_dc<dc>/worker_<n>.lock``，0-31 共 32 个编号，
谁先抢到谁使用，并在进程存活期间保持文件句柄（不解锁、不删除），进程退出后
由操作系统自动释放。Windows 用 ``msvcrt.locking``，Unix 用 ``fcntl.flock``。

容错：任何异常都只降级为「回退到显式配置 + 明确警告」，**绝不抛异常**。
``alembic/env.py`` 会经 ``app.models`` 导入本模块，抛错会打断迁移与配置导入，
因此这里把可用性放在第一位；管理员可从警告日志中及时发现编号耗尽。
"""

from __future__ import annotations

import os
import tempfile
import warnings

# 进程内已分配结果缓存：避免同进程重复抢占多个编号
_ALLOCATED_WORKER_ID: int | None = None
# 已持有的锁文件对象：保持强引用，确保进程存活期间不释放锁
_HELD_LOCKS: list[object] = []
# worker_id 取值范围（与 Snowflake.WORKER_BITS = 5 对应）
MAX_WORKER_ID = 31
# 显式配置文件锁时的告警类别
_WORKER_ID_WARNING = RuntimeWarning


def _lock_directory(datacenter_id: int) -> str:
    """返回锁目录（位于系统临时目录，绝不落在项目目录）。

    :param datacenter_id: 数据中心位，用于隔离不同数据中心的编号池
    :return: 锁目录绝对路径
    """
    return os.path.join(tempfile.gettempdir(), f"pos_snowflake_dc{datacenter_id}")


def _try_lock(worker_id: int, datacenter_id: int) -> bool:
    """尝试独占某个编号的锁文件；成功时保持句柄直到进程结束。

    :param worker_id: 待抢占的机器位编号（0-31）
    :param datacenter_id: 数据中心位
    :return: 抢锁成功返回 True；被占用或环境不支持返回 False
    """
    path = os.path.join(_lock_directory(datacenter_id), f"worker_{worker_id}.lock")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        lock_file = open(path, "a+b")
    except OSError:
        return False
    try:
        if os.name == "nt":
            # Windows：msvcrt.locking 锁定自当前文件位置起的 1 个字节，
            # 需要文件至少含 1 字节，否则锁定范围无效。
            import msvcrt

            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            # Unix：flock 为整个文件加非阻塞排他锁
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, ImportError):
        lock_file.close()
        return False
    # 只追加不移除：进程存活期间始终持有锁
    _HELD_LOCKS.append(lock_file)
    return True


def _explicit_worker_id() -> int | None:
    """读取显式配置的 SNOWFLAKE_WORKER_ID（合法时才返回）。

    :return: 0-31 的编号；未配置或非法返回 None
    """
    raw = os.getenv("SNOWFLAKE_WORKER_ID")
    if raw is None or not raw.strip():
        return None
    try:
        value = int(raw.strip())
    except ValueError:
        return None
    return value if 0 <= value <= MAX_WORKER_ID else None


def allocate_worker_id(
    datacenter_id: int = 1, fallback_worker_id: int = 1
) -> int:
    """为本进程分配唯一的雪花 ID 机器位。

    优先自动抢占 0-31 中未被占用的编号；若配置了 ``SNOWFLAKE_WORKER_ID``，
    会优先尝试该编号（单实例时与配置保持一致，多实例时自动错开）。
    全部编号占用或临时目录不可用时回退到显式配置/配置默认值并给出明确警告。

    :param datacenter_id: 数据中心位（来自配置 SNOWFLAKE_DATACENTER_ID）
    :param fallback_worker_id: 抢锁全部失败时的回退编号（来自配置默认值）
    :return: 0-31 的机器位编号
    """
    global _ALLOCATED_WORKER_ID
    if _ALLOCATED_WORKER_ID is not None:
        return _ALLOCATED_WORKER_ID

    candidates = list(range(MAX_WORKER_ID + 1))
    preferred = _explicit_worker_id()
    if preferred is not None:
        candidates.remove(preferred)
        candidates.insert(0, preferred)
    for worker_id in candidates:
        if _try_lock(worker_id, datacenter_id):
            _ALLOCATED_WORKER_ID = worker_id
            return worker_id

    # 容错降级：绝不抛异常（alembic/env.py 的导入路径不能被打断）
    if preferred is not None:
        fallback = preferred
        reason = "SNOWFLAKE_WORKER_ID 显式配置"
    else:
        fallback = fallback_worker_id if 0 <= fallback_worker_id <= MAX_WORKER_ID else 0
        reason = "配置默认值"
    warnings.warn(
        "雪花 ID 机器位自动分配失败（0-31 编号均被占用或系统临时目录不可用），"
        f"已回退到{reason} worker_id={fallback}；多实例部署可能生成重复 ID，"
        "请检查存活进程数量，并为每个实例显式配置互不相同的 "
        "SNOWFLAKE_WORKER_ID / SNOWFLAKE_DATACENTER_ID。",
        _WORKER_ID_WARNING,
        stacklevel=2,
    )
    _ALLOCATED_WORKER_ID = fallback
    return fallback
