"""Excel 导入结果模型。"""

from pydantic import BaseModel


class ImportRowError(BaseModel):
    """单行导入错误信息。"""

    # 出错行号（Excel 行号，从 2 开始）
    row: int
    # 错误原因
    error: str


class ImportResult(BaseModel):
    """Excel 导入结果：统计成功/失败行数与错误明细。"""

    # 总行数
    total: int = 0
    # 成功行数
    success: int = 0
    # 失败行数
    failed: int = 0
    # 新建商品数
    created: int = 0
    # 更新商品数
    updated: int = 0
    # 错误明细列表
    errors: list[ImportRowError] = []
