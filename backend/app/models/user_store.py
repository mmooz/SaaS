"""用户门店关联模型：一个用户可访问其所属租户下的多个门店。"""

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.snowflake import next_id


class UserStore(Base):
    """用户门店关联表：记录用户被授权访问的门店。"""

    __tablename__ = "user_stores"

    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=next_id)
    # 用户 ID
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True, nullable=False
    )
    # 门店 ID
    store_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stores.id"), index=True, nullable=False
    )
