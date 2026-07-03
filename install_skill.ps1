$ErrorActionPreference = "Stop"

$Source = Join-Path $PSScriptRoot "skills\admission-case-collector"
$TargetRoot = Join-Path $HOME ".codex\skills"
$Target = Join-Path $TargetRoot "admission-case-collector"

if (!(Test-Path $Source)) {
  throw "Missing skill source: $Source"
}

New-Item -ItemType Directory -Force -Path $TargetRoot | Out-Null
if (Test-Path $Target) {
  Remove-Item -LiteralPath $Target -Recurse -Force
}
Copy-Item -LiteralPath $Source -Destination $Target -Recurse
Write-Host "Installed skill to $Target"
