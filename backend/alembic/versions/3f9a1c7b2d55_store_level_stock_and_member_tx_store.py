"""商品库存拆分到门店级，会员流水补充门店归属。

Revision ID: 3f9a1c7b2d55
Revises: 1dbfb81240dd
Create Date: 2026-11-06

变更内容：
1. 新建 product_stocks 表，把 products.stock / safety_stock 按商品当前归属门店搬入。
   products 上的 stock/safety_stock 仅保留为迁移来源，不再作为业务库存。
2. member_transactions 增加 store_id，并用会员当前归属门店回填存量流水。
"""

from alembic import op
import sqlalchemy as sa

# 迁移版本号与上下游版本
revision = "3f9a1c7b2d55"
down_revision = "1dbfb81240dd"
branch_labels = None
depends_on = None


def _insert_product_stocks(bind) -> None:
    """把 products 表中的库存数据搬入门店库存表。

    :param bind: 数据库连接
    """
    # 延迟导入雪花 ID 生成器，避免迁移脚本在模块加载时依赖应用配置
    from app.services.snowflake import next_id

    rows = bind.execute(
        sa.text(
            "SELECT id, tenant_id, store_id, stock, safety_stock, created_at, updated_at "
            "FROM products"
        )
    ).fetchall()
    for row in rows:
        bind.execute(
            sa.text(
                "INSERT INTO product_stocks "
                "(id, product_id, tenant_id, store_id, stock, safety_stock, created_at, updated_at) "
                "VALUES (:id, :product_id, :tenant_id, :store_id, :stock, :safety_stock, "
                ":created_at, :updated_at)"
            ),
            {
                "id": next_id(),
                "product_id": row[0],
                "tenant_id": row[1],
                "store_id": row[2],
                "stock": row[3] or 0,
                "safety_stock": row[4] or 0,
                "created_at": row[5],
                "updated_at": row[6],
            },
        )


def _backfill_member_transaction_store(bind) -> None:
    """用会员归属门店回填会员流水的 store_id。

    :param bind: 数据库连接
    """
    bind.execute(
        sa.text(
            "UPDATE member_transactions SET store_id = ("
            "SELECT store_id FROM members WHERE members.id = member_transactions.member_id"
            ") WHERE store_id IS NULL"
        )
    )
    # 回填后仍为空说明存在孤儿流水，直接中止迁移，避免写出归属不明的数据
    remaining = bind.execute(
        sa.text("SELECT COUNT(*) FROM member_transactions WHERE store_id IS NULL")
    ).scalar()
    if remaining:
        raise RuntimeError(
            f"存在 {remaining} 条会员流水无法确定门店归属，请先修复 member_id 关联后再迁移"
        )


def upgrade() -> None:
    """执行升级：建门店库存表并搬迁库存，会员流水补门店字段。"""
    bind = op.get_bind()

    # 1. 门店库存表
    op.create_table(
        "product_stocks",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("stock", sa.Float(), nullable=False),
        sa.Column("safety_stock", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_stocks_product_id", "product_stocks", ["product_id"])
    op.create_index("ix_product_stocks_tenant_id", "product_stocks", ["tenant_id"])
    op.create_index("ix_product_stocks_store_id", "product_stocks", ["store_id"])
    op.create_index(
        "uq_product_stocks_product_store",
        "product_stocks",
        ["product_id", "store_id"],
        unique=True,
    )

    # 2. 搬迁存量库存
    _insert_product_stocks(bind)

    # 3. 会员流水补充门店归属
    op.add_column("member_transactions", sa.Column("store_id", sa.BigInteger(), nullable=True))
    _backfill_member_transaction_store(bind)
    # SQLite 需借助 batch 模式重建表才能把列改为非空
    with op.batch_alter_table("member_transactions") as batch_op:
        batch_op.alter_column("store_id", existing_type=sa.BigInteger(), nullable=False)
        batch_op.create_index("ix_member_transactions_store_id", ["store_id"])


def downgrade() -> None:
    """回滚：库存写回商品行，删除门店库存表与会员流水门店字段。"""
    bind = op.get_bind()

    # 1. 把门店库存写回商品行（优先取商品所属门店的库存记录）
    stocks = bind.execute(
        sa.text(
            "SELECT product_id, stock, safety_stock FROM product_stocks "
            "WHERE store_id = (SELECT store_id FROM products WHERE products.id = product_stocks.product_id)"
        )
    ).fetchall()
    for row in stocks:
        bind.execute(
            sa.text("UPDATE products SET stock = :stock, safety_stock = :safety WHERE id = :pid"),
            {"stock": row[1] or 0, "safety": row[2] or 0, "pid": row[0]},
        )

    # 2. 删除门店库存表
    op.drop_index("uq_product_stocks_product_store", table_name="product_stocks")
    op.drop_index("ix_product_stocks_store_id", table_name="product_stocks")
    op.drop_index("ix_product_stocks_tenant_id", table_name="product_stocks")
    op.drop_index("ix_product_stocks_product_id", table_name="product_stocks")
    op.drop_table("product_stocks")

    # 3. 删除会员流水门店字段
    with op.batch_alter_table("member_transactions") as batch_op:
        batch_op.drop_index("ix_member_transactions_store_id")
        batch_op.drop_column("store_id")
