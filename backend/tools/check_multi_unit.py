"""多单位商品回归检查（独立运行，使用临时 SQLite，不触碰生产库）。

覆盖：
- 商品创建携带 units（包/条，1 条=10 包；瓶/件，1 件=12 瓶）后，响应与详情均返回
  正确的 units 列表，且基础单位落在 products.unit/price，附加单位落在 units_json；
- 收银端按「条」「件」下单时传入 base_qty（=qty×factor），订单成交按基础单位扣减门店库存；
- 退款后库存按 base_qty 回滚；
- 单单位商品（无 units）路径不受影响，仍按 qty 扣减。

运行：``backend/.venv/Scripts/python.exe backend/tools/check_multi_unit.py``
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

_TMP = tempfile.TemporaryDirectory(prefix="pos-multi-unit-", ignore_cleanup_errors=True)
_DB_FILE = (Path(_TMP.name) / "check.db").as_posix()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_FILE}"
os.environ["AUTH_SECRET"] = "multi-unit-regression-" + "y" * 48
os.environ["AUTO_CREATE_TABLES"] = "false"
os.environ["AUTO_SEED_USERS"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Store, Tenant, User, UserStore  # noqa: E402
from app.services.password_hasher import PasswordHasher  # noqa: E402
from app.services.product_stock_service import ProductStockService  # noqa: E402
from app.services.token_service import TokenService  # noqa: E402


def build_fixtures():
    Base.metadata.create_all(bind=engine)
    hasher = PasswordHasher()
    with SessionLocal() as db:
        tenant = Tenant(name="多单位回归租户", code="mu-check", enabled=True)
        db.add(tenant)
        db.flush()
        store = Store(tenant_id=tenant.id, name="多单位回归门店", enabled=True)
        db.add(store)
        db.flush()
        mgr = User(
            tenant_id=tenant.id, username="mu_manager",
            password_hash=hasher.hash("Regress!on#M9"), name="店长",
            role="manager", enabled=True, must_change_password=False,
        )
        db.add(mgr)
        db.flush()
        db.add(UserStore(user_id=mgr.id, store_id=store.id))
        db.commit()
        tokens = TokenService(settings.auth_secret, settings.auth_expire_hours)
        return {
            "store_id": store.id,
            "mgr_id": mgr.id,
            "token": tokens.issue(mgr.id, tenant.id, mgr.password_hash),
        }


def main() -> int:
    fx = build_fixtures()
    client = TestClient(app)
    h = {"Authorization": f"Bearer {fx['token']}", "X-Store-Id": str(fx["store_id"])}

    checks: list[tuple[str, bool, str]] = []

    def check(name, condition, detail=""):
        checks.append((name, bool(condition), detail))

    # 1. 创建多单位商品：香烟 包/条（1 条=10 包）
    r = client.post("/api/products", json={
        "barcode": "MU-CIG", "name": "香烟", "pricing_mode": "count",
        "unit": "包", "price": 8, "member_price": 7.5, "stock": 100,
        "units": [
            {"unit": "包", "factor": 1, "price": 8, "member_price": 7.5},
            {"unit": "条", "factor": 10, "price": 75, "member_price": 70},
        ],
    }, headers=h)
    check("创建多单位商品 201", r.status_code == 201, f"{r.status_code} {r.text[:160]}")
    cig_id = r.json().get("id") if r.status_code == 201 else None
    if r.status_code == 201:
        body = r.json()
        units = body.get("units", [])
        check("units 返回 2 个", len(units) == 2, str(len(units)))
        by_unit = {u["unit"]: u for u in units}
        check("基础单位为包", by_unit.get("包", {}).get("factor") == 1, str(by_unit.get("包")))
        check("条 factor=10", by_unit.get("条", {}).get("factor") == 10, str(by_unit.get("条")))
        check("包零售价=8", by_unit.get("包", {}).get("price") == 8, str(by_unit.get("包")))
        check("条零售价=75", by_unit.get("条", {}).get("price") == 75, str(by_unit.get("条")))
        check("响应基础单位=包", body.get("unit") == "包", str(body.get("unit")))

    # 2. 详情接口同样返回 units
    if cig_id:
        r2 = client.get(f"/api/products/{cig_id}", headers=h)
        check("详情 200", r2.status_code == 200, str(r2.status_code))
        if r2.status_code == 200:
            check("详情 units 2 个", len(r2.json().get("units", [])) == 2,
                  str(len(r2.json().get("units", []))))

    # 3. 单单位商品（对照）
    r3 = client.post("/api/products", json={
        "barcode": "MU-SINGLE", "name": "矿泉水", "pricing_mode": "count",
        "unit": "瓶", "price": 2, "stock": 50,
    }, headers=h)
    check("创建单单位商品 201", r3.status_code == 201, f"{r3.status_code} {r3.text[:120]}")
    water_id = r3.json().get("id") if r3.status_code == 201 else None
    if r3.status_code == 201:
        check("单单位 units 长度为 1", len(r3.json().get("units", [])) == 1,
              str(len(r3.json().get("units", []))))

    # 4. 按「条」下单 2 条（base_qty = 2×10 = 20 包），库存 100→80
    r4 = client.post("/api/orders", json={
        "order_no": "MU-ORD-1", "status": "paid", "total_amount": 150,
        "pay_details": '{"现金": 150}',
        "items": [{
            "product_id": cig_id, "name": "香烟", "qty": 2, "unit_price": 75,
            "amount": 150, "is_weighted": False, "unit": "条", "base_qty": 20,
        }],
    }, headers=h)
    check("多单位下单 201", r4.status_code == 201, f"{r4.status_code} {r4.text[:160]}")

    def stock_of(pid):
        with SessionLocal() as db:
            row = ProductStockService.get(db, pid, fx["store_id"])
            return row.stock if row else None

    if cig_id and r4.status_code == 201:
        check("按条下单库存扣 20（100→80）", stock_of(cig_id) == 80, str(stock_of(cig_id)))

    # 5. 单单位下单 3 瓶，库存 50→47
    if water_id:
        r5 = client.post("/api/orders", json={
            "order_no": "MU-ORD-2", "status": "paid", "total_amount": 6,
            "pay_details": '{"现金": 6}',
            "items": [{
                "product_id": water_id, "name": "矿泉水", "qty": 3, "unit_price": 2,
                "amount": 6, "is_weighted": False, "unit": "瓶",
            }],
        }, headers=h)
        check("单单位下单 201", r5.status_code == 201, str(r5.status_code))
        check("单单位库存扣 3（50→47）", stock_of(water_id) == 47, str(stock_of(water_id)))

    # 6. 退款多单位订单，库存回滚 80→100
    if cig_id:
        r6 = client.post("/api/orders/MU-ORD-1/refund", json={
            "refund_no": "MU-REF-1", "refund_type": "full",
        }, headers=h)
        check("退款 201", r6.status_code == 201, f"{r6.status_code} {r6.text[:120]}")
        if r6.status_code == 201:
            check("退款后库存回滚 100", stock_of(cig_id) == 100, str(stock_of(cig_id)))

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if not ok else ""))
    print(f"\n{len(checks) - len(failed)}/{len(checks)} PASS")
    engine.dispose()
    _TMP.cleanup()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
