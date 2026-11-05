"""会员建档请求模型。"""

from pydantic import BaseModel, Field


class MemberCreate(BaseModel):
    """新增会员请求体：手机号唯一，姓名可选。"""

    # 手机号（唯一标识，必填）
    mobile: str = Field(..., min_length=6, max_length=20)
    # 会员姓名
    name: str | None = Field(None, max_length=50)
    # 等级：normal=普通，silver=银卡，gold=金卡
    level: str = Field("normal", pattern="^(normal|silver|gold)$")
    # 预留门店 ID（多店扩展）
    store_id: int = 1
