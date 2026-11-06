"""tenant scoped unique barcode and mobile

商品条码与会员手机号的唯一范围由「全局唯一」调整为「同租户唯一」。

Revision ID: f7c921310f04
Revises: e80564232196
Create Date: 2026-11-06 12:52:23.746577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7c921310f04'
down_revision: Union[str, None] = 'e80564232196'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _assert_no_duplicates(
    table: str, column: str, scope: list[str] | None, label: str
) -> None:
    """校验指定范围内不存在重复值，存在重复时中止迁移并给出处理提示。

    :param table: 待校验表名
    :param column: 需要唯一的字段名
    :param scope: 唯一性生效的字段范围（如 tenant_id）；None 表示全局
    :param label: 报错时展示的业务名称
    """
    bind = op.get_bind()
    group_columns = (scope or []) + [column]
    group_sql = ", ".join(group_columns)
    scope_label = "+".join(scope) if scope else "全局"
    rows = bind.execute(
        sa.text(
            f"SELECT {group_sql}, COUNT(*) AS cnt "
            f"FROM {table} GROUP BY {group_sql} HAVING COUNT(*) > 1 LIMIT 10"
        )
    ).fetchall()
    if rows:
        detail = "; ".join(str(tuple(row)) for row in rows)
        raise RuntimeError(
            f"迁移中止：{label}在 {scope_label} 范围内存在重复数据（{detail}）。"
            "请先合并或删除重复记录，再重新执行迁移。"
        )


def upgrade() -> None:
    """升级：条码与手机号改为同租户唯一。"""
    # 已有数据先做重复检查，避免建唯一索引时才报错且无法定位问题
    _assert_no_duplicates("products", "barcode", ["tenant_id"], "商品条码")
    _assert_no_duplicates("members", "mobile", ["tenant_id"], "会员手机号")

    # 商品条码：去掉全局唯一索引，保留普通索引用于条码检索，新增租户+条码唯一索引
    op.drop_index("ix_products_barcode", table_name="products")
    op.create_index("ix_products_barcode", "products", ["barcode"], unique=False)
    op.create_index(
        "uq_products_tenant_barcode", "products", ["tenant_id", "barcode"], unique=True
    )

    # 会员手机号：同上
    op.drop_index("ix_members_mobile", table_name="members")
    op.create_index("ix_members_mobile", "members", ["mobile"], unique=False)
    op.create_index(
        "uq_members_tenant_mobile", "members", ["tenant_id", "mobile"], unique=True
    )


def downgrade() -> None:
    """降级：恢复条码与手机号的全局唯一索引。"""
    # 回退前检查跨租户重复，否则全局唯一索引无法创建
    _assert_no_duplicates("products", "barcode", None, "商品条码")
    _assert_no_duplicates("members", "mobile", None, "会员手机号")

    op.drop_index("uq_products_tenant_barcode", table_name="products")
    op.drop_index("ix_products_barcode", table_name="products")
    op.create_index("ix_products_barcode", "products", ["barcode"], unique=True)

    op.drop_index("uq_members_tenant_mobile", table_name="members")
    op.drop_index("ix_members_mobile", table_name="members")
    op.create_index("ix_members_mobile", "members", ["mobile"], unique=True)
