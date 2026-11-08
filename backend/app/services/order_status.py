"""B3 公共契约：订单状态常量与支付方式枚举占位。

设计依据：``.trae/documents/鲜衡云B3与PG迁移增量设计.md`` A.3.1 / A.3.2 / A.7。

- **SQLite 阶段（B3）只统一状态字面量**，``Order.status`` 列仍为 ``String(16)``；
  列宽扩到 ``String(32)``、加 CHECK 约束随 PG baseline 一次性实施（拍板 4）。
- ``partially_refunded`` 为 18 字符，SQLite 不校验 VARCHAR 长度故当前可写入；
  切 PG 后由 baseline 的 VARCHAR(32) 承接。B3 **不改任何列定义、不新增迁移**。
- ``PaymentMethod`` 仅为 Q20 / Q06 的契约占位：结构化 ``pay_details`` 由 B4 新增的
  结算接口定义，B3 **不解析、不启用**该枚举，前端 ``pay_details`` 生成逻辑一律不变。
"""

from enum import Enum


class OrderStatus:
    """订单状态常量（B3 唯一来源，业务代码禁止再散落状态字面量）。"""

    # 待支付 / 进行中
    PENDING: str = "pending"
    # 已结算
    PAID: str = "paid"
    # 整单已退款
    REFUNDED: str = "refunded"
    # 部分退款（18 字符，列宽随 PG baseline 扩 String(32)）
    PARTIALLY_REFUNDED: str = "partially_refunded"

    # 允许出现在 Order.status 列的全量值域
    ALL_STATUSES: frozenset[str] = frozenset(
        {PENDING, PAID, REFUNDED, PARTIALLY_REFUNDED}
    )


class PaymentMethod(str, Enum):
    """支付方式枚举占位（Q20 / Q06 契约冻结，B3 不启用）。

    B3 的 ``pay_details`` 仍是中文自由文本 JSON（如 ``{"储值": x, "现金": y}``），
    结构化契约由 B4 结算接口定义。本枚举**不参与任何解析、不写入数据库、不做
    比较判断**，仅登记待实现的值域，避免 B3 提前按中文 key 实现「按比例退储值」
    而在 Q06 改结构后整体返工（Q20 随 B4，见设计 A.3.2）。
    """

    CASH = "cash"
    WECHAT = "wechat"
    ALIPAY = "alipay"
    STORED_VALUE = "stored_value"
