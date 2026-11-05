"""雪花 ID 序列化类型：接口统一以字符串传输，避免前端 Number 精度丢失。

雪花 ID 为 64 位整数（约 1.8e18），超出 JavaScript Number 的安全整数范围（2^53），
因此所有响应中的 ID 一律序列化为字符串；请求中传入的字符串数字由 Pydantic 自动转换。
"""

from typing import Annotated

from pydantic import BeforeValidator


def _to_string(value: object) -> object:
    """把整数型 ID 转为字符串（None 保持为 None）。

    :param value: 原始值（来自 ORM 的 int 或请求中的字符串）
    :return: 字符串 ID 或 None
    """
    if value is None:
        return None
    return str(value)


# 雪花 ID 类型：输出为字符串，输入兼容数字与字符串
SnowflakeId = Annotated[str, BeforeValidator(_to_string)]
