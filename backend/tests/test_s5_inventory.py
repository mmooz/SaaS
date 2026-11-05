"""临时验证脚本：库存 API（查询/入库/盘点/报损/预警/销售扣减）。"""

import time

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

# 选取一个称重商品与一个按件商品
products = client.get("/api/products", params={"page_size": 100}).json()["items"]
weighed = next(p for p in products if p["pricing_mode"] == "weigh")
counted = next(p for p in products if p["pricing_mode"] == "count")
weighed_stock = weighed["stock"]
counted_stock = counted["stock"]

# 1. 库存列表
r = client.get("/api/inventory")
check("库存列表查询", r.status_code == 200 and r.json()["total"] > 0, r.text)

# 2. 采购入库
r = client.post(
    "/api/inventory/inbound",
    json={"product_id": weighed["id"], "qty": 5, "cost_price": 12.5},
)
check("入库成功", r.status_code == 200 and r.json()["stock"] == round(weighed_stock + 5, 3), r.text)

# 3. 入库流水
r = client.get("/api/inventory/movements", params={"product_id": weighed["id"], "type": "inbound"})
check("入库流水已记录", r.status_code == 200 and r.json()["total"] >= 1, r.text)
check("流水含商品名称", r.json()["items"][0]["product_name"] == weighed["name"], r.text)

# 4. 盘点：实盘 = 当前 + 3，库存被覆盖
r = client.post(
    "/api/inventory/stocktake",
    json={"product_id": weighed["id"], "actual": weighed_stock + 8},
)
check("盘点覆盖库存", r.status_code == 200 and r.json()["stock"] == round(weighed_stock + 8, 3), r.text)
check("盘点差异正确", r.json()["diff"] == 3, r.text)

# 5. 报损数量超过库存应拒绝
r = client.post("/api/inventory/breakage", json={"product_id": weighed["id"], "qty": 9999})
check("超库存报损返回400", r.status_code == 400, r.text)

# 6. 报损 1 单位
before = weighed_stock + 8
r = client.post("/api/inventory/breakage", json={"product_id": weighed["id"], "qty": 1})
check("报损扣减库存", r.status_code == 200 and r.json()["stock"] == round(before - 1, 3), r.text)

# 7. 订单销售自动扣库存（称重 0.5kg）
order_no = "INV" + str(int(time.time()))[-8:]
current = client.get(f"/api/products/{weighed['id']}").json()["stock"]
r = client.post(
    "/api/orders",
    json={
        "order_no": order_no,
        "total_amount": 20,
        "pay_details": '{"现金": 20}',
        "items": [
            {
                "product_id": weighed["id"],
                "name": weighed["name"],
                "qty": 1,
                "weight_kg": 0.5,
                "unit_price": 40,
                "amount": 20,
                "is_weighted": True,
            }
        ],
    },
)
check("上传订单成功", r.status_code == 201, r.text)
after = client.get(f"/api/products/{weighed['id']}").json()["stock"]
check("订单自动扣减库存 0.5", round(after, 3) == round(current - 0.5, 3), f"{current}->{after}")
sale = client.get(
    "/api/inventory/movements", params={"product_id": weighed["id"], "type": "sale"}
).json()
check("销售流水已记录", any(m["ref_id"] is not None for m in sale["items"]), str(sale))

# 8. 预警：把按件商品盘点为 0 后应出现在预警列表
client.post("/api/inventory/stocktake", json={"product_id": counted["id"], "actual": 0})
r = client.get("/api/inventory/alerts")
check("售罄商品出现在预警", any(i["product_id"] == counted["id"] for i in r.json()["items"]), r.text)
check("预警状态为 out", any(i["status"] == "out" for i in r.json()["items"]), r.text)

# 9. 恢复演示库存，避免污染数据
client.post("/api/inventory/stocktake", json={"product_id": weighed["id"], "actual": weighed_stock})
client.post("/api/inventory/stocktake", json={"product_id": counted["id"], "actual": counted_stock})

client.close()
print(f"\n=== 结果: {PASS} 通过, {FAIL} 失败 ===")
raise SystemExit(1 if FAIL else 0)
