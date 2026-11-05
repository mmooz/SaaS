//! 秤工厂：根据配置创建具体的秤实现（可插拔协议适配）。

use super::mock_scale::MockScale;
use super::serial_scale::{SerialScale, SerialScaleConfig};
use super::tcp_scale::{TcpScale, TcpScaleConfig};
use super::weigh_scale::{ScaleConnection, WeighScale};

/// 称重设备工厂：按连接方式创建对应实现
pub struct ScaleFactory;

impl ScaleFactory {
    /// 创建秤实例
    ///
    /// # 参数
    /// - connection: 连接方式（mock/serial/tcp）
    /// - port_name: 串口名称（serial 时使用）
    /// - baud_rate: 波特率（serial 时使用）
    /// - tcp_addr: 网口地址 ip:port（tcp 时使用）
    pub fn create(
        connection: &ScaleConnection,
        port_name: Option<&str>,
        baud_rate: Option<u32>,
        tcp_addr: Option<&str>,
    ) -> Box<dyn WeighScale + Send> {
        match connection {
            ScaleConnection::Mock => Box::new(MockScale::new()),
            ScaleConnection::Serial => Box::new(SerialScale::new(SerialScaleConfig {
                port_name: port_name.unwrap_or("COM1").to_string(),
                baud_rate: baud_rate.unwrap_or(9600),
                ..Default::default()
            })),
            ScaleConnection::Tcp => Box::new(TcpScale::new(TcpScaleConfig {
                addr: tcp_addr.unwrap_or("192.168.1.100:5000").to_string(),
            })),
        }
    }
}
