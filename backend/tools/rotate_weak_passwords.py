#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""离线运维脚本：轮换既有 SQLite 库中的弱口令账号（R2），并置 R19 待改密标记。

=========================== 用途与适用时机 ===========================
B0/Q08 关闭了种子账号的弱口令、B2/R8 关闭了「新建用户默认弱口令」与
「重置为固定弱口令」，但**既有库**中已落库的账号口令不会自动变化。
本脚本用于运维侧显式轮换这些历史账号，补齐 R2 的最后一环。

2026-11-08 起同时配合 R19「强制首次改密」：轮换产生的随机口令只用于
首次登录换绑，服务端 ``get_current_user`` 守卫会拒绝该账号除
``POST /api/auth/change-password`` 外的全部业务请求，直到本人改密。

=========================== 安全提醒（必读） ===========================
1. 本脚本只做三件事（``--apply`` 时）：``users`` 表缺少
   ``must_change_password`` 列时幂等补列、更新匹配账号的
   ``password_hash``、把匹配账号的 ``must_change_password`` 置 1。
   不改其它表、不建表、不执行 Alembic 迁移、不启动 FastAPI 服务、
   不导入 ``app.main``，因此无需 AUTH_SECRET。补列与迁移
   ``c4d5e6f7a8b9`` 幂等兼容，之后执行 ``alembic upgrade head`` 不会重复加列。
2. 必须在**服务已停止**时执行，避免 SQLite 并发写锁与服务端缓存旧哈希。
   轮换后由于令牌绑定密码版本（R19），所有此前签发的令牌立即失效。
3. 写库前会在**数据库同目录**自动生成 ``<库名>.bak.<timestamp>`` 备份
   （含全部业务数据与旧的弱口令哈希，按敏感数据妥善保管，切勿提交版本库）。
   默认 dry-run 模式不写库、不生成备份、不产生任何文件变更。
4. 明文密码只在本次终端输出（``--random`` 模式）或由调用方通过
   ``--password`` 自行保管；脚本绝不把明文写入日志、备份或任何文件。
5. 哈希算法沿用 ``PasswordHasher.hash``（PBKDF2-HMAC-SHA256），**未改变**
   算法与轮数，轮换后可直接用新口令登录，无需改动用户模型。
6. ``--all-weak`` 每个账号生成**互不相同**的随机口令；批量模式强制要求
   ``--random``，避免多账号共用一个口令造成一处泄露全盘失守。

=========================== 用法示例 ===========================
    # 1) 先预览：找出仍在使用已知弱口令的账号（不写任何文件）
    python backend/tools/rotate_weak_passwords.py --db backend/pos.db \
        --all-weak --random

    # 2) 确认无误后真正写库（一次备份，逐账号独立随机口令）
    python backend/tools/rotate_weak_passwords.py --db backend/pos.db \
        --all-weak --random --apply

    # 3) 只轮换单个账号并指定新口令（同样要求 >=8 位且非弱口令）
    python backend/tools/rotate_weak_passwords.py --db backend/pos.db \
        --user cashier01 --password 'Xk9!mQ2vLp7s' --apply

    # 4) 追加自定义弱口令候选（可重复传入）
    python backend/tools/rotate_weak_passwords.py --db backend/pos.db \
        --all-weak --random --weak-password 'abc@123' --apply
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

# 已知的历史默认弱口令候选。命中判定用 PasswordHasher.verify 与库中哈希比对，
# 不依赖任何明文落库；可用 --weak-password 追加业务自定义候选。
DEFAULT_WEAK_CANDIDATES = (
    "123456",
    "12345678",
    "123456789",
    "888888",
    "000000",
    "password",
    "admin123",
)

FLAG_COLUMN = "must_change_password"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。

    :param argv: 参数列表，None 表示取 sys.argv
    :return: 解析结果
    """
    parser = argparse.ArgumentParser(
        description="轮换既有 SQLite 库中的弱口令账号（默认 dry-run）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db",
        default="./pos.db",
        help="SQLite 数据库文件路径（默认 ./pos.db）",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--user",
        help="只轮换指定登录用户名（Q11 后全平台唯一）",
    )
    target.add_argument(
        "--all-weak",
        action="store_true",
        help="轮换库中所有仍在使用已知弱口令的账号（每账号独立随机口令）",
    )
    secret = parser.add_mutually_exclusive_group(required=True)
    secret.add_argument("--password", help="指定新口令（>=8 位且非弱口令）")
    secret.add_argument(
        "--random",
        action="store_true",
        help="为账号生成 16 位随机临时口令并在终端打印一次",
    )
    parser.add_argument(
        "--weak-password",
        action="append",
        default=None,
        help="追加弱口令候选（可重复）；不传则使用内置默认候选",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="真正写库（缺省为 dry-run，只预览不写任何文件）",
    )
    return parser.parse_args(argv)


def _hash_prefix(password_hash: str) -> str:
    """只取哈希的算法标识用于展示，避免把完整哈希打印到终端。

    :param password_hash: 库中保存的哈希字符串
    :return: 形如 pbkdf2_sha256$260000 的前缀
    """
    parts = (password_hash or "").split("$")
    return "$".join(parts[:2]) if len(parts) >= 2 else "未知格式"


def _has_flag_column(connection: sqlite3.Connection) -> bool:
    """判断 users 是否已有 R19 待改密列。

    :param connection: 数据库连接
    :return: 列存在返回 True
    """
    columns = connection.execute("PRAGMA table_info(users)").fetchall()
    return any(row[1] == FLAG_COLUMN for row in columns)


def _find_weak_users(
    connection: sqlite3.Connection, candidates: tuple[str, ...]
) -> list[tuple[int, str, str]]:
    """找出仍在使用已知弱口令的账号。

    :param connection: 数据库连接
    :param candidates: 弱口令候选明文
    :return: [(用户 ID, 用户名, 命中的弱口令)]
    """
    rows = connection.execute(
        "SELECT id, username, password_hash FROM users ORDER BY id"
    ).fetchall()
    result: list[tuple[int, str, str]] = []
    for user_id, username, password_hash in rows:
        for candidate in candidates:
            if PasswordHasher.verify(candidate, password_hash):
                result.append((user_id, username, candidate))
                break
    return result


def main(argv: list[str] | None = None) -> int:
    """脚本主流程：定位目标 → 预览/备份 → 幂等补列 → 更新哈希与标记 → 交接口令。

    :param argv: 参数列表，None 表示取 sys.argv
    :return: 进程退出码（0 成功，1 数据问题，2 参数/强度问题）
    """
    args = _parse_args(argv)
    db_path = Path(args.db).expanduser().resolve()
    if not db_path.is_file():
        print(f"[错误] 数据库文件不存在：{db_path}")
        return 1
    if args.all_weak and not args.random:
        print("[错误] --all-weak 必须配合 --random，禁止多账号共用同一口令")
        return 2
    if not args.random:
        try:
            ensure_strong_password(args.password, "新口令")
        except ValueError as exc:
            print(f"[错误] 新口令不合规：{exc}")
            return 2

    candidates = (
        tuple(args.weak_password)
        if args.weak_password
        else DEFAULT_WEAK_CANDIDATES
    )
    connection = sqlite3.connect(str(db_path))
    try:
        if args.all_weak:
            targets = _find_weak_users(connection, candidates)
            if not targets:
                print("[提示] 未发现仍使用已知弱口令的账号，无需轮换。")
                return 0
        else:
            row = connection.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (args.user.strip(),),
            ).fetchone()
            if row is None:
                print(f"[错误] 用户不存在：{args.user}")
                return 1
            targets = [(row[0], row[1], "（按账号指定）")]

        plan = []
        for user_id, username, matched in targets:
            new_password = (
                generate_temporary_password() if args.random else args.password
            )
            plan.append(
                (user_id, username, matched, new_password, PasswordHasher.hash(new_password))
            )

        has_flag = _has_flag_column(connection)
        mode = "APPLY（写库）" if args.apply else "DRY-RUN（仅预览）"
        print("=" * 68)
        print(f"模式        : {mode}")
        print(f"数据库      : {db_path}")
        print(f"匹配账号数  : {len(plan)}")
        print(f"弱口令候选  : {len(candidates)} 个")
        print(f"待改密列    : {'已存在' if has_flag else '缺失，--apply 时幂等补列'}")
        print(f"影响列      : users.password_hash / users.{FLAG_COLUMN}")
        for _, username, matched, _, new_hash in plan:
            print(f"  - {username:<14} 命中 {matched:<12} 新哈希 {_hash_prefix(new_hash)}")

        if not args.apply:
            print("[DRY-RUN] 未写库、未生成备份、未产生任何文件变更。")
            if args.random:
                print("[DRY-RUN] 以下预览口令均未生效，执行 --apply 时会重新生成：")
                for _, username, _, preview, _ in plan:
                    print(f"  {username:<14} {preview}")
            print("=" * 68)
            print("确认无误后请追加 --apply 重新执行。")
            return 0

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        backup_path = db_path.with_name(f"{db_path.name}.bak.{timestamp}")
        shutil.copy2(db_path, backup_path)
        print(f"已备份      : {backup_path}")

        if not has_flag:
            connection.execute(
                f"ALTER TABLE users ADD COLUMN {FLAG_COLUMN} BOOLEAN NOT NULL DEFAULT 0"
            )
            print(f"已补列      : users.{FLAG_COLUMN} BOOLEAN NOT NULL DEFAULT 0")

        for user_id, _, _, _, new_hash in plan:
            connection.execute(
                f"UPDATE users SET password_hash = ?, {FLAG_COLUMN} = 1 WHERE id = ?",
                (new_hash, user_id),
            )
        connection.commit()
        print(f"[完成] 已轮换 {len(plan)} 个账号，全部置为「首次登录须改密」。")
        print("-" * 68)
        if args.random:
            print("临时口令（仅本次输出，请立即复制并通过安全渠道转交本人）：")
            for _, username, _, new_password, _ in plan:
                print(f"  {username:<14} {new_password}")
        else:
            print("请通过安全渠道把新口令转交本人（脚本不保存明文）。")
        print("账号首次登录后会被服务端强制修改密码；旧令牌已全部失效。")
        print("=" * 68)
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())
