"""商品销售排行行模型。"""

from pydantic import BaseModel


class ReportRankRow(BaseModel):
    """商品排行行：销量、销售额与占比。"""

    # 商品 ID（快照明细可能为空）
    product_id: int | None = None
    # 商品名称
    name: str
    # 分类名称
    category: str
    # 销量（称重商品为 kg，按件商品为件数）
    qty: float = 0
    # 计量单位
    unit: str = "kg"
    # 是否称重商品
    is_weighted: bool = False
    # 销售额（元）
    amount: float = 0
    # 销售额占比（百分比 0-100）
    ratio: float = 0
