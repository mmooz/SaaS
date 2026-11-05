//! 小票打印任务数据模型。

use serde::Deserialize;

/// 小票打印任务：由前端把订单与门店信息组装后传入原生打印层
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReceiptJob {
    /// 门店名称
    pub store_name: String,
    /// 门店地址
    #[serde(default)]
    pub store_address: String,
    /// 联系电话
    #[serde(default)]
    pub phone: String,
    /// 小票抬头
    #[serde(default)]
    pub receipt_header: String,
    /// 页脚广告语
    #[serde(default)]
    pub slogan: String,
    /// 纸宽（mm），58 或 80
    #[serde(default = "default_paper_width")]
    pub paper_width: u32,
    /// 订单号（同时作为 CODE128 条码内容）
    pub order_no: String,
    /// 交易时间文本
    #[serde(default)]
    pub time: String,
    /// 收银员姓名
    #[serde(default)]
    pub cashier_name: String,
    /// 会员手机号
    #[serde(default)]
    pub member_mobile: Option<String>,
    /// 商品明细
    #[serde(default)]
    pub items: Vec<super::receipt_item::ReceiptItem>,
    /// 应收合计（优惠前）
    #[serde(default)]
    pub total_amount: f64,
    /// 优惠金额
    #[serde(default)]
    pub discount: f64,
    /// 支付方式
    #[serde(default)]
    pub pay_method: Option<String>,
    /// 实收现金
    #[serde(default)]
    pub cash_received: Option<f64>,
    /// 找零
    #[serde(default)]
    pub change: Option<f64>,
}

/// 纸宽默认值（58mm）
fn default_paper_width() -> u32 {
    58
}
