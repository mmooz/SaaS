//! Windows 打印队列直连：枚举本机打印机，并把原始指令写入打印作业。

use std::ffi::c_void;

use windows_sys::Win32::Graphics::Printing::{
    ClosePrinter, EndDocPrinter, EndPagePrinter, EnumPrintersW, GetPrinterW, OpenPrinterW,
    StartDocPrinterW, StartPagePrinter, WritePrinter, DOC_INFO_1W, PRINTER_ENUM_CONNECTIONS,
    PRINTER_ENUM_LOCAL, PRINTER_HANDLE, PRINTER_INFO_4W,
};

use super::printer_status::PrinterStatus;

/// Win32 打印队列操作封装
pub struct WinSpooler;

impl WinSpooler {
    /// 枚举本机及已连接的打印机名称
    ///
    /// # 返回
    /// - `Ok(Vec<String>)`：打印机名称列表（已去重）
    /// - `Err(String)`：枚举失败
    pub fn list() -> Result<Vec<String>, String> {
        unsafe {
            let flags = PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS;
            let mut needed = 0u32;
            let mut returned = 0u32;

            // 第一次调用仅探测所需缓冲区大小
            EnumPrintersW(
                flags,
                std::ptr::null(),
                4,
                std::ptr::null_mut(),
                0,
                &mut needed,
                &mut returned,
            );
            if needed == 0 {
                return Ok(Vec::new());
            }

            let mut buffer = vec![0u8; needed as usize];
            let ok = EnumPrintersW(
                flags,
                std::ptr::null(),
                4,
                buffer.as_mut_ptr(),
                needed,
                &mut needed,
                &mut returned,
            );
            if ok == 0 {
                return Err(format!("枚举打印机失败：{}", std::io::Error::last_os_error()));
            }

            let infos = buffer.as_ptr() as *const PRINTER_INFO_4W;
            let mut names: Vec<String> = Vec::new();
            for index in 0..returned as usize {
                let name = Self::wide_to_string((*infos.add(index)).pPrinterName);
                if !name.is_empty() && !names.contains(&name) {
                    names.push(name);
                }
            }
            names.sort();
            Ok(names)
        }
    }

    /// 把原始指令作为打印作业发送到指定打印机
    ///
    /// # 参数
    /// - printer_name：系统打印机名称
    /// - data：ESC/POS 或 TSPL 指令字节
    pub fn print_raw(printer_name: &str, data: &[u8]) -> Result<(), String> {
        if printer_name.trim().is_empty() {
            return Err("未选择打印机".to_string());
        }
        if data.is_empty() {
            return Err("打印指令为空".to_string());
        }

        unsafe {
            let printer = Self::wide(printer_name);
            let mut handle = PRINTER_HANDLE {
                Value: std::ptr::null_mut(),
            };
            if OpenPrinterW(printer.as_ptr(), &mut handle, std::ptr::null()) == 0 {
                return Err(format!(
                    "打开打印机「{}」失败：{}",
                    printer_name,
                    std::io::Error::last_os_error()
                ));
            }

            let mut doc_name = Self::wide("POS 打印任务");
            let mut data_type = Self::wide("RAW");
            let doc_info = DOC_INFO_1W {
                pDocName: doc_name.as_mut_ptr(),
                pOutputFile: std::ptr::null_mut(),
                pDatatype: data_type.as_mut_ptr(),
            };

            let job_id = StartDocPrinterW(handle, 1, &doc_info);
            if job_id == 0 {
                ClosePrinter(handle);
                return Err(format!("创建打印作业失败：{}", std::io::Error::last_os_error()));
            }

            if StartPagePrinter(handle) == 0 {
                EndDocPrinter(handle);
                ClosePrinter(handle);
                return Err(format!("开始打印页失败：{}", std::io::Error::last_os_error()));
            }

            let mut written = 0u32;
            let write_ok = WritePrinter(
                handle,
                data.as_ptr() as *const c_void,
                data.len() as u32,
                &mut written,
            );

            EndPagePrinter(handle);
            EndDocPrinter(handle);
            ClosePrinter(handle);

            if write_ok == 0 {
                return Err(format!("写入打印数据失败：{}", std::io::Error::last_os_error()));
            }
            if written as usize != data.len() {
                return Err(format!(
                    "打印数据写入不完整：{}/{} 字节",
                    written,
                    data.len()
                ));
            }
            Ok(())
        }
    }

    /// 查询打印机当前状态（GetPrinter level 6 返回状态位）
    ///
    /// # 参数
    /// - printer_name：系统打印机名称
    ///
    /// # 返回
    /// - `Ok(PrinterStatus)`：状态位与告警说明
    /// - `Err(String)`：打印机不存在或读取状态失败
    pub fn status(printer_name: &str) -> Result<PrinterStatus, String> {
        if printer_name.trim().is_empty() {
            return Err("未选择打印机".to_string());
        }

        unsafe {
            let printer = Self::wide(printer_name);
            let mut handle = PRINTER_HANDLE {
                Value: std::ptr::null_mut(),
            };
            if OpenPrinterW(printer.as_ptr(), &mut handle, std::ptr::null()) == 0 {
                return Err(format!(
                    "打开打印机「{}」失败：{}",
                    printer_name,
                    std::io::Error::last_os_error()
                ));
            }

            let result = Self::read_status(handle, printer_name);
            ClosePrinter(handle);
            result
        }
    }

    /// 读取 printer level 6 状态位
    ///
    /// # 参数
    /// - handle：已打开的打印机句柄
    /// - printer_name：打印机名称（仅用于错误提示）
    ///
    /// # 返回
    /// - `Ok(PrinterStatus)`：状态位解析结果
    /// - `Err(String)`：读取失败
    unsafe fn read_status(handle: PRINTER_HANDLE, printer_name: &str) -> Result<PrinterStatus, String> {
        let mut needed = 0u32;
        // 第一次调用仅探测所需缓冲区大小，返回 FALSE 属正常
        GetPrinterW(handle, 6, std::ptr::null_mut(), 0, &mut needed);
        if needed == 0 {
            return Err(format!(
                "读取打印机「{}」状态失败：{}",
                printer_name,
                std::io::Error::last_os_error()
            ));
        }

        // 按 u32 对齐分配缓冲区，避免从字节切片读取状态位时的对齐问题
        let words = (needed as usize + 3) / 4;
        let mut buffer = vec![0u32; words];
        if GetPrinterW(
            handle,
            6,
            buffer.as_mut_ptr() as *mut u8,
            needed,
            &mut needed,
        ) == 0
        {
            return Err(format!(
                "读取打印机「{}」状态失败：{}",
                printer_name,
                std::io::Error::last_os_error()
            ));
        }

        Ok(PrinterStatus::from_flags(printer_name, buffer[0]))
    }

    /// 把字符串编码为 Windows 宽字符（带结尾 0）
    fn wide(text: &str) -> Vec<u16> {
        text.encode_utf16().chain(std::iter::once(0)).collect()
    }

    /// 把 Windows 宽字符指针转为字符串
    fn wide_to_string(ptr: *const u16) -> String {
        if ptr.is_null() {
            return String::new();
        }
        unsafe {
            let mut length = 0usize;
            while *ptr.add(length) != 0 {
                length += 1;
            }
            String::from_utf16_lossy(std::slice::from_raw_parts(ptr, length))
        }
    }
}
