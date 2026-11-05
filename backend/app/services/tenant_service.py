"""租户管理服务：租户列表统计、创建（含初始管理员）、更新与删除校验。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Store, Tenant, User, UserStore
from app.schemas.tenant_update import TenantUpdate
from app.services.password_hasher import PasswordHasher

# 平台运营租户编码（超级管理员所在租户，不参与业务租户管理）
PLATFORM_TENANT_CODE = "platform"
# 新建租户时自动创建的默认门店名称
DEFAULT_STORE_NAME = "总店"


class TenantService:
    """租户管理服务：封装租户数据访问与业务规则校验。"""

    @staticmethod
    def list_with_stats(db: Session) -> list[dict]:
        """查询全部业务租户（排除平台租户），并统计门店数与用户数。

        :param db: 数据库会话
        :return: 租户信息字典列表（含 store_count/user_count）
        """
        tenants = db.scalars(
            select(Tenant)
            .where(Tenant.code != PLATFORM_TENANT_CODE)
            .order_by(Tenant.id.desc())
        ).all()
        if not tenants:
            return []

        # 批量统计门店数量
        store_counts = dict(
            db.execute(
                select(Store.tenant_id, func.count(Store.id))
                .where(Store.tenant_id.in_([t.id for t in tenants]))
                .group_by(Store.tenant_id)
            ).all()
        )
        # 批量统计用户数量
        user_counts = dict(
            db.execute(
                select(User.tenant_id, func.count(User.id))
                .where(User.tenant_id.in_([t.id for t in tenants]))
                .group_by(User.tenant_id)
            ).all()
        )

        return [
            {
                "id": t.id,
                "name": t.name,
                "code": t.code,
                "enabled": t.enabled,
                "created_at": t.created_at,
                "store_count": int(store_counts.get(t.id, 0)),
                "user_count": int(user_counts.get(t.id, 0)),
            }
            for t in tenants
        ]

    @staticmethod
    def get_stats(db: Session, tenant: Tenant) -> dict:
        """查询单个租户的门店数与用户数。

        :param db: 数据库会话
        :param tenant: 租户 ORM 对象
        :return: 租户信息字典（含 store_count/user_count）
        """
        store_count = int(
            db.scalar(
                select(func.count()).select_from(Store).where(Store.tenant_id == tenant.id)
            )
            or 0
        )
        user_count = int(
            db.scalar(
                select(func.count()).select_from(User).where(User.tenant_id == tenant.id)
            )
            or 0
        )
        return {
            "id": tenant.id,
            "name": tenant.name,
            "code": tenant.code,
            "enabled": tenant.enabled,
            "created_at": tenant.created_at,
            "store_count": store_count,
            "user_count": user_count,
        }

    @staticmethod
    def _assert_code_unique(db: Session, code: str, exclude_id: int | None = None) -> None:
        """校验租户编码唯一性，重复时抛 ValueError。

        :param db: 数据库会话
        :param code: 待校验的租户编码
        :param exclude_id: 排除的租户 ID（更新时排除自身）
        :return: 无返回值，校验失败抛 ValueError
        """
        stmt = select(Tenant.id).where(Tenant.code == code)
        if exclude_id is not None:
            stmt = stmt.where(Tenant.id != exclude_id)
        if db.scalar(stmt) is not None:
            raise ValueError("租户编码已存在")

    @staticmethod
    def create(
        db: Session,
        name: str,
        code: str,
        enabled: bool,
        admin_username: str | None,
        admin_password: str | None,
        admin_name: str | None,
    ) -> Tenant:
        """创建租户；填写管理员账号时同时创建默认门店与租户管理员。

        :param db: 数据库会话
        :param name: 租户名称
        :param code: 租户编码
        :param enabled: 是否启用
        :param admin_username: 初始管理员登录账号（可为空）
        :param admin_password: 初始管理员密码（可为空）
        :param admin_name: 初始管理员姓名（可为空）
        :return: 已提交的租户 ORM 对象
        """
        code = code.strip()
        TenantService._assert_code_unique(db, code)

        tenant = Tenant(name=name.strip(), code=code, enabled=enabled)
        db.add(tenant)
        db.flush()

        # 可选：创建初始管理员，并自动建默认门店、授权访问
        if admin_username:
            username = admin_username.strip()
            # 登录按用户名全局查找，因此账号需全局唯一
            exists = db.scalar(select(User.id).where(User.username == username))
            if exists is not None:
                raise ValueError("管理员账号已存在")
            store = Store(tenant_id=tenant.id, name=DEFAULT_STORE_NAME, enabled=True)
            db.add(store)
            db.flush()
            user = User(
                tenant_id=tenant.id,
                username=username,
                password_hash=PasswordHasher.hash(admin_password or "123456"),
                name=(admin_name or username).strip(),
                role="admin",
                enabled=True,
            )
            db.add(user)
            db.flush()
            db.add(UserStore(user_id=user.id, store_id=store.id))

        db.commit()
        db.refresh(tenant)
        return tenant

    @staticmethod
    def update(db: Session, tenant: Tenant, data: TenantUpdate) -> Tenant:
        """更新租户信息（仅修改传入字段）。

        :param db: 数据库会话
        :param tenant: 待更新的租户 ORM 对象
        :param data: 更新请求体
        :return: 已提交的租户 ORM 对象
        """
        updates = data.model_dump(exclude_unset=True)
        if "code" in updates and updates["code"]:
            new_code = updates["code"].strip()
            if new_code != tenant.code:
                TenantService._assert_code_unique(db, new_code, exclude_id=tenant.id)
            tenant.code = new_code
        if "name" in updates and updates["name"]:
            tenant.name = updates["name"].strip()
        if "enabled" in updates and updates["enabled"] is not None:
            tenant.enabled = updates["enabled"]
        db.commit()
        db.refresh(tenant)
        return tenant

    @staticmethod
    def delete(db: Session, tenant: Tenant) -> None:
        """删除租户：存在门店或用户时拒绝，避免产生孤儿数据。

        :param db: 数据库会话
        :param tenant: 待删除的租户 ORM 对象
        :return: 无返回值，校验失败抛 ValueError
        """
        if tenant.code == PLATFORM_TENANT_CODE:
            raise ValueError("平台租户不允许删除")
        store_count = int(
            db.scalar(
                select(func.count()).select_from(Store).where(Store.tenant_id == tenant.id)
            )
            or 0
        )
        user_count = int(
            db.scalar(
                select(func.count()).select_from(User).where(User.tenant_id == tenant.id)
            )
            or 0
        )
        if store_count or user_count:
            raise ValueError("租户下存在门店或用户，请先清理后再删除")
        db.delete(tenant)
        db.commit()
