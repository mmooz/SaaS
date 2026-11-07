"""应用配置模块：通过环境变量读取配置，支持 SQLite/PostgreSQL 切换。"""

from pydantic_settings import BaseSettings, SettingsConfigDict

# 签名密钥最小长度：低于该值视为弱密钥，应用启动校验时拒绝
MIN_AUTH_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """应用全局配置类。"""

    # 应用名称与版本
    app_name: str = "鲜衡云 API"
    app_version: str = "0.1.0"

    # 数据库连接串：默认 SQLite，切换 PostgreSQL 时改为
    # postgresql+psycopg2://user:password@host:port/dbname
    database_url: str = "sqlite:///./pos.db"

    # 是否在启动时自动建表（开发期用；生产环境使用 Alembic 迁移）
    # 纵深防御：默认关闭，避免 create_all 与 Alembic 并存导致 schema 失控
    auto_create_tables: bool = False

    # 是否在启动时写入默认登录账号（仅 users 表为空时生效，开发期便利）
    # 纵深防御：默认关闭，避免自动写入弱口令演示账号
    auto_seed_users: bool = False

    # 登录令牌签名密钥：必须由环境变量 AUTH_SECRET 注入，不提供硬编码默认值
    auth_secret: str = ""
    # 登录令牌有效期（小时）
    auth_expire_hours: int = 12

    # 雪花 ID 机器位与数据中心位（0-31，多实例部署时需各不相同）
    snowflake_worker_id: int = 1
    snowflake_datacenter_id: int = 1

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# 单例配置对象（类本身与单例均可正常导入，安全校验由应用入口显式触发）
settings = Settings()


def validate_startup_security() -> None:
    """应用启动前强校验安全配置：签名密钥必须由环境注入且长度足够。

    校验只在应用入口显式调用，保证 ``Settings`` 类与单例可正常导入
    （Alembic 等工具无需 AUTH_SECRET 也能读取配置），但任何加载 FastAPI
    应用的路径（uvicorn / TestClient / gunicorn）都会先经过本校验。

    :raises RuntimeError: 未提供 AUTH_SECRET、密钥为空白或密钥长度不足
    """
    secret = settings.auth_secret
    if not secret or not secret.strip():
        raise RuntimeError(
            "服务启动失败：未配置 AUTH_SECRET。请在 backend/.env 中设置至少 32 位随机密钥，"
            '可用 python -c "import secrets; print(secrets.token_urlsafe(48))" 生成。'
        )
    if len(secret) < MIN_AUTH_SECRET_LENGTH:
        raise RuntimeError(
            f"服务启动失败：AUTH_SECRET 长度不足（当前 {len(secret)} 位，"
            f"要求至少 {MIN_AUTH_SECRET_LENGTH} 位），请更换为随机长密钥。"
        )
