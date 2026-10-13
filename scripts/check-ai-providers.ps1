# Check Watcher AI providers (config + live ping).
# Usage: from repo root  .\scripts\check-ai-providers.ps1
#        .\scripts\check-ai-providers.ps1 -NoPing
#        .\scripts\check-ai-providers.ps1 -Json

param(
    [switch]$NoPing,
    [switch]$Json,
    [double]$Timeout = 30
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "watcher-backend"
$Script = Join-Path $PSScriptRoot "check-ai-providers.py"

$argsList = @($Script)
if ($NoPing) { $argsList += "--no-ping" }
if ($Json) { $argsList += "--json" }
$argsList += @("--timeout", "$Timeout")

Push-Location $Backend
try {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        & uv run python @argsList
        exit $LASTEXITCODE
    }
    if (Test-Path ".\.venv\Scripts\python.exe") {
        & ".\.venv\Scripts\python.exe" @argsList
        exit $LASTEXITCODE
    }
    & python @argsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
