//! 鲜衡 POS Tauri 应用入口：注册称重命令与状态管理。
//!
//! 前端通过 `@tauri-apps/api` 的 invoke 调用以下命令完成电子秤接入。

use std::sync::Mutex;

use tauri::State;

use crate::scale::{ScaleConnection, ScaleFactory, WeighScale};

mod scale;

/// 全局应用状态：持有当前电子秤实例（跨线程共享，需 Send）
struct ScaleState(Mutex<Box<dyn WeighScale + Send>>);

/// 连接电子秤命令
///
/// # 参数
/// - connection: 连接方式（mock/serial/tcp）
/// - port_name: 串口名称（serial 时使用）
/// - baud_rate: 波特率（serial 时使用）
#[tauri::command]
fn connect_scale(
    connection: String,
    port_name: Option<String>,
    baud_rate: Option<u32>,
    state: State<'_, ScaleState>,
) -> Result<String, String> {
    let scale_conn = match connection.as_str() {
        "mock" => ScaleConnection::Mock,
        "serial" => ScaleConnection::Serial,
        "tcp" => ScaleConnection::Tcp,
        _ => return Err(format!("未知秤连接方式: {connection}")),
    };
    let mut scale = ScaleFactory::create(&scale_conn, port_name.as_deref(), baud_rate);
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

/// 应用入口：启动 Tauri 并注册称重命令
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // 初始状态使用模拟秤（无硬件时可正常开发调试）
    let initial_scale = ScaleFactory::create(&ScaleConnection::Mock, None, None);
    tauri::Builder::default()
        .manage(ScaleState(Mutex::new(initial_scale)))
        .invoke_handler(tauri::generate_handler![
            connect_scale,
            read_scale_weight,
            scale_tare,
            scale_zero,
            scale_connected
        ])
        .run(tauri::generate_context!())
        .expect("运行 Tauri 应用失败");
}
