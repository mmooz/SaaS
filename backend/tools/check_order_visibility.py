"""订单查询权限回归检查（独立运行，使用临时 SQLite，不触碰生产库）。

覆盖：收银员只能查本人订单 / 管理员（店长及以上）可查全店订单 / 单号详情与
退款记录同样受控 / 收银员上传订单归属强制取令牌用户 / 幂等通道不可读他人单。

运行：``backend/.venv/Scripts/python.exe backend/tools/check_order_visibility.py``
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# 必须在导入任何 app.* 之前注入：config 单例与 database engine 都在导入期读取配置
_TMP = tempfile.TemporaryDirectory(prefix="pos-order-scope-", ignore_cleanup_errors=True)
_DB_FILE = (Path(_TMP.name) / "check.db").as_posix()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_FILE}"
os.environ["AUTH_SECRET"] = "order-scope-regression-" + "x" * 48
os.environ["AUTO_CREATE_TABLES"] = "false"
os.environ["AUTO_SEED_USERS"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Order, OrderItem, Store, Tenant, User, UserStore  # noqa: E402
from app.services.password_hasher import PasswordHasher  # noqa: E402
from app.services.token_service import TokenService  # noqa: E402


def build_fixtures():
    """在临时库建表并写入两个收银员、一个店长与两笔订单。"""
    Base.metadata.create_all(bind=engine)
    hasher = PasswordHasher()
    with SessionLocal() as db:
        tenant = Tenant(name="回归租户", code="order-scope-check", enabled=True)
        db.add(tenant)
        db.flush()
        store = Store(tenant_id=tenant.id, name="回归门店", enabled=True)
        db.add(store)
        db.flush()

        users = {
            "cashier_a": User(
                tenant_id=tenant.id, username="scope_cashier_a",
                password_hash=hasher.hash("Regress!on#A1"), name="收银员甲",
                role="cashier", enabled=True, must_change_password=False,
            ),
            "cashier_b": User(
                tenant_id=tenant.id, username="scope_cashier_b",
                password_hash=hasher.hash("Regress!on#B2"), name="收银员乙",
                role="cashier", enabled=True, must_change_password=False,
            ),
            "manager": User(
                tenant_id=tenant.id, username="scope_manager",
                password_hash=hasher.hash("Regress!on#M3"), name="店长丙",
                role="manager", enabled=True, must_change_password=False,
            ),
        }
        db.add_all(list(users.values()))
        db.flush()
        db.add_all([
            UserStore(user_id=u.id, store_id=store.id) for u in users.values()
        ])

        def order(no: str, cashier: User, amount: float) -> Order:
            obj = Order(
                order_no=no, tenant_id=tenant.id, store_id=store.id,
                cashier_id=cashier.id, status="paid", total_amount=amount,
                discount_amount=0, pay_details=json.dumps({"现金": amount}, ensure_ascii=False),
                synced=True, created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            obj.items.append(OrderItem(
                tenant_id=tenant.id, product_id=None, name="回归商品",
                qty=1, unit_price=amount, amount=amount,
            ))
            return obj

        db.add(order("SCOPE-A-0001", users["cashier_a"], 10.0))
        db.add(order("SCOPE-B-0001", users["cashier_b"], 20.0))
        db.commit()

        tokens = TokenService(settings.auth_secret, settings.auth_expire_hours)
        return {
            "store_id": store.id,
            "users": {k: u.id for k, u in users.items()},
            "tokens": {
                k: tokens.issue(u.id, tenant.id, u.password_hash)
                for k, u in users.items()
            },
        }


def main() -> int:
    """执行全部断言，任一失败即以非零码退出。"""
    fx = build_fixtures()
    client = TestClient(app)

    def headers(role: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {fx['tokens'][role]}",
            "X-Store-Id": str(fx["store_id"]),
        }

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append((name, bool(condition), detail))

    # 1. 收银员列表：仅本人订单，scope=own
    r = client.get("/api/orders", headers=headers("cashier_a"))
    body = r.json()
    check("收银员列表 200", r.status_code == 200, str(r.status_code))
    check("收银员只见本人 1 单", body.get("total") == 1, str(body.get("total")))
    check(
        "收银员列表均为本人单",
        [i["order_no"] for i in body.get("items", [])] == ["SCOPE-A-0001"],
        str([i.get("order_no") for i in body.get("items", [])]),
    )
    check("收银员 scope=own", body.get("scope") == "own", str(body.get("scope")))
    check(
        "响应补齐收银员姓名",
        body.get("items", [{}])[0].get("cashier_name") == "收银员甲",
        str(body.get("items", [{}])[0].get("cashier_name")),
    )

    # 2. 收银员详情：本人可读、他人 404
    r = client.get("/api/orders/SCOPE-A-0001", headers=headers("cashier_a"))
    check("收银员读本人单 200", r.status_code == 200, str(r.status_code))
    r = client.get("/api/orders/SCOPE-B-0001", headers=headers("cashier_a"))
    check("收银员读他人单 404", r.status_code == 404, str(r.status_code))

    # 3. 退款记录同样受控
    r = client.get("/api/orders/SCOPE-B-0001/refunds", headers=headers("cashier_a"))
    check("收银员读他人退款记录 404", r.status_code == 404, str(r.status_code))

    # 4. 店长列表：全店可见，scope=all
    r = client.get("/api/orders", headers=headers("manager"))
    body = r.json()
    check("店长列表 200", r.status_code == 200, str(r.status_code))
    check("店长可见全店 2 单", body.get("total") == 2, str(body.get("total")))
    check("店长 scope=all", body.get("scope") == "all", str(body.get("scope")))
    r = client.get("/api/orders/SCOPE-B-0001", headers=headers("manager"))
    check("店长读他人单 200", r.status_code == 200, str(r.status_code))

    # 5. 收银员上传时 cashier_id 不得伪造为他人
    payload = {
        "order_no": "SCOPE-A-0002",
        "cashier_id": fx["users"]["cashier_b"],
        "status": "paid",
        "total_amount": 5.0,
        "pay_details": json.dumps({"现金": 5.0}, ensure_ascii=False),
        "items": [{"name": "回归商品", "qty": 1, "unit_price": 5.0, "amount": 5.0}],
    }
    r = client.post("/api/orders", json=payload, headers=headers("cashier_a"))
    check("收银员上传 201", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
    if r.status_code == 201:
        check(
            "上传归属强制为本人",
            str(r.json().get("cashier_id")) == str(fx["users"]["cashier_a"]),
            str(r.json().get("cashier_id")),
        )

    # 6. 幂等通道不得读取他人订单
    r = client.post(
        "/api/orders",
        json={**payload, "order_no": "SCOPE-B-0001"},
        headers=headers("cashier_a"),
    )
    check("收银员幂等他人单 403", r.status_code == 403, str(r.status_code))

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if not ok else ""))
    print(f"\n{len(checks) - len(failed)}/{len(checks)} PASS")
    # Windows 下 SQLite 文件需先释放连接池才能删除临时目录
    engine.dispose()
    _TMP.cleanup()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
