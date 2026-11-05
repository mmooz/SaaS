"""订单明细输出模型：在创建模型基础上补充主键与退货标记。"""

from pydantic import ConfigDict

from app.schemas.order_item_create import OrderItemCreate
from app.schemas.snowflake_id import SnowflakeId


class OrderItemOut(OrderItemCreate):
    """订单明细响应体：含明细主键与是否已退货。"""

    model_config = ConfigDict(from_attributes=True)

    # 明细主键（退款时用于定位商品行）
    id: SnowflakeId
    # 商品 ID（输出为字符串，避免前端精度丢失）
    product_id: SnowflakeId | None = None
    # 是否已退货（该行已存在于退款明细中）
    refunded: bool = False
