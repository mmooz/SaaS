"""默认账号种子：开发期 users 表为空时写入演示账号，便于直接登录体验。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.services.password_hasher import PasswordHasher


class UserSeeder:
    """默认账号种子器：按账号名判断是否已存在，避免重复写入。"""

    # 默认账号：账号、姓名、角色、是否启用
    DEFAULT_USERS = [
        ("admin", "张经理", "admin", True),
        ("store01", "王店长", "manager", True),
        ("cashier01", "李收银", "cashier", True),
        ("cashier02", "张收银", "cashier", True),
        ("cashier03", "陈收银", "cashier", False),
    ]
    # 默认密码（仅用于开发期演示账号）
    DEFAULT_PASSWORD = "123456"

    @classmethod
    def seed(cls, db: Session) -> int:
        """写入尚不存在的默认账号。

        :param db: 数据库会话
        :return: 本次新增的账号数量
        """
        created = 0
        for username, name, role, enabled in cls.DEFAULT_USERS:
            exists = db.scalar(select(User).where(User.username == username))
            if exists:
                continue
            db.add(
                User(
                    username=username,
                    password_hash=PasswordHasher.hash(cls.DEFAULT_PASSWORD),
                    name=name,
                    role=role,
                    enabled=enabled,
                )
            )
            created += 1
        if created:
            db.commit()
        return created
