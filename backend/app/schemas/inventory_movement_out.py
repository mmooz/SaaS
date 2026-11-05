"""库存变动流水输出模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.snowflake_id import SnowflakeId


class InventoryMovementOut(BaseModel):
    """库存流水响应体：含商品名称便于展示。"""

    model_config = ConfigDict(from_attributes=True)

    # 流水 ID
    id: SnowflakeId
    # 商品 ID
    product_id: SnowflakeId
    # 商品名称（查询时填充）
    product_name: str | None = None
    # 类型：inbound/sale/stocktake/breakage
    type: str
    # 变动件数
    qty: float
    # 变动重量 kg
    weight_kg: float | None
    # 来源单据 ID
    ref_id: SnowflakeId | None
    # 操作人用户 ID
    operator_id: SnowflakeId | None
    # 变动时间
    created_at: datetime
