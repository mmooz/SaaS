//! 标签打印任务数据模型。

use serde::Deserialize;

/// 标签打印任务：一次可包含多张称重标签
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LabelJob {
    /// 门店名称
    pub store_name: String,
    /// 打印时间文本
    #[serde(default)]
    pub print_time: String,
    /// 标签列表
    pub labels: Vec<super::label_item::LabelItem>,
}
