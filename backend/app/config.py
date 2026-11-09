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

    # 是否在启动时自动执行 Alembic 迁移（生产环境默认开启，自愈缺列问题）
    # 与 auto_create_tables 职责分离：migrate 走 Alembic（真实环境权威 schema 来源），
    # create_all 仅开发期可选开关。迁移幂等：对已达 head 的库为安全空操作。
    auto_migrate: bool = True

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

    # ---- Q24 会员流水历史门店归属分界（拍板 2：不重算历史、零 DDL）----
    # 取 3f9a1c7b2d55 迁移执行 / 上线时间，ISO 8601（建议带 Z，按 naive UTC 比较）。
    # 留空 = 未配置，安全回退为「全部历史流水标注门店归属不可信」；
    # 该配置只影响报表标注，不改库内数据、不新增列、不新增迁移。
    member_tx_store_reliable_since: str = ""

    # ---- R20 临时资金管控（Q06 完成后由 B4 统一解除，非永久业务逻辑）----
    # 数值待产品确认：确认后只改 .env / 配置中心，不改代码、不发版；
    # 前端文案一律不写死具体数字（只说「限额 / 时限」）。
    # 在线储值支付开关：默认关闭。⚠️ 警告：Q06 结算接口完成前**严禁设为 true**，
    # 否则「有订单无扣款」的「不扣先返」套利面重新敞开（见设计 A.3.5）。
    online_stored_value_payment_enabled: bool = False
    # 离线订单补传金额上限（元）
    offline_order_max_amount: float = 200.0
    # 离线订单发生时间距今时限（小时）
    offline_order_max_age_hours: float = 2.0

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
