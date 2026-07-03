param(
  [Parameter(Position = 0)]
  [ValidateSet("init", "patch", "crawl-xhs", "crawl-weibo", "start-wechat", "crawl-wechat", "ocr-check", "build", "all")]
  [string]$Command = "build"
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (!(Test-Path $Python)) {
  throw "Missing .venv. Run .\setup.ps1 first."
}

function Run-Cli([string[]]$Args) {
  & $Python -m admission_case_crawler.cli @Args
}

switch ($Command) {
  "init" { Run-Cli @("init") }
  "patch" { Run-Cli @("patch") }
  "crawl-xhs" { Run-Cli @("crawl", "--platform", "xhs") }
  "crawl-weibo" { Run-Cli @("crawl", "--platform", "weibo") }
  "start-wechat" { Run-Cli @("start-wechat") }
  "crawl-wechat" { Run-Cli @("crawl", "--platform", "wechat") }
  "ocr-check" { Run-Cli @("ocr-check") }
  "build" { Run-Cli @("build") }
  "all" {
    Run-Cli @("patch")
    Run-Cli @("crawl", "--platform", "xhs")
    Run-Cli @("crawl", "--platform", "weibo")
    Write-Host "Open another PowerShell and run: .\run.ps1 start-wechat"
    Write-Host "Scan login in http://127.0.0.1:3000, then run: .\run.ps1 crawl-wechat"
    Write-Host "After WeChat crawl, run: .\run.ps1 build"
  }
}
