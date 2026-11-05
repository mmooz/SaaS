"""临时验证脚本：会员 API（建档/查询/充值/消费/积分/流水）。"""
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

# 每次运行使用唯一手机号，避免与历史数据冲突
mobile = "139" + str(int(time.time()))[-8:]

# 1. 会员建档
r = client.post("/api/members", json={"mobile": mobile, "name": "测试会员"})
check("会员建档成功", r.status_code == 201, r.text)
member = r.json()
member_id = member.get("id")
check("建档初始余额为 0", member.get("balance") == 0 and member.get("points") == 0, r.text)

# 2. 重复建档应返回 409
r = client.post("/api/members", json={"mobile": mobile, "name": "重复"})
check("重复手机号建档返回409", r.status_code == 409, r.text)

# 3. 按手机号查询
r = client.get(f"/api/members/{mobile}")
check("按手机号查会员", r.status_code == 200 and r.json()["id"] == member_id, r.text)

# 4. 会员列表与关键字搜索
r = client.get("/api/members", params={"keyword": mobile})
check("会员列表按手机号搜索", r.status_code == 200 and r.json()["total"] >= 1, r.text)

# 5. 更新姓名与等级
r = client.patch(f"/api/members/{member_id}", json={"name": "张三", "level": "gold"})
check("更新会员资料", r.status_code == 200 and r.json()["level"] == "gold", r.text)

# 6. 储值充值 100 元 + 赠送 10 积分
r = client.post(f"/api/members/{member_id}/recharge", json={"amount": 100, "bonus_points": 10})
check("充值后余额 100", r.status_code == 200 and r.json()["balance"] == 100, r.text)
check("充值赠送积分 10", r.json()["points"] == 10, r.text)

# 7. 储值消费 30 元（默认 1 元 1 积分）
r = client.post(f"/api/members/{member_id}/consume", json={"amount": 30, "order_no": "TEST-0001"})
data = r.json()
check("消费后余额扣减到 70", r.status_code == 200 and data["balance"] == 70, r.text)
check("消费累计积分 40", data["points"] == 40, r.text)
check("累计消费额 30", data["total_spent"] == 30, r.text)

# 8. 余额不足时消费应拒绝
r = client.post(f"/api/members/{member_id}/consume", json={"amount": 999})
check("余额不足消费返回400", r.status_code == 400, r.text)

# 9. 手工增加积分 20
r = client.post(f"/api/members/{member_id}/points", json={"points": 20})
check("积分调整为 60", r.status_code == 200 and r.json()["points"] == 60, r.text)

# 10. 扣减超过现有积分应拒绝
r = client.post(f"/api/members/{member_id}/points", json={"points": -100})
check("超额扣减积分返回400", r.status_code == 400, r.text)

# 11. 流水查询（充值1 + 消费1 + 积分1 = 3 条）
r = client.get(f"/api/members/{member_id}/transactions")
tx = r.json()
check("会员流水共 3 条", r.status_code == 200 and tx["total"] == 3, r.text)
check("流水含消费记录", any(t["type"] == "consume" for t in tx["items"]), r.text)

# 12. 不存在的会员返回 404
r = client.get("/api/members/00000000000")
check("不存在会员返回404", r.status_code == 404, r.text)

# 13. 充值赠送金额计入余额
mobile2 = "138" + str(int(time.time()))[-8:]
r = client.post("/api/members", json={"mobile": mobile2, "name": "赠金会员"})
check("第二个会员建档", r.status_code == 201, r.text)
member2_id = r.json()["id"]
r = client.post(
    f"/api/members/{member2_id}/recharge", json={"amount": 50, "gift_amount": 5}
)
check("赠金充值余额 55", r.status_code == 200 and r.json()["balance"] == 55, r.text)

# 14. 会员概览统计
r = client.get("/api/members/stats")
data = r.json()
check("统计返回会员总数", r.status_code == 200 and data["total"] >= 2, r.text)
check("统计返回消费排行", isinstance(data["top"], list) and len(data["top"]) >= 1, r.text)
check("统计含本月充值", data["recharge_this_month"] >= 55, r.text)

# 15. 全量流水查询（按会员筛选）
r = client.get("/api/members/transactions/all", params={"member_id": member_id})
check("全量流水含会员手机号", r.status_code == 200 and r.json()["items"][0]["mobile"] == mobile, r.text)

client.close()
print(f"\n=== 结果: {PASS} 通过, {FAIL} 失败 ===")
raise SystemExit(1 if FAIL else 0)
