"""密码强度策略：集中维护最小长度、弱口令判定与临时密码生成。

R8：新建后台用户、租户初始管理员与离线口令轮换脚本共用同一套规则，
避免各入口各写一份弱口令名单导致规则漂移。本模块只处理明文密码，
不接触数据库、不加载应用入口，因此离线运维脚本也可以安全导入。

历史库中已存在的弱口令账号请使用 ``backend/tools/rotate_weak_passwords.py``
轮换（默认 dry-run，绝不自动写库）。
"""

import secrets
import string

# 密码最小长度（与 UserCreate / UserUpdate / TenantAdminCreate 保持一致）
MIN_PASSWORD_LENGTH = 8
# 常见弱口令名单（统一按小写比较）；纯递增数字与单字符重复由规则兜底，
# 不把具体数字序列写成字面量，避免与「默认口令」产生任何混淆
WEAK_PASSWORDS = frozenset(
    {
        "password",
        "passw0rd",
        "p@ssw0rd",
        "admin123",
        "admin888",
        "qwerty123",
        "abc123",
        "letmein",
        "iloveyou",
        "welcome",
    }
)
# 临时密码字符集：仅字母与数字，便于人工抄写、复制与输入
_TEMP_PASSWORD_ALPHABET = string.ascii_letters + string.digits
# 临时密码长度（≥12，满足验收要求）
TEMP_PASSWORD_LENGTH = 16


def is_weak_password(value: str) -> bool:
    """判断密码是否属于弱口令（命中名单、单字符重复或纯连续递增数字）。

    :param value: 已去除首尾空白并转为小写的密码
    :return: 是弱口令返回 True
    """
    if not value:
        return True
    if value in WEAK_PASSWORDS:
        return True
    # 单字符重复，如全 1 / 全 a
    if len(set(value)) == 1:
        return True
    # 纯数字连续递增（如常见的顺序数字串），覆盖任意长度，不写死字面量
    if value.isdigit() and len(value) > 1:
        return all(
            ord(value[index + 1]) - ord(value[index]) == 1
            for index in range(len(value) - 1)
        )
    return False


def ensure_strong_password(password: str | None, label: str = "密码") -> str:
    """校验密码强度，不合规则抛出 ValueError（Pydantic 会转换为 422）。

    校验使用 strip + lower 后的值，但返回用户输入的原文，不改变实际密码内容。

    :param password: 明文密码
    :param label: 错误提示中使用的字段名
    :return: 原样返回明文密码
    :raises ValueError: 密码为空、长度不足或属于常见弱口令
    """
    value = password or ""
    normalized = value.strip().lower()
    if len(normalized) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"{label}至少需要 {MIN_PASSWORD_LENGTH} 位")
    if is_weak_password(normalized):
        raise ValueError(f"{label}过于简单，请更换")
    return value


def generate_temporary_password(length: int = TEMP_PASSWORD_LENGTH) -> str:
    """生成一次性随机临时密码（仅字母数字，长度至少 12 位）。

    :param length: 期望长度，低于 12 时按 12 处理
    :return: 随机明文密码
    """
    size = max(length, 12)
    while True:
        candidate = "".join(
            secrets.choice(_TEMP_PASSWORD_ALPHABET) for _ in range(size)
        )
        if not is_weak_password(candidate.lower()):
            return candidate
