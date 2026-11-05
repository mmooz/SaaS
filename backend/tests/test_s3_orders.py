"""临时验证脚本：订单上传 API（幂等收单/列表/详情）。"""
import httpx

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0


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

# 1. 上传订单（称重+按件混合）
order = {
    "order_no": "20261105-00001",
    "cashier_id": 1,
    "status": "paid",
    "total_amount": 18.68,
    "discount_amount": 0,
    "pay_details": '{"微信": 18.68}',
    "items": [
        {"product_id": 1, "name": "上海青", "qty": 1, "weight_kg": 0.86, "unit_price": 4.8, "amount": 4.13, "is_weighted": True, "label_printed": True},
        {"product_id": 2, "name": "五花肉", "qty": 1, "weight_kg": 0.5, "unit_price": 28.8, "amount": 14.4, "is_weighted": True, "label_printed": True},
        {"product_id": 14, "name": "鲜鸡蛋(盒)", "qty": 1, "unit_price": 13.8, "amount": 13.8, "is_weighted": False, "label_printed": False},
    ],
}
r = client.post("/api/orders", json=order)
check("上传订单成功", r.status_code == 201, r.text)
saved = r.json()
check("订单含明细", len(saved["items"]) == 3, r.text)

# 2. 幂等：重复上传同 order_no 返回已有订单
r2 = client.post("/api/orders", json=order)
check("重复上传幂等返回已有订单", r2.status_code == 201 and r2.json()["id"] == saved["id"], r2.text)

# 3. 订单列表
r = client.get("/api/orders")
data = r.json()
check("订单列表查询", r.status_code == 200 and data["total"] >= 1, r.text)

# 4. 按订单号查询详情
r = client.get("/api/orders/20261105-00001")
check("按订单号查详情", r.status_code == 200 and r.json()["items"][0]["name"] == "上海青", r.text)

# 5. 不存在的订单返回 404
r = client.get("/api/orders/NOT-EXIST")
check("不存在订单返回404", r.status_code == 404, r.text)

client.close()
print(f"\n=== 结果: {PASS} 通过, {FAIL} 失败 ===")
raise SystemExit(1 if FAIL else 0)
