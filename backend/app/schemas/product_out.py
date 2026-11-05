"""商品输出模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.snowflake_id import SnowflakeId


class ProductOut(BaseModel):
    """商品响应体：输出全部档案字段与分类名称。"""

    model_config = ConfigDict(from_attributes=True)

    # 商品 ID
    id: SnowflakeId
    # 商品条码
    barcode: str
    # 商品名称
    name: str
    # 拼音码
    pinyin: str | None
    # 所属分类 ID
    category_id: SnowflakeId | None
    # 分类名称（联表查询时填充）
    category_name: str | None = None
    # 计价方式
    pricing_mode: str
    # 计量单位
    unit: str
    # 零售单价
    price: float
    # 会员单价
    member_price: float | None
    # 进价
    cost_price: float | None
    # 保质期天数
    shelf_life_days: int | None
    # 是否默认打印价格标签
    label_enabled: bool
    # 当前库存
    stock: float
    # 安全库存
    safety_stock: float
    # 是否启用
    enabled: bool
    # 预留门店 ID
    store_id: int
    # 创建与更新时间
    created_at: datetime
    updated_at: datetime
