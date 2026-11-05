//! 单张称重标签数据模型。

use serde::Deserialize;

/// 单张称重价格标签
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LabelItem {
    /// 商品名称
    pub name: String,
    /// 重量（kg）
    pub weight: f64,
    /// 单价（元/kg）
    pub price: f64,
    /// 金额
    pub amount: f64,
    /// 15 位标签码（同时作为 CODE128 条码内容）
    pub code: String,
}
