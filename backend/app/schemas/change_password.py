"""R19 强制首次改密：修改本人密码的请求/响应模型。"""

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.password_policy import MIN_PASSWORD_LENGTH, ensure_strong_password


class ChangePasswordRequest(BaseModel):
    """修改本人密码请求体。

    ``old_password`` 不做强度校验：它的典型取值正是需要被换掉的弱口令 /
    临时口令；校验由服务端与库中哈希比对完成。
    """

    # 当前正在使用的密码（弱口令或临时口令均可）
    old_password: str = Field(..., min_length=1, max_length=64)
    # 新密码：必须满足统一强度策略，且不得与原密码相同
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=64)

    @field_validator("new_password")
    @classmethod
    def _check_strength(cls, value: str) -> str:
        """拒绝常见弱口令，与新建用户/重置密码/离线轮换共用同一规则。

        :param value: 新密码明文
        :return: 校验通过的原文
        :raises ValueError: 密码过短或属于弱口令
        """
        return ensure_strong_password(value, "新密码")

    @model_validator(mode="after")
    def _reject_same_password(self) -> "ChangePasswordRequest":
        """禁止「新密码 = 原密码」，否则强制改密可被原地绕过。

        :return: 校验通过的请求体
        :raises ValueError: 新旧密码相同
        """
        if self.old_password == self.new_password:
            raise ValueError("新密码不能与原密码相同")
        return self


class ChangePasswordOut(BaseModel):
    """改密结果：返回清除后的强制改密标记。"""

    # 恒为 False；客户端可据此确认改密已生效
    must_change_password: bool = False
