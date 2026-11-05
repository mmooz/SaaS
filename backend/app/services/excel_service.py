"""Excel 导入导出服务：商品模板生成、批量导入与导出。"""

from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, Product
from app.schemas.import_result import ImportResult, ImportRowError

# 商品 Excel 列定义
COLUMNS = [
    "条码",
    "名称",
    "拼音码",
    "分类名称",
    "计价方式",
    "单位",
    "零售价",
    "会员价",
    "进价",
    "保质期",
    "库存",
    "安全库存",
    "启用",
]


class ExcelService:
    """商品 Excel 导入导出服务类。"""

    # 表头样式
    HEADER_FONT = Font(bold=True, color="FFFFFF")
    HEADER_FILL = PatternFill(start_color="2F9E5F", end_color="2F9E5F", fill_type="solid")

    def build_template(self) -> BytesIO:
        """生成导入模板（含一行示例数据），返回字节流。"""
        wb = Workbook()
        ws = wb.active
        ws.title = "商品导入"
        # 写入表头
        ws.append(COLUMNS)
        for cell in ws[1]:
            cell.font = self.HEADER_FONT
            cell.fill = self.HEADER_FILL
        # 写入示例行
        ws.append(
            ["2000000000011", "上海青", "shq", "蔬菜/叶菜", "weigh", "kg", 4.8, 4.5, 3.2, 3, 0, 10, "是"]
        )
        ws.append(
            ["6901234567890", "鲜鸡蛋(盒)", "xjd", "粮油副食", "count", "盒", 13.8, 13.0, 11.5, 30, 0, 30, "是"]
        )
        # 调整列宽
        for col, _ in enumerate(COLUMNS, start=1):
            ws.column_dimensions[chr(64 + col)].width = 14
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    def import_products(
        self, db: Session, file_bytes: bytes, tenant_id: int, store_id: int
    ) -> ImportResult:
        """解析 Excel 并批量导入/更新商品，返回导入结果。

        :param db: 数据库会话
        :param file_bytes: Excel 文件字节流
        :param tenant_id: 所属租户 ID
        :param store_id: 所属门店 ID
        :return: 导入结果
        """
        result = ImportResult()
        wb = load_workbook(BytesIO(file_bytes))
        ws = wb.active

        # 校验表头
        headers = [cell.value for cell in ws[1]]
        if headers[: len(COLUMNS)] != COLUMNS:
            result.failed = max(0, ws.max_row - 1)
            result.total = result.failed
            result.errors.append(ImportRowError(row=1, error="表头不匹配，请使用导入模板"))
            return result

        # 分类名称缓存（避免重复建分类）
        category_cache: dict[str, Category] = {}
        # 已存在条码缓存
        barcode_cache: dict[str, Product] = {}

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            result.total += 1
            try:
                values = list(row)
                # 空行跳过
                if not values or all(v is None or str(v).strip() == "" for v in values):
                    continue
                product = self._parse_row(
                    db, row_idx, values, category_cache, barcode_cache, tenant_id, store_id
                )
                result.success += 1
                if product.id:
                    result.updated += 1
                else:
                    result.created += 1
            except ValueError as exc:
                result.failed += 1
                result.errors.append(ImportRowError(row=row_idx, error=str(exc)))

        db.commit()
        return result

    def _parse_row(
        self,
        db: Session,
        row_idx: int,
        values: list,
        category_cache: dict[str, Category],
        barcode_cache: dict[str, Product],
        tenant_id: int,
        store_id: int,
    ) -> Product:
        """解析单行数据并按条码 upsert 商品。

        :param db: 数据库会话
        :param row_idx: 行号
        :param values: 单元格值列表
        :param category_cache: 分类缓存
        :param barcode_cache: 条码缓存
        :param tenant_id: 所属租户 ID
        :param store_id: 所属门店 ID
        :return: 商品 ORM 对象
        """
        (barcode, name, pinyin, category_name, pricing_mode, unit,
         price, member_price, cost_price, shelf_life, stock, safety_stock, enabled) = (
            (values + [None] * len(COLUMNS))[: len(COLUMNS)]
        )

        # 必填校验
        barcode = str(barcode or "").strip()
        name = str(name or "").strip()
        if not barcode:
            raise ValueError("条码不能为空")
        if not name:
            raise ValueError("名称不能为空")

        # 数字字段解析
        price = self._to_float(price, "零售价")
        member_price = self._to_float(member_price, "会员价", allow_none=True)
        cost_price = self._to_float(cost_price, "进价", allow_none=True)
        shelf_life = self._to_int(shelf_life, "保质期", allow_none=True)
        stock = self._to_float(stock, "库存", allow_none=True) or 0
        safety_stock = self._to_float(safety_stock, "安全库存", allow_none=True) or 0

        # 计价方式与单位归一化
        pricing_mode = (str(pricing_mode or "weigh")).strip().lower()
        if pricing_mode not in ("weigh", "count"):
            pricing_mode = "weigh" if pricing_mode in ("称重", "重量") else "count"
        unit = str(unit or "").strip() or ("kg" if pricing_mode == "weigh" else "件")
        enabled = str(enabled or "是").strip() not in ("否", "false", "0", "停用")

        # 分类：按名称查找或自动创建（支持"一级/二级"路径）
        category_id = self._resolve_category(db, category_name, category_cache, tenant_id, store_id)

        # 按条码查找已有商品（限定当前门店，使用缓存避免重复查询）
        product = barcode_cache.get(barcode)
        if product is None:
            product = db.scalar(
                select(Product).where(Product.barcode == barcode, Product.store_id == store_id)
            )

        if product:
            # 更新已有商品
            product.name = name
            product.pinyin = pinyin or None
            product.category_id = category_id
            product.pricing_mode = pricing_mode
            product.unit = unit
            product.price = price
            product.member_price = member_price
            product.cost_price = cost_price
            product.shelf_life_days = shelf_life
            product.stock = stock
            product.safety_stock = safety_stock
            product.enabled = enabled
        else:
            # 新建商品
            product = Product(
                tenant_id=tenant_id,
                store_id=store_id,
                barcode=barcode,
                name=name,
                pinyin=pinyin or None,
                category_id=category_id,
                pricing_mode=pricing_mode,
                unit=unit,
                price=price,
                member_price=member_price,
                cost_price=cost_price,
                shelf_life_days=shelf_life,
                stock=stock,
                safety_stock=safety_stock,
                enabled=enabled,
            )
            db.add(product)
            db.flush()  # 立即获取自增 ID，确保统计 created/updated 准确
        barcode_cache[barcode] = product
        return product

    def export_products(self, db: Session, store_id: int) -> BytesIO:
        """导出指定门店全部商品为 Excel，返回字节流。

        :param db: 数据库会话
        :param store_id: 门店 ID
        :return: Excel 字节流
        """
        wb = Workbook()
        ws = wb.active
        ws.title = "商品列表"
        ws.append(COLUMNS)
        for cell in ws[1]:
            cell.font = self.HEADER_FONT
            cell.fill = self.HEADER_FILL

        products = db.scalars(
            select(Product)
            .where(Product.store_id == store_id)
            .order_by(Product.category_id, Product.id)
        ).all()
        for p in products:
            ws.append(
                [
                    p.barcode,
                    p.name,
                    p.pinyin or "",
                    p.category.name if p.category else "",
                    p.pricing_mode,
                    p.unit,
                    p.price,
                    p.member_price or "",
                    p.cost_price or "",
                    p.shelf_life_days or "",
                    p.stock,
                    p.safety_stock,
                    "是" if p.enabled else "否",
                ]
            )
        for col, _ in enumerate(COLUMNS, start=1):
            ws.column_dimensions[chr(64 + col)].width = 14
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def _to_float(value, label: str, allow_none: bool = False) -> float | None:
        """将单元格值解析为浮点数，非法时抛出带行号说明的错误。"""
        if value is None or str(value).strip() == "":
            if allow_none:
                return None
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{label}格式不正确")

    @staticmethod
    def _to_int(value, label: str, allow_none: bool = False) -> int | None:
        """将单元格值解析为整数，非法时抛出带行号说明的错误。"""
        if value is None or str(value).strip() == "":
            return None if allow_none else 0
        try:
            return int(float(value))
        except (TypeError, ValueError):
            raise ValueError(f"{label}格式不正确")

    @staticmethod
    def _resolve_category(
        db: Session,
        category_name: str | None,
        category_cache: dict[str, Category],
        tenant_id: int,
        store_id: int,
    ) -> int | None:
        """按名称解析分类（支持 一级/二级 路径），不存在则自动创建（限定当前门店）。

        :param db: 数据库会话
        :param category_name: 分类名称路径
        :param category_cache: 分类缓存
        :param tenant_id: 所属租户 ID
        :param store_id: 所属门店 ID
        :return: 分类 ID
        """
        if not category_name:
            return None
        name = str(category_name).strip()
        # 归一化分隔符（支持 "/" 和 "/"）
        parts = [p.strip() for p in name.replace("\\", "/").split("/") if p.strip()]
        if not parts:
            return None

        # 逐级查找或创建分类
        parent_id = None
        for part in parts:
            key = f"{parent_id}:{part}"
            if key in category_cache:
                parent_id = category_cache[key].id
                continue
            category = db.scalar(
                select(Category).where(
                    Category.name == part,
                    Category.parent_id == parent_id,
                    Category.store_id == store_id,
                )
            )
            if category is None:
                category = Category(
                    name=part, parent_id=parent_id, tenant_id=tenant_id, store_id=store_id
                )
                db.add(category)
                db.flush()  # 获取自增 ID
            category_cache[key] = category
            parent_id = category.id
        return parent_id


# 全局服务实例
excel_service = ExcelService()
