"""门店输出模型。"""

from pydantic import BaseModel, ConfigDict

from app.schemas.snowflake_id import SnowflakeId


class StoreOut(BaseModel):
    """门店信息：登录后返回用户可访问的门店列表。"""

    model_config = ConfigDict(from_attributes=True)

    # 门店 ID
    id: SnowflakeId
    # 门店名称
    name: str
    # 门店地址
    address: str | None = None
    # 联系电话
    phone: str | None = None
    # 是否启用（停用门店不出现在可切换列表）
    enabled: bool = True
