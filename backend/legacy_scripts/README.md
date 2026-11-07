# 历史临时验证脚本（禁止直接用 pytest 运行）

本目录原为 `backend/tests/`，存放 S2–S6 阶段的 6 个**模块顶层 `httpx` 直连
`127.0.0.1:8000` 的临时验证脚本**。它们不是 pytest 用例：没有 `def test_`、
没有断言、没有 fixture，末尾 `raise SystemExit`，且不带 `Authorization` /
`X-Store-Id` 请求头。

其中 `s2_api_check.py` 原在**模块顶层**执行 `sqlite3.connect("pos.db")` +
`DELETE FROM product_price_history / products / categories` + `commit()`，
相对路径不受 `DATABASE_URL` 控制；pytest 在**收集阶段**（import 时）就会执行，
QA 实测会真实删库。

## Q27-a 已做的止血

- 目录整体重命名为 `legacy_scripts/`，6 个脚本去掉 `test_` 前缀
  （`s2_api_check.py` 等），因此任何 `pytest` 调用都不会再收集、导入它们。
- `s2_api_check.py` 的顶层 DELETE 块已注释禁用，即使被显式指定为文件运行
  也不会产生任何 DELETE。
- 6 个脚本内容一字未删，完整保留供 B5 重写参考。
- 未引入 `pytest.ini`：改名后全项目已无任何 `test_*.py`，pytest 默认收集 0 个文件；
  `testpaths` 只能约束「无参数 pytest」，无法阻止显式路径，反而会引入
  「指向空目录」的困惑；待 B5 重建用例时再配套引入更合理。

## 约束

- **禁止**用 `pytest` 或 `python` 直接运行本目录下的任何脚本：它们会连接
  `127.0.0.1:8000`，并对当前工作目录下的 `pos.db` 做写操作。
- 所有验证必须在系统临时目录沙箱 + `pos.db` 副本上进行，
  真实 `backend/pos.db` 不得被改动。
- 真实 pytest 用例重建见整改清单 **Q27-b（B5 批次）**：`TestClient` +
  独立内存库 fixture + 依赖覆盖注入认证上下文 + 越权矩阵 / 资损 / 幂等回归断言。
