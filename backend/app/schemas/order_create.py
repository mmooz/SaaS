"""订单创建请求模型。"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.order_item_create import OrderItemCreate
from app.services.order_status import OrderStatus


class OrderCreate(BaseModel):
    """收银端上传订单请求体。"""

    # 订单主键（离线收银端生成的雪花 ID，联网补传时保留）
    id: int | None = None
    # 下单时间（离线补传时保留原始时间）
    created_at: datetime | None = None
    # 订单号（收银端生成，唯一，用于幂等去重）
    order_no: str = Field(..., min_length=1, max_length=32)
    # Q26：离线补传时携带的「结算发生时」门店，仅用于与 X-Store-Id 做一致性校验，
    # 绝不作为订单归属数据来源（落库门店仍以 get_store_id 解析结果为准）
    store_id: str | int | None = None
    # 离线端本地记录的租户标识（服务端忽略，由上下文决定租户）
    tenant_id: str | int | None = None
    # 收银员用户 ID
    cashier_id: int | None = None
    # 交接班会话 ID
    shift_id: int | None = None
    # 订单状态：客户端只能创建待支付/已支付单，退款状态由退款流程写入。
    # 值域引用 OrderStatus 常量；Order.status 列宽仍为 String(16)（随 PG baseline 扩 32）。
    status: str = Field(
        OrderStatus.PAID,
        pattern=rf"^({OrderStatus.PENDING}|{OrderStatus.PAID})$",
    )
    # 应收总额
    total_amount: float = Field(0, ge=0)
    # 优惠金额（Q22：不得为负）
    discount_amount: float = Field(0, ge=0)
    # 支付方式明细（B3 冻结：仍为中文自由文本 JSON，如 {"储值": x, "现金": y}）。
    # 结构化契约（支付方式枚举 + 金额）由 B4 / Q06 新增结算接口定义，本批不变；
    # 前端 pay_details 生成逻辑亦逐字符不动，避免 Q06 改结构后整体返工（见设计 A.3.2）。
    pay_details: str | None = None
    # 关联会员 ID
    member_id: int | None = None
    # 备注
    remark: str | None = Field(None, max_length=200)
    # 订单明细
    items: list[OrderItemCreate] = []
