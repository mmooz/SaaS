"""临时验证脚本：促销规则 API（创建/查询/生效/更新/删除）。"""
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
created_ids = []

# 1. 新建限时特价（商品 1，特价 3.9）
r = client.post(
    "/api/promotions",
    json={"type": "special", "name": "上海青限时特价", "product_ids": [1], "params": {"price": 3.9}},
)
check("新建限时特价", r.status_code == 201, r.text)
special = r.json()
created_ids.append(special["id"])
check("返回参数已解析为对象", special["params"]["price"] == 3.9, r.text)
check("返回商品列表已解析", special["product_ids"] == [1], r.text)

# 2. 新建折扣促销（全场 9 折）
r = client.post(
    "/api/promotions",
    json={"type": "discount", "name": "全场9折", "params": {"rate": 0.9}},
)
check("新建折扣促销", r.status_code == 201, r.text)
discount = r.json()
created_ids.append(discount["id"])

# 3. 新建满减促销（满100减10）
r = client.post(
    "/api/promotions",
    json={"type": "full_reduce", "name": "满100减10", "params": {"threshold": 100, "reduce": 10}},
)
check("新建满减促销", r.status_code == 201, r.text)
created_ids.append(r.json()["id"])

# 4. 列表与生效列表
r = client.get("/api/promotions")
check("促销列表查询", r.status_code == 200 and len(r.json()) >= 3, r.text)
r = client.get("/api/promotions/active")
names = {p["name"] for p in r.json()}
check("生效列表含特价与满减", {"上海青限时特价", "满100减10"} <= names, r.text)

# 5. 停用特价后不再出现在生效列表
r = client.patch(f"/api/promotions/{special['id']}", json={"enabled": False})
check("停用促销", r.status_code == 200 and r.json()["enabled"] is False, r.text)
r = client.get("/api/promotions/active")
check("停用后不在生效列表", "上海青限时特价" not in {p["name"] for p in r.json()}, r.text)

# 6. 按启用状态筛选
r = client.get("/api/promotions", params={"enabled": "false"})
check("按停用状态筛选", r.status_code == 200 and any(p["id"] == special["id"] for p in r.json()), r.text)

# 7. 时间窗口外的促销不生效
r = client.post(
    "/api/promotions",
    json={
        "type": "special",
        "name": "已过期特价",
        "params": {"price": 1.0},
        "start_at": "2020-01-01T00:00:00",
        "end_at": "2020-12-31T00:00:00",
    },
)
check("新建过期促销", r.status_code == 201, r.text)
expired_id = r.json()["id"]
created_ids.append(expired_id)
check("过期促销不在生效列表", "已过期特价" not in {p["name"] for p in client.get("/api/promotions/active").json()}, "")

# 8. 删除促销
r = client.delete(f"/api/promotions/{discount['id']}")
check("删除促销返回204", r.status_code == 204, r.text)
r = client.get("/api/promotions")
check("删除后列表不含该促销", all(p["id"] != discount["id"] for p in r.json()), r.text)

# 9. 更新不存在的促销返回 404
r = client.patch("/api/promotions/999999", json={"name": "不存在"})
check("更新不存在促销返回404", r.status_code == 404, r.text)

# 清理本次创建的促销，保证脚本可重复运行
for pid in created_ids:
    client.delete(f"/api/promotions/{pid}")

client.close()
print(f"\n=== 结果: {PASS} 通过, {FAIL} 失败 ===")
raise SystemExit(1 if FAIL else 0)
