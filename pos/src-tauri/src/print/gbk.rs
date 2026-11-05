//! GBK 文本编码器：热敏打印机使用 GBK（代码页 936）显示中文。

#[cfg(target_os = "windows")]
use windows_sys::Win32::Globalization::WideCharToMultiByte;

/// 把 UTF-8 文本转换为 GBK 字节
pub struct Gbk;

impl Gbk {
    /// 简体中文 GBK 代码页
    #[cfg(target_os = "windows")]
    const CODE_PAGE: u32 = 936;

    /// 将文本编码为 GBK 字节；非 Windows 平台或失败时退回 UTF-8 字节
    ///
    /// # 参数
    /// - text：待编码文本
    pub fn encode(text: &str) -> Vec<u8> {
        #[cfg(target_os = "windows")]
        {
            let wide: Vec<u16> = text.encode_utf16().collect();
            if wide.is_empty() {
                return Vec::new();
            }
            unsafe {
                // 第一次调用获取目标字节长度
                let size = WideCharToMultiByte(
                    Self::CODE_PAGE,
                    0,
                    wide.as_ptr(),
                    wide.len() as i32,
                    std::ptr::null_mut(),
                    0,
                    std::ptr::null(),
                    std::ptr::null_mut(),
                );
                if size <= 0 {
                    return text.as_bytes().to_vec();
                }
                let mut buffer = vec![0u8; size as usize];
                let written = WideCharToMultiByte(
                    Self::CODE_PAGE,
                    0,
                    wide.as_ptr(),
                    wide.len() as i32,
                    buffer.as_mut_ptr(),
                    size,
                    std::ptr::null(),
                    std::ptr::null_mut(),
                );
                if written <= 0 {
                    return text.as_bytes().to_vec();
                }
                buffer.truncate(written as usize);
                buffer
            }
        }
        #[cfg(not(target_os = "windows"))]
        {
            text.as_bytes().to_vec()
        }
    }
}
