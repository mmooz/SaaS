"""交接班服务：开班、当前班次、班次汇总与交班落库。"""

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Order, ShiftSession
from app.schemas.payment_summary_out import PaymentSummaryOut
from app.schemas.shift_summary_out import ShiftSummaryOut
from app.services.report_net import net_total, refund_map


class ShiftService:
    """交接班业务服务。"""

    @staticmethod
    def open(db: Session, cashier_id: int, base_cash: float, tenant_id: int, store_id: int) -> ShiftSession:
        """开班：若已有进行中的班次则直接返回，避免重复开班。

        :param db: 数据库会话
        :param cashier_id: 收银员用户 ID
        :param base_cash: 现金底金
        :param tenant_id: 所属租户 ID
        :param store_id: 所属门店 ID
        :return: 进行中的班次
        """
        current = ShiftService.current(db, cashier_id, store_id)
        if current:
            return current
        shift = ShiftSession(
            tenant_id=tenant_id,
            cashier_id=cashier_id,
            store_id=store_id,
            base_cash=base_cash,
            status="open",
        )
        db.add(shift)
        db.flush()
        return shift

    @staticmethod
    def current(db: Session, cashier_id: int, store_id: int) -> ShiftSession | None:
        """查询收银员当前进行中的班次（限定门店）。

        :param db: 数据库会话
        :param cashier_id: 收银员用户 ID
        :param store_id: 所属门店 ID
        :return: 进行中的班次，无则返回 None
        """
        return db.scalar(
            select(ShiftSession)
            .where(
                ShiftSession.cashier_id == cashier_id,
                ShiftSession.store_id == store_id,
                ShiftSession.status == "open",
            )
            .order_by(ShiftSession.id.desc())
        )

    @staticmethod
    def _orders(db: Session, shift: ShiftSession) -> list[Order]:
        """查询班次时间窗内该收银员的订单（限定本门店、本租户）。

        Q21：原实现只按 ``cashier_id`` + 时间窗过滤，多门店授权的收银员会把
        其它门店同期订单计入本店班次汇总。补 ``store_id`` / ``tenant_id`` 过滤，
        与其余查询口径一致。

        :param db: 数据库会话
        :param shift: 班次
        :return: 订单列表
        """
        stmt = select(Order).where(
            Order.cashier_id == shift.cashier_id,
            Order.store_id == shift.store_id,
            Order.tenant_id == shift.tenant_id,
            Order.created_at >= shift.start_at,
        )
        if shift.end_at:
            stmt = stmt.where(Order.created_at <= shift.end_at)
        return list(db.scalars(stmt.order_by(Order.id.asc())).all())

    @staticmethod
    def summary(db: Session, shift: ShiftSession) -> ShiftSummaryOut:
        """统计班次销售与支付方式汇总（净额法，与报表口径严格一致）。

        Q05：退款映射与净销售额一律复用 ``services/report_net.py``，删除本类
        原有的自建净额逻辑，消除「报表一套 / 班次一套」的口径矛盾（拍板 3）。
        输出结构不变，仅数值口径与五类报表统一。

        :param db: 数据库会话
        :param shift: 班次
        :return: 班次汇总
        """
        orders = ShiftService._orders(db, shift)
        # 传入同一订单集，保证 refund_map 与 net_total 使用完全相同的订单范围；
        # 口径为「按订单关联、区间内订单统计退款」，见 report_net 顶部说明。
        window_end = shift.end_at or datetime.now()
        refunds = refund_map(db, shift.start_at, window_end, shift.store_id, orders=orders)
        total_sales = net_total(orders, refunds)

        # 按支付方式累计金额与笔数（净额 = 原支付金额 - 本单退款，按支付比例摊回）
        method_amount: dict[str, float] = {}
        method_count: dict[str, int] = {}
        for order in orders:
            refunded = refunds.get(order.id, 0)
            try:
                pay = json.loads(order.pay_details) if order.pay_details else {}
            except (TypeError, ValueError):
                pay = {}
            gross = sum(float(v or 0) for v in pay.values())
            for method, amount in pay.items():
                value = float(amount or 0)
                # 有退款时按该支付方式占原单比例扣除
                ratio = value / gross if gross > 0 else 0
                net_value = round(value - refunded * ratio, 2)
                if net_value <= 0:
                    continue
                method_amount[method] = method_amount.get(method, 0) + net_value
                method_count[method] = method_count.get(method, 0) + 1

        payments = [
            PaymentSummaryOut(
                method=method, amount=round(amount, 2), count=method_count.get(method, 0)
            )
            for method, amount in method_amount.items()
        ]
        cash = next((p.amount for p in payments if p.method == "现金"), 0)
        return ShiftSummaryOut(
            shift=shift,
            order_count=len(orders),
            total_sales=total_sales,
            refund_amount=round(sum(refunds.values()), 2),
            payments=payments,
            cash_should=round((shift.base_cash or 0) + cash, 2),
            actual_cash=None,
        )

    @staticmethod
    def sync(db: Session, items: list, tenant_id: int, store_id: int) -> int:
        """批量补传离线班次：按班次主键幂等写入或更新。

        :param db: 数据库会话
        :param items: 班次快照列表（ShiftSyncItem）
        :param tenant_id: 所属租户 ID
        :param store_id: 所属门店 ID
        :return: 成功处理的班次数
        """
        synced = 0
        for item in items:
            # Q04：载荷携带门店时必须与当前上下文一致，防止 A 店离线、
            # B 店联网补传把班次落到错误门店（Q26 的完整修复见 B2）
            if item.store_id is not None and item.store_id != store_id:
                raise ValueError("班次所属门店与当前登录门店不一致，拒绝补传")
            shift = db.get(ShiftSession, item.id)
            if shift:
                # Q04：db.get 按主键全局查找，命中后必须校验归属，
                # 否则客户端传他店班次 ID 即可篡改其销售额与交班状态
                if shift.tenant_id != tenant_id or shift.store_id != store_id:
                    raise ValueError("班次不属于当前租户或门店，拒绝补传")
                # 已存在则补全交班信息与本地统计
                shift.end_at = item.end_at or shift.end_at
                shift.status = item.status
                shift.total_sales = item.total_sales
                shift.order_count = item.order_count
                shift.base_cash = item.base_cash
            else:
                db.add(
                    ShiftSession(
                        id=item.id,
                        tenant_id=tenant_id,
                        cashier_id=item.cashier_id,
                        store_id=store_id,
                        start_at=item.start_at,
                        end_at=item.end_at,
                        base_cash=item.base_cash,
                        total_sales=item.total_sales,
                        order_count=item.order_count,
                        status=item.status,
                    )
                )
            synced += 1
        db.flush()
        return synced

    @staticmethod
    def close(db: Session, shift: ShiftSession, actual_cash: float | None) -> ShiftSummaryOut:
        """交班：写入交班时间、销售汇总并置为已交班。

        :param db: 数据库会话
        :param shift: 进行中的班次
        :param actual_cash: 实际点钞现金
        :return: 交班后的班次汇总
        """
        summary = ShiftService.summary(db, shift)
        shift.end_at = datetime.now()
        shift.status = "closed"
        shift.total_sales = summary.total_sales
        shift.order_count = summary.order_count
        summary.actual_cash = actual_cash
        summary.shift = shift
        db.flush()
        return summary
