//! 串口电子秤：通过 RS232 串口读取 ASCII 帧并解析重量。
//!
//! 通用文本协议：秤持续输出形如 "1.234 kg" 的数据帧，
//! 从中提取首个数字作为重量。不同厂商协议可通过调整解析规则扩展。

use std::io::Read;

use super::weigh_scale::{ScaleConnection, WeighScale};

/// 串口秤配置
#[derive(Debug, Clone)]
pub struct SerialScaleConfig {
    /// 串口名称（Windows 如 COM1，Linux 如 /dev/ttyUSB0）
    pub port_name: String,
    /// 波特率（常见 9600/4800）
    pub baud_rate: u32,
    /// 是否启用校验位
    pub parity: bool,
}

impl Default for SerialScaleConfig {
    fn default() -> Self {
        Self {
            port_name: "COM1".to_string(),
            baud_rate: 9600,
            parity: false,
        }
    }
}

/// 串口秤实现：读取串口数据流并按帧解析重量
pub struct SerialScale {
    /// 串口配置
    config: SerialScaleConfig,
    /// 串口连接对象
    port: Option<Box<dyn serialport::SerialPort>>,
    /// 皮重偏移（kg）
    tare_offset: f64,
}

impl SerialScale {
    /// 创建串口秤实例
    pub fn new(config: SerialScaleConfig) -> Self {
        Self {
            config,
            port: None,
            tare_offset: 0.0,
        }
    }

    /// 解析一行数据帧中的重量（kg）：取行内首个可解析的数值
    pub(crate) fn parse_weight_line(line: &str) -> Option<f64> {
        // 以非数值字符为分隔符切分，再逐个尝试解析（如 "1.234 kg" -> 1.234）
        line.split(|c: char| !(c.is_ascii_digit() || c == '.' || c == '-' || c == '+'))
            .filter(|s| !s.is_empty())
            .find_map(|s| s.parse::<f64>().ok())
    }
}

impl WeighScale for SerialScale {
    fn connect(&mut self) -> Result<(), String> {
        if self.port.is_some() {
            return Ok(()); // 已连接
        }
        // 打开串口：读取超时 200ms，校验位按配置启用（部分工业秤要求偶校验）
        let builder = serialport::new(&self.config.port_name, self.config.baud_rate)
            .timeout(std::time::Duration::from_millis(200));
        let builder = if self.config.parity {
            builder.parity(serialport::Parity::Even)
        } else {
            builder
        };
        let port = builder.open().map_err(|e| format!("串口打开失败: {e}"))?;
        // serialport 的 open 已返回 Box<dyn SerialPort>，直接持有即可
        self.port = Some(port);
        Ok(())
    }

    fn disconnect(&mut self) -> Result<(), String> {
        self.port = None;
        Ok(())
    }

    fn read_weight(&mut self) -> Result<f64, String> {
        let port = self.port.as_mut().ok_or("串口秤未连接")?;
        let mut buf = [0u8; 64];
        let n = port.read(&mut buf).map_err(|e| format!("串口读取失败: {e}"))?;
        let text = String::from_utf8_lossy(&buf[..n]);
        // 从数据帧中解析重量
        for line in text.lines() {
            if let Some(weight) = Self::parse_weight_line(line) {
                return Ok((weight - self.tare_offset).max(0.0));
            }
        }
        // 本次未读到有效帧，返回上次值语义：调用方以错误提示重试
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
        self.port.is_some()
    }

    fn kind(&self) -> ScaleConnection {
        ScaleConnection::Serial
    }
}
