"""数据库模块：创建 SQLAlchemy 引擎、会话与模型基类。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy 模型基类：所有 ORM 模型继承此类。"""


# SQLite 需要 check_same_thread=False 以支持多线程访问
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

# 数据库引擎
engine = create_engine(settings.database_url, connect_args=connect_args)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI 依赖：提供数据库会话，请求结束后关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
