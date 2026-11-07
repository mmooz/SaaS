#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""离线运维脚本：轮换既有 SQLite 库中指定账号的弱口令（R2）。

=========================== 用途与适用时机 ===========================
B0/Q08 关闭了种子账号的弱口令、B2/R8 关闭了「新建用户默认弱口令」与
「重置为固定弱口令」，但**既有库**中已落库的账号口令不会自动变化。
本脚本用于运维侧显式轮换这些历史账号的口令，补齐 R2 的最后一环。

=========================== 安全提醒（必读） ===========================
1. 本脚本**只更新 users.password_hash 一个字段**：不改其它表、不建表、
   不执行 Alembic 迁移、不启动 FastAPI 服务、不导入 app.main，因此无需
   AUTH_SECRET，也不会触发应用启动校验或自动种子逻辑。
2. 必须在**服务已停止**时执行，避免 SQLite 并发写锁与服务端缓存旧哈希。
3. 写库前会在**数据库同目录**自动生成 ``<库名>.bak.<timestamp>`` 备份
   （含全部业务数据，请按敏感数据妥善保管，切勿提交到版本库）。
   默认 dry-run 模式不写库、不生成备份、不产生任何文件变更。
4. 明文密码只在本次终端输出（``--random`` 模式）或由调用方通过
   ``--password`` 自行保管；脚本绝不把明文写入日志、备份或任何文件。
5. 哈希算法沿用 ``PasswordHasher.hash``（PBKDF2-HMAC-SHA256），**未改变**
   算法与轮数，轮换后可直接用新口令登录，无需改动用户模型或迁移。
6. 「强制首次登录改密」需要 User 模型新增字段 + Alembic 迁移 + 前端流程，
   超出本批次范围，本脚本不实现，也不改变登录流程。

=========================== 用法示例 ===========================
    # 1) 只预览，不写任何文件（默认）
    python backend/tools/rotate_weak_passwords.py --db backend/pos.db \
        --user admin --random

    # 2) 确认无误后真正写库（自动备份）
    python backend/tools/rotate_weak_passwords.py --db backend/pos.db \
        --user admin --random --apply

    # 3) 指定新口令（同样要求 >=8 位且非弱口令）
    python backend/tools/rotate_weak_passwords.py --db backend/pos.db \
        --user cashier01 --password 'Xk9!mQ2vLp7s' --apply

    # 4) 一次只处理一个账号；多个账号请逐个执行（每次都会独立备份）
=====================================================================
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# 让脚本可以从任意工作目录执行：把 backend/ 加入模块搜索路径。
# 只导入两个不依赖应用入口的服务模块，绝不加载 app.main。
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.password_hasher import PasswordHasher  # noqa: E402
from app.services.password_policy import (  # noqa: E402
    ensure_strong_password,
    generate_temporary_password,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。

    :param argv: 参数列表，None 表示取 sys.argv
    :return: 解析结果
    """
    parser = argparse.ArgumentParser(
        description="轮换既有 SQLite 库中指定账号的弱口令（默认 dry-run）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db",
        default="./pos.db",
        help="SQLite 数据库文件路径（默认 ./pos.db）",
    )
    parser.add_argument(
        "--user",
        required=True,
        help="要轮换口令的登录用户名（Q11 后全平台唯一）",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--password", help="指定新口令（>=8 位且非弱口令）")
    group.add_argument(
        "--random",
        action="store_true",
        help="生成 16 位随机临时口令并在终端打印一次",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="真正写库（缺省为 dry-run，只预览不写任何文件）",
    )
    return parser.parse_args(argv)


def _resolve_new_password(args: argparse.Namespace) -> str:
    """确定新口令并做强度校验。

    :param args: 命令行参数
    :return: 通过强度校验的明文新口令
    :raises ValueError: 指定口令强度不足
    """
    if args.random:
        return generate_temporary_password()
    return ensure_strong_password(args.password, "新口令")


def _hash_prefix(password_hash: str) -> str:
    """只取哈希的算法标识用于展示，避免把完整哈希打印到终端。

    :param password_hash: 库中保存的哈希字符串
    :return: 形如 pbkdf2_sha256$260000 的前缀
    """
    parts = (password_hash or "").split("$")
    return "$".join(parts[:2]) if len(parts) >= 2 else "未知格式"


def main(argv: list[str] | None = None) -> int:
    """脚本主流程：校验参数 → 预览/备份 → 更新单字段 → 打印结果。

    :param argv: 参数列表，None 表示取 sys.argv
    :return: 进程退出码（0 成功，1 数据问题，2 参数/强度问题）
    """
    args = _parse_args(argv)
    db_path = Path(args.db).expanduser().resolve()
    if not db_path.is_file():
        print(f"[错误] 数据库文件不存在：{db_path}")
        return 1

    try:
        new_password = _resolve_new_password(args)
    except ValueError as exc:
        print(f"[错误] 新口令不合规：{exc}")
        return 2

    connection = sqlite3.connect(str(db_path))
    try:
        row = connection.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (args.user.strip(),),
        ).fetchone()
        if row is None:
            print(f"[错误] 用户不存在：{args.user}")
            return 1
        user_id, username, old_hash = row
        new_hash = PasswordHasher.hash(new_password)

        mode = "APPLY（写库）" if args.apply else "DRY-RUN（仅预览）"
        print("=" * 62)
        print(f"模式        : {mode}")
        print(f"数据库      : {db_path}")
        print(f"目标账号    : {username}（id={user_id}）")
        print(f"旧哈希算法  : {_hash_prefix(old_hash)}")
        print(f"新哈希算法  : {_hash_prefix(new_hash)}（PBKDF2-SHA256，算法未变）")
        print(f"影响列      : users.password_hash（仅此一列）")

        if not args.apply:
            print("[DRY-RUN] 未写库、未生成备份、未产生任何文件变更。")
            if args.random:
                print(f"[DRY-RUN] 预览用随机口令（未生效）：{new_password}")
            print("=" * 62)
            print("确认无误后请追加 --apply 重新执行。")
            return 0

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        backup_path = db_path.with_name(f"{db_path.name}.bak.{timestamp}")
        shutil.copy2(db_path, backup_path)
        print(f"已备份      : {backup_path}")

        connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user_id),
        )
        connection.commit()
        print(f"[完成] 已更新 {username} 的 password_hash，提交 1 行。")
        if args.random:
            print("-" * 62)
            print(f"临时口令（仅本次输出，请立即复制并转交本人）：{new_password}")
            print("-" * 62)
        else:
            print("请通过安全渠道把新口令转交本人（脚本不保存明文）。")
        print("=" * 62)
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())
