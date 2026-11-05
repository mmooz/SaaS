//! 原生打印模块：把订单转为 ESC/POS / TSPL 指令并通过系统打印队列直连输出。

mod escpos_builder;
mod gbk;
mod label_item;
mod label_job;
mod receipt_item;
mod receipt_job;
mod tspl_builder;
#[cfg(target_os = "windows")]
mod win_spooler;

pub use escpos_builder::EscPosBuilder;
pub use label_job::LabelJob;
pub use receipt_job::ReceiptJob;
pub use tspl_builder::TsplBuilder;

/// 列出本机可用打印机名称
///
/// # 返回
/// - `Ok(Vec<String>)`：打印机名称列表
/// - `Err(String)`：当前平台不支持或枚举失败
pub fn list_printers() -> Result<Vec<String>, String> {
    #[cfg(target_os = "windows")]
    {
        win_spooler::WinSpooler::list()
    }
    #[cfg(not(target_os = "windows"))]
    {
        Err("当前平台暂不支持原生直连打印".to_string())
    }
}

/// 向指定打印机发送原始字节指令
///
/// # 参数
/// - printer：系统打印机名称
/// - data：完整指令字节流
pub fn print_raw(printer: &str, data: &[u8]) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        win_spooler::WinSpooler::print_raw(printer, data)
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = (printer, data);
        Err("当前平台暂不支持原生直连打印".to_string())
    }
}
