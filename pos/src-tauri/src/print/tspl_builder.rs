//! TSPL 标签指令构建器：生成 40mm×30mm 称重价格标签的打印机指令。

use super::gbk::Gbk;
use super::label_job::LabelJob;

/// 标签纸宽（203dpi 下 40mm 约 320 点）
const LABEL_WIDTH: u32 = 320;

/// TSPL 标签构建器（适配 TSC / 佳博标签机）
pub struct TsplBuilder;

impl TsplBuilder {
    /// 构建标签指令
    ///
    /// # 参数
    /// - job：标签打印任务
    ///
    /// # 返回
    /// - `Ok(Vec<u8>)`：完整 TSPL 指令字节（GBK 编码）
    /// - `Err(String)`：没有可打印标签时返回错误
    pub fn build(job: &LabelJob) -> Result<Vec<u8>, String> {
        if job.labels.is_empty() {
            return Err("没有可打印的标签".to_string());
        }

        let mut commands = String::new();
        for item in &job.labels {
            // 每张标签独立初始化并打印
            commands.push_str("SIZE 40 mm, 30 mm\r\n");
            commands.push_str("GAP 2 mm, 0 mm\r\n");
            commands.push_str("DIRECTION 1\r\n");
            commands.push_str("CLS\r\n");

            let store = Self::truncate(&job.store_name, LABEL_WIDTH - 16, 24, 12);
            commands.push_str(&Self::text_cmd(
                Self::center_x(&store, 24, 12),
                6,
                "TSS24.BF2",
                1,
                1,
                &store,
            ));

            let name = Self::truncate(&item.name, LABEL_WIDTH - 16, 24, 12);
            commands.push_str(&Self::text_cmd(
                Self::center_x(&name, 24, 12),
                32,
                "TSS24.BF2",
                1,
                1,
                &name,
            ));

            let weight = format!("{:.2} kg", item.weight);
            commands.push_str(&Self::text_cmd(
                Self::center_x(&weight, 48, 24),
                58,
                "TSS24.BF2",
                2,
                2,
                &weight,
            ));

            let detail = format!("单价{:.2}/kg  金额{:.2}", item.price, item.amount);
            commands.push_str(&Self::text_cmd(
                Self::center_x(&detail, 24, 12).max(8),
                112,
                "TSS24.BF2",
                1,
                1,
                &detail,
            ));

            // 条码：128 码，高度 40 点，不显示可读字符，窄条 2 点、宽条 4 点
            commands.push_str(&format!(
                "BARCODE 20,140,\"128\",40,0,0,2,4,\"{}\"\r\n",
                Self::escape(&item.code)
            ));

            commands.push_str(&Self::text_cmd(
                Self::center_x(&item.code, 16, 16),
                184,
                "2",
                1,
                1,
                &item.code,
            ));

            if !job.print_time.trim().is_empty() {
                let time = Self::truncate(&job.print_time, LABEL_WIDTH - 16, 12, 12);
                commands.push_str(&Self::text_cmd(
                    Self::center_x(&time, 12, 12),
                    212,
                    "1",
                    1,
                    1,
                    &time,
                ));
            }

            commands.push_str("PRINT 1,1\r\n");
        }

        Ok(Gbk::encode(&commands))
    }

    /// 生成 TEXT 指令
    fn text_cmd(x: u32, y: u32, font: &str, x_mul: u32, y_mul: u32, content: &str) -> String {
        format!(
            "TEXT {}, {},\"{}\",0,{},{},\"{}\"\r\n",
            x,
            y,
            font,
            x_mul,
            y_mul,
            Self::escape(content)
        )
    }

    /// 计算文本横向点数
    fn text_width(text: &str, wide: u32, narrow: u32) -> u32 {
        text.chars()
            .map(|ch| if ch.is_ascii() { narrow } else { wide })
            .sum()
    }

    /// 计算居中的 x 坐标
    fn center_x(text: &str, wide: u32, narrow: u32) -> u32 {
        LABEL_WIDTH.saturating_sub(Self::text_width(text, wide, narrow)) / 2
    }

    /// 按点宽截断文本
    fn truncate(text: &str, max_dots: u32, wide: u32, narrow: u32) -> String {
        let mut width = 0;
        let mut result = String::new();
        for ch in text.chars() {
            let char_width = if ch.is_ascii() { narrow } else { wide };
            if width + char_width > max_dots {
                break;
            }
            width += char_width;
            result.push(ch);
        }
        result
    }

    /// 转义 TSPL 字符串中的引号与反斜杠
    fn escape(text: &str) -> String {
        text.replace('\\', "\\\\").replace('"', "\\\"")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::print::label_item::LabelItem;

    /// 构造测试用标签任务
    fn sample_job() -> LabelJob {
        LabelJob {
            store_name: "鲜衡生鲜超市".to_string(),
            print_time: "2026-11-05 12:00".to_string(),
            labels: vec![LabelItem {
                name: "上海青".to_string(),
                weight: 1.23,
                price: 4.8,
                amount: 5.9,
                code: "202611050010123".to_string(),
            }],
        }
    }

    /// 校验尺寸、条码与打印指令
    #[test]
    fn builds_tspl_commands() {
        let bytes = TsplBuilder::build(&sample_job()).unwrap();
        assert!(bytes.starts_with(b"SIZE 40 mm, 30 mm"));
        assert!(bytes.windows(7).any(|window| window == b"BARCODE"));
        assert!(bytes.windows(9).any(|window| window == b"PRINT 1,1"));
    }

    /// 校验空标签列表会被拒绝
    #[test]
    fn rejects_empty_labels() {
        let mut job = sample_job();
        job.labels.clear();
        assert!(TsplBuilder::build(&job).is_err());
    }
}
