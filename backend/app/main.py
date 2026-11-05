"""FastAPI 应用入口：创建应用、注册路由、CORS 与启动初始化。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, categories, inventory, members, orders, products, promotions, reports, sync
from app.config import settings
from app.database import Base, SessionLocal, engine
from app import models  # 导入模型模块，确保建表时注册所有表
from app.services.user_seeder import UserSeeder


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时按配置自动建表并写入默认账号（开发期便利，生产用 Alembic）。"""
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    if settings.auto_seed_users:
        with SessionLocal() as db:
            UserSeeder.seed(db)
    yield


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
app.include_router(sync.router)


@app.get("/api/health")
def health_check():
    """健康检查接口：确认服务与数据库可用。"""
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}
