"""离线班次批量补传请求模型。"""

from pydantic import BaseModel

from app.schemas.shift_sync_item import ShiftSyncItem


class ShiftSyncRequest(BaseModel):
    """离线收银端批量补传班次的请求体。"""

    # 待补传的班次快照列表
    shifts: list[ShiftSyncItem] = []
