"""商品创建请求模型。"""

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """新增商品请求体。"""

    # 商品条码（唯一，含生鲜店内码）
    barcode: str = Field(..., min_length=1, max_length=32)
    # 商品名称
    name: str = Field(..., min_length=1, max_length=80)
    # 拼音码（快速检索）
    pinyin: str | None = Field(None, max_length=50)
    # 所属分类 ID
    category_id: int | None = None
    # 计价方式：weigh=按重量，count=按件
    pricing_mode: str = Field("weigh", pattern="^(weigh|count)$")
    # 计量单位
    unit: str = Field("kg", max_length=10)
    # 零售单价
    price: float = Field(0, ge=0)
    # 会员单价
    member_price: float | None = Field(None, ge=0)
    # 进价
    cost_price: float | None = Field(None, ge=0)
    # 保质期天数
    shelf_life_days: int | None = Field(None, ge=0)
    # 是否默认打印价格标签
    label_enabled: bool = True
    # 当前库存
    stock: float = 0
    # 安全库存
    safety_stock: float = 0
    # 是否启用
    enabled: bool = True
    # 预留门店 ID（多店扩展）
    store_id: int = 1
