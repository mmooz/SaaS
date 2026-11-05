"""会员资料更新请求模型。"""

from pydantic import BaseModel, Field


class MemberUpdate(BaseModel):
    """更新会员资料请求体：仅允许修改姓名与等级。"""

    # 会员姓名（不传则保持原值）
    name: str | None = Field(None, max_length=50)
    # 等级：normal=普通，silver=银卡，gold=金卡
    level: str | None = Field(None, pattern="^(normal|silver|gold)$")
