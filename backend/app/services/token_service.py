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

    @staticmethod
    def password_version(password_hash: str | None) -> str:
        """由密码哈希派生短版本号（哈希变化 = 版本变化）。

        R19：把该值写进令牌载荷并在解析时与库中当前哈希比对，使「修改密码 /
        轮换弱口令」后所有此前签发的令牌立即失效。无需新增用户表列或 token
        黑名单，无状态令牌保持无状态。

        :param password_hash: 库中保存的密码哈希
        :return: 16 位十六进制版本串；空哈希返回空串
        """
        if not password_hash:
            return ""
        return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]

    def issue(self, user_id: int, tenant_id: int, password_hash: str = "") -> str:
        """为用户签发令牌，载荷携带用户 ID、租户 ID 与密码版本。

        :param user_id: 用户 ID
        :param tenant_id: 所属租户 ID
        :param password_hash: 当前密码哈希（R19：用于绑定密码版本）
        :return: 令牌字符串（载荷.签名）
        """
        payload = {
            "uid": user_id,
            "tid": tenant_id,
            "exp": int(time.time()) + self.expire_seconds,
            "pv": self.password_version(password_hash),
        }
        body = self._encode(json.dumps(payload, separators=(",", ":")))
        return f"{body}.{self._sign(body)}"

    def verify(self, token: str) -> dict | None:
        """校验令牌并取出用户 ID 与租户 ID。

        :param token: 待校验令牌
        :return: 校验通过返回 {"user_id", "tenant_id", "password_version"}；
            签名错误、格式错误或已过期返回 None
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
        version = payload.get("pv", "")
        if not isinstance(version, str):
            return None
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "password_version": version,
        }

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
