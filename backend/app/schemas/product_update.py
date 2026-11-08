"""商品更新请求模型。"""

from pydantic import BaseModel, Field

from app.schemas.unit_spec import UnitSpec


class ProductUpdate(BaseModel):
    """更新商品请求体：全部字段可选，仅更新传入的字段。"""

    # 商品条码
    barcode: str | None = Field(None, min_length=1, max_length=32)
    # 商品名称
    name: str | None = Field(None, min_length=1, max_length=80)
    # 拼音码
    pinyin: str | None = Field(None, max_length=50)
    # 所属分类 ID
    category_id: int | None = None
    # 计价方式
    pricing_mode: str | None = Field(None, pattern="^(weigh|count)$")
    # 计量单位
    unit: str | None = Field(None, max_length=10)
    # 零售单价
    price: float | None = Field(None, ge=0)
    # 会员单价
    member_price: float | None = Field(None, ge=0)
    # 进价
    cost_price: float | None = Field(None, ge=0)
    # 保质期天数
    shelf_life_days: int | None = Field(None, ge=0)
    # 是否默认打印价格标签
    label_enabled: bool | None = None
    # 当前库存
    stock: float | None = None
    # 安全库存
    safety_stock: float | None = None
    # 是否启用
    enabled: bool | None = None
    # 多单位换算列表：完整可售单位（含 factor=1 的基础单位）。传入会整体覆盖既有配置。
    units: list[UnitSpec] | None = None
