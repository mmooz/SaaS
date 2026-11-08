"""会员流水输出模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.snowflake_id import SnowflakeId


class MemberTransactionOut(BaseModel):
    """会员流水响应体：展示充值/消费/积分变动明细。"""

    model_config = ConfigDict(from_attributes=True)

    # 流水 ID
    id: SnowflakeId
    # 关联会员 ID
    member_id: SnowflakeId
    # 发生门店 ID（会员库租户共享后，流水仍需区分门店）
    store_id: SnowflakeId
    # 类型：recharge/consume/refund/points
    type: str
    # 金额变动
    amount: float
    # 积分变动
    points: int
    # 操作人用户 ID
    operator_id: SnowflakeId | None
    # 流水时间
    created_at: datetime
    # Q24 流水级标注：门店归属是否可信（历史流水为 False）。
    # 可选新增字段、默认 True，向后兼容；由 API 依据 MEMBER_TX_STORE_RELIABLE_SINCE
    # 显式覆盖，不改库内历史数据、不新增 DB 列、不新增迁移。
    store_attribution_reliable: bool = True
