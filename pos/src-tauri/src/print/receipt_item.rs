//! 小票商品明细数据模型。

use serde::Deserialize;

/// 小票商品明细
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReceiptItem {
    /// 商品名称
    pub name: String,
    /// 是否称重商品
    #[serde(default)]
    pub weighted: bool,
    /// 重量（kg，称重商品使用）
    #[serde(default)]
    pub weight: Option<f64>,
    /// 数量（按件商品使用）
    #[serde(default)]
    pub qty: Option<f64>,
    /// 单价
    pub price: f64,
    /// 小计金额
    pub amount: f64,
}
