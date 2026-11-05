"""临时验证脚本：报表 API（日报/商品排行/时段/毛利/会员）。"""

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
start, end = "2020-01-01", "2026-12-31"
query = {"start": start, "end": end}

# 1. 销售日报
r = client.get("/api/reports/daily", params=query)
check("日报接口可用", r.status_code == 200, r.text)
daily = r.json()
check("日报汇总字段完整", set(daily["summary"].keys()) == {"sales", "orders", "avg_price", "weight_kg"})
check("日报客单价计算正确", abs(daily["summary"]["avg_price"] - round(daily["summary"]["sales"] / daily["summary"]["orders"], 2)) < 0.01)
check("趋势合计等于销售额", abs(sum(p["sales"] for p in daily["trend"]) - daily["summary"]["sales"]) < 0.05)

# 2. 按周趋势
r = client.get("/api/reports/daily", params={**query, "mode": "week"})
check("按周趋势可用", r.status_code == 200 and len(r.json()["trend"]) >= 1, r.text)

# 3. 商品排行
r = client.get("/api/reports/products", params={**query, "limit": 15})
check("商品排行可用", r.status_code == 200, r.text)
rank = r.json()
check("排行为倒序", all(rank["items"][i]["amount"] >= rank["items"][i + 1]["amount"] for i in range(len(rank["items"]) - 1)))
check("商品销售额与日报一致", abs(rank["total_amount"] - daily["summary"]["sales"]) < 0.05, f"{rank['total_amount']} vs {daily['summary']['sales']}")
check("排行占比合计接近 100", abs(sum(i["ratio"] for i in rank["items"]) - 100) <= 5 if rank["items"] else True)

# 4. 时段分析
r = client.get("/api/reports/hourly", params=query)
check("时段分析可用", r.status_code == 200, r.text)
hourly = r.json()
check("时段点数量为 24", len(hourly["points"]) == 24)
check("时段销售额与日报一致", abs(hourly["total_sales"] - daily["summary"]["sales"]) < 0.05)
check("高峰销售额为最大时段", hourly["peak_sales"] == max(p["sales"] for p in hourly["points"]))

# 5. 毛利分析
r = client.get("/api/reports/profit", params=query)
check("毛利分析可用", r.status_code == 200, r.text)
profit = r.json()
check("毛利销售额与日报一致", abs(profit["sales"] - daily["summary"]["sales"]) < 0.05)
check("毛利 = 销售额 - 成本", abs(profit["profit"] - (profit["sales"] - profit["cost"])) < 0.05)
check("分类毛利合计一致", abs(sum(c["sales"] for c in profit["categories"]) - profit["sales"]) < 0.05)

# 6. 会员分析
r = client.get("/api/reports/members", params={**query, "limit": 10})
check("会员分析可用", r.status_code == 200, r.text)
members = r.json()
check("会员总数大于 0", members["member_total"] > 0)
check("会员消费不超过总销售", members["member_sales"] <= daily["summary"]["sales"] + 0.01)
check("会员占比计算正确", abs(members["member_ratio"] - round(members["member_sales"] / daily["summary"]["sales"] * 100, 1)) < 0.11 if daily["summary"]["sales"] else True)
check("会员排行金额倒序", all(members["items"][i]["amount"] >= members["items"][i + 1]["amount"] for i in range(len(members["items"]) - 1)))

# 7. 参数校验
r = client.get("/api/reports/daily", params={"start": start, "end": end, "mode": "bad"})
check("非法模式被拒绝", r.status_code == 422)

print(f"\n结果：PASS={PASS} FAIL={FAIL}")
