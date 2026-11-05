"""系统设置服务：按分组读写门店信息与收银参数。"""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SystemSetting

# 允许的设置分组
SETTING_GROUPS = ("store", "cashier")


class SettingService:
    """系统设置服务：以 JSON 文本按分组存取设置项（按租户+门店+分组唯一）。"""

    @staticmethod
    def get_group(db: Session, group: str, tenant_id: int, store_id: int) -> dict:
        """读取指定分组的设置内容（按租户+门店+分组复合主键）。

        :param db: 数据库会话
        :param group: 分组名（store/cashier）
        :param tenant_id: 所属租户 ID
        :param store_id: 所属门店 ID
        :return: 设置字典（不存在时为空字典）
        """
        setting = db.scalar(
            select(SystemSetting).where(
                SystemSetting.tenant_id == tenant_id,
                SystemSetting.store_id == store_id,
                SystemSetting.group == group,
            )
        )
        if not setting:
            return {}
        try:
            return json.loads(setting.value)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def get_all(db: Session, tenant_id: int, store_id: int) -> dict:
        """读取全部分组设置（当前租户+门店）。

        :param db: 数据库会话
        :param tenant_id: 所属租户 ID
        :param store_id: 所属门店 ID
        :return: {group: 设置字典}
        """
        return {
            group: SettingService.get_group(db, group, tenant_id, store_id)
            for group in SETTING_GROUPS
        }

    @staticmethod
    def save_group(
        db: Session, group: str, data: dict, tenant_id: int, store_id: int
    ) -> dict:
        """保存指定分组的设置内容（整体覆盖，按复合主键 upsert）。

        :param db: 数据库会话
        :param group: 分组名（store/cashier）
        :param data: 设置字典
        :param tenant_id: 所属租户 ID
        :param store_id: 所属门店 ID
        :return: 保存后的设置字典
        """
        setting = db.scalar(
            select(SystemSetting).where(
                SystemSetting.tenant_id == tenant_id,
                SystemSetting.store_id == store_id,
                SystemSetting.group == group,
            )
        )
        text = json.dumps(data, ensure_ascii=False)
        if setting:
            setting.value = text
        else:
            db.add(
                SystemSetting(
                    tenant_id=tenant_id, store_id=store_id, group=group, value=text
                )
            )
        db.commit()
        return data
