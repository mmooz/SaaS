"""一次性修复 2026-11-05 历史示例数据的中文乱码（mojibake）。

背景
----
2026-11-05 15:08–15:20 由临时验证脚本灌入的示例数据，中文在写入环节被
逐字替换为半角问号（"上海青" -> "???"、"蔬菜" -> "??"）。原始中文可从
``backend/legacy_scripts/s2_api_check.py``、``s3_orders_check.py``、
``s5_members_check.py``、``s5_promotions_check.py``、``s5_inventory_check.py``
考据，同源条码 / 价格 / 促销参数均能对上。

这不是当前应用的编码缺陷：2026-11-06 之后新建的「跨店测试商品」「香烟」
中文均正常，且 11-08 迁移前的备份里已经是问号，故无法从备份恢复原文。

安全约束
--------
* 默认 dry-run，只打印将要修改的记录；**显式传入 --apply 才写库**。
* 写库前自动在同目录生成 ``pos.db.bak.<时间戳>.pre-mojibake`` 备份。
* 幂等：只按精确乱码值匹配，二次执行会报告 0 处改动；绝不匹配正常中文。
* 只改展示文本，不改任何 ID / 金额 / 价格 / 状态 / 关联关系。
* 会同步 bump ``products.updated_at`` / ``members.updated_at``，否则
  ``/api/sync/products`` 的增量游标不会把新名字推给 POS 本地缓存
  （分类与促销是全量下发，无需 bump）。

用法
----
    python -X utf8 backend/tools/fix_mojibake_demo_data.py
    python -X utf8 backend/tools/fix_mojibake_demo_data.py --apply
    python -X utf8 backend/tools/fix_mojibake_demo_data.py --db /path/pos.db --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# 精确乱码值 -> 考据所得原名。只匹配这些值，不误伤任何正常数据。
PRODUCT_NAME = ("???", "上海青")
CATEGORY_NAME = ("??", "蔬菜")
MEMBER_NAME = ("????", "测试会员")
PROMOTION_NAME = ("????", "全场9折")  # type=discount, params={"rate": 0.9}
ORDER_ITEM_NAME = ("???", "上海青")
PAY_DETAIL_KEY = ("??", "现金")  # s5_inventory_check.py:73 使用 {"现金": 20}
LOG_FRAGMENT = ("新增商品 ???（", "新增商品 上海青（")
STORE_NAME = ("99", "鲜果超市 · 总店")  # 与 admin-web Settings.vue 默认值一致
STORE_ADDRESS = ("????", "地址待补充")  # 原文无从考据，用中性占位名


def sha256(path: Path) -> str:
    """返回文件 SHA256。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now_naive() -> str:
    """与库内既有 updated_at 一致的 naive UTC 秒精度字符串。"""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def collect_changes(db: sqlite3.Connection) -> dict[str, list[str]]:
    """只读扫描，返回每张表待修改的描述列表（不执行任何写操作）。"""
    now = utc_now_naive()
    plan: dict[str, list[str]] = {}

    def add(table: str, desc: str) -> None:
        plan.setdefault(table, []).append(desc)

    bad, good = PRODUCT_NAME
    for row in db.execute(
        "SELECT id, barcode, pinyin FROM products WHERE name = ?", (bad,)
    ):
        add("products", f"id={row[0]} barcode={row[1]}: name '{bad}' -> '{good}'"
            + (", pinyin NULL -> 'shq'" if row[2] is None else "")
            + f", updated_at -> {now}")

    bad, good = CATEGORY_NAME
    for row in db.execute("SELECT id FROM categories WHERE name = ?", (bad,)):
        add("categories", f"id={row[0]}: name '{bad}' -> '{good}'")

    bad, good = MEMBER_NAME
    for row in db.execute("SELECT id, mobile FROM members WHERE name = ?", (bad,)):
        add("members", f"id={row[0]} mobile={row[1]}: name '{bad}' -> '{good}', "
            f"updated_at -> {now}")

    bad, good = PROMOTION_NAME
    for row in db.execute("SELECT id, type FROM promotions WHERE name = ?", (bad,)):
        add("promotions", f"id={row[0]} type={row[1]}: name '{bad}' -> '{good}'")

    bad, good = ORDER_ITEM_NAME
    for row in db.execute("SELECT id, order_id FROM order_items WHERE name = ?", (bad,)):
        add("order_items", f"id={row[0]} order_id={row[1]}: name '{bad}' -> '{good}'")

    bad, good = PAY_DETAIL_KEY
    for row in db.execute(
        "SELECT id, pay_details FROM orders WHERE pay_details LIKE ?", (f'%"{bad}"%',)
    ):
        add("orders", f"id={row[0]}: pay_details 键 '{bad}' -> '{good}'")

    bad, good = LOG_FRAGMENT
    for row in db.execute(
        "SELECT id, detail FROM operation_logs WHERE detail LIKE ?", (f"%{bad}%",)
    ):
        add("operation_logs", f"id={row[0]}: detail '{row[1]}' -> "
            f"'{row[1].replace(bad, good)}'")

    for row in db.execute(
        "SELECT tenant_id, store_id, value FROM system_settings WHERE value LIKE '%?%'"
    ):
        try:
            data = json.loads(row[2])
        except (TypeError, ValueError):
            continue
        changes = []
        if data.get("name") == STORE_NAME[0]:
            changes.append(f"name '99' -> '{STORE_NAME[1]}'")
        if data.get("address") == STORE_ADDRESS[0]:
            changes.append(f"address '{STORE_ADDRESS[0]}' -> '{STORE_ADDRESS[1]}'")
        if changes:
            add("system_settings", f"tenant={row[0]} store={row[1]}: " + "; ".join(changes))

    return plan


def apply_changes(db: sqlite3.Connection) -> dict[str, int]:
    """执行修复，返回每张表实际更新的行数。必须在事务内调用。"""
    now = utc_now_naive()
    counts: dict[str, int] = {}

    def run(table: str, sql: str, params: tuple) -> None:
        cur = db.execute(sql, params)
        counts[table] = counts.get(table, 0) + cur.rowcount

    bad, good = PRODUCT_NAME
    run("products",
        "UPDATE products SET name = ?, pinyin = COALESCE(pinyin, 'shq'), "
        "updated_at = ? WHERE name = ?", (good, now, bad))

    bad, good = CATEGORY_NAME
    run("categories", "UPDATE categories SET name = ? WHERE name = ?", (good, bad))

    bad, good = MEMBER_NAME
    run("members", "UPDATE members SET name = ?, updated_at = ? WHERE name = ?",
        (good, now, bad))

    bad, good = PROMOTION_NAME
    run("promotions", "UPDATE promotions SET name = ? WHERE name = ?", (good, bad))

    bad, good = ORDER_ITEM_NAME
    run("order_items", "UPDATE order_items SET name = ? WHERE name = ?", (good, bad))

    bad, good = PAY_DETAIL_KEY
    for row in db.execute(
        "SELECT id, pay_details FROM orders WHERE pay_details LIKE ?", (f'%"{bad}"%',)
    ).fetchall():
        try:
            details = json.loads(row[1])
        except (TypeError, ValueError):
            continue
        if bad not in details:
            continue
        rebuilt = {(good if k == bad else k): v for k, v in details.items()}
        run("orders", "UPDATE orders SET pay_details = ? WHERE id = ?",
            (json.dumps(rebuilt, ensure_ascii=False), row[0]))

    bad, good = LOG_FRAGMENT
    run("operation_logs",
        "UPDATE operation_logs SET detail = REPLACE(detail, ?, ?) "
        "WHERE detail LIKE ?", (bad, good, f"%{bad}%"))

    for row in db.execute(
        "SELECT tenant_id, store_id, value FROM system_settings WHERE value LIKE '%?%'"
    ).fetchall():
        try:
            data = json.loads(row[2])
        except (TypeError, ValueError):
            continue
        dirty = False
        if data.get("name") == STORE_NAME[0]:
            data["name"] = STORE_NAME[1]
            dirty = True
        if data.get("address") == STORE_ADDRESS[0]:
            data["address"] = STORE_ADDRESS[1]
            dirty = True
        if dirty:
            run("system_settings",
                "UPDATE system_settings SET value = ? WHERE tenant_id = ? AND store_id = ?",
                (json.dumps(data, ensure_ascii=False), row[0], row[1]))

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="修复 11-05 示例数据中文乱码")
    parser.add_argument("--db", default=None, help="数据库路径，默认 backend/pos.db")
    parser.add_argument("--apply", action="store_true", help="实际写库（默认 dry-run）")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    db_path = Path(args.db).resolve() if args.db else root / "backend" / "pos.db"
    if not db_path.is_file():
        print(f"[错误] 数据库不存在：{db_path}")
        return 1

    print(f"数据库      : {db_path}")
    print(f"模式        : {'APPLY（写库）' if args.apply else 'DRY-RUN（只读预览）'}")
    print(f"写前 SHA256 : {sha256(db_path)}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        plan = collect_changes(conn)
        total = sum(len(v) for v in plan.values())
        print(f"\n发现 {total} 处待修复：")
        for table, lines in plan.items():
            for line in lines:
                print(f"  [{table}] {line}")

        if total == 0:
            print("\n无需修改（可能已修复过）。")
            return 0

        if not args.apply:
            print("\n[Dry-run] 未写库。确认无误后加 --apply 执行。")
            print("提示：执行前会自动备份，且商品/会员会 bump updated_at 以便 POS 增量同步。")
            return 0

        stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        backup = db_path.with_name(f"{db_path.name}.bak.{stamp}.pre-mojibake")
        conn.close()  # 备份前关闭连接，确保 WAL/缓冲区全部落盘
        shutil.copy2(db_path, backup)
        print(f"\n已备份      : {backup}")
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        with conn:
            counts = apply_changes(conn)
        print("实际更新    : " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    finally:
        conn.close()

    print(f"写后 SHA256 : {sha256(db_path)}")
    print("\n[完成] 请在 POS 上执行一次商品同步（或清 localStorage 后刷新），")
    print("       分类/促销为全量下发，商品/会员已 bump updated_at 走增量。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
