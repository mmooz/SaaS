//! ESC/POS 小票指令构建器：把订单转为热敏打印机可执行的字节流。

use super::gbk::Gbk;
use super::receipt_job::ReceiptJob;

/// ESC/POS 小票构建器（适配 58mm / 80mm 热敏打印机）
pub struct EscPosBuilder;

impl EscPosBuilder {
    /// 初始化打印机：ESC @
    const INIT: [u8; 2] = [0x1B, 0x40];

    /// 左对齐：ESC a 0
    const ALIGN_LEFT: [u8; 3] = [0x1B, 0x61, 0x00];

    /// 居中对齐：ESC a 1
    const ALIGN_CENTER: [u8; 3] = [0x1B, 0x61, 0x01];

    /// 双倍宽高字号：GS ! 0x11
    const FONT_DOUBLE: [u8; 3] = [0x1D, 0x21, 0x11];

    /// 正常字号：GS ! 0x00
    const FONT_NORMAL: [u8; 3] = [0x1D, 0x21, 0x00];

    /// 走纸 3 行并切纸：ESC d 3 + GS V 66 0
    const FEED_AND_CUT: [u8; 7] = [0x1B, 0x64, 0x03, 0x1D, 0x56, 0x42, 0x00];

    /// 构建小票指令
    ///
    /// # 参数
    /// - job：小票打印任务
    ///
    /// # 返回
    /// - `Ok(Vec<u8>)`：完整 ESC/POS 指令字节
    /// - `Err(String)`：订单号为空等参数错误
    pub fn build(job: &ReceiptJob) -> Result<Vec<u8>, String> {
        if job.order_no.trim().is_empty() {
            return Err("订单号不能为空".to_string());
        }

        // 58mm 每行 32 个半角字符，80mm 每行 48 个
        let width = if job.paper_width >= 80 { 48 } else { 32 };
        let mut out = Vec::new();

        out.extend_from_slice(&Self::INIT);
        out.extend_from_slice(&Self::ALIGN_CENTER);
        out.extend_from_slice(&Self::FONT_DOUBLE);
        Self::write_line(&mut out, &job.store_name);
        out.extend_from_slice(&Self::FONT_NORMAL);

        if !job.receipt_header.trim().is_empty() {
            Self::write_center(&mut out, &job.receipt_header, width);
        }

        let mut contact = job.store_address.trim().to_string();
        if !job.phone.trim().is_empty() {
            if !contact.is_empty() {
                contact.push_str(" · ");
            }
            contact.push_str(job.phone.trim());
        }
        if !contact.is_empty() {
            Self::write_center(&mut out, &contact, width);
        }

        out.extend_from_slice(&Self::ALIGN_LEFT);
        Self::write_line(&mut out, &Self::divider(width));
        Self::write_columns(&mut out, "单号", &job.order_no, width);
        if !job.time.trim().is_empty() {
            Self::write_columns(&mut out, "时间", &job.time, width);
        }
        if !job.cashier_name.trim().is_empty() {
            Self::write_columns(&mut out, "收银员", &job.cashier_name, width);
        }
        if let Some(mobile) = job.member_mobile.as_deref() {
            if !mobile.trim().is_empty() {
                Self::write_columns(&mut out, "会员手机", mobile, width);
            }
        }

        Self::write_line(&mut out, &Self::divider(width));
        Self::write_columns(&mut out, "品名 / 数量", "金额", width);
        Self::write_line(&mut out, &Self::divider(width));

        for item in &job.items {
            let name = Self::truncate(&item.name, width);
            Self::write_line(&mut out, &name);
            let quantity = if item.weighted {
                format!(
                    "{:.2}kg × {:.2}",
                    item.weight.unwrap_or(0.0),
                    item.price
                )
            } else {
                format!("{:.0} × {:.2}", item.qty.unwrap_or(0.0), item.price)
            };
            Self::write_columns(&mut out, &quantity, &format!("{:.2}", item.amount), width);
        }

        Self::write_line(&mut out, &Self::divider(width));
        Self::write_columns(&mut out, "商品件数", &job.items.len().to_string(), width);
        Self::write_columns(&mut out, "合计", &format!("{:.2}", job.total_amount), width);
        if job.discount > 0.0 {
            Self::write_columns(&mut out, "优惠", &format!("-{:.2}", job.discount), width);
        }
        let payable = (job.total_amount - job.discount).max(0.0);
        Self::write_columns(&mut out, "应收", &format!("{:.2}", payable), width);

        if let Some(method) = job.pay_method.as_deref() {
            if !method.trim().is_empty() {
                Self::write_columns(&mut out, method, &format!("{:.2}", payable), width);
            }
        }
        if job.cash_received.is_some() {
            Self::write_columns(
                &mut out,
                "实收",
                &format!("{:.2}", job.cash_received.unwrap_or(0.0)),
                width,
            );
        }
        if job.change.is_some() {
            Self::write_columns(
                &mut out,
                "找零",
                &format!("{:.2}", job.change.unwrap_or(0.0)),
                width,
            );
        }

        Self::write_line(&mut out, &Self::divider(width));
        out.extend_from_slice(&Self::ALIGN_CENTER);
        Self::write_barcode(&mut out, &job.order_no);
        if !job.slogan.trim().is_empty() {
            Self::write_center(&mut out, &job.slogan, width);
        }
        out.extend_from_slice(&Self::FEED_AND_CUT);

        Ok(out)
    }

    /// 写入一行 GBK 文本并换行
    fn write_line(out: &mut Vec<u8>, text: &str) {
        out.extend(Gbk::encode(text));
        out.push(b'\n');
    }

    /// 写入居中一行文本
    fn write_center(out: &mut Vec<u8>, text: &str, width: usize) {
        let pad = width.saturating_sub(Self::text_width(text)) / 2;
        if pad > 0 {
            out.extend(std::iter::repeat(b' ').take(pad));
        }
        Self::write_line(out, text);
    }

    /// 写入左右两列文本（自动补空格）
    fn write_columns(out: &mut Vec<u8>, left: &str, right: &str, width: usize) {
        let gap = width
            .saturating_sub(Self::text_width(left) + Self::text_width(right))
            .max(1);
        let line = format!("{}{}{}", left, " ".repeat(gap), right);
        Self::write_line(out, &line);
    }

    /// 计算文本占用的半角字符宽度（ASCII 记 1，中文记 2）
    fn text_width(text: &str) -> usize {
        text.chars()
            .map(|ch| if ch.is_ascii() { 1 } else { 2 })
            .sum()
    }

    /// 按半角字符宽度截断文本
    fn truncate(text: &str, max_width: usize) -> String {
        let mut width = 0;
        let mut result = String::new();
        for ch in text.chars() {
            let char_width = if ch.is_ascii() { 1 } else { 2 };
            if width + char_width > max_width {
                break;
            }
            width += char_width;
            result.push(ch);
        }
        result
    }

    /// 生成分隔线
    fn divider(width: usize) -> String {
        "-".repeat(width)
    }

    /// 写入 CODE128 条码（HRI 打印在条码下方）
    fn write_barcode(out: &mut Vec<u8>, order_no: &str) {
        // 仅保留 ASCII 字符，保证 CODE128 B 可编码
        let barcode_text: String = order_no.chars().filter(|ch| ch.is_ascii()).collect();
        let barcode_text = if barcode_text.is_empty() {
            "0".to_string()
        } else {
            barcode_text
        };

        // HRI 位置（下方）、条码高度 60 点、模块宽度 2 点
        out.extend_from_slice(&[0x1D, 0x48, 0x02]);
        out.extend_from_slice(&[0x1D, 0x68, 60]);
        out.extend_from_slice(&[0x1D, 0x77, 0x02]);

        // CODE128：GS k 73 n，数据以 {B 表示 Code Set B
        let mut payload = vec![b'{', b'B'];
        payload.extend_from_slice(barcode_text.as_bytes());
        if payload.len() > 255 {
            payload.truncate(255);
        }
        out.extend_from_slice(&[0x1D, 0x6B, 0x49, payload.len() as u8]);
        out.extend_from_slice(&payload);
        out.push(b'\n');
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::print::receipt_item::ReceiptItem;

    /// 构造测试用小票任务
    fn sample_job() -> ReceiptJob {
        ReceiptJob {
            store_name: "鲜衡生鲜超市".to_string(),
            store_address: "测试地址".to_string(),
            phone: "13800000000".to_string(),
            receipt_header: String::new(),
            slogan: "多谢惠顾".to_string(),
            paper_width: 58,
            order_no: "20261105-120001-00001".to_string(),
            time: "2026-11-05 12:00".to_string(),
            cashier_name: "测试".to_string(),
            member_mobile: None,
            items: vec![ReceiptItem {
                name: "上海青".to_string(),
                weighted: true,
                weight: Some(1.23),
                qty: None,
                price: 4.8,
                amount: 5.9,
            }],
            total_amount: 12.8,
            discount: 0.0,
            pay_method: Some("现金".to_string()),
            cash_received: Some(20.0),
            change: Some(7.2),
        }
    }

    /// 校验初始化、条码与切纸指令
    #[test]
    fn builds_receipt_commands() {
        let bytes = EscPosBuilder::build(&sample_job()).unwrap();
        assert_eq!(&bytes[0..2], &[0x1B, 0x40]);
        assert!(bytes.windows(3).any(|window| window == [0x1D, 0x6B, 0x49]));
        assert!(bytes.windows(3).any(|window| window == [0x1D, 0x56, 0x42]));
        assert!(bytes.len() > 100);
    }

    /// 校验空订单号会被拒绝
    #[test]
    fn rejects_empty_order_no() {
        let mut job = sample_job();
        job.order_no = String::new();
        assert!(EscPosBuilder::build(&job).is_err());
    }
}
