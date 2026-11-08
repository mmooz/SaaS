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
# R4：复用后台「储值充值赠送比例」rechargeGift（百分比，10 表示 10% / 充 100 送 10）。
# 原新增项 rechargeBonusPointsPerYuan 在后台 UI 无任何输入控件，运营配置永不生效，
# 形成契约断层；B3 废弃该新增项，改为由 rechargeGift 做「百分比 → 每元赠送积分」
# 单位换算，运营在 Settings.vue 的配置即刻生效。
RECHARGE_GIFT_KEY = "rechargeGift"
DEFAULT_RECHARGE_GIFT_PERCENT = 0.0
# 百分比换算为「每 1 元」比例的系数：10% -> 0.1（充 100 送 10 分）
PERCENT_TO_PER_YUAN = 100.0
# 积分比例 / 赠送百分比上限：异常配置（含客户端历史天文数字）一律回退默认值，防止资损
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

        复用 system_settings 的 cashier 分组、且全部复用后台已有输入控件：
        ``pointRatio`` = 消费 1 元获得的积分；``rechargeGift`` = 储值充值赠送比例
        （百分比）。R4 把后者换算为「每充值 1 元赠送积分」= ``rechargeGift / 100``，
        例如后台填 10（10%）时，充值 100 元赠送 10 积分。
        未配置或配置越界（``MAX_POINT_RATIO``）时回退安全默认值（1 元 1 分 / 不赠送）。

        :param db: 数据库会话
        :param tenant_id: 所属租户 ID
        :param store_id: 所属门店 ID
        :return: (每元消费积分, 每元充值赠送积分)
        """
        cfg = SettingService.get_group(db, "cashier", tenant_id, store_id)
        points_per_yuan = SettingService._resolve_ratio(
            cfg.get(POINT_RATIO_KEY), DEFAULT_POINT_RATIO
        )
        gift_percent = SettingService._resolve_ratio(
            cfg.get(RECHARGE_GIFT_KEY), DEFAULT_RECHARGE_GIFT_PERCENT
        )
        bonus_per_yuan = gift_percent / PERCENT_TO_PER_YUAN
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
