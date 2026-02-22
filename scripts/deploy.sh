#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

GCP_PROJECT="gen-lang-client-0306718397"

fetch_secret() {
  local secret_name="$1"
  local token
  token=$(curl -sf -H "Metadata-Flavor: Google" \
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

  curl -sf -H "Authorization: Bearer $token" \
    "https://secretmanager.googleapis.com/v1/projects/${GCP_PROJECT}/secrets/${secret_name}/versions/latest:access" \
    | python3 -c "import sys,json,base64; print(base64.b64decode(json.load(sys.stdin)['payload']['data']).decode(), end='')"
}

echo "==> Reading secrets from Secret Manager..."
GOOGLE_API_KEY=$(fetch_secret "watcher-prod-google-api-key") || {
  echo "ERROR: Could not read watcher-prod-google-api-key"
  if [ -f .env.production ]; then
    echo "==> Falling back to existing .env.production"
    GOOGLE_API_KEY=""
  else
    echo "FATAL: No .env.production and no Secret Manager access"
    exit 1
  fi
}

DB_PASSWORD=$(fetch_secret "watcher-prod-db-password") || {
  echo "WARNING: Could not read watcher-prod-db-password"
  DB_PASSWORD=""
}

if [ -n "$GOOGLE_API_KEY" ] && [ -n "$DB_PASSWORD" ]; then
  echo "==> Generating .env.production from secrets..."
  cat > .env.production << EOF
DB_PASSWORD=${DB_PASSWORD}
DATABASE_URL=postgresql+asyncpg://watcher:${DB_PASSWORD}@db:5432/watcher
SYNC_DATABASE_URL=postgresql://watcher:${DB_PASSWORD}@db:5432/watcher
GOOGLE_API_KEY=${GOOGLE_API_KEY}
LLM_PROVIDER=google
LLM_MODEL=gemini-2.0-flash
ENVIRONMENT=production
ALLOWED_ORIGINS=http://34.170.135.94,https://34.170.135.94
EOF
  echo "==> .env.production generated"
else
  echo "==> Keeping existing .env.production"
fi

echo "==> Stopping containers..."
sudo docker compose down --timeout 30

echo "==> Building and starting containers..."
sudo docker compose up --build -d

echo "==> Waiting for backend to be healthy..."
for i in $(seq 1 30); do
  if curl -sf http://localhost/api/v1/health > /dev/null 2>&1; then
    echo "==> Health check passed!"
    sudo docker compose ps
    exit 0
  fi
  sleep 2
done

echo "WARNING: Health check did not pass within 60 seconds"
sudo docker compose ps
sudo docker compose logs backend --tail 20
exit 1
