"""数据备份输出模型。"""

from datetime import datetime

from pydantic import BaseModel


class BackupOut(BaseModel):
    """备份文件响应体：文件名、大小与创建时间。"""

    # 备份文件名
    name: str
    # 文件大小（字节）
    size: float
    # 创建时间
    created_at: datetime
