"""退款服务：整单退款/单项退货的校验、记账、库存回滚与储值返还。"""

import json
import random
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Member, MemberTransaction, Order, RefundItem, RefundRecord
from app.schemas.refund_create import RefundCreate
from app.services.inventory_service import InventoryService
from app.services.member_tx_store_service import resolve_store_id
from app.services.order_status import OrderStatus


class RefundService:
    """退款业务服务（静态方法，供订单 API 复用）。"""

    @staticmethod
    def refunded_amount(db: Session, order_id: int) -> float:
        """统计订单已退款金额。

        :param db: 数据库会话
        :param order_id: 订单主键
        :return: 已退款金额合计
        """
        total = db.scalar(
            select(func.coalesce(func.sum(RefundRecord.amount), 0)).where(
                RefundRecord.order_id == order_id
            )
        )
        return round(float(total or 0), 2)

    @staticmethod
    def refunded_item_ids(db: Session, order_id: int) -> set[int]:
        """查询订单中已退过货的明细主键集合（同一行不允许重复退货）。

        :param db: 数据库会话
        :param order_id: 订单主键
        :return: 已退货的订单明细主键集合
        """
        rows = db.scalars(
            select(RefundItem.order_item_id)
            .join(RefundRecord, RefundItem.refund_id == RefundRecord.id)
            .where(RefundRecord.order_id == order_id)
        ).all()
        return {row for row in rows if row is not None}

    @staticmethod
    def _build_refund_no() -> str:
        """生成退款单号：RF + 时间戳 + 4 位随机数。

        :return: 退款单号
        """
        return f"RF{datetime.now():%Y%m%d%H%M%S}{random.randint(1000, 9999)}"

    @staticmethod
    def _refund_stored_value(
        db: Session,
        order: Order,
        amount: float,
        data: RefundCreate,
        tenant_id: int,
        actor_id: int,
    ) -> None:
        """储值支付订单退款：把金额退回会员余额并写入资金流水。

        :param db: 数据库会话
        :param order: 原订单
        :param amount: 退款金额
        :param data: 退款请求
        :param tenant_id: 所属租户 ID
        :param actor_id: 服务端令牌用户 ID（Q17：流水 operator_id 主体可信）
        """
        if not order.member_id or amount <= 0:
            return
        try:
            pay = json.loads(order.pay_details) if order.pay_details else {}
        except (TypeError, ValueError):
            return

        # ---- Q20 / Q06 契约冻结：B3 只登记，不改逻辑（详见设计 A.3.2）----
        # 现状：仅当 list(pay.keys()) == ["储值"]（纯储值支付）才自动退回余额，
        # 混合支付不返储值、不写标记/流水，且判断依赖中文 key 的字面量与顺序。
        # TODO(B4 / Q06 + Q20)：由 Q06 新增的结算接口在单事务内产出「支付方式枚举
        #   + 金额」的结构化 pay_details 与同事务的 type=consume 扣款流水；退款改为
        #   按各支付方式金额比例计算应退储值，并在返前校验原单确有对应 consume 流水
        #   （无流水不返钱，堵「不扣先返」套利）。B3 提前改动会因①结构契约未定、
        #   ②扣款流水不存在（当前 consumeMember 为独立 HTTP 且 order_no 后端未使用）、
        #   ③R20 已临时下线在线储值支付无验证流量而整体返工，故本批冻结现状。
        if list(pay.keys()) != ["储值"]:
            return
        member = db.get(Member, order.member_id)
        if not member:
            return
        member.balance = round((member.balance or 0) + amount, 2)
        db.add(
            MemberTransaction(
                tenant_id=tenant_id,
                # Q24：退款流水按订单号反查门店，统一走共享服务（拍板 2 不重算历史）
                store_id=resolve_store_id(db, tenant_id, order.store_id, order.order_no),
                member_id=member.id,
                type="refund",
                amount=amount,
                points=0,
                # Q17：取服务端令牌用户，不再取客户端 data.cashier_id
                operator_id=actor_id,
            )
        )

    @staticmethod
    def refund(
        db: Session, order: Order, data: RefundCreate, tenant_id: int, actor_id: int
    ) -> RefundRecord:
        """执行退款：校验可退范围、生成退款单、回滚库存并返还储值。

        :param db: 数据库会话
        :param order: 原订单 ORM 对象
        :param data: 退款请求
        :param tenant_id: 所属租户 ID
        :param actor_id: 服务端令牌用户 ID（Q17：退款单与流水的操作主体）
        :return: 新建的退款单
        :raises ValueError: 订单状态或退货明细不满足退款条件
        """
        if order.status == OrderStatus.REFUNDED:
            raise ValueError("订单已全额退款，不能重复退款")

        refunded_ids = RefundService.refunded_item_ids(db, order.id)
        refunded_sum = RefundService.refunded_amount(db, order.id)
        remaining = round(order.total_amount - refunded_sum, 2)

        if data.refund_type == "full":
            # 整单退款：未退过的明细全部回滚库存，金额退剩余应收
            items = [item for item in order.items if item.id not in refunded_ids]
            if not items:
                raise ValueError("订单商品均已退货，无需再次退款")
            amount = remaining
            if amount <= 0:
                raise ValueError("订单已无可退金额")
            order.status = OrderStatus.REFUNDED
        else:
            # 单项退货：校验选中明细存在且未退过货
            if not data.item_ids:
                raise ValueError("请选择要退货的商品")
            selected_ids = set(data.item_ids)
            items = [item for item in order.items if item.id in selected_ids]
            if len(items) != len(selected_ids):
                raise ValueError("存在无效的退货商品")
            if any(item.id in refunded_ids for item in items):
                raise ValueError("选中商品已退过货，不能重复退货")
            amount = round(min(sum(item.amount for item in items), remaining), 2)
            if amount <= 0:
                raise ValueError("退款金额无效")
            order.status = OrderStatus.PARTIALLY_REFUNDED

        record_kwargs = {
            "tenant_id": tenant_id,
            "refund_no": data.refund_no or RefundService._build_refund_no(),
            "order_id": order.id,
            "order_no": order.order_no,
            "refund_type": data.refund_type,
            "amount": amount,
            "reason": data.reason,
            # Q17：操作主体取令牌用户 ID，不再取客户端 cashier_id
            "cashier_id": actor_id,
            # Q17 / 拍板 1：不做授权人，字段保留（DB 列与 RefundOut）但恒为 null
            "authorizer_id": None,
        }
        # 离线补传时保留收银端原始退款时间
        if data.created_at is not None:
            record_kwargs["created_at"] = data.created_at
        record = RefundRecord(**record_kwargs)
        for item in items:
            record.items.append(
                RefundItem(
                    tenant_id=tenant_id,
                    order_item_id=item.id,
                    name=item.name,
                    qty=item.qty,
                    weight_kg=item.weight_kg,
                    amount=round(item.amount, 2),
                    is_weighted=item.is_weighted,
                )
            )

        db.add(record)
        # 库存回滚与储值返还
        InventoryService.restore_for_refund(db, order, items)
        RefundService._refund_stored_value(db, order, amount, data, tenant_id, actor_id)
        db.flush()
        return record

    @staticmethod
    def list_refunds(db: Session, order_id: int) -> list[RefundRecord]:
        """查询订单的全部退款记录（时间倒序）。

        :param db: 数据库会话
        :param order_id: 订单主键
        :return: 退款单列表
        """
        return list(
            db.scalars(
                select(RefundRecord)
                .where(RefundRecord.order_id == order_id)
                .order_by(RefundRecord.id.desc())
            ).all()
        )
