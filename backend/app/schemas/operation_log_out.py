"""操作日志输出模型。"""

from datetime import datetime

from pydantic import BaseModel


class OperationLogOut(BaseModel):
    """操作日志响应体：含操作人账号、姓名与角色。"""

    # 日志 ID
    id: int
    # 操作人账号（无关联用户时为空）
    operator: str | None = None
    # 操作人姓名
    operator_name: str | None = None
    # 操作人角色
    role: str | None = None
    # 操作动作
    action: str
    # 操作详情
    detail: str | None = None
    # 操作时间
    created_at: datetime
