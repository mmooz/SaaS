"""单位换算辅助：在请求 units 列表与商品 units_json 之间互转。

约定：
- 商品的「基础单位」始终存于 Product.unit / price / member_price（factor=1）；
- 其余可售单位（factor>1）以 JSON 列表存于 Product.units_json；
- 列表项结构：{unit, factor, price, member_price}。
- units 为空 / None 表示单一单位，units_json 留空。
"""

from __future__ import annotations

import json

from app.models import Product
from app.schemas.unit_spec import UnitSpec


class UnitConfigError(ValueError):
    """units 配置不合法（如缺少基础单位、存在重复单位）。"""


def parse_units_json(raw: str | None) -> list[UnitSpec]:
    """把 products.units_json 文本解析为附加单位列表（不含基础单位）。"""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    specs: list[UnitSpec] = []
    for item in data:
        if not isinstance(item, dict) or "unit" not in item or "factor" not in item:
            continue
        specs.append(
            UnitSpec(
                unit=str(item["unit"]),
                factor=float(item["factor"]),
                price=float(item.get("price", 0)),
                member_price=(
                    float(item["member_price"])
                    if item.get("member_price") is not None
                    else None
                ),
            )
        )
    return specs


def serialize_units(units: list[UnitSpec] | None) -> tuple[str | None, str | None, float | None, float | None]:
    """把请求中的 units 列表转成 (units_json, base_unit, base_price, base_member_price)。

    - 必须恰好有一个 factor=1 的基础单位；
    - factor>1 的单位存入 units_json；
    - 返回的基础单位字段用于覆盖 Product.unit / price / member_price。
    """
    if not units:
        return None, None, None, None
    bases = [u for u in units if abs(u.factor - 1) < 1e-9]
    if len(bases) != 1:
        raise UnitConfigError("units 必须且只能包含一个 factor=1 的基础单位")
    base = bases[0]
    seen = {base.unit}
    extra: list[dict] = []
    # 其余单位按 factor 升序，保证输出稳定
    for u in sorted((u for u in units if u is not base), key=lambda x: x.factor):
        if u.unit in seen:
            raise UnitConfigError(f"单位「{u.unit}」重复")
        seen.add(u.unit)
        extra.append(
            {
                "unit": u.unit,
                "factor": u.factor,
                "price": u.price,
                "member_price": u.member_price,
            }
        )
    units_json = json.dumps(extra, ensure_ascii=False) if extra else None
    return units_json, base.unit, base.price, base.member_price


def build_units_list(product: Product) -> list[UnitSpec]:
    """构造商品的完整 units 列表（基础单位 + 附加单位），按 factor 升序。"""
    base = UnitSpec(
        unit=product.unit,
        factor=1,
        price=product.price,
        member_price=product.member_price,
    )
    extra = parse_units_json(product.units_json)
    return [base, *extra]
