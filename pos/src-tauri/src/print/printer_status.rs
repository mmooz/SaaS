//! 打印机状态模型：把 Win32 打印机状态位映射为前端可读的告警项。

use serde::Serialize;

/// 打印机已暂停（Win32 PRINTER_STATUS_PAUSED）
const STATUS_PAUSED: u32 = 0x0000_0001;
/// 打印机故障（Win32 PRINTER_STATUS_ERROR）
const STATUS_ERROR: u32 = 0x0000_0002;
/// 卡纸（Win32 PRINTER_STATUS_PAPER_JAM）
const STATUS_PAPER_JAM: u32 = 0x0000_0008;
/// 缺纸（Win32 PRINTER_STATUS_PAPER_OUT）
const STATUS_PAPER_OUT: u32 = 0x0000_0010;
/// 离线（Win32 PRINTER_STATUS_OFFLINE）
const STATUS_OFFLINE: u32 = 0x0000_0080;
/// 出纸仓已满（Win32 PRINTER_STATUS_OUTPUT_BIN_FULL）
const STATUS_OUTPUT_BIN_FULL: u32 = 0x0000_0800;
/// 打印机不可用（Win32 PRINTER_STATUS_NOT_AVAILABLE）
const STATUS_NOT_AVAILABLE: u32 = 0x0000_1000;
/// 需要人工处理（Win32 PRINTER_STATUS_USER_INTERVENTION）
const STATUS_USER_INTERVENTION: u32 = 0x0010_0000;
/// 墨粉不足（Win32 PRINTER_STATUS_NO_TONER）
const STATUS_NO_TONER: u32 = 0x0004_0000;
/// 纸盒门未关闭（Win32 PRINTER_STATUS_DOOR_OPEN）
const STATUS_DOOR_OPEN: u32 = 0x0040_0000;

/// 打印机状态信息（返回给前端）
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PrinterStatus {
    /// 打印机名称
    pub printer_name: String,
    /// Win32 原始状态位
    pub status_code: u32,
    /// 是否可以正常出票
    pub usable: bool,
    /// 状态说明列表（为空表示状态正常）
    pub problems: Vec<String>,
}

impl PrinterStatus {
    /// 按 Win32 状态位构造打印机状态
    ///
    /// # 参数
    /// - printer_name：打印机名称
    /// - status_code：GetPrinter（level 6）返回的状态位
    ///
    /// # 返回
    /// - 打印机状态：存在告警项时 usable 为 false
    pub fn from_flags(printer_name: &str, status_code: u32) -> Self {
        // 会阻断出票的状态位与中文说明（按严重度排序）
        let flags = [
            (STATUS_PAUSED, "已暂停"),
            (STATUS_ERROR, "打印机故障"),
            (STATUS_PAPER_JAM, "卡纸"),
            (STATUS_PAPER_OUT, "缺纸"),
            (STATUS_OFFLINE, "离线"),
            (STATUS_OUTPUT_BIN_FULL, "出纸仓已满"),
            (STATUS_NOT_AVAILABLE, "不可用"),
            (STATUS_USER_INTERVENTION, "需要人工处理"),
            (STATUS_NO_TONER, "墨粉不足"),
            (STATUS_DOOR_OPEN, "纸盒门未关闭"),
        ];

        let mut problems = Vec::new();
        for (flag, label) in flags {
            if status_code & flag != 0 {
                problems.push(label.to_string());
            }
        }

        Self {
            printer_name: printer_name.to_string(),
            status_code,
            usable: problems.is_empty(),
            problems,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// 状态位为 0 时应判定为可用
    #[test]
    fn zero_flags_is_usable() {
        let status = PrinterStatus::from_flags("测试打印机", 0);
        assert!(status.usable);
        assert!(status.problems.is_empty());
    }

    /// 离线 + 缺纸应同时上报并判定为不可用
    #[test]
    fn offline_and_paper_out_are_reported() {
        let status = PrinterStatus::from_flags("测试打印机", STATUS_OFFLINE | STATUS_PAPER_OUT);
        assert!(!status.usable);
        assert_eq!(status.problems, vec!["缺纸".to_string(), "离线".to_string()]);
    }
}
