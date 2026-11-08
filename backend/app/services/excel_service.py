"""Excel 导入导出服务：商品模板生成、批量导入与导出。"""

from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, Product
from app.schemas.import_result import ImportResult, ImportRowError
from app.services.inventory_service import round_stock
from app.services.product_stock_service import ProductStockService

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

# Q23：导入文件大小上限，防止超大工作簿拖垮内存 / 长时间占用事务。
# 服务层与 API 层共用同一常量（API 超限返回 413，服务层作为防御纵深再校验一次）。
MAX_IMPORT_FILE_BYTES = 5 * 1024 * 1024

# Q18：软删商品条码占位前缀。雪花 ID 最长 19 位 + 1 位前缀 = 20 字符，
# 仍在 Product.barcode 的 String(32) 范围内，不需要改列定义或唯一索引。
BARCODE_DELETED_PREFIX = "D"


def deleted_barcode(product_id: int) -> str:
    """生成软删商品的条码占位值（Q18 过渡方案）。

    同租户条码唯一索引是物理唯一的，软删行仍会占用原条码。删除商品或导入
    命中历史软删行时，把该行条码改写为 ``D{id}`` 释放占用，使原条码可复用。
    PG baseline 改为部分唯一索引 ``WHERE deleted = false`` 后可移除该逻辑。

    :param product_id: 被软删商品的主键 ID
    :return: 占位条码（长度不超过 20 字符）
    """
    return f"{BARCODE_DELETED_PREFIX}{product_id}"


def release_deleted_barcode(db: Session, tenant_id: int, barcode: str) -> int:
    """释放被历史软删记录占用的指定条码（Q18）。

    B3 之前删除的商品只打了 ``deleted=True`` 标记，条码未改写，仍持有唯一
    索引键。新建 / 改条码 / Excel 导入前调用本函数，把这些遗留行的条码改写
    为 ``D{id}``，避免插入时触发唯一约束冲突。

    :param db: 数据库会话
    :param tenant_id: 所属租户 ID（唯一索引含租户维度）
    :param barcode: 待释放的条码
    :return: 被改写释放的软删行数
    """
    rows = db.scalars(
        select(Product).where(
            Product.barcode == barcode,
            Product.tenant_id == tenant_id,
            Product.deleted.is_(True),
        )
    ).all()
    for row in rows:
        row.barcode = deleted_barcode(row.id)
    if rows:
        db.flush()
    return len(rows)


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

        Q23：每行独立 SAVEPOINT，失败行只回滚自身写入；``category_cache`` /
        ``barcode_cache`` 是 Python 层字典，SAVEPOINT 不会回滚它们，故每行
        进入前做快照，失败时整体还原，避免后续行引用已回滚 ORM 对象抛
        ``InvalidRequestError``。

        :param db: 数据库会话
        :param file_bytes: Excel 文件字节流
        :param tenant_id: 所属租户 ID
        :param store_id: 所属门店 ID
        :return: 导入结果
        """
        result = ImportResult()
        # Q23：load_workbook 之前先限制大小，超限直接拒绝，不进入解析
        if len(file_bytes) > MAX_IMPORT_FILE_BYTES:
            raise ValueError("导入文件超过系统允许的大小上限，请拆分后重试")
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
            values = list(row)
            # 空行跳过
            if not values or all(v is None or str(v).strip() == "" for v in values):
                continue

            # 缓存快照：SAVEPOINT 只回滚数据库，Python 层缓存必须单独还原
            category_snapshot = dict(category_cache)
            barcode_snapshot = dict(barcode_cache)
            try:
                # Q23：单行写入包在 SAVEPOINT 内；异常离开 with 时由 SQLAlchemy
                # 回滚该 SAVEPOINT，其余已成功行不受影响。
                with db.begin_nested():
                    product, created = self._parse_row(
                        db, row_idx, values, category_cache, barcode_cache, tenant_id, store_id
                    )
            except Exception as exc:
                # 还原缓存（删除本行新增条目，并恢复被本行覆盖的旧条目）
                category_cache.clear()
                category_cache.update(category_snapshot)
                barcode_cache.clear()
                barcode_cache.update(barcode_snapshot)
                # 校验类错误保留原始说明；数据库/未知异常收敛为通用文案，
                # 避免把 SQL 细节暴露给前端，同时不影响其余行继续导入。
                message = (
                    str(exc)
                    if isinstance(exc, ValueError)
                    else "该行数据写入失败，请检查是否与现有记录冲突后重试"
                )
                result.failed += 1
                result.errors.append(ImportRowError(row=row_idx, error=message))
                continue
            result.success += 1
            if created:
                result.created += 1
            else:
                result.updated += 1

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
    ) -> tuple[Product, bool]:
        """解析单行数据并按条码 upsert 商品。

        :param db: 数据库会话
        :param row_idx: 行号
        :param values: 单元格值列表
        :param category_cache: 分类缓存
        :param barcode_cache: 条码缓存
        :param tenant_id: 所属租户 ID
        :param store_id: 所属门店 ID
        :return: (商品 ORM 对象, 是否新建)
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

        # 按条码查找已有商品（租户级共享，同租户内唯一，使用缓存避免重复查询）
        # Q18：查重排除软删行；历史软删行仍占唯一索引时，改写其条码释放占用。
        product = barcode_cache.get(barcode)
        if product is None:
            product = db.scalar(
                select(Product).where(
                    Product.barcode == barcode,
                    Product.tenant_id == tenant_id,
                    Product.deleted.is_(False),
                )
            )

        created = False
        if product:
            # 更新已有商品（库存写入当前导入门店，不落在商品档案上）
            product.name = name
            product.pinyin = pinyin or None
            product.category_id = category_id
            product.pricing_mode = pricing_mode
            product.unit = unit
            product.price = price
            product.member_price = member_price
            product.cost_price = cost_price
            product.shelf_life_days = shelf_life
            product.enabled = enabled
        else:
            # Q18：先释放 B3 之前遗留的软删行条码占位，再新建，避免唯一键冲突
            release_deleted_barcode(db, tenant_id, barcode)
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
                stock=0,
                safety_stock=0,
                enabled=enabled,
            )
            db.add(product)
            db.flush()  # 立即获取自增 ID，确保统计 created/updated 准确
            created = True
        # 库存/安全库存写入当前门店库存表
        ProductStockService.apply(
            db, product, store_id, stock=stock, safety_stock=safety_stock
        )
        barcode_cache[barcode] = product
        return product, created

    def export_products(self, db: Session, tenant_id: int, store_id: int) -> BytesIO:
        """导出本租户全部商品为 Excel（库存取当前门店），返回字节流。

        :param db: 数据库会话
        :param tenant_id: 所属租户 ID
        :param store_id: 当前门店 ID（用于取门店库存）
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
            .where(Product.tenant_id == tenant_id, Product.deleted.is_(False))
            .order_by(Product.category_id, Product.id)
        ).all()
        stocks = ProductStockService.get_map(db, [p.id for p in products], store_id)
        for p in products:
            row = stocks.get(p.id)
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
                    round_stock(row.stock) if row else 0,
                    (row.safety_stock or 0) if row else 0,
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
        """按名称解析分类（支持 一级/二级 路径），不存在则自动创建（租户级共享）。

        :param db: 数据库会话
        :param category_name: 分类名称路径
        :param category_cache: 分类缓存
        :param tenant_id: 所属租户 ID
        :param store_id: 创建分类时记录的归属门店 ID
        :return: 分类 ID
        """
        if not category_name:
            return None
        name = str(category_name).strip()
        # 归一化分隔符（支持 "/" 和 "\\"）
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
                    Category.tenant_id == tenant_id,
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
