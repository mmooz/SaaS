"""退款服务：整单退款/单项退货的校验、记账、库存回滚与储值返还。"""

import json
import random
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Member, MemberTransaction, Order, RefundItem, RefundRecord
from app.schemas.refund_create import RefundCreate
from app.services.inventory_service import InventoryService


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
        db: Session, order: Order, amount: float, data: RefundCreate
    ) -> None:
        """储值支付订单退款：把金额退回会员余额并写入资金流水。

        :param db: 数据库会话
        :param order: 原订单
        :param amount: 退款金额
        :param data: 退款请求
        """
        if not order.member_id or amount <= 0:
            return
        try:
            pay = json.loads(order.pay_details) if order.pay_details else {}
        except (TypeError, ValueError):
            return
        # 仅纯储值支付才自动退回余额，混合支付需线下处理
        if list(pay.keys()) != ["储值"]:
            return
        member = db.get(Member, order.member_id)
        if not member:
            return
        member.balance = round((member.balance or 0) + amount, 2)
        db.add(
            MemberTransaction(
                member_id=member.id,
                type="refund",
                amount=amount,
                points=0,
                operator_id=data.cashier_id,
            )
        )

    @staticmethod
    def refund(db: Session, order: Order, data: RefundCreate) -> RefundRecord:
        """执行退款：校验可退范围、生成退款单、回滚库存并返还储值。

        :param db: 数据库会话
        :param order: 原订单 ORM 对象
        :param data: 退款请求
        :return: 新建的退款单
        :raises ValueError: 订单状态或退货明细不满足退款条件
        """
        if order.status == "refunded":
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
            order.status = "refunded"
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
            order.status = "partially_refunded"

        record = RefundRecord(
            refund_no=RefundService._build_refund_no(),
            order_id=order.id,
            order_no=order.order_no,
            refund_type=data.refund_type,
            amount=amount,
            reason=data.reason,
            cashier_id=data.cashier_id or order.cashier_id,
            authorizer_id=data.authorizer_id,
        )
        for item in items:
            record.items.append(
                RefundItem(
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
        RefundService._refund_stored_value(db, order, amount, data)
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
