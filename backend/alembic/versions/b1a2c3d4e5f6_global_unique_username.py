"""全局唯一用户名

Q11：登录按用户名全局查找（api/auth.py），但创建用户的唯一性校验带
tenant_id，DB 也只有非唯一索引 ix_users_username，导致两个租户可以创建
同名账号、后创建者永远无法登录或误入他人账号。统一为全平台唯一：
先检测历史重名数据（存在则拒绝升级，需人工清洗），再把非唯一索引
替换为唯一索引。

Revision ID: b1a2c3d4e5f6
Revises: 3f9a1c7b2d55
Create Date: 2026-11-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1a2c3d4e5f6"
down_revision: Union[str, None] = "3f9a1c7b2d55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """把用户名索引升级为全局唯一索引。"""
    conn = op.get_bind()
    duplicates = conn.execute(
        sa.text(
            "SELECT username, COUNT(*) AS c FROM users "
            "GROUP BY username HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if duplicates:
        names = ", ".join(str(row[0]) for row in duplicates[:10])
        raise RuntimeError(
            "存在重名账号，无法创建全局唯一索引，请先人工清洗后再升级：" + names
        )
    op.drop_index("ix_users_username", table_name="users")
    op.create_index("uq_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    """回退为普通非唯一索引（会重新允许跨租户重名，仅供回滚使用）。"""
    op.drop_index("uq_users_username", table_name="users")
    op.create_index("ix_users_username", "users", ["username"], unique=False)
