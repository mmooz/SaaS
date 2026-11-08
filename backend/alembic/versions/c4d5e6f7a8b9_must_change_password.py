"""R19：users 新增「强制首次改密」标记。

B0 关闭了种子弱口令、B2/R8 关闭了新建用户与重置密码的默认弱口令，
但「临时口令必须由本人在首次登录时改掉」此前没有服务端强制力，管理员
重置出的随机口令会被长期使用，历史弱口令账号也只能靠运维自觉轮换。

本迁移只加一个布尔列，不改任何既有数据：
- 既有行一律取默认值 False（无需改密），避免升级后全租户账号被锁；
- 历史弱口令账号由 ``backend/tools/rotate_weak_passwords.py --apply``
  在轮换时显式置位，迁移脚本不硬编码任何账号名；
- 服务端守卫见 ``app/dependencies.py::get_current_user``，改密接口见
  ``app/api/auth.py::change_password``。

方言无关说明：``sa.false()`` 在 SQLite 编译为 0、在 PostgreSQL 编译为
false，因此本迁移逻辑可直接被 PG baseline 复用；升级前先检查列是否已存在，
对「已用离线脚本幂等加列」的库重复执行也安全（PG 切库时同样适用）。

Revision ID: c4d5e6f7a8b9
Revises: b1a2c3d4e5f6
Create Date: 2026-11-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b1a2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMN_NAME = "must_change_password"


def _has_column() -> bool:
    """判断 users 表是否已有目标列（兼容手工/离线脚本提前加列的环境）。

    :return: 列存在返回 True
    """
    columns = sa.inspect(op.get_bind()).get_columns("users")
    return any(column["name"] == COLUMN_NAME for column in columns)


def upgrade() -> None:
    """新增 must_change_password 列，已存在则跳过。"""
    if _has_column():
        return
    op.add_column(
        "users",
        sa.Column(
            COLUMN_NAME,
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    """移除 must_change_password 列（batch 模式兼容 SQLite）。"""
    if not _has_column():
        return
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column(COLUMN_NAME)
