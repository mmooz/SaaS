"""临时接口验证脚本：覆盖 S2 商品后台全部接口。"""
import io
import sqlite3

import httpx
from openpyxl import Workbook

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0

# [Q27-a 止血] 以下模块顶层清库语句已禁用：
# 原逻辑在 pytest 收集阶段（import 时）就会执行 sqlite3.connect("pos.db") + DELETE + commit，
# 且相对路径不受 DATABASE_URL 控制，会直接删掉当前工作目录下的真实 pos.db。
# 原语句保留为注释，供 B5 / Q27-b 重写为「独立内存库 fixture」真实用例时参考：
# conn = sqlite3.connect("pos.db")
# conn.execute("DELETE FROM product_price_history")
# conn.execute("DELETE FROM products")
# conn.execute("DELETE FROM categories")
# conn.commit()
# conn.close()


def check(name, cond, extra=""):
    """记录一项验证结果。"""
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {extra}")


client = httpx.Client(base_url=BASE, timeout=10)

# 1. 健康检查
r = client.get("/api/health")
check("健康检查", r.status_code == 200 and r.json()["status"] == "ok", r.text)

# 2. 创建分类
r = client.post("/api/categories", json={"name": "蔬菜"})
check("创建一级分类-蔬菜", r.status_code == 201, r.text)
veg_id = r.json()["id"]
r = client.post("/api/categories", json={"name": "水果"})
check("创建一级分类-水果", r.status_code == 201, r.text)
fruit_id = r.json()["id"]
r = client.post("/api/categories", json={"name": "粮油副食"})
check("创建一级分类-粮油副食", r.status_code == 201, r.text)
grain_id = r.json()["id"]
r = client.post("/api/categories", json={"name": "叶菜", "parent_id": veg_id})
check("创建二级分类-叶菜", r.status_code == 201, r.text)

# 3. 分类树
r = client.get("/api/categories/tree")
tree = r.json()
check("分类树返回一级节点", r.status_code == 200 and len(tree) == 3, r.text)
veg_node = next((n for n in tree if n["name"] == "蔬菜"), None)
check("蔬菜分类含子分类", veg_node is not None and len(veg_node["children"]) == 1)

# 4. 创建商品
r = client.post("/api/products", json={
    "barcode": "2000000000011", "name": "上海青", "pinyin": "shq",
    "category_id": veg_id, "pricing_mode": "weigh", "unit": "kg",
    "price": 4.8, "member_price": 4.5, "cost_price": 3.2,
    "shelf_life_days": 3, "safety_stock": 10,
})
check("创建称重商品-上海青", r.status_code == 201, r.text)
r = client.post("/api/products", json={
    "barcode": "6901234567890", "name": "鲜鸡蛋(盒)", "pinyin": "xjd",
    "category_id": grain_id, "pricing_mode": "count", "unit": "盒",
    "price": 13.8, "member_price": 13.0, "cost_price": 11.5,
    "shelf_life_days": 30, "safety_stock": 30,
})
check("创建按件商品-鲜鸡蛋", r.status_code == 201, r.text)
# 重复条码
r = client.post("/api/products", json={
    "barcode": "2000000000011", "name": "重复", "pricing_mode": "weigh", "unit": "kg", "price": 1,
})
check("重复条码被拒绝(409)", r.status_code == 409, r.text)

# 5. 商品列表（筛选）
r = client.get("/api/products", params={"keyword": "上海"})
data = r.json()
check("按关键字筛选商品", r.status_code == 200 and data["total"] == 1, r.text)
r = client.get("/api/products", params={"pricing_mode": "count"})
data = r.json()
check("按计价方式筛选商品", r.status_code == 200 and data["total"] == 1, r.text)

# 6. 更新商品
pid = data["items"][0]["id"]
r = client.put(f"/api/products/{pid}", json={"price": 14.5})
check("更新商品价格", r.status_code == 200 and r.json()["price"] == 14.5, r.text)

# 7. 批量改价（按分类 +10%）
r = client.post("/api/products/batch-price", json={
    "mode": "category", "category_id": grain_id, "adjust_type": "percent", "value": 10,
})
check("按分类批量+10%", r.status_code == 200, r.text)
r = client.get(f"/api/products/{pid}")
# 商品此前已从 13.8 更新为 14.5，批量 +10% 后应为 14.5*1.1=15.95
check("批量改价生效(14.5->15.95)", r.json()["price"] == 15.95, r.text)

# 8. Excel 模板下载
r = client.get("/api/products/import-template")
check("导入模板下载", r.status_code == 200 and len(r.content) > 1000)

# 9. Excel 导入（构造测试文件）
wb = Workbook()
ws = wb.active
ws.append(["条码", "名称", "拼音码", "分类名称", "计价方式", "单位", "零售价", "会员价", "进价", "保质期", "库存", "安全库存", "启用"])
ws.append(["2000000000022", "西红柿", "xhs", "蔬菜/茄果", "weigh", "kg", 6.5, 6.0, 4.5, 4, 0, 15, "是"])
ws.append(["2000000000033", "黄瓜", "hg", "蔬菜/瓜类", "weigh", "kg", 5.2, 5.0, 3.8, 4, 0, 15, "是"])
ws.append(["", "坏数据", "", "", "weigh", "kg", 1, "", "", "", "", "", "是"])  # 缺条码 → 失败
buf = io.BytesIO()
wb.save(buf)
buf.seek(0)
r = client.post("/api/products/import", files={"file": ("test.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
result = r.json()
check("Excel 导入成功2行失败1行", r.status_code == 200 and result["success"] == 2 and result["failed"] == 1, r.text)
# 导入应自动创建"蔬菜/茄果"、"蔬菜/瓜类"两级分类
r = client.get("/api/sync/products")
cate_names = [c["name"] for c in r.json()["categories"]]
check("导入自动创建二级分类(茄果/瓜类)", "茄果" in cate_names and "瓜类" in cate_names, str(cate_names))

# 10. Excel 导出
r = client.get("/api/products/export")
check("商品导出", r.status_code == 200 and len(r.content) > 1000)

# 11. 同步接口（增量）
r = client.get("/api/sync/products")
data = r.json()
check("同步接口返回商品", r.status_code == 200 and len(data["products"]) >= 3, r.text)
check("同步接口返回分类", len(data["categories"]) >= 5, r.text)
after = data["server_time"]
r2 = client.get("/api/sync/products", params={"after": after})
check("增量同步(无新增)", r2.json()["products"] == [], r2.text)

# 12. 删除（临时商品）
r = client.post("/api/products", json={
    "barcode": "9999999999999", "name": "待删除", "pricing_mode": "count", "unit": "件", "price": 1,
})
tmp_id = r.json()["id"]
r = client.delete(f"/api/products/{tmp_id}")
check("删除商品", r.status_code == 200, r.text)

# 13. 删除有商品的分类被拒绝
r = client.delete(f"/api/categories/{veg_id}")
check("有商品分类删除被拒(409)", r.status_code == 409, r.text)

client.close()
print(f"\n=== 结果: {PASS} 通过, {FAIL} 失败 ===")
raise SystemExit(1 if FAIL else 0)
