//! 称重模块：统一的可插拔电子秤接入接口。
//!
//! 支持三类实现：模拟秤（开发调试）、串口秤（RS232 通用文本协议）、网口秤（预留）。
//! 通过 `ScaleFactory` 按配置创建具体实现，收银逻辑只依赖 `WeighScale` 接口。

pub mod mock_scale;
pub mod scale_factory;
pub mod serial_scale;
pub mod weigh_scale;

pub use scale_factory::ScaleFactory;
pub use weigh_scale::{ScaleConnection, WeighScale};
