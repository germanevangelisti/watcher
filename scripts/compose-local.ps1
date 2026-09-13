# Postgres + Neo4j with workstation memory (cooperledge).
# Windows equivalent of `make compose-local`.
# Requires Docker Desktop: winget install -e --id Docker.DockerDesktop

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    $hint = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin\docker.exe"
    if (Test-Path $hint) { $env:Path = "$(Split-Path $hint);$env:Path"; $docker = Get-Command docker -ErrorAction SilentlyContinue }
}
if (-not $docker) {
    Write-Error @"
Docker CLI is not in PATH. Docker Desktop is installed under %LOCALAPPDATA%\Programs\DockerDesktop
but it cannot start without WSL2 (this machine reports: hypervisor present, WSL not installed).

Fix Docker (elevated PowerShell, then reboot):
  .\scripts\enable-wsl.ps1

Until then, run the pipeline on the host without Postgres/Neo4j:
  .\scripts\start-backend-local.ps1
"@
}

Write-Host "Starting Postgres + Neo4j with workstation memory (cooperledge)..."
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d db neo4j
docker compose -f docker-compose.yml -f docker-compose.local.yml ps db neo4j
