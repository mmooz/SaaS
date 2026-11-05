"""订单明细创建请求模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    """上传订单的明细行（同时用于订单输出时的明细展示）。"""

    model_config = ConfigDict(from_attributes=True)

    # 明细主键（离线收银端生成的雪花 ID，联网补传时保留以支持后续退货）
    id: int | None = None
    # 下单时间（离线补传时保留原始时间）
    created_at: datetime | None = None
    # 商品 ID（可空，商品删除后保留名称快照）
    product_id: int | None = None
    # 商品名称
    name: str = Field(..., min_length=1, max_length=80)
    # 数量（按件商品）
    qty: int = Field(1, ge=1)
    # 重量 kg（称重商品）
    weight_kg: float | None = Field(None, ge=0)
    # 成交单价
    unit_price: float = Field(0, ge=0)
    # 行金额
    amount: float = Field(0, ge=0)
    # 是否称重商品
    is_weighted: bool = False
    # 是否已打印价格标签
    label_printed: bool = False
