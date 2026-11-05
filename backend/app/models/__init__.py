"""数据模型包：集中导入所有 ORM 模型，确保建表/迁移时全部注册。

遵循"一个类一个文件"约定，每个模型类独立一个模块文件。
"""

from app.models.category import Category
from app.models.inventory_movement import InventoryMovement
from app.models.member import Member
from app.models.member_transaction import MemberTransaction
from app.models.operation_log import OperationLog
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_price_history import ProductPriceHistory
from app.models.promotion import Promotion
from app.models.refund_item import RefundItem
from app.models.refund_record import RefundRecord
from app.models.shift_session import ShiftSession
from app.models.store import Store
from app.models.sync_record import SyncRecord
from app.models.system_setting import SystemSetting
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_store import UserStore

__all__ = [
    "Tenant",
    "Store",
    "User",
    "UserStore",
    "Category",
    "Product",
    "ProductPriceHistory",
    "Order",
    "OrderItem",
    "Member",
    "MemberTransaction",
    "Promotion",
    "InventoryMovement",
    "ShiftSession",
    "RefundRecord",
    "RefundItem",
    "SyncRecord",
    "OperationLog",
    "SystemSetting",
]
