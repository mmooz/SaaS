"""同步下发的会员档案模型（Q19）。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.snowflake_id import SnowflakeId


class MemberSyncOut(BaseModel):
    """收银端同步下发的会员档案：仅身份识别与会员价所需字段。

    按 tenant_id 过滤后下发，**刻意不包含** balance / total_spent / points
    等资金与积分字段，也不包含任何口令类字段，避免其它租户数据或敏感信息
    落到 POS 本地缓存。Q06（储值结算原子化）完成前，本地会员缓存只允许用于
    身份识别与会员价，禁止任何离线余额扣减、离线储值支付或写 balance 逻辑。
    """

    model_config = ConfigDict(from_attributes=True)

    # 会员 ID
    id: SnowflakeId
    # 手机号（离线按此识别会员）
    mobile: str
    # 姓名
    name: str | None
    # 等级（会员价与展示用）
    level: str
    # 更新时间（前端增量游标使用）
    updated_at: datetime
