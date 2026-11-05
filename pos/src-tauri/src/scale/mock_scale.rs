//! 模拟秤：无硬件环境下模拟重量变化，用于开发与演示。

use std::time::Duration;

use super::weigh_scale::{ScaleConnection, WeighScale};

/// 模拟秤实现：每次读取产生小幅波动，模拟真实秤的称重过程
pub struct MockScale {
    /// 目标重量（kg）
    target_weight: f64,
    /// 当前重量（kg）
    current_weight: f64,
    /// 皮重偏移（kg）
    tare_offset: f64,
    /// 是否已连接
    connected: bool,
}

impl MockScale {
    /// 创建模拟秤实例（初始目标重量随机 0.3~1.2kg）
    pub fn new() -> Self {
        // 使用时间种子产生可复现性较弱的随机目标重量
        let seed = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or(Duration::ZERO)
            .subsec_nanos() as f64;
        let target = 0.3 + (seed % 900_000.0) / 1_000_000.0;
        Self {
            target_weight: target,
            current_weight: 0.0,
            tare_offset: 0.0,
            connected: false,
        }
    }
}

impl WeighScale for MockScale {
    fn connect(&mut self) -> Result<(), String> {
        self.connected = true;
        Ok(())
    }

    fn disconnect(&mut self) -> Result<(), String> {
        self.connected = false;
        Ok(())
    }

    fn read_weight(&mut self) -> Result<f64, String> {
        if !self.connected {
            return Err("模拟秤未连接".to_string());
        }
        // 向目标重量缓慢收敛，接近目标后小幅抖动
        if self.current_weight < self.target_weight {
            self.current_weight += 0.15 + (self.target_weight - self.current_weight) * 0.1;
        } else {
            self.current_weight = self.target_weight;
        }
        Ok((self.current_weight - self.tare_offset).max(0.0))
    }

    fn tare(&mut self) -> Result<(), String> {
        self.tare_offset = self.current_weight;
        Ok(())
    }

    fn zero(&mut self) -> Result<(), String> {
        self.tare_offset = 0.0;
        self.current_weight = 0.0;
        Ok(())
    }

    fn is_connected(&self) -> bool {
        self.connected
    }

    fn kind(&self) -> ScaleConnection {
        ScaleConnection::Mock
    }
}
