"""系统设置服务：按分组读写门店信息与收银参数。"""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SystemSetting

# 允许的设置分组
SETTING_GROUPS = ("store", "cashier")

# ---- 会员资金相关的服务端配置（Q02）----
# key 命名沿用后台「收银参数」表单的 camelCase 约定（admin-web/src/views/Settings.vue）
# 复用已有设置项：积分比例 pointRatio（消费 1 元获得的积分）
POINT_RATIO_KEY = "pointRatio"
DEFAULT_POINT_RATIO = 1.0
# 新增明确配置项：每充值 1 元赠送的积分（客户端不可伪造 bonus_points）
RECHARGE_BONUS_POINTS_PER_YUAN_KEY = "rechargeBonusPointsPerYuan"
DEFAULT_RECHARGE_BONUS_POINTS_PER_YUAN = 0.0
# 积分比例上限：异常配置（含客户端历史天文数字）一律回退默认值，防止资损
MAX_POINT_RATIO = 100.0
# 单笔充值金额上限（元，含赠金）：服务端安全上限，客户端不可覆盖
MAX_RECHARGE_AMOUNT = 10000.0


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
    def _resolve_ratio(value: object, default: float) -> float:
        """把配置值解析为合法的非负比例，缺失或越界时回退默认值。

        :param value: 配置字典中的原始值
        :param default: 回退默认值
        :return: 位于 [0, MAX_POINT_RATIO] 区间内的浮点数
        """
        try:
            ratio = float(value)
        except (TypeError, ValueError):
            return default
        if ratio < 0 or ratio > MAX_POINT_RATIO:
            return default
        return ratio

    @staticmethod
    def get_member_point_config(
        db: Session, tenant_id: int, store_id: int
    ) -> tuple[float, float]:
        """读取会员积分相关的服务端配置（客户端不可覆盖）。

        复用 system_settings 的 cashier 分组：pointRatio 沿用后台「积分比例」已有
        设置项；rechargeBonusPointsPerYuan 为本次新增的「每元充值赠送积分」配置项。
        未配置或配置非法时回退到安全默认值（1 元 1 分 / 不自动赠送积分）。

        :param db: 数据库会话
        :param tenant_id: 所属租户 ID
        :param store_id: 所属门店 ID
        :return: (每元消费积分, 每元充值赠送积分)
        """
        cfg = SettingService.get_group(db, "cashier", tenant_id, store_id)
        points_per_yuan = SettingService._resolve_ratio(
            cfg.get(POINT_RATIO_KEY), DEFAULT_POINT_RATIO
        )
        bonus_per_yuan = SettingService._resolve_ratio(
            cfg.get(RECHARGE_BONUS_POINTS_PER_YUAN_KEY),
            DEFAULT_RECHARGE_BONUS_POINTS_PER_YUAN,
        )
        return points_per_yuan, bonus_per_yuan

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
