"""冒烟测试：验证收银端数据加载相关接口在「已应用迁移」的临时库上是否正常。

用于隔离两类问题：
  A. 代码 bug（接口本身报错）→ 即便迁移就绪也会 500；
  B. 迁移未跑（真实库缺 units_json 列）→ 接口 500。

本脚本建临时库并执行 alembic upgrade head（覆盖 B 的前提），只排查 A。
不触碰真实库。
"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(".").resolve()
sys.path.insert(0, str(BACKEND))

os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.mkdtemp()) / 'smoke.db'}"
os.environ["AUTH_SECRET"] = "smoke-load-" + "x" * 48
os.environ["AUTO_CREATE_TABLES"] = "false"
os.environ["AUTO_SEED_USERS"] = "false"

from alembic import command
from alembic.config import Config

cfg = Config(str(BACKEND / "alembic.ini"))
cfg.set_main_option("script_location", str(BACKEND / "alembic"))
command.upgrade(cfg, "head")

from app.database import Base, SessionLocal, engine
from app.models import Store, Tenant, User, UserStore
from app.services.password_hasher import PasswordHasher
from app.services.token_service import TokenService
from app.config import settings
from fastapi.testclient import TestClient
from app.main import app

h = PasswordHasher()
with SessionLocal() as db:
    t = Tenant(name="t", code="tc", enabled=True)
    db.add(t)
    db.flush()
    s = Store(tenant_id=t.id, name="s", enabled=True)
    db.add(s)
    db.flush()
    u = User(
        tenant_id=t.id,
        username="smoke",
        password_hash=h.hash("Regress!on#M9"),
        name="m",
        role="manager",
        enabled=True,
        must_change_password=False,
    )
    db.add(u)
    db.flush()
    db.add(UserStore(user_id=u.id, store_id=s.id))
    db.commit()
    tid, uid, sid = t.id, u.id, s.id

ts = TokenService(settings.auth_secret, settings.auth_expire_hours)
token = ts.issue(uid, tid, u.password_hash)
H = {"Authorization": f"Bearer {token}", "X-Store-Id": str(sid)}


def hit(method, path, **kw):
    fn = getattr(client := TestClient(app), method)
    r = fn(path, headers=H, **kw)
    return r.status_code, (r.json() if r.status_code < 500 else r.text[:240])


client = TestClient(app)
paths = [
    ("get", "/api/sync/products"),
    ("get", "/api/reports/daily?start=2026-01-01&end=2026-01-01&mode=day"),
    ("get", "/api/reports/profit?start=2026-01-01&end=2026-01-01"),
    ("get", "/api/inventory/alerts"),
    ("get", "/api/orders?page=1&pageSize=6"),
]
ok = True
for m, p in paths:
    code, body = hit(m, p)
    flag = "OK" if code < 400 else "FAIL"
    if code >= 400:
        ok = False
    print(f"[{flag}] {m.upper():4} {p} -> {code}  {body if code >= 400 else ''}")
print("SMOKE", "ALL_OK" if ok else "HAS_FAILURE")
sys.exit(0 if ok else 1)
