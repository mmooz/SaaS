"""重置密码响应模型。"""

from pydantic import BaseModel

from app.schemas.user_admin_out import UserAdminOut


class UserPasswordResetOut(BaseModel):
    """重置密码结果：用户信息 + 一次性返回的随机临时密码。

    R8：临时密码只在本次响应中返回，服务端不落明文、不写日志、不提供查询接口。
    """

    # 被重置的用户信息（不含口令字段）
    user: UserAdminOut
    # 一次性随机临时密码（仅本次响应可见，请立即转交本人）
    temporary_password: str
