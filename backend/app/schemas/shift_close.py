"""交班请求模型：收银员交班时点钞金额。"""

from pydantic import BaseModel, Field


class ShiftClose(BaseModel):
    """交班请求体。"""

    # 实际点钞现金（可选，用于长短款核对）
    actual_cash: float | None = Field(None, ge=0)
    # 交班备注
    remark: str | None = Field(None, max_length=200)
