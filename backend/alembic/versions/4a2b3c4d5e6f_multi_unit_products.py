"""商品支持多单位与单位换算。

Revision ID: 4a2b3c4d5e6f
Revises: c4d5e6f7a8b9
Create Date: 2026-11-09

变更内容：
1. products 增加 units_json（TEXT，可空）：存储可售单位列表，每项含 unit/factor/price/member_price。
   factor 为该单位相当于基础单位（products.unit）的倍数，基础单位 factor=1；为空表示仅单一单位。
2. order_items 增加 unit（销售单位，如「条」「件」）与 base_qty（基础单位数量 = qty × factor），
   用于多单位商品按基础单位扣减门店库存并保留售出单位快照。
"""

from alembic import op
import sqlalchemy as sa


# 迁移版本号与上下游版本
revision = "4a2b3c4d5e6f"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """执行升级：新增多单位相关列。"""
    op.add_column(
        "products",
        sa.Column("units_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("unit", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "order_items",
        sa.Column("base_qty", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    """回滚：删除多单位相关列。"""
    op.drop_column("order_items", "base_qty")
    op.drop_column("order_items", "unit")
    op.drop_column("products", "units_json")
