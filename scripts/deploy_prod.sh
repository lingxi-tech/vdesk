#!/usr/bin/env bash
set -euo pipefail

# Production deployment script for vdesk
# Usage: sudo ./scripts/deploy_prod.sh

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_DIR="/opt/vdesk"
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_FILE="/etc/systemd/system/vdesk-backend.service"
NGINX_SITE="/etc/nginx/sites-available/vdesk"
NGINX_LINK="/etc/nginx/sites-enabled/vdesk"

echo "Deploying vdesk from $REPO_DIR to $INSTALL_DIR"

if [ "$EUID" -ne 0 ]; then
  echo "This script must be run as root (use sudo)"
  exit 1
fi

# Install required packages (Debian/Ubuntu)
apt update
apt install -y python3 python3-venv python3-pip curl ca-certificates nginx rsync

# Copy repo to installation directory
mkdir -p "$INSTALL_DIR"
rsync -a --delete "$REPO_DIR/" "$INSTALL_DIR/"

# Create Python virtualenv and install backend requirements
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
if [ -f "$INSTALL_DIR/web/backend/requirements.txt" ]; then
  pip install -r "$INSTALL_DIR/web/backend/requirements.txt"
else
  echo "Warning: backend requirements.txt not found: $INSTALL_DIR/web/backend/requirements.txt"
fi
deactivate

# Install nvm and Node.js LTS for this user (script runs as root; installs into root's home)
echo "Installing nvm and Node.js LTS..."
export NVM_DIR="$HOME/.nvm"
if [ ! -d "$NVM_DIR" ]; then
  # install nvm (pinned version v0.39.6); use local copy if available, otherwise download
  if [ -f "$REPO_DIR/scripts/nvm-install.sh" ]; then
    echo "Using local nvm install script (v0.39.6)"
    bash "$REPO_DIR/scripts/nvm-install.sh"
  else
    echo "Downloading nvm install script from official repo (v0.39.6)"
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.6/install.sh | bash
  fi
fi
# load nvm
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
else
  echo "nvm install failed or nvm.sh not found at $NVM_DIR/nvm.sh"
fi

# install and use Node.js LTS so npm is available for frontend build
if command -v nvm >/dev/null 2>&1; then
  nvm install --lts
  nvm alias default 'lts/*' || true
else
  echo "nvm not available; frontend build may fail"
fi

# Build frontend production assets
if [ -d "$INSTALL_DIR/web/frontend" ]; then
  cd "$INSTALL_DIR/web/frontend"
  if command -v npm >/dev/null 2>&1; then
    npm ci --silent
    npm run build --silent
  else
    echo "npm not found; please install Node.js/npm before running this script"
    exit 1
  fi
else
  echo "frontend folder not found: $INSTALL_DIR/web/frontend"
fi

# Create systemd service for the backend
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=vdesk backend service
After=network.target

[Service]
User=root
WorkingDirectory=$INSTALL_DIR/web/backend
Environment=PYTHONPATH=$INSTALL_DIR/web/backend
ExecStart=$VENV_DIR/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# comment the following lines for using in dockerfile
# systemctl daemon-reload
# systemctl enable vdesk-backend
# systemctl restart vdesk-backend || systemctl start vdesk-backend || true

# Nginx configuration to serve frontend and proxy /api to backend
cat > "$NGINX_SITE" <<'EOF'
server {
    listen 80;
    server_name _;

    root REPLACE_ROOT_DIST;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        # Proxy to backend (supports WebSocket upgrades)
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_buffering off;
    }
}
EOF

# Point nginx to the built frontend dist folder
DIST_DIR="$INSTALL_DIR/web/frontend/dist"
if [ ! -d "$DIST_DIR" ]; then
  echo "Warning: frontend dist directory not found: $DIST_DIR"
  # still continue, nginx will fail config test if missing
fi
sed -i "s|REPLACE_ROOT_DIST|$DIST_DIR|g" "$NGINX_SITE"
ln -sf "$NGINX_SITE" "$NGINX_LINK"

# Test and reload nginx
nginx -t
# comment the following lines for using in dockerfile
# systemctl restart nginx

echo "Deployment finished."
echo "Frontend: http://<server-host>/"
echo "Backend API proxied at: http://<server-host>/api/ (backend listens on 127.0.0.1:8000)"

exit 0
