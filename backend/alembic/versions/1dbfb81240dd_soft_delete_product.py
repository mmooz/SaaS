"""soft delete product

商品删除改为软删除：新增 deleted 标记字段与索引。

Revision ID: 1dbfb81240dd
Revises: f7c921310f04
Create Date: 2026-11-06 13:01:37.592333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1dbfb81240dd'
down_revision: Union[str, None] = 'f7c921310f04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级：新增商品软删除标记字段及检索索引。"""
    # 历史数据默认视为未删除
    op.add_column(
        "products",
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.create_index("ix_products_deleted", "products", ["deleted"], unique=False)


def downgrade() -> None:
    """降级：移除软删除标记字段及索引。"""
    op.drop_index("ix_products_deleted", table_name="products")
    op.drop_column("products", "deleted")

