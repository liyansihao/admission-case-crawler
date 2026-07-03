param(
  [switch]$InstallOCR
)

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$ThirdParty = Join-Path $Root "third_party"
$MediaCrawler = Join-Path $ThirdParty "MediaCrawler"
$WechatExporter = Join-Path $ThirdParty "wechat-article-exporter"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

function Assert-Command($Name, $InstallHint) {
  if (!(Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Missing command: $Name. $InstallHint"
  }
}

function Remove-UnderThirdParty($Path) {
  $resolvedParent = [System.IO.Path]::GetFullPath($ThirdParty)
  $resolvedTarget = [System.IO.Path]::GetFullPath($Path)
  if (!$resolvedTarget.StartsWith($resolvedParent, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove path outside third_party: $resolvedTarget"
  }
  Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
}

Assert-Command git "Install Git first: https://git-scm.com/download/win"
Assert-Command python "Install Python 3.11+ first: https://www.python.org/downloads/"
Assert-Command node "Install Node.js 22+ first: https://nodejs.org/"

New-Item -ItemType Directory -Force -Path $ThirdParty | Out-Null

if ((Test-Path (Join-Path $Root ".git")) -and (Test-Path (Join-Path $Root ".gitmodules"))) {
  git -C $Root submodule update --init --recursive
}

if (!(Test-Path (Join-Path $MediaCrawler "main.py"))) {
  if (Test-Path $MediaCrawler) {
    Remove-UnderThirdParty $MediaCrawler
  }
  git clone https://github.com/NanmiCoder/MediaCrawler.git $MediaCrawler
}

if (!(Test-Path (Join-Path $WechatExporter "package.json"))) {
  if (Test-Path $WechatExporter) {
    Remove-UnderThirdParty $WechatExporter
  }
  git clone https://github.com/wechat-article/wechat-article-exporter.git $WechatExporter
}

python -m venv (Join-Path $Root ".venv")
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $Root "requirements.txt")

if ($InstallOCR) {
  $version = & $VenvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
  if ([version]$version -ge [version]"3.13") {
    throw "PaddleOCR currently requires Python 3.11 or 3.12 in this setup. Please install Python 3.11/3.12 and rerun setup.ps1 -InstallOCR."
  }
  & $VenvPython -m pip install ".[ocr]"
}

if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
  & $VenvPython -m pip install uv
  $env:Path = (Join-Path $env:USERPROFILE "AppData\Roaming\Python\Python311\Scripts") + ";" + $env:Path
}

Push-Location $MediaCrawler
try {
  uv sync
}
finally {
  Pop-Location
}

$CacheRoot = Join-Path $Root ".cache"
$env:YARN_CACHE_FOLDER = Join-Path $CacheRoot "yarn"
$env:TEMP = Join-Path $CacheRoot "tmp"
$env:TMP = $env:TEMP
$env:npm_config_cache = Join-Path $CacheRoot "npm"
$env:PUPPETEER_SKIP_DOWNLOAD = "true"
$env:PUPPETEER_SKIP_CHROMIUM_DOWNLOAD = "true"
New-Item -ItemType Directory -Force -Path $env:YARN_CACHE_FOLDER, $env:TEMP, $env:npm_config_cache | Out-Null

corepack yarn --version | Out-Null
Push-Location $WechatExporter
try {
  if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
  }
  corepack yarn install --frozen-lockfile --cache-folder $env:YARN_CACHE_FOLDER
}
finally {
  Pop-Location
}

& $VenvPython -m admission_case_crawler.cli init
& $VenvPython -m admission_case_crawler.cli patch

Write-Host ""
Write-Host "Setup complete."
if (!$InstallOCR) {
  Write-Host "OCR optional: run .\setup.ps1 -InstallOCR, then set ocr.enabled: true in config.yaml"
}
Write-Host "Run Xiaohongshu: .\run.ps1 crawl-xhs"
Write-Host "Run Weibo:      .\run.ps1 crawl-weibo"
Write-Host "Run WeChat:     .\run.ps1 start-wechat, scan login, then .\run.ps1 crawl-wechat"
Write-Host "Build Excel:    .\run.ps1 build"
