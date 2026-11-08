"""门店数据隔离回归检查（独立运行，使用临时 SQLite，不触碰生产库）。

验证「功能只管理本店数据」：分类 / 商品 / 会员三类资源，店长仅能读写当前门店
（X-Store-Id）的数据，跨门店既不可见也不可改，新增/上传自动归属当前门店。

运行：``backend/.venv/Scripts/python.exe backend/tools/check_store_isolation.py``
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# 必须在导入任何 app.* 之前注入：config 单例与 database engine 都在导入期读取配置
_TMP = tempfile.TemporaryDirectory(prefix="pos-store-iso-", ignore_cleanup_errors=True)
_DB_FILE = (Path(_TMP.name) / "check.db").as_posix()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_FILE}"
os.environ["AUTH_SECRET"] = "store-isolation-regression-" + "x" * 40
os.environ["AUTO_CREATE_TABLES"] = "false"
os.environ["AUTO_SEED_USERS"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Category,
    Member,
    Product,
    Store,
    Tenant,
    User,
    UserStore,
)
from app.services.password_hasher import PasswordHasher  # noqa: E402
from app.services.token_service import TokenService  # noqa: E402


def build_fixtures():
    """建表并写入两门店、各一名店长，以及分别归属两店的分类/商品/会员。"""
    Base.metadata.create_all(bind=engine)
    hasher = PasswordHasher()
    with SessionLocal() as db:
        tenant = Tenant(name="隔离租户", code="store-iso-check", enabled=True)
        db.add(tenant)
        db.flush()
        store_a = Store(tenant_id=tenant.id, name="门店A", enabled=True)
        store_b = Store(tenant_id=tenant.id, name="门店B", enabled=True)
        db.add_all([store_a, store_b])
        db.flush()

        mgr_a = User(
            tenant_id=tenant.id, username="iso_mgr_a",
            password_hash=hasher.hash("Regress!on#A1"), name="店长甲",
            role="manager", enabled=True, must_change_password=False,
        )
        mgr_b = User(
            tenant_id=tenant.id, username="iso_mgr_b",
            password_hash=hasher.hash("Regress!on#B2"), name="店长乙",
            role="manager", enabled=True, must_change_password=False,
        )
        db.add_all([mgr_a, mgr_b])
        db.flush()
        db.add_all([
            UserStore(user_id=mgr_a.id, store_id=store_a.id),
            UserStore(user_id=mgr_b.id, store_id=store_b.id),
        ])

        cat_a = Category(name="A蔬菜", tenant_id=tenant.id, store_id=store_a.id, sort=0)
        cat_b = Category(name="B蔬菜", tenant_id=tenant.id, store_id=store_b.id, sort=0)
        db.add_all([cat_a, cat_b])
        db.flush()

        prod_a = Product(
            barcode="A001", name="A青菜", tenant_id=tenant.id, store_id=store_a.id,
            category_id=cat_a.id, pricing_mode="weigh", unit="kg", price=3.0,
        )
        prod_b = Product(
            barcode="B001", name="B青菜", tenant_id=tenant.id, store_id=store_b.id,
            category_id=cat_b.id, pricing_mode="weigh", unit="kg", price=4.0,
        )
        db.add_all([prod_a, prod_b])

        mem_a = Member(mobile="13800000001", name="会员甲", tenant_id=tenant.id, store_id=store_a.id)
        mem_b = Member(mobile="13800000002", name="会员乙", tenant_id=tenant.id, store_id=store_b.id)
        db.add_all([mem_a, mem_b])
        db.commit()

        tokens = TokenService(settings_auth_secret(), settings_expire())
        return {
            "tenant_id": tenant.id,
            "store_a": store_a.id,
            "store_b": store_b.id,
            "cat_a": cat_a.id,
            "cat_b": cat_b.id,
            "prod_a": prod_a.id,
            "prod_b": prod_b.id,
            "mem_a": mem_a.id,
            "mem_b": mem_b.id,
            "token_a": tokens.issue(mgr_a.id, tenant.id, mgr_a.password_hash),
            "token_b": tokens.issue(mgr_b.id, tenant.id, mgr_b.password_hash),
        }


def settings_auth_secret() -> str:
    from app.config import settings
    return settings.auth_secret


def settings_expire() -> int:
    from app.config import settings
    return settings.auth_expire_hours


def main() -> int:
    fx = build_fixtures()
    client = TestClient(app)

    def hdr_a() -> dict[str, str]:
        return {"Authorization": f"Bearer {fx['token_a']}", "X-Store-Id": str(fx["store_a"])}

    def hdr_b() -> dict[str, str]:
        return {"Authorization": f"Bearer {fx['token_b']}", "X-Store-Id": str(fx["store_b"])}

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append((name, bool(condition), detail))

    # --- 分类 ---
    r = client.get("/api/categories/tree", headers=hdr_a())
    check("A店长看分类树 200", r.status_code == 200, str(r.status_code))
    check("A店长只见A店分类", r.status_code == 200 and len(r.json()) == 1 and r.json()[0]["name"] == "A蔬菜",
          str([c.get("name") for c in r.json()]))
    # 用 B 店分类做父级，A 店长新建子分类应 404（父级不在本店）
    r = client.post("/api/categories", json={"name": "A叶菜", "parent_id": fx["cat_b"]}, headers=hdr_a())
    check("A店长用B店父分类建类 404", r.status_code == 404, str(r.status_code))
    # 在 A 店正常建类
    r = client.post("/api/categories", json={"name": "A水果"}, headers=hdr_a())
    check("A店长建类 201", r.status_code == 201, f"{r.status_code} {r.text[:120]}")
    if r.status_code == 201:
        check("新建分类归属A店", r.json().get("store_id") == fx["store_a"], str(r.json().get("store_id")))
    # 改/删 B 店分类应 404
    r = client.put(f"/api/categories/{fx['cat_b']}", json={"name": "X"}, headers=hdr_a())
    check("A店长改B店分类 404", r.status_code == 404, str(r.status_code))
    r = client.delete(f"/api/categories/{fx['cat_b']}", headers=hdr_a())
    check("A店长删B店分类 404", r.status_code == 404, str(r.status_code))

    # --- 商品 ---
    r = client.get("/api/products", headers=hdr_a())
    check("A店长列商品 200", r.status_code == 200, str(r.status_code))
    check("A店长只见A店商品", r.status_code == 200 and r.json().get("total") == 1 and r.json()["items"][0]["name"] == "A青菜",
          str(r.json().get("total")))
    r = client.get(f"/api/products/{fx['prod_b']}", headers=hdr_a())
    check("A店长看B店商品详情 404", r.status_code == 404, str(r.status_code))
    r = client.put(f"/api/products/{fx['prod_b']}", json={"price": 9.9}, headers=hdr_a())
    check("A店长改B店商品 404", r.status_code == 404, str(r.status_code))
    r = client.delete(f"/api/products/{fx['prod_b']}", headers=hdr_a())
    check("A店长删B店商品 404", r.status_code == 404, str(r.status_code))
    # A 店长建商品自动归属 A 店
    r = client.post(
        "/api/products",
        json={"barcode": "A002", "name": "A苹果", "pricing_mode": "count", "unit": "个", "price": 5.0, "stock": 10},
        headers=hdr_a(),
    )
    check("A店长建商品 201", r.status_code == 201, f"{r.status_code} {r.text[:120]}")
    if r.status_code == 201:
        check("新建商品归属A店", r.json().get("store_id") == fx["store_a"], str(r.json().get("store_id")))

    # --- 会员：列表仅本店，但按手机号查询仍为租户级（跨店可用）---
    r = client.get("/api/members", headers=hdr_a())
    check("A店长列会员 200", r.status_code == 200, str(r.status_code))
    check("A店长只见A店会员", r.status_code == 200 and r.json().get("total") == 1 and r.json()["items"][0]["name"] == "会员甲",
          str(r.json().get("total")))
    r = client.get("/api/members?keyword=会员乙", headers=hdr_a())
    check("A店长按名搜B店会员为空", r.status_code == 200 and r.json().get("total") == 0, str(r.json().get("total")))
    # 按手机号查会员跨店仍可用（收银端刷卡场景）
    r = client.get("/api/members/13800000002", headers=hdr_a())
    check("A店长按手机号查B店会员 200", r.status_code == 200, str(r.status_code))
    # 列表接口加 X-Store-Id=B 时只应见 B 店会员
    r = client.get("/api/members", headers=hdr_b())
    check("B店长只见B店会员", r.status_code == 200 and r.json().get("total") == 1 and r.json()["items"][0]["name"] == "会员乙",
          str(r.json().get("total")))

    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if not ok else ""))
    print(f"\n{len(checks) - len(failed)}/{len(checks)} PASS")
    engine.dispose()
    _TMP.cleanup()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
