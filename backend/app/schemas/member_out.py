"""会员输出模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MemberOut(BaseModel):
    """会员响应体：输出档案与积分/储值余额。"""

    model_config = ConfigDict(from_attributes=True)

    # 会员 ID
    id: int
    # 手机号
    mobile: str
    # 姓名
    name: str | None
    # 等级
    level: str
    # 积分余额
    points: int
    # 储值余额（元）
    balance: float
    # 累计消费金额
    total_spent: float
    # 预留门店 ID
    store_id: int
    # 创建与更新时间
    created_at: datetime
    updated_at: datetime
