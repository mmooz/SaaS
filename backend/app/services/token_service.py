"""登录令牌服务：使用标准库 HMAC 签名的无状态令牌，无需额外依赖。"""

import base64
import hashlib
import hmac
import json
import time


class TokenService:
    """令牌服务：签发与校验携带用户 ID 与过期时间的签名令牌。"""

    def __init__(self, secret: str, expire_hours: int):
        """初始化令牌服务。

        :param secret: 签名密钥
        :param expire_hours: 令牌有效期（小时）
        """
        # 签名密钥（字节形式，供 HMAC 使用）
        self._secret = secret.encode("utf-8")
        # 令牌有效期（秒）
        self.expire_seconds = expire_hours * 3600

    def issue(self, user_id: int, tenant_id: int) -> str:
        """为用户签发令牌，载荷携带用户 ID 与所属租户 ID。

        :param user_id: 用户 ID
        :param tenant_id: 所属租户 ID
        :return: 令牌字符串（载荷.签名）
        """
        payload = {
            "uid": user_id,
            "tid": tenant_id,
            "exp": int(time.time()) + self.expire_seconds,
        }
        body = self._encode(json.dumps(payload, separators=(",", ":")))
        return f"{body}.{self._sign(body)}"

    def verify(self, token: str) -> dict | None:
        """校验令牌并取出用户 ID 与租户 ID。

        :param token: 待校验令牌
        :return: 校验通过返回 {"user_id":..., "tenant_id":...}；签名错误、格式错误或已过期返回 None
        """
        try:
            body, signature = token.split(".")
        except ValueError:
            return None
        # 先验签名再解析内容，防止伪造载荷
        if not hmac.compare_digest(self._sign(body), signature):
            return None
        try:
            payload = json.loads(self._decode(body))
        except (ValueError, TypeError):
            return None
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        user_id = payload.get("uid")
        tenant_id = payload.get("tid")
        if not isinstance(user_id, int) or not isinstance(tenant_id, int):
            return None
        return {"user_id": user_id, "tenant_id": tenant_id}

    def _sign(self, body: str) -> str:
        """对载荷做 HMAC-SHA256 签名。

        :param body: Base64URL 编码后的载荷
        :return: 十六进制签名串
        """
        return hmac.new(self._secret, body.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def _encode(data: str) -> str:
        """把字符串编码为 Base64URL（去掉填充符）。

        :param data: 原始字符串
        :return: Base64URL 字符串
        """
        raw = base64.urlsafe_b64encode(data.encode("utf-8")).decode("utf-8")
        return raw.rstrip("=")

    @staticmethod
    def _decode(data: str) -> str:
        """把 Base64URL 字符串还原为原始字符串。

        :param data: Base64URL 字符串
        :return: 原始字符串
        """
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding).decode("utf-8")
