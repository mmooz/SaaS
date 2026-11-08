"""Q24 会员流水门店归属服务（拍板 2：不重算历史、零 DDL、零回填）。

- **新数据**：退款流水按订单号反查 ``Order.store_id``，统一走 :func:`resolve_store_id`；
  充值 / 积分流水无订单关联，仍取现场门店（语义正确，不改）；
  在线 ``consume`` 仍取现场门店，随 Q06 结算接口在同事务内收口（B3 不改）。
- **历史数据**：不改迁移、不写回填 UPDATE、不新增列；仅由
  :func:`is_store_attribution_reliable` 依据配置项 ``MEMBER_TX_STORE_RELIABLE_SINCE``
  判定「门店归属是否可信」，报表与流水列表据此展示标注。
- 配置未填写时回退**安全默认**：全部历史流水均标注「不可信」。
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Order

# 历史门店归属提示文案（后端响应字段与前端提示条共用，避免多处硬编码）
STORE_ATTRIBUTION_NOTE_UNRELIABLE = "历史数据门店归属不可信"


def _parse_reliable_since(value: str) -> datetime | None:
    """解析配置的可信基线时间为 naive UTC datetime。

    接受 ISO 8601 字符串（可带 ``Z`` 或 ``±HH:MM`` 偏移），统一转为 naive UTC
    与库内 ``DateTime`` 列（naive UTC）比较；空值或非法格式返回 ``None``，
    由调用方按「未配置」的安全默认处理。

    :param value: 配置字符串
    :return: naive UTC 时间，未配置或解析失败返回 ``None``
    """
    text = (value or "").strip()
    if not text:
        return None
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def is_store_attribution_reliable(created_at: datetime | None) -> bool:
    """判断某条流水（或某个查询区间起点）的门店归属是否可信。

    ``created_at < MEMBER_TX_STORE_RELIABLE_SINCE`` 视为历史不可信；
    配置项留空 / 非法时**全部按不可信**处理（安全默认，不声称历史准确）；
    ``created_at`` 缺失同样按不可信处理。

    :param created_at: 流水时间，或报表查询区间起点（naive UTC 或 aware datetime）
    :return: 门店归属可信返回 ``True``，否则 ``False``
    """
    since = _parse_reliable_since(settings.member_tx_store_reliable_since)
    if since is None or created_at is None:
        return False
    moment = created_at
    if moment.tzinfo is not None:
        moment = moment.astimezone(timezone.utc).replace(tzinfo=None)
    return moment >= since


def resolve_store_id(
    db: Session,
    tenant_id: int,
    fallback_store_id: int,
    order_no: str | None = None,
) -> int:
    """解析会员流水应记录的门店 ID：优先按订单反查，否则用现场门店。

    :param db: 数据库会话
    :param tenant_id: 当前租户 ID（反查订单时强制隔离，防止跨租户串店）
    :param fallback_store_id: 现场门店 ID（请求上下文 ``X-Store-Id``）
    :param order_no: 关联订单号；为空或查不到本租户订单时回退现场门店
    :return: 门店 ID
    """
    if order_no:
        order = db.scalar(
            select(Order).where(
                Order.order_no == order_no,
                Order.tenant_id == tenant_id,
            )
        )
        if order is not None:
            return order.store_id
    return fallback_store_id
