"""密码哈希工具：使用标准库 PBKDF2-HMAC-SHA256 加盐哈希，无需额外依赖。"""

import hashlib
import hmac
import secrets


class PasswordHasher:
    """密码哈希器：生成与校验 PBKDF2-SHA256 哈希（格式 pbkdf2_sha256$轮数$盐$哈希）。"""

    # 迭代轮数：数值越高越安全，但登录校验耗时相应增加
    ITERATIONS = 260000

    @classmethod
    def hash(cls, password: str) -> str:
        """把明文密码哈希为可入库的字符串。

        :param password: 明文密码
        :return: pbkdf2_sha256$轮数$盐$哈希
        """
        # 每次哈希使用随机盐，避免相同密码产生相同结果
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), cls.ITERATIONS
        )
        return f"pbkdf2_sha256${cls.ITERATIONS}${salt}${digest.hex()}"

    @classmethod
    def verify(cls, password: str, stored: str) -> bool:
        """校验明文密码与库中哈希是否匹配。

        :param password: 待校验明文密码
        :param stored: 库中保存的哈希字符串
        :return: 匹配返回 True；密码错误或哈希格式不合法返回 False
        """
        try:
            algorithm, iterations, salt, digest = stored.split("$")
            if algorithm != "pbkdf2_sha256":
                return False
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)
            )
        except (ValueError, AttributeError):
            return False
        # 恒定时间比较，避免通过响应时间推断密码
        return hmac.compare_digest(actual.hex(), digest)
