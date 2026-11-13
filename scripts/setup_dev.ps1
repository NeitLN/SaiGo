# Dựng môi trường phát triển SaiGo trên Windows bằng một lệnh.
#
#   powershell -ExecutionPolicy Bypass -File scripts\setup_dev.ps1          # app + test
#   powershell -ExecutionPolicy Bypass -File scripts\setup_dev.ps1 -Data    # thêm OSMnx (Minh, T02/T30)
#
# Chạy ở thư mục gốc của repo. Chạy lại nhiều lần không sao.

param([switch]$Data)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host "LỖI: $msg" -ForegroundColor Red; exit 1 }

Step "Kiểm tra công cụ"
foreach ($cmd in "git", "python", "node", "npm") {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Fail "chưa cài '$cmd' (xem docs/team/ONBOARDING.md mục 1)" }
}
$py = (python -c "import sys; print('%d.%d' % sys.version_info[:2])")
if ([version]$py -lt [version]"3.11") { Fail "cần Python 3.11 trở lên, máy đang có $py" }
if ($py -ne "3.11") {
    Write-Host "CHÚ Ý: nhóm và CI dùng Python 3.11; máy đang có $py nên vài thư viện có thể khác phiên bản đã khóa. Số liệu benchmark phải chạy trên 3.11." -ForegroundColor Yellow
}
$node = (node -p "process.versions.node.split('.')[0]")
if ([int]$node -lt 20) { Fail "cần Node.js 20 trở lên, máy đang có $node" }
Write-Host "Python $py, Node $node, $(git --version)"

Step "Kiểm tra tên/email git (commit phải mang tên của chính bạn)"
$name = git config user.name
$email = git config user.email
if (-not $name -or -not $email) {
    Fail "chưa đặt tên/email git. Chạy: git config --global user.name ""Họ Tên""; git config --global user.email ""email-dang-ky-GitHub"""
}
Write-Host "Commit sẽ mang tên: $name <$email>"

if ((Get-Location).Path -match '[^\x00-\x7F]') {
    Write-Host "CHÚ Ý: đường dẫn repo có ký tự có dấu. Script vẫn chạy, nhưng một số công cụ (pip install -e, thư viện địa lý) dễ lỗi; nên clone vào thư mục không dấu, ví dụ C:\dev\SaiGo." -ForegroundColor Yellow
}

Step "Môi trường Python (.venv)"
if (-not (Test-Path .venv\Scripts\python.exe)) { python -m venv .venv }
$vpy = ".venv\Scripts\python.exe"
& $vpy -m pip install --quiet --upgrade pip setuptools
# Chỉ cài thư viện phụ thuộc trong pyproject.toml, không cài chính package:
# pytest (pythonpath = backend) và uvicorn (--app-dir backend) tự tìm code, và cách này không lỗi với đường dẫn có dấu.
# Phiên bản theo requirements-lock.txt (constraints) để mọi máy và CI dùng cùng thư viện.
$groups = if ($Data) { "dev,bench,data" } else { "dev,bench" }
$deps = & $vpy -c "import sys, tomllib; p = tomllib.load(open('pyproject.toml', 'rb'))['project']; print('\n'.join(p['dependencies'] + [d for g in sys.argv[1].split(',') for d in p['optional-dependencies'][g]]))" $groups
$lock = if ($py -eq "3.11") { @("-c", "requirements-lock.txt") } else { @() }
Write-Host "Đang tải và cài thư viện Python. Lần đầu có thể mất 5–15 phút và không in gì trong lúc chạy; đừng tắt cửa sổ."
& $vpy -m pip install --quiet @($deps) @lock
if ($LASTEXITCODE -ne 0) { Fail "pip install thất bại" }

Step "Chạy test backend"
& $vpy -m pytest -q
if ($LASTEXITCODE -ne 0) { Fail "pytest thất bại" }

Step "Frontend (npm ci + build)"
Push-Location frontend
npm ci --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { Pop-Location; Fail "npm ci thất bại" }
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; Fail "npm run build thất bại" }
Pop-Location

if ($Data) {
    Step "Kiểm tra OSMnx"
    & $vpy -c "import osmnx, networkx; print('osmnx', osmnx.__version__, '| networkx', networkx.__version__)"
    if ($LASTEXITCODE -ne 0) { Fail "không import được osmnx; thử môi trường conda-forge (docs/team/start/MINH.md)" }
}

Step "Xong"
Write-Host "Kích hoạt môi trường:   .venv\Scripts\Activate.ps1"
Write-Host "Chạy backend:           uvicorn app.main:app --reload --app-dir backend"
Write-Host "Chạy frontend:          cd frontend; npm run dev   (mở http://localhost:5173)"
