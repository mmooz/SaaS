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

    # 是否在启动时写入默认登录账号（仅 users 表为空时生效，开发期便利）
    auto_seed_users: bool = True

    # 登录令牌签名密钥（生产环境务必通过环境变量覆盖）
    auth_secret: str = "xianheng-pos-dev-secret"
    # 登录令牌有效期（小时）
    auth_expire_hours: int = 12

    # 雪花 ID 机器位与数据中心位（0-31，多实例部署时需各不相同）
    snowflake_worker_id: int = 1
    snowflake_datacenter_id: int = 1

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# 单例配置对象
settings = Settings()
