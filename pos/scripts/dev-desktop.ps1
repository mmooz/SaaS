<#
.SYNOPSIS
    启动 Tauri 桌面端开发程序，并自动设置 WebView2 数据目录。
.DESCRIPTION
    部分机器上 %LOCALAPPDATA% 下的默认 WebView2 数据目录会被安全软件或权限策略锁定，
    导致应用启动时报 0x800700AA（请求的资源在使用中）或 拒绝访问。
    本脚本把数据目录改到 pos/src-tauri/target/wv2data，再启动调试版 pos.exe。
    运行前需先执行 cargo build，并另开终端执行 npm run dev。
#>

$ErrorActionPreference = 'Stop'

# pos 目录（scripts 目录的上一级）
$posRoot = Split-Path -Parent $PSScriptRoot
# 调试版可执行文件路径
$exePath = Join-Path $posRoot 'src-tauri\target\debug\pos.exe'
# 独立的 WebView2 用户数据目录（放在构建产物目录内，避免污染系统用户数据）
$webviewDataDir = Join-Path $posRoot 'src-tauri\target\wv2data'

if (-not (Test-Path $exePath)) {
    Write-Host "未找到 $exePath" -ForegroundColor Red
    Write-Host "请先执行：cargo build --manifest-path src-tauri/Cargo.toml" -ForegroundColor Yellow
    exit 1
}

# 确保 WebView2 数据目录存在并注入环境变量
New-Item -ItemType Directory -Force -Path $webviewDataDir | Out-Null
$env:WEBVIEW2_USER_DATA_FOLDER = $webviewDataDir

# 提示前端开发服务是否就绪（调试版桌面端默认加载 http://localhost:5174）
try {
    $status = (Invoke-WebRequest -UseBasicParsing 'http://localhost:5174' -TimeoutSec 3).StatusCode
    Write-Host "前端开发服务已就绪（HTTP $status）" -ForegroundColor Green
} catch {
    Write-Host "前端开发服务未启动，请另开终端执行 npm run dev" -ForegroundColor Yellow
}

Write-Host "启动桌面端：$exePath" -ForegroundColor Cyan
& $exePath
