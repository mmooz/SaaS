"""操作日志服务：记录关键操作并提供分页查询。"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import OperationLog, User
from app.schemas.operation_log_out import OperationLogOut


class OperationLogService:
    """操作日志服务：统一写入与查询操作留痕。"""

    @staticmethod
    def record(
        db: Session,
        action: str,
        detail: str | None = None,
        operator_id: int | None = None,
        tenant_id: int | None = None,
    ) -> None:
        """写入一条操作日志（不提交事务，由调用方统一提交）。

        :param db: 数据库会话
        :param action: 操作动作（如 登录/退款/交班/批量改价）
        :param detail: 操作详情
        :param operator_id: 操作人用户 ID
        :param tenant_id: 所属租户 ID（多租户隔离用）
        """
        if tenant_id is None:
            raise ValueError("多租户模式下操作日志必须指定 tenant_id")
        db.add(
            OperationLog(
                operator_id=operator_id,
                action=action,
                detail=detail,
                tenant_id=tenant_id,
            )
        )

    @staticmethod
    def list_logs(
        db: Session, keyword: str | None, page: int, page_size: int
    ) -> dict:
        """分页查询操作日志，关联操作人账号/姓名/角色。

        :param db: 数据库会话
        :param keyword: 搜索关键字（匹配操作内容或操作人账号/姓名）
        :param page: 页码（从 1 开始）
        :param page_size: 每页数量
        :return: {total, page, page_size, items}
        """
        stmt = (
            select(OperationLog, User.username, User.name, User.role)
            .outerjoin(User, User.id == OperationLog.operator_id)
            .order_by(OperationLog.id.desc())
        )
        if keyword:
            kw = f"%{keyword}%"
            stmt = stmt.where(
                or_(OperationLog.action.like(kw), OperationLog.detail.like(kw), User.username.like(kw), User.name.like(kw))
            )
        total = db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = db.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        ).all()
        items = [
            OperationLogOut(
                id=log.id,
                operator=username,
                operator_name=name,
                role=role,
                action=log.action,
                detail=log.detail,
                created_at=log.created_at,
            )
            for log, username, name, role in rows
        ]
        return {"total": total, "page": page, "page_size": page_size, "items": items}
