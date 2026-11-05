"""接班请求模型：收银员开班时填写现金底金。"""

from pydantic import BaseModel, Field


class ShiftOpen(BaseModel):
    """接班请求体。"""

    # 收银员用户 ID
    cashier_id: int
    # 现金底金
    base_cash: float = Field(0, ge=0)
