"""退款单输出模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.refund_item_out import RefundItemOut
from app.schemas.snowflake_id import SnowflakeId


class RefundOut(BaseModel):
    """退款单响应体：含退款明细。"""

    model_config = ConfigDict(from_attributes=True)

    # 退款单主键
    id: SnowflakeId
    # 退款单号
    refund_no: str
    # 原订单号
    order_no: str
    # 退款类型：full/item
    refund_type: str
    # 退款金额
    amount: float
    # 退款原因
    reason: str | None
    # 操作收银员用户 ID（Q17 语义变化：恒为服务端令牌用户 ID，不再取客户端传值）
    cashier_id: SnowflakeId | None
    # 店长授权人用户 ID（Q17 弃用：字段保留以兼容前端，恒为 null；
    # 拍板 1 不做「本人当班」判定与授权人，DB 列保留但 B3 不写入、不新增迁移）
    authorizer_id: SnowflakeId | None
    # 退款时间
    created_at: datetime
    # 退款明细
    items: list[RefundItemOut] = []
