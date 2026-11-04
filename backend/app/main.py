"""FastAPI 应用入口：创建应用、注册路由与启动初始化。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import Base, engine
from app import models  # 导入模型模块，确保建表时注册所有表


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时按配置自动建表（开发期便利，生产用 Alembic）。"""
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    yield


# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)


@app.get("/api/health")
def health_check():
    """健康检查接口：确认服务与数据库可用。"""
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}
