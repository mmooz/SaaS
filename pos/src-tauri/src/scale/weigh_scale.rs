//! 电子秤统一接口定义：收银逻辑只依赖此 trait，具体秤型通过工厂创建。

use serde::Serialize;

/// 秤连接方式枚举（可插拔协议适配）
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum ScaleConnection {
    /// 模拟秤（开发调试/无硬件演示）
    Mock,
    /// 串口秤（RS232 通用文本协议）
    Serial,
    /// 网口秤（预留扩展）
    Tcp,
}

/// 电子秤统一接口：所有秤型实现必须满足该接口
pub trait WeighScale {
    /// 连接秤设备
    fn connect(&mut self) -> Result<(), String>;

    /// 断开连接
    fn disconnect(&mut self) -> Result<(), String>;

    /// 读取当前重量（单位 kg，含皮重偏移后的净重）
    fn read_weight(&mut self) -> Result<f64, String>;

    /// 去皮：将当前重量作为皮重
    fn tare(&mut self) -> Result<(), String>;

    /// 置零：清空皮重并归零
    fn zero(&mut self) -> Result<(), String>;

    /// 是否已连接
    fn is_connected(&self) -> bool;

    /// 返回秤型标识（mock/serial/tcp）
    fn kind(&self) -> ScaleConnection;
}
