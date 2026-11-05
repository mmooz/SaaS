//! 网口电子秤：通过 TCP 连接读取秤输出的 ASCII 数据帧并解析重量。
//!
//! 协议与串口秤保持一致（每帧一行文本，行内首个数值为重量 kg），
//! 适配常见「串口服转网口」模块或原生网口秤。

use std::io::Read;
use std::net::TcpStream;
use std::time::Duration;

use super::serial_scale::SerialScale;
use super::weigh_scale::{ScaleConnection, WeighScale};

/// 网口秤配置
#[derive(Debug, Clone)]
pub struct TcpScaleConfig {
    /// 秤地址（ip:port，如 192.168.1.100:5000）
    pub addr: String,
}

impl Default for TcpScaleConfig {
    fn default() -> Self {
        Self {
            addr: "192.168.1.100:5000".to_string(),
        }
    }
}

/// 网口秤实现：从 TCP 数据流按帧解析重量
pub struct TcpScale {
    /// 网口配置
    config: TcpScaleConfig,
    /// TCP 连接对象
    stream: Option<TcpStream>,
    /// 皮重偏移（kg）
    tare_offset: f64,
}

impl TcpScale {
    /// 创建网口秤实例
    ///
    /// # 参数
    /// - config：网口秤配置
    pub fn new(config: TcpScaleConfig) -> Self {
        Self {
            config,
            stream: None,
            tare_offset: 0.0,
        }
    }
}

impl WeighScale for TcpScale {
    fn connect(&mut self) -> Result<(), String> {
        if self.stream.is_some() {
            return Ok(()); // 已连接
        }
        // 建立 TCP 连接并设置 200ms 读超时，避免阻塞收银界面
        let stream = TcpStream::connect(&self.config.addr)
            .map_err(|e| format!("网口秤连接失败: {e}"))?;
        stream
            .set_read_timeout(Some(Duration::from_millis(200)))
            .map_err(|e| format!("设置读超时失败: {e}"))?;
        self.stream = Some(stream);
        Ok(())
    }

    fn disconnect(&mut self) -> Result<(), String> {
        self.stream = None;
        Ok(())
    }

    fn read_weight(&mut self) -> Result<f64, String> {
        let stream = self.stream.as_mut().ok_or("网口秤未连接")?;
        let mut buf = [0u8; 64];
        let n = stream.read(&mut buf).map_err(|e| format!("网口读取失败: {e}"))?;
        let text = String::from_utf8_lossy(&buf[..n]);
        // 复用串口秤的文本帧解析规则
        for line in text.lines() {
            if let Some(weight) = SerialScale::parse_weight_line(line) {
                return Ok((weight - self.tare_offset).max(0.0));
            }
        }
        Err("未收到有效称重数据帧".to_string())
    }

    fn tare(&mut self) -> Result<(), String> {
        let weight = self.read_weight()?;
        self.tare_offset = weight;
        Ok(())
    }

    fn zero(&mut self) -> Result<(), String> {
        self.tare_offset = 0.0;
        Ok(())
    }

    fn is_connected(&self) -> bool {
        self.stream.is_some()
    }

    fn kind(&self) -> ScaleConnection {
        ScaleConnection::Tcp
    }
}
