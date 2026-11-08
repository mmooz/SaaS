<#
.SYNOPSIS
    鲜衡云本地测试环境：一键启动 / 停止 / 查看状态。

.DESCRIPTION
    启动三个独立控制台窗口：
      - 后端 FastAPI      http://127.0.0.1:8000
      - 后台管理 Vite     http://localhost:5173
      - POS 收银台 Vite   http://localhost:5174

    启动前自动完成：依赖检查、端口检查、backend/.env 的 AUTH_SECRET 准备、
    数据库迁移状态只读检查、R20 前端策略变量注入；就绪后自动打开浏览器。

    安全边界：本脚本不写入 backend/pos.db、不执行 Alembic 迁移、
    不执行弱口令轮换、不包含也不输出任何明文口令。

.PARAMETER Action
    start（默认）/ stop / status

.PARAMETER NoBrowser
    启动后不自动打开浏览器

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dev-env.ps1 -Action start
#>
[CmdletBinding()]
param(
    [ValidateSet('start', 'stop', 'status')]
    [string]$Action = 'start',
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'

# ---- 路径与常量（全部由脚本位置推导，不依赖双击时的工作目录）----
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$AdminWeb = Join-Path $Root 'admin-web'
$Pos = Join-Path $Root 'pos'
$Python = Join-Path $Backend '.venv\Scripts\python.exe'
$EnvFile = Join-Path $Backend '.env'
$EnvExample = Join-Path $Backend '.env.example'
$DbFile = Join-Path $Backend 'pos.db'
$StateDir = Join-Path $env:TEMP 'xianheng-dev'
$PidFile = Join-Path $StateDir 'pids.json'
$Ports = [ordered]@{ backend = 8000; admin = 5173; pos = 5174 }
$ExpectedHead = 'c4d5e6f7a8b9'

function Write-Title([string]$Text) { Write-Host "`n== $Text ==" -ForegroundColor Cyan }
function Write-Ok([string]$Text) { Write-Host "  [OK]   $Text" -ForegroundColor Green }
function Write-WarnMsg([string]$Text) { Write-Host "  [WARN] $Text" -ForegroundColor Yellow }
function Write-Fail([string]$Text) { Write-Host "  [FAIL] $Text" -ForegroundColor Red }

# 查询端口监听进程 PID；优先用 Get-NetTCPConnection，失败回退 netstat
function Get-ListenPid([int]$Port) {
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($conn) { return [int]$conn.OwningProcess }
    } catch { }
    $pattern = '^\s*TCP\s+\S+:' + $Port + '\s+\S+\s+LISTENING\s+(\d+)\s*$'
    foreach ($line in (netstat -ano -p tcp)) {
        if ($line -match $pattern) { return [int]$Matches[1] }
    }
    return 0
}

function Show-Status {
    Write-Title '当前服务状态'
    foreach ($key in $Ports.Keys) {
        $port = $Ports[$key]
        $owner = Get-ListenPid $port
        if ($owner -gt 0) {
            Write-Ok ("{0,-8} 端口 {1} 正在监听 (PID {2})" -f $key, $port, $owner)
        } else {
            Write-WarnMsg ("{0,-8} 端口 {1} 未监听" -f $key, $port)
        }
    }
}

# 读取本次启动记录的窗口 PID（供一键停止使用）
function Get-SavedPids {
    if (-not (Test-Path $PidFile)) { return $null }
    try { return (Get-Content -LiteralPath $PidFile -Raw -Encoding UTF8 | ConvertFrom-Json) }
    catch { return $null }
}

function Stop-All {
    Write-Title '停止开发环境'
    $saved = Get-SavedPids
    if ($null -eq $saved) {
        Write-WarnMsg '没有找到本次启动记录；若服务仍在运行，请在对应窗口按 Ctrl+C'
    } else {
        foreach ($key in $Ports.Keys) {
            $procId = 0
            try { $procId = [int]($saved.$key) } catch { $procId = 0 }
            if ($procId -le 0) { continue }
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            # 只终止本脚本启动的控制台窗口及其子进程，避免误杀 PID 复用后的无关进程
            if ($null -ne $proc -and $proc.ProcessName -eq 'cmd') {
                $prevPref = $ErrorActionPreference
                $ErrorActionPreference = 'Continue'
                try { & taskkill /PID $procId /T /F 2>&1 | Out-Null }
                finally { $ErrorActionPreference = $prevPref }
                Write-Ok "已关闭 $key 窗口 (PID $procId)"
            } else {
                Write-WarnMsg "$key 窗口已退出或 PID 已被复用，跳过"
            }
        }
    }
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 900
    Show-Status
    Write-Host ''
    Write-Host '  如需重新启动，双击「一键启动.bat」即可。' -ForegroundColor Gray
}

function Assert-Prereq {
    $problems = New-Object System.Collections.Generic.List[string]
    if (-not (Test-Path $Python)) {
        $problems.Add("缺少后端虚拟环境：$Python`n          请在 backend 下创建 .venv 并安装 requirements.txt")
    }
    foreach ($dir in @($AdminWeb, $Pos)) {
        if (-not (Test-Path (Join-Path $dir 'node_modules'))) {
            $problems.Add("缺少前端依赖：$dir\node_modules`n          请在该目录执行 npm install")
        }
    }
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        $problems.Add('未找到 npm.cmd，请先安装 Node.js 并确保其在 PATH 中')
    }
    if (-not (Test-Path $DbFile)) {
        $problems.Add("缺少数据库：$DbFile")
    }
    if ($problems.Count -gt 0) {
        foreach ($p in $problems) { Write-Fail $p }
        exit 1
    }
    Write-Ok '依赖检查通过（Python 虚拟环境 / Node / 双前端依赖 / 数据库）'
}

# 从 .env 读取单个键值；空值或不存在时返回 fallback
function Read-EnvValue([string[]]$Lines, [string]$Key, [string]$Fallback) {
    $pattern = '^\s*' + [regex]::Escape($Key) + '\s*=\s*(.*?)\s*$'
    foreach ($line in $Lines) {
        if ($line -match $pattern) {
            $value = $Matches[1]
            if ($value -ne '') { return $value }
        }
    }
    return $Fallback
}

# 确保 backend/.env 存在且 AUTH_SECRET 有效；已有效则沿用，避免重启后令牌全部失效
function Ensure-LocalEnv {
    $lines = @()
    if (Test-Path $EnvFile) {
        $lines = @(Get-Content -LiteralPath $EnvFile -Encoding UTF8)
    } elseif (Test-Path $EnvExample) {
        $lines = @(Get-Content -LiteralPath $EnvExample -Encoding UTF8)
    }

    $existing = ''
    foreach ($line in $lines) {
        if ($line -match '^\s*AUTH_SECRET\s*=\s*(.*?)\s*$') { $existing = $Matches[1] }
    }
    if ($existing.Length -ge 32) {
        Write-Ok 'backend/.env 已有有效 AUTH_SECRET（沿用，重启后登录态保持有效）'
    } else {
        $bytes = New-Object 'byte[]' 48
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
        $secret = -join ($bytes | ForEach-Object { $_.ToString('x2') })
        $found = $false
        $output = New-Object System.Collections.Generic.List[string]
        foreach ($line in $lines) {
            if ($line -match '^\s*AUTH_SECRET\s*=') {
                $output.Add("AUTH_SECRET=$secret")
                $found = $true
            } else {
                $output.Add($line)
            }
        }
        if (-not $found) { $output.Add("AUTH_SECRET=$secret") }
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($EnvFile, ($output -join "`r`n") + "`r`n", $utf8NoBom)
        Write-Ok '已生成 backend/.env 并写入 96 位随机 AUTH_SECRET（仅本机，已被 .gitignore 排除）'
    }
    return @(Get-Content -LiteralPath $EnvFile -Encoding UTF8)
}

# 只读检查数据库迁移版本与待改密列，绝不写库、绝不自动升级
function Show-DbState {
    $probeFile = Join-Path $StateDir 'db_state_probe.py'
    [string[]]$probeLines = @(
        'import sqlite3'
        'c = sqlite3.connect("pos.db")'
        'try:'
        '    row = c.execute("select version_num from alembic_version").fetchone()'
        'except Exception:'
        '    row = None'
        'cols = [r[1] for r in c.execute("pragma table_info(users)")]'
        'n = c.execute("select count(*) from users").fetchone()[0]'
        'print("version=%s|flag=%s|users=%s" % (row[0] if row else "NONE", "must_change_password" in cols, n))'
        'c.close()'
    )
    New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($probeFile, $probeLines, $utf8NoBom)
    Push-Location $Backend
    $prevPref = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $raw = (& $Python -X utf8 $probeFile 2>&1 | Out-String).Trim()
    } finally {
        $ErrorActionPreference = $prevPref
        Pop-Location
    }
    if ($raw -match 'version=(\S+)\|flag=(\w+)\|users=(\d+)') {
        $version = $Matches[1]
        $hasFlag = $Matches[2]
        $userCount = $Matches[3]
        Write-Ok ("数据库只读检查：alembic_version={0}，用户数={1}" -f $version, $userCount)
        if ($version -ne $ExpectedHead -or $hasFlag -ne 'True') {
            Write-WarnMsg "迁移未到 head（期望 $ExpectedHead 且含 must_change_password 列），登录可能失败"
            Write-WarnMsg '请在 backend 目录先执行：.venv\Scripts\python.exe -m alembic upgrade head'
        }
    } else {
        Write-WarnMsg "数据库状态读取失败：$raw"
    }
}

# 用原始 TCP 连接探活：绕开系统 HTTP 代理与 IPv6 解析，避免误判
function Wait-PortReady([string]$Name, [int]$Port, [int]$TimeoutSec) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $client = New-Object System.Net.Sockets.TcpClient
        try {
            $async = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
            if ($async.AsyncWaitHandle.WaitOne(1000, $false) -and $client.Connected) {
                Write-Ok ("{0} 已就绪：127.0.0.1:{1}" -f $Name, $Port)
                return $true
            }
        } catch { }
        finally { $client.Close() }
        Start-Sleep -Milliseconds 700
    }
    Write-Fail "$Name 在 $TimeoutSec 秒内未就绪，请查看对应控制台窗口的报错"
    return $false
}

# 后端额外做一次 HTTP 健康检查；Proxy = $null 明确绕开环境代理
function Test-ApiHealth {
    try {
        $req = [System.Net.HttpWebRequest]::Create('http://127.0.0.1:8000/api/health')
        $req.Proxy = $null
        $req.Timeout = 3000
        $resp = $req.GetResponse()
        $code = [int]$resp.StatusCode
        $resp.Close()
        return ($code -eq 200)
    } catch {
        return $false
    }
}

function Start-All {
    Write-Title '环境检查'
    Assert-Prereq

    $busy = $false
    foreach ($key in $Ports.Keys) {
        $port = $Ports[$key]
        $owner = Get-ListenPid $port
        if ($owner -gt 0) {
            Write-Fail "端口 $port 已被 PID $owner 占用；若属上次启动，请先运行「一键停止.bat」"
            $busy = $true
        }
    }
    if ($busy) { exit 1 }
    Write-Ok '端口 8000 / 5173 / 5174 均空闲'

    $envLines = Ensure-LocalEnv
    Show-DbState

    # R20 前端策略：数值一律从 backend/.env 读取，保证前后端口径一致（不写死在脚本里）
    $env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
    $env:VITE_OFFLINE_ORDER_MAX_AMOUNT = Read-EnvValue $envLines 'OFFLINE_ORDER_MAX_AMOUNT' '200'
    $env:VITE_OFFLINE_ORDER_MAX_AGE_HOURS = Read-EnvValue $envLines 'OFFLINE_ORDER_MAX_AGE_HOURS' '2'
    $env:VITE_ONLINE_STORED_VALUE_PAYMENT_ENABLED = Read-EnvValue $envLines 'ONLINE_STORED_VALUE_PAYMENT_ENABLED' 'false'
    # 后端绝对路径通过环境变量传给 cmd，避免中文路径在批处理文件中出现编码问题
    $env:XH_PYTHON = $Python
    Write-Ok ("已注入 VITE_* 策略：离线限额 {0} 元 / {1} 小时，在线储值 {2}" -f `
        $env:VITE_OFFLINE_ORDER_MAX_AMOUNT, $env:VITE_OFFLINE_ORDER_MAX_AGE_HOURS, `
        $env:VITE_ONLINE_STORED_VALUE_PAYMENT_ENABLED)

    Write-Title '启动三个服务窗口'
    New-Item -ItemType Directory -Force -Path $StateDir | Out-Null

    $backendCmd = 'title XH-Backend-8000 && "%XH_PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000'
    $adminCmd = 'title XH-AdminWeb-5173 && npm run dev'
    $posCmd = 'title XH-POS-5174 && npm run dev'

    $pBackend = Start-Process -FilePath 'cmd.exe' -ArgumentList "/k $backendCmd" `
        -WorkingDirectory $Backend -PassThru
    Write-Ok "后端 FastAPI 窗口已启动 (PID $($pBackend.Id))"
    $pAdmin = Start-Process -FilePath 'cmd.exe' -ArgumentList "/k $adminCmd" `
        -WorkingDirectory $AdminWeb -PassThru
    Write-Ok "后台管理窗口已启动 (PID $($pAdmin.Id))"
    $pPos = Start-Process -FilePath 'cmd.exe' -ArgumentList "/k $posCmd" `
        -WorkingDirectory $Pos -PassThru
    Write-Ok "POS 收银台窗口已启动 (PID $($pPos.Id))"

    $state = [ordered]@{
        backend = $pBackend.Id
        admin = $pAdmin.Id
        pos = $pPos.Id
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($PidFile, ($state | ConvertTo-Json), $utf8NoBom)

    Write-Title '等待服务就绪'
    $apiOk = Wait-PortReady '后端 API' 8000 40
    $adminOk = Wait-PortReady '后台管理' 5173 40
    $posOk = Wait-PortReady 'POS 收银台' 5174 40
    if ($apiOk) {
        if (Test-ApiHealth) { Write-Ok '后端 /api/health 返回 200' }
        else { Write-WarnMsg '后端端口已监听，但 /api/health 未返回 200，请查看后端窗口' }
    }

    if ($apiOk -and $adminOk -and $posOk -and -not $NoBrowser) {
        Start-Process 'http://127.0.0.1:5173'
        Start-Sleep -Milliseconds 400
        Start-Process 'http://127.0.0.1:5174'
        Write-Ok '已在默认浏览器打开后台管理与 POS 收银台'
    }

    Write-Title '启动完成'
    Write-Host '  后台管理   http://127.0.0.1:5173' -ForegroundColor White
    Write-Host '  POS 收银   http://127.0.0.1:5174' -ForegroundColor White
    Write-Host '  API 文档   http://127.0.0.1:8000/docs' -ForegroundColor White
    Write-Host '  健康检查   http://127.0.0.1:8000/api/health' -ForegroundColor White
    Write-Host ''
    Write-Host '  登录提示：2026-11-08 已完成弱口令轮换，旧口令 123456 全部失效。' -ForegroundColor Yellow
    Write-Host '  首次登录须使用各账号的临时口令，并按页面引导强制改密。' -ForegroundColor Yellow
    Write-Host '  临时口令不写入任何脚本 / 文档；若已丢失，可在项目根目录重新生成单账号临时口令：' -ForegroundColor Yellow
    Write-Host '    backend\.venv\Scripts\python.exe -X utf8 backend\tools\rotate_weak_passwords.py --db backend\pos.db --user admin --random --apply' -ForegroundColor Gray
    Write-Host '  账号：superadmin / admin / store01 / cashier01 / cashier02 / cashier03' -ForegroundColor Gray
    Write-Host '  注意：cashier03 为既有停用账号，需先在后台启用后才能登录。' -ForegroundColor Gray
    Write-Host ''
    Write-Host '  停止服务：双击「一键停止.bat」，或在三个控制台窗口按 Ctrl+C。' -ForegroundColor Cyan
    Write-Host '  桌面端（可选）：先构建 Tauri，再在 pos 目录执行 npm run dev:desktop。' -ForegroundColor Gray
    Write-Host ''
}

switch ($Action) {
    'start' { Start-All }
    'stop' { Stop-All }
    'status' { Show-Status }
}
