"""退款请求模型：整单退款或按明细退货。

Q17 契约变更（拍板 1）：
- **移除 ``authorizer_id``**：不做「本人当班」判定与店长授权人；DB 列与
  ``RefundOut.authorizer_id`` 保留但恒为 ``null``（兼容前端、避免迁移）。
- ``cashier_id`` **弃用并被服务端忽略**：操作主体一律取令牌用户 ID。
- 旧客户端仍可能传这两个字段，``extra="ignore"`` 保证被静默忽略、**不返回 422**。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RefundCreate(BaseModel):
    """收银端退款请求体（操作主体由服务端令牌决定，客户端不可指定）。"""

    # Q17：显式声明忽略额外字段，兼容旧客户端继续传 authorizer_id / cashier_id，
    # 不产生 422；服务端只消费下面列出的业务字段。
    model_config = ConfigDict(extra="ignore")

    # 退款单号（离线收银端生成，联网补传时保留，用于幂等去重）
    refund_no: str | None = Field(None, min_length=1, max_length=32)
    # 退款时间（离线补传时保留原始时间）
    created_at: datetime | None = None
    # 退款类型：full=整单退款，item=单项退货
    refund_type: str = Field("full", pattern="^(full|item)$")
    # 退货明细主键列表（refund_type=item 时必填）
    item_ids: list[int] = []
    # 退款原因
    reason: str | None = Field(None, max_length=200)
    # 操作收银员用户 ID（B3 弃用：保留字段仅为兼容旧客户端，服务端一律忽略，
    # RefundRecord.cashier_id / 操作日志 / 会员流水 operator_id 均取令牌用户 ID）
    cashier_id: int | None = None
