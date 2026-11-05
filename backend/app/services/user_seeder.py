"""默认账号种子：开发期 users 表为空时写入演示账号，便于直接登录体验。

多租户改造后，种子同时创建默认租户与门店，并把演示账号挂到该租户的默认门店；
另外创建平台租户与超级管理员账号，用于跨租户管理。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Store, Tenant, User, UserStore
from app.services.password_hasher import PasswordHasher
from app.services.tenant_service import PLATFORM_TENANT_CODE


class UserSeeder:
    """默认账号种子器：按账号名判断是否已存在，避免重复写入。"""

    # 平台租户名称（超级管理员所在租户）
    PLATFORM_TENANT_NAME = "平台运营中心"
    # 超级管理员：账号、姓名、角色、是否启用
    SUPER_USER = ("superadmin", "超级管理员", "super", True)
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
        """写入平台租户、默认租户、门店、超级管理员与演示账号。

        :param db: 数据库会话
        :return: 本次新增的账号数量
        """
        # 1. 确保存在平台租户（超级管理员归属，不对外提供业务数据）
        platform = db.scalar(select(Tenant).where(Tenant.code == PLATFORM_TENANT_CODE))
        if not platform:
            platform = Tenant(
                name=cls.PLATFORM_TENANT_NAME, code=PLATFORM_TENANT_CODE, enabled=True
            )
            db.add(platform)
            db.flush()

        # 2. 确保存在默认租户（不存在则创建）
        tenant = db.scalar(select(Tenant).where(Tenant.code == "default"))
        if not tenant:
            tenant = Tenant(name="鲜衡云演示租户", code="default", enabled=True)
            db.add(tenant)
            db.flush()

        # 3. 确保存在默认门店（不存在则创建）
        store = db.scalar(select(Store).where(Store.tenant_id == tenant.id, Store.name == "总店"))
        if not store:
            store = Store(tenant_id=tenant.id, name="总店", address="演示门店地址", phone="0000-0000000", enabled=True)
            db.add(store)
            db.flush()

        # 4. 写入超级管理员（归属平台租户，不绑定任何门店）
        created = 0
        super_username, super_name, super_role, super_enabled = cls.SUPER_USER
        if not db.scalar(select(User).where(User.username == super_username)):
            db.add(
                User(
                    username=super_username,
                    password_hash=PasswordHasher.hash(cls.DEFAULT_PASSWORD),
                    name=super_name,
                    role=super_role,
                    enabled=super_enabled,
                    tenant_id=platform.id,
                )
            )
            created += 1

        # 5. 写入尚不存在的演示账号，并关联默认门店
        for username, name, role, enabled in cls.DEFAULT_USERS:
            exists = db.scalar(select(User).where(User.username == username))
            if exists:
                continue
            user = User(
                username=username,
                password_hash=PasswordHasher.hash(cls.DEFAULT_PASSWORD),
                name=name,
                role=role,
                enabled=enabled,
                tenant_id=tenant.id,
            )
            db.add(user)
            db.flush()
            # 演示账号均授权访问默认门店
            db.add(UserStore(user_id=user.id, store_id=store.id))
            created += 1
        if created:
            db.commit()
        return created

