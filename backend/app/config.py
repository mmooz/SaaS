"""应用配置模块：通过环境变量读取配置，支持 SQLite/PostgreSQL 切换。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置类。"""

    # 应用名称与版本
    app_name: str = "鲜衡云 API"
    app_version: str = "0.1.0"

    # 数据库连接串：默认 SQLite，切换 PostgreSQL 时改为
    # postgresql+psycopg2://user:password@host:port/dbname
    database_url: str = "sqlite:///./pos.db"

    # 是否在启动时自动建表（开发期用；生产环境使用 Alembic 迁移）
    auto_create_tables: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# 单例配置对象
settings = Settings()
