# Host-local Watcher backend (no Docker).
# SQLite + Ollama + local embeddings. Neo4j stays optional (NEO4J_URI unset).

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Warning "Ollama not in PATH. LocalPro will fall back to FreeProvider."
}

Set-Location (Join-Path $Root "watcher-backend")
Write-Host "Syncing backend extras (dev + local GPU)..."
uv sync --extra dev --extra local

Write-Host "Starting API on http://127.0.0.1:8001  (Ctrl+C to stop)"
uv run uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8001
