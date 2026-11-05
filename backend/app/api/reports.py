"""报表 API：销售日报月报、商品排行、时段分析、毛利分析、会员分析。"""

from collections import defaultdict
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, Member, Order, OrderItem, Product
from app.schemas.report_daily_out import ReportDailyOut
from app.schemas.report_hourly_out import ReportHourlyOut
from app.schemas.report_hourly_point import ReportHourlyPoint
from app.schemas.report_member_out import ReportMemberOut
from app.schemas.report_member_row import ReportMemberRow
from app.schemas.report_profit_out import ReportProfitOut
from app.schemas.report_profit_row import ReportProfitRow
from app.schemas.report_rank_out import ReportRankOut
from app.schemas.report_rank_row import ReportRankRow
from app.schemas.report_sales_summary import ReportSalesSummary
from app.schemas.report_trend_point import ReportTrendPoint

# 报表路由
router = APIRouter(prefix="/api/reports", tags=["报表中心"])


def _window(start: date, end: date) -> tuple[datetime, datetime]:
    """把日期区间转换为左闭右开的 datetime 窗口。

    :param start: 开始日期（含）
    :param end: 结束日期（含）
    :return: (开始时间, 结束时间+1天)
    """
    return datetime.combine(start, time.min), datetime.combine(end + timedelta(days=1), time.min)


def _paid_orders(db: Session, start: datetime, end: datetime) -> list[Order]:
    """查询时间窗口内已结算的订单。

    :param db: 数据库会话
    :param start: 开始时间
    :param end: 结束时间（不含）
    :return: 订单列表
    """
    return list(
        db.scalars(
            select(Order).where(
                Order.status == "paid",
                Order.created_at >= start,
                Order.created_at < end,
            )
        ).all()
    )


def _item_amount_rows(db: Session, start: datetime, end: datetime):
    """查询时间窗口内的订单明细，附带商品、分类与订单信息。

    :param db: 数据库会话
    :param start: 开始时间
    :param end: 结束时间（不含）
    :return: (订单明细, 商品, 分类, 订单) 结果行列表
    """
    stmt = (
        select(OrderItem, Product, Category, Order)
        .join(Order, Order.id == OrderItem.order_id)
        .outerjoin(Product, Product.id == OrderItem.product_id)
        .outerjoin(Category, Category.id == Product.category_id)
        .where(
            Order.status == "paid",
            Order.created_at >= start,
            Order.created_at < end,
        )
    )
    return db.execute(stmt).all()


def _item_share_rows(db: Session, start: datetime, end: datetime):
    """查询订单明细，并按订单实收金额分摊满减等整单优惠。

    :param db: 数据库会话
    :param start: 开始时间
    :param end: 结束时间（不含）
    :return: [(订单明细, 商品, 分类, 分摊后销售额)] 列表
    """
    rows = _item_amount_rows(db, start, end)
    # 每个订单的明细金额合计，用于计算整单优惠分摊比例
    order_sums: dict[int, float] = defaultdict(float)
    for item, _product, _category, order in rows:
        order_sums[order.id] += item.amount

    result = []
    for item, product, category, order in rows:
        base = order_sums[order.id]
        # 订单实收 / 明细合计；明细合计为 0 时不分摊
        factor = order.total_amount / base if base else 1.0
        result.append((item, product, category, round(item.amount * factor, 2)))
    return result


def _item_qty(item: OrderItem) -> float:
    """取明细的销量：称重商品取重量，按件商品取数量。

    :param item: 订单明细
    :return: 销量数值
    """
    if item.is_weighted:
        return float(item.weight_kg or 0)
    return float(item.qty or 0)


@router.get("/daily", response_model=ReportDailyOut)
def daily_report(
    start: date,
    end: date,
    mode: str = Query("day", pattern="day|week"),
    db: Session = Depends(get_db),
):
    """销售日报月报：返回区间汇总与按日/按周趋势。"""
    begin, finish = _window(start, end)
    orders = _paid_orders(db, begin, finish)

    # 区间汇总
    sales = round(sum(o.total_amount for o in orders), 2)
    order_count = len(orders)
    avg_price = round(sales / order_count, 2) if order_count else 0
    # 称重重量：仅统计称重商品明细
    weight = db.scalar(
        select(func.coalesce(func.sum(OrderItem.weight_kg), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.status == "paid",
            Order.created_at >= begin,
            Order.created_at < finish,
            OrderItem.is_weighted.is_(True),
        )
    )
    summary = ReportSalesSummary(
        sales=sales,
        orders=order_count,
        avg_price=avg_price,
        weight_kg=round(float(weight or 0), 2),
    )

    # 趋势分组：按日或按 ISO 周
    buckets: dict[tuple, dict] = {}
    for order in orders:
        created = order.created_at
        if mode == "week":
            iso = created.isocalendar()
            key: tuple = (iso.year, iso.week)
            label = f"第{iso.week}周"
        else:
            key = (created.year, created.month, created.day)
            label = created.strftime("%m-%d")
        record = buckets.setdefault(key, {"label": label, "sales": 0.0, "orders": 0})
        record["sales"] += order.total_amount
        record["orders"] += 1

    trend = [
        ReportTrendPoint(
            label=buckets[key]["label"],
            sales=round(buckets[key]["sales"], 2),
            orders=int(buckets[key]["orders"]),
        )
        for key in sorted(buckets.keys())
    ]

    return ReportDailyOut(summary=summary, trend=trend)


@router.get("/products", response_model=ReportRankOut)
def product_rank(
    start: date,
    end: date,
    limit: int = Query(15, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """商品销售排行：按销售额倒序返回 Top N。"""
    begin, finish = _window(start, end)
    rows = _item_share_rows(db, begin, finish)

    # 按商品聚合：商品 ID 缺失时按名称聚合
    agg: dict[object, dict] = {}
    total_amount = 0.0
    for item, product, category, share in rows:
        key: object = item.product_id if item.product_id is not None else f"name:{item.name}"
        record = agg.setdefault(
            key,
            {
                "product_id": item.product_id,
                "name": item.name,
                "category": category.name if category else "未分类",
                "qty": 0.0,
                "unit": product.unit if product else ("kg" if item.is_weighted else "件"),
                "is_weighted": item.is_weighted,
                "amount": 0.0,
            },
        )
        record["qty"] += _item_qty(item)
        record["amount"] += share
        total_amount += share

    items: list[ReportRankRow] = []
    for record in agg.values():
        amount = record["amount"]
        items.append(
            ReportRankRow(
                product_id=record["product_id"],
                name=record["name"],
                category=record["category"],
                qty=round(record["qty"], 2),
                unit=record["unit"],
                is_weighted=record["is_weighted"],
                amount=round(amount, 2),
                ratio=round(amount / total_amount * 100, 1) if total_amount else 0,
            )
        )
    items.sort(key=lambda r: r.amount, reverse=True)
    return ReportRankOut(total_amount=round(total_amount, 2), items=items[:limit])


@router.get("/hourly", response_model=ReportHourlyOut)
def hourly_report(start: date, end: date, db: Session = Depends(get_db)):
    """时段分析：逐小时销售额曲线与早/午/晚高峰汇总。"""
    begin, finish = _window(start, end)
    orders = _paid_orders(db, begin, finish)

    buckets: dict[int, list[float]] = defaultdict(lambda: [0.0, 0])
    for order in orders:
        hour = order.created_at.hour
        buckets[hour][0] += order.total_amount
        buckets[hour][1] += 1

    points = [
        ReportHourlyPoint(
            hour=hour,
            label=f"{hour:02d}:00",
            sales=round(buckets[hour][0], 2),
            orders=int(buckets[hour][1]),
        )
        for hour in range(24)
    ]
    total_sales = round(sum(p.sales for p in points), 2)
    peak = max(points, key=lambda p: p.sales) if points else None
    morning = round(sum(p.sales for p in points if 8 <= p.hour < 11), 2)
    noon = round(sum(p.sales for p in points if 11 <= p.hour < 15), 2)
    evening = round(sum(p.sales for p in points if 15 <= p.hour <= 21), 2)

    return ReportHourlyOut(
        total_sales=total_sales,
        peak_label=peak.label if peak else "",
        peak_sales=peak.sales if peak else 0,
        morning_sales=morning,
        noon_sales=noon,
        evening_sales=evening,
        points=points,
    )


@router.get("/profit", response_model=ReportProfitOut)
def profit_report(start: date, end: date, db: Session = Depends(get_db)):
    """毛利分析：按分类统计销售额、成本与毛利。"""
    begin, finish = _window(start, end)
    rows = _item_share_rows(db, begin, finish)

    agg: dict[str, dict] = {}
    for item, product, category, share in rows:
        name = category.name if category else "未分类"
        record = agg.setdefault(name, {"sales": 0.0, "cost": 0.0})
        record["sales"] += share
        cost_price = float(product.cost_price or 0) if product else 0
        record["cost"] += cost_price * _item_qty(item)

    categories: list[ReportProfitRow] = []
    for name, record in agg.items():
        sales = record["sales"]
        cost = record["cost"]
        profit = sales - cost
        categories.append(
            ReportProfitRow(
                category=name,
                sales=round(sales, 2),
                cost=round(cost, 2),
                profit=round(profit, 2),
                rate=round(profit / sales * 100, 1) if sales else 0,
            )
        )
    categories.sort(key=lambda r: r.sales, reverse=True)

    sales_total = round(sum(r.sales for r in categories), 2)
    cost_total = round(sum(r.cost for r in categories), 2)
    profit_total = round(sales_total - cost_total, 2)
    return ReportProfitOut(
        sales=sales_total,
        cost=cost_total,
        profit=profit_total,
        rate=round(profit_total / sales_total * 100, 1) if sales_total else 0,
        categories=categories,
    )


@router.get("/members", response_model=ReportMemberOut)
def member_report(
    start: date,
    end: date,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """会员分析：会员规模、消费贡献、复购率与消费排行。"""
    begin, finish = _window(start, end)
    orders = _paid_orders(db, begin, finish)

    # 全部销售与会员销售
    total_sales = sum(o.total_amount for o in orders)
    member_orders = [o for o in orders if o.member_id is not None]
    member_sales = sum(o.total_amount for o in member_orders)

    # 会员规模与区间新增
    member_total = int(db.scalar(select(func.count()).select_from(Member)) or 0)
    new_in_range = int(
        db.scalar(
            select(func.count())
            .select_from(Member)
            .where(Member.created_at >= begin, Member.created_at < finish)
        )
        or 0
    )

    # 按会员聚合消费金额与笔数
    agg: dict[int, list[float]] = defaultdict(lambda: [0.0, 0])
    for order in member_orders:
        agg[order.member_id][0] += order.total_amount
        agg[order.member_id][1] += 1

    # 复购率：消费 2 笔及以上的会员 / 有消费的会员
    repeat_count = sum(1 for amount_orders in agg.values() if amount_orders[1] >= 2)
    repurchase_rate = round(repeat_count / len(agg) * 100, 1) if agg else 0

    # 会员信息
    member_ids = list(agg.keys())
    members = (
        {m.id: m for m in db.scalars(select(Member).where(Member.id.in_(member_ids))).all()}
        if member_ids
        else {}
    )

    items: list[ReportMemberRow] = []
    for member_id, (amount, count) in agg.items():
        member = members.get(member_id)
        items.append(
            ReportMemberRow(
                member_id=member_id,
                name=(member.name if member and member.name else f"会员{member_id}"),
                level=member.level if member else "normal",
                orders=int(count),
                amount=round(amount, 2),
                ratio=round(amount / member_sales * 100, 1) if member_sales else 0,
            )
        )
    items.sort(key=lambda r: r.amount, reverse=True)

    return ReportMemberOut(
        member_total=member_total,
        new_in_range=new_in_range,
        member_sales=round(member_sales, 2),
        member_orders=len(member_orders),
        member_ratio=round(member_sales / total_sales * 100, 1) if total_sales else 0,
        repurchase_rate=repurchase_rate,
        items=items[:limit],
    )
