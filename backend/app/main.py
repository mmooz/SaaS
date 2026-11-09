"""FastAPI 应用入口：创建应用、注册路由、CORS 与启动初始化。"""

import logging
import os
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    backups,
    categories,
    inventory,
    members,
    operation_logs,
    orders,
    products,
    promotions,
    reports,
    shifts,
    stores,
    sync,
    system_settings,
    tenants,
    users,
)
from app.config import settings, validate_startup_security
from app.database import Base, SessionLocal, engine
from app import models  # 导入模型模块，确保建表时注册所有表
from app.services.user_seeder import UserSeeder

# 模块日志器
logger = logging.getLogger(__name__)

# 应用加载即强校验安全配置：未注入 AUTH_SECRET 或密钥过短时直接拒绝启动
validate_startup_security()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时按配置自动执行 Alembic 迁移（自愈缺列），并可开发期建表/写默认账号。"""
    # 1) 自动迁移：幂等，确保真实库 schema 与模型一致（修复缺列导致的数据加载失败）
    if settings.auto_migrate:
        _run_alembic_upgrade_head()
    # 2) 开发期可选建表（仅 create_all 开关；生产由 Alembic 管理，职责分离）
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    # 3) 可选写入默认账号（仅 users 表为空时生效）
    if settings.auto_seed_users:
        with SessionLocal() as db:
            UserSeeder.seed(db)
    yield


def _run_alembic_upgrade_head() -> None:
    """执行 ``alembic upgrade head``，确保数据库 schema 与最新迁移一致。

    使用 backend/alembic.ini 配置，并把 ``script_location`` 设为 backend/alembic 目录、
    把 ``sqlalchemy.url`` 覆盖为当前 ``settings.database_url``，从而：

    - 无论进程工作目录在哪都能找到迁移脚本（路径由 ``__file__`` 相对推导）；
    - 迁移操作的是与 ORM 完全相同的数据库（避免迁移到错误的库）。

    幂等性：对已达 head 的库为空操作，安全可重复执行。迁移失败时打印清晰 ERROR
    日志并重新抛出，让启动失败可被察觉，而非静默吞掉。
    """
    # 由本文件位置推导 backend 根目录：backend/app/main.py -> backend/
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(backend_root, "alembic.ini")
    script_location = os.path.join(backend_root, "alembic")

    cfg = Config(ini_path)
    # 关键：显式指定脚本目录与数据库 url
    cfg.set_main_option("script_location", script_location)
    cfg.set_main_option("sqlalchemy.url", settings.database_url)

    logger.info(
        "自动迁移：开始执行 alembic upgrade head（database_url=%s）",
        settings.database_url,
    )
    try:
        command.upgrade(cfg, "head")
    except Exception as exc:  # noqa: BLE001 - 需捕获所有异常以暴露迁移失败原因
        logger.error(
            "自动迁移失败：alembic upgrade head 执行异常，服务将中止启动。"
            "请检查迁移脚本与数据库连接。错误=%s",
            exc,
        )
        raise
    logger.info("自动迁移：完成（alembic upgrade head 已执行）")


# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# 跨域配置：允许前后端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册业务路由
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(members.router)
app.include_router(promotions.router)
app.include_router(inventory.router)
app.include_router(reports.router)
app.include_router(shifts.router)
app.include_router(sync.router)
app.include_router(users.router)
app.include_router(operation_logs.router)
app.include_router(system_settings.router)
app.include_router(tenants.router)
app.include_router(stores.router)
app.include_router(backups.router)


@app.get("/api/health")
def health_check():
    """健康检查接口：确认服务与数据库可用。"""
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}
