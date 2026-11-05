"""系统设置服务：按分组读写门店信息与收银参数。"""

import json

from sqlalchemy.orm import Session

from app.models import SystemSetting

# 允许的设置分组
SETTING_GROUPS = ("store", "cashier")


class SettingService:
    """系统设置服务：以 JSON 文本按分组存取设置项。"""

    @staticmethod
    def get_group(db: Session, group: str) -> dict:
        """读取指定分组的设置内容。

        :param db: 数据库会话
        :param group: 分组名（store/cashier）
        :return: 设置字典（不存在时为空字典）
        """
        setting = db.get(SystemSetting, group)
        if not setting:
            return {}
        try:
            return json.loads(setting.value)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def get_all(db: Session) -> dict:
        """读取全部分组设置。

        :param db: 数据库会话
        :return: {group: 设置字典}
        """
        return {group: SettingService.get_group(db, group) for group in SETTING_GROUPS}

    @staticmethod
    def save_group(db: Session, group: str, data: dict) -> dict:
        """保存指定分组的设置内容（整体覆盖）。

        :param db: 数据库会话
        :param group: 分组名（store/cashier）
        :param data: 设置字典
        :return: 保存后的设置字典
        """
        setting = db.get(SystemSetting, group)
        text = json.dumps(data, ensure_ascii=False)
        if setting:
            setting.value = text
        else:
            db.add(SystemSetting(group=group, value=text))
        db.commit()
        return data
