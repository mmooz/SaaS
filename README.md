# 鲜衡云 · 电子秤收银系统

多租户 SaaS 电子秤收银系统：FastAPI + SQLite 后端、Vue3 后台管理、Vue3 / Tauri2 POS 收银台。

## 一键启动（本地测试）

**双击项目根目录的 `一键启动.bat`** 即可。脚本会依次完成：

1. 检查 Python 虚拟环境、Node/npm、双前端 `node_modules`、数据库文件是否齐备；
2. 检查 8000 / 5173 / 5174 端口是否空闲（被占用会提示先停止，不会重复启动）；
3. 首次运行时由 `backend/.env.example` 生成 `backend/.env`，写入 96 位随机 `AUTH_SECRET`（已被 `.gitignore` 排除，重启沿用同一密钥，登录态不会失效）；
4. 只读检查数据库迁移版本与 `must_change_password` 列，版本落后时给出明确提示；
5. 从 `backend/.env` 读取 R20 策略并注入前端 `VITE_*` 变量，保证前后端限额 / 时限口径一致；
6. 打开三个独立控制台窗口运行后端与两个前端，等待全部就绪后自动打开浏览器。

停止服务：双击 **`一键停止.bat`**（会关闭三个窗口及其子进程），或在各窗口按 `Ctrl+C`。

也可在 PowerShell 中直接使用核心脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev-env.ps1 -Action start
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev-env.ps1 -Action status
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev-env.ps1 -Action stop
# 只启动不打开浏览器
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev-env.ps1 -Action start -NoBrowser
```

| 服务 | 地址 | 启动命令 |
| --- | --- | --- |
| 后端 API / 文档 | `http://127.0.0.1:8000/docs` | `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`（`backend` 目录） |
| 后台管理 | `http://127.0.0.1:5173` | `npm run dev`（`admin-web` 目录） |
| POS 收银台（浏览器） | `http://127.0.0.1:5174` | `npm run dev`（`pos` 目录） |

访问地址统一用 `127.0.0.1`（IPv4 直连）：本机若配置了 `HTTP_PROXY`，`localhost` 可能被代理或 IPv6 解析干扰。脚本已设置 `NO_PROXY` 并用原始 TCP 端口探活，不受代理影响。

Tauri 桌面端为可选项，需先构建 Rust 侧，再在 `pos` 目录执行 `npm run dev:desktop`；一键脚本默认只启动浏览器版 POS。

## 登录账号（重要）

2026-11-08 已完成弱口令轮换：6 个账号的旧口令 `123456` **全部失效**，各持独立的临时口令并启用**服务端强制首次改密**。临时口令只在轮换时于终端输出一次，**不写入任何脚本、文档或版本库**。

- 账号：`superadmin` / `admin` / `store01` / `cashier01` / `cashier02` / `cashier03`
- 首次登录需使用临时口令，页面会强制要求修改密码；改密后所有旧令牌立即失效
- `cashier03` 为既有停用账号（`enabled=0`），需先在后台启用
- 临时口令丢失时，可在项目根目录单独重轮换（只在终端输出一次，不落盘）：

```bat
backend\.venv\Scripts\python.exe -X utf8 backend\tools\rotate_weak_passwords.py --db backend\pos.db --user admin --random --apply
```

## 脚本的安全边界

一键脚本**不会**写入 `backend/pos.db`、不会执行 `alembic upgrade head`、不会执行弱口令轮换、不包含也不输出任何明文口令。数据库迁移与账号轮换仍是有意保留的显式运维动作。

`backend/pos.db.bak.*` 两份备份含旧口令哈希与全量业务数据，属于敏感文件（已排除版本控制），请按敏感数据保管或销毁。

## 常见问题

| 现象 | 处理 |
| --- | --- |
| 浏览器打不开页面 | 用 `127.0.0.1` 而非 `localhost`；确认三个服务窗口没有报错，检查浏览器代理是否绕过本地地址 |
| 提示端口被占用 | 先双击 `一键停止.bat`；若仍占用，用 `netstat -ano \| findstr :8000` 查 PID |
| 提示缺少 `node_modules` | 在对应前端目录执行 `npm install` |
| 后端窗口启动即退出 | 多为 `AUTH_SECRET` 缺失或短于 32 位，脚本会自动生成；手工启动时请自行配置 `backend/.env` |
| 提示迁移未到 head | 在 `backend` 目录执行 `.venv\Scripts\python.exe -m alembic upgrade head` |
| 登录一直 403「请先修改密码」 | 属 R19 强制改密，按登录页引导改密后重新登录 |
| 离线订单被拒绝 | R20 临时资金管控：离线单限额 / 时限由 `backend/.env` 控制，在线储值支付默认关闭 |

更多整改背景与遗留风险见 `.trae/documents/电子秤收银系统整改清单.md`，B3 与 PostgreSQL 迁移设计见 `.trae/documents/鲜衡云B3与PG迁移增量设计.md`。
