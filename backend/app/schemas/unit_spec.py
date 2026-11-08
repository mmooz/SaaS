"""多单位换算规格模型。

一个商品可售多个单位（如香烟：包/条，1 条 = 10 包；啤酒：瓶/件，1 件 = 12 瓶）。
每个 UnitSpec 描述一个可售单位相对于「基础单位」的换算系数与独立价格。
- factor：该单位相当于基础单位的倍数，基础单位 factor=1；
- price / member_price：该单位自身的零售价 / 会员价（各单位独立定价）。
"""

from pydantic import BaseModel, Field


class UnitSpec(BaseModel):
    """单个可售单位规格。"""

    # 单位名称（如「包」「条」「瓶」「件」），最长 10 字符
    unit: str = Field(..., min_length=1, max_length=10)
    # 换算系数：相对基础单位的倍数，>=1
    factor: float = Field(..., gt=0)
    # 该单位零售单价
    price: float = Field(0, ge=0)
    # 该单位会员单价（可空）
    member_price: float | None = Field(None, ge=0)
