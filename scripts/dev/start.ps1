<#
.SYNOPSIS
    Chạy Web Dashboard trên máy: API (Python) + giao diện (React).

.DESCRIPTION
    Mặc định: build frontend rồi chạy scripts/dev/run_server.py, mở http://localhost:8000.
    -Dev     : chạy backend trong cửa sổ PowerShell mới + Vite dev server, mở http://localhost:5173
               (sửa code frontend là thấy ngay).
    -Install : cài thư viện Python (requirements.txt + pytest) và npm trước khi chạy.

    Cảnh báo: server dùng DATABASE_URL trong .env. Xem thì an toàn; tick hoàn thành hay
    thêm deadline sẽ GHI THẬT vào DB đó. Muốn thử an toàn, đặt DATABASE_URL của staging trước:
        $env:DATABASE_URL = "<url staging>"; .\scripts\dev\start.ps1

.EXAMPLE
    .\scripts\dev\start.ps1
.EXAMPLE
    .\scripts\dev\start.ps1 -Dev
.EXAMPLE
    .\scripts\dev\start.ps1 -Install -Dev
#>
param(
    [switch]$Dev,
    [switch]$Install
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root

function Invoke-Step([string]$Title, [scriptblock]$Command) {
    Write-Host "==> $Title" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Lỗi ở bước: $Title (exit code $LASTEXITCODE)"
    }
}

if ($Install) {
    Invoke-Step 'Cài thư viện Python' { python -m pip install -r requirements.txt pytest }
    Invoke-Step 'Cài thư viện frontend (npm)' { npm --prefix frontend install }
}

if ($Dev) {
    Write-Host '==> Mở backend API (http://localhost:8000) trong cửa sổ mới' -ForegroundColor Cyan
    Start-Process powershell -WorkingDirectory $root -ArgumentList '-NoExit', '-Command', 'python scripts/dev/run_server.py'
    Write-Host '==> Vite dev server: mở http://localhost:5173 (Ctrl+C để dừng; nhớ tắt cả cửa sổ backend)' -ForegroundColor Cyan
    npm --prefix frontend run dev
}
else {
    Invoke-Step 'Build frontend' { npm --prefix frontend run build }
    Write-Host '==> Chạy API + Web Dashboard: mở http://localhost:8000 (Ctrl+C để dừng)' -ForegroundColor Cyan
    python scripts/dev/run_server.py
}
