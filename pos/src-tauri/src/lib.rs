//! 鲜衡 POS Tauri 应用入口：注册称重与原生打印命令。
//!
//! 前端通过 Tauri invoke 调用以下命令完成电子秤接入与打印机直连出票。

use std::sync::Mutex;

use tauri::State;

use crate::scale::{ScaleConnection, ScaleFactory, WeighScale};

mod print;
mod scale;

/// 全局应用状态：持有当前电子秤实例（跨线程共享，需 Send）
struct ScaleState(Mutex<Box<dyn WeighScale + Send>>);

/// 连接电子秤命令
///
/// # 参数
/// - connection: 连接方式（mock/serial/tcp）
/// - port_name: 串口名称（serial 时使用）
/// - baud_rate: 波特率（serial 时使用）
/// - tcp_addr: 网口地址 ip:port（tcp 时使用）
#[tauri::command]
fn connect_scale(
    connection: String,
    port_name: Option<String>,
    baud_rate: Option<u32>,
    tcp_addr: Option<String>,
    state: State<'_, ScaleState>,
) -> Result<String, String> {
    let scale_conn = match connection.as_str() {
        "mock" => ScaleConnection::Mock,
        "serial" => ScaleConnection::Serial,
        "tcp" => ScaleConnection::Tcp,
        _ => return Err(format!("未知秤连接方式: {connection}")),
    };
    let mut scale = ScaleFactory::create(
        &scale_conn,
        port_name.as_deref(),
        baud_rate,
        tcp_addr.as_deref(),
    );
    scale.connect()?;
    let kind = scale.kind();
    *state.0.lock().unwrap() = scale;
    Ok(format!("秤已连接: {kind:?}"))
}

/// 读取当前重量命令（kg）
#[tauri::command]
fn read_scale_weight(state: State<'_, ScaleState>) -> Result<f64, String> {
    let mut scale = state.0.lock().unwrap();
    scale.read_weight()
}

/// 去皮命令
#[tauri::command]
fn scale_tare(state: State<'_, ScaleState>) -> Result<(), String> {
    let mut scale = state.0.lock().unwrap();
    scale.tare()
}

/// 置零命令
#[tauri::command]
fn scale_zero(state: State<'_, ScaleState>) -> Result<(), String> {
    let mut scale = state.0.lock().unwrap();
    scale.zero()
}

/// 查询秤连接状态命令
#[tauri::command]
fn scale_connected(state: State<'_, ScaleState>) -> Result<bool, String> {
    let scale = state.0.lock().unwrap();
    Ok(scale.is_connected())
}

/// 列出本机可用打印机命令
#[tauri::command]
fn list_printers() -> Result<Vec<String>, String> {
    crate::print::list_printers()
}

/// 查询打印机状态命令
///
/// # 参数
/// - printer_name：系统打印机名称
#[tauri::command]
fn printer_status(printer_name: String) -> Result<crate::print::PrinterStatus, String> {
    crate::print::printer_status(&printer_name)
}

/// 原生直连打印小票命令（ESC/POS）
///
/// # 参数
/// - printer_name：系统打印机名称
/// - job：小票打印任务
#[tauri::command]
fn native_print_receipt(
    printer_name: String,
    job: crate::print::ReceiptJob,
) -> Result<(), String> {
    let data = crate::print::EscPosBuilder::build(&job)?;
    crate::print::print_raw(&printer_name, &data)
}

/// 原生直连打印称重标签命令（TSPL）
///
/// # 参数
/// - printer_name：系统打印机名称
/// - job：标签打印任务
///
/// # 返回
/// - 实际打印的标签张数
#[tauri::command]
fn native_print_labels(
    printer_name: String,
    job: crate::print::LabelJob,
) -> Result<u32, String> {
    let count = job.labels.len() as u32;
    let data = crate::print::TsplBuilder::build(&job)?;
    crate::print::print_raw(&printer_name, &data)?;
    Ok(count)
}

/// 查询当前平台是否支持原生直连打印
#[tauri::command]
fn native_print_supported() -> bool {
    cfg!(target_os = "windows")
}

/// 应用入口：启动 Tauri 并注册称重与打印命令
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // 初始状态使用模拟秤（无硬件时可正常开发调试）
    let initial_scale = ScaleFactory::create(&ScaleConnection::Mock, None, None, None);
    tauri::Builder::default()
        // 注册本地 SQLite 插件（离线订单/退货/班次持久化）
        .plugin(tauri_plugin_sql::Builder::default().build())
        .manage(ScaleState(Mutex::new(initial_scale)))
        .invoke_handler(tauri::generate_handler![
            connect_scale,
            read_scale_weight,
            scale_tare,
            scale_zero,
            scale_connected,
            list_printers,
            printer_status,
            native_print_receipt,
            native_print_labels,
            native_print_supported
        ])
        .run(tauri::generate_context!())
        .expect("运行 Tauri 应用失败");
}
