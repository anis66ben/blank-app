#!/usr/bin/env bash
# ============================================================
# Concierge Flow — Script de déploiement VPS
# Usage : ./deploy.sh [port] [domaine]
# Exemples :
#   ./deploy.sh                     → port 3001, pas de domaine
#   ./deploy.sh 3001 flow.monsite.com
# ============================================================
set -euo pipefail

VPS="root@168.231.83.29"
APP_NAME="concierge-flow"
REPO="https://github.com/anis66ben/blank-app.git"
BRANCH="claude/app-github-deployment-awkmz7"
APP_DIR="/var/www/concierge-flow"
PORT="${1:-3001}"
DOMAIN="${2:-}"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   Concierge Flow — Déploiement VPS           ║"
echo "║   VPS  : $VPS                   ║"
echo "║   Port : $PORT                               ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ─── 1. Audit rapide du VPS ───────────────────────────────────
echo "▶ Audit du VPS…"
ssh "$VPS" bash <<'REMOTE'
echo "OS      : $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"')"
echo "Node    : $(node --version 2>/dev/null || echo 'absent')"
echo "npm     : $(npm --version 2>/dev/null || echo 'absent')"
echo "PM2     : $(pm2 --version 2>/dev/null || echo 'absent')"
echo "Nginx   : $(nginx -v 2>&1 | head -1 || echo 'absent')"
echo "Ports   : $(ss -tlnp | awk '/LISTEN/{print $4}' | paste -sd' ')"
REMOTE

# ─── 2. Installation Node.js 22 LTS si absent ─────────────────
echo ""
echo "▶ Vérification / Installation Node.js 22 LTS…"
ssh "$VPS" bash <<'REMOTE'
if ! command -v node &>/dev/null || [[ $(node --version | cut -d. -f1 | tr -d 'v') -lt 20 ]]; then
  echo "  → Installation Node.js 22 via NodeSource…"
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
  echo "  ✓ Node $(node --version) installé"
else
  echo "  ✓ Node $(node --version) déjà présent"
fi
REMOTE

# ─── 3. Installation PM2 si absent ────────────────────────────
echo ""
echo "▶ Vérification / Installation PM2…"
ssh "$VPS" bash <<'REMOTE'
if ! command -v pm2 &>/dev/null; then
  npm install -g pm2
  pm2 startup systemd -u root --hp /root | tail -1 | bash
  echo "  ✓ PM2 installé et configuré au démarrage"
else
  echo "  ✓ PM2 déjà présent"
fi
REMOTE

# ─── 4. Clone / Pull du dépôt ────────────────────────────────
APP_PORT="$PORT"
echo ""
echo "▶ Déploiement du code…"
ssh "$VPS" bash -s -- "$APP_DIR" "$REPO" "$BRANCH" <<'REMOTE'
APP_DIR="$1"; REPO="$2"; BRANCH="$3"
if [ -d "$APP_DIR/.git" ]; then
  echo "  → Mise à jour du dépôt existant"
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  echo "  → Clonage du dépôt"
  mkdir -p "$(dirname "$APP_DIR")"
  git clone --branch "$BRANCH" --depth 1 "$REPO" "$APP_DIR"
fi
echo "  ✓ Code à jour"
REMOTE

# ─── 5. Installation des dépendances & build ──────────────────
echo ""
echo "▶ npm install + next build (peut prendre 1-2 min)…"
ssh "$VPS" bash -s -- "$APP_DIR" <<'REMOTE'
APP_DIR="$1"
cd "$APP_DIR"
npm ci --no-audit --no-fund
npm run build
echo "  ✓ Build terminé"
REMOTE

# ─── 6. (Re)démarrage PM2 ─────────────────────────────────────
echo ""
echo "▶ Démarrage de l'application via PM2 (port $APP_PORT)…"
ssh "$VPS" bash -s -- "$APP_DIR" "$APP_NAME" "$APP_PORT" <<'REMOTE'
APP_DIR="$1"; APP_NAME="$2"; PORT="$3"
cd "$APP_DIR"

# Arrêter l'instance précédente si elle existe
pm2 delete "$APP_NAME" 2>/dev/null || true

# Démarrer avec l'environnement de production
PORT="$PORT" pm2 start npm \
  --name "$APP_NAME" \
  --cwd "$APP_DIR" \
  -- start

pm2 save
echo "  ✓ Application démarrée sur le port $PORT"
pm2 show "$APP_NAME" | grep -E "status|port|uptime|memory" || true
REMOTE

# ─── 7. Configuration Nginx ──────────────────────────────────
echo ""
echo "▶ Configuration Nginx…"
ssh "$VPS" bash -s -- "$APP_NAME" "$APP_PORT" "$DOMAIN" <<'REMOTE'
APP_NAME="$1"; PORT="$2"; DOMAIN="$3"

if ! command -v nginx &>/dev/null; then
  echo "  → Installation Nginx…"
  apt-get install -y nginx
fi

# Détecter config dir
if [ -d /etc/nginx/sites-available ]; then
  CONF_DIR="/etc/nginx/sites-available"
  ENABLED_DIR="/etc/nginx/sites-enabled"
else
  CONF_DIR="/etc/nginx/conf.d"
  ENABLED_DIR="$CONF_DIR"
fi

CONF_FILE="$CONF_DIR/$APP_NAME.conf"

# Nom de serveur : domaine ou IP publique
if [ -n "$DOMAIN" ]; then
  SERVER_NAME="$DOMAIN www.$DOMAIN"
else
  SERVER_NAME="$(curl -s ifconfig.me || hostname -I | awk '{print $1}')";
fi

cat > "$CONF_FILE" <<NGINX
# Concierge Flow — généré automatiquement
server {
    listen 80;
    server_name $SERVER_NAME;

    # Logs dédiés
    access_log /var/log/nginx/${APP_NAME}_access.log;
    error_log  /var/log/nginx/${APP_NAME}_error.log;

    # Proxy vers Next.js
    location / {
        proxy_pass         http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade \$http_upgrade;
        proxy_set_header   Connection 'upgrade';
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # Fichiers statiques Next.js (_next/static) servis directement
    location /_next/static {
        alias /var/www/${APP_NAME}/.next/static;
        expires 365d;
        add_header Cache-Control "public, immutable";
    }
}
NGINX

# Activer le site (Debian/Ubuntu)
if [ -d /etc/nginx/sites-enabled ] && [ ! -L "$ENABLED_DIR/$APP_NAME.conf" ]; then
  ln -sf "$CONF_FILE" "$ENABLED_DIR/$APP_NAME.conf"
fi

# Tester et recharger
nginx -t && systemctl reload nginx
echo "  ✓ Nginx configuré → $SERVER_NAME"
REMOTE

# ─── 8. Test final ────────────────────────────────────────────
echo ""
echo "▶ Test HTTP…"
sleep 3
PUBLIC_IP=$(ssh "$VPS" "curl -s ifconfig.me || hostname -I | awk '{print \$1}'" 2>/dev/null)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://$PUBLIC_IP/" 2>/dev/null || echo "timeout")
echo "  HTTP $HTTP_CODE — http://$PUBLIC_IP/"
[ -n "$DOMAIN" ] && echo "  Domaine → http://$DOMAIN/"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   ✅ Déploiement terminé !                               ║"
echo "║                                                          ║"
echo "║   URL    : http://$PUBLIC_IP/                            ║"
[ -n "$DOMAIN" ] && echo "║   Domaine : http://$DOMAIN/                              ║"
echo "║   Port   : $PORT (interne)                              ║"
echo "║                                                          ║"
echo "║   Commandes utiles :                                     ║"
echo "║   pm2 logs $APP_NAME                                     ║"
echo "║   pm2 restart $APP_NAME                                  ║"
echo "║   pm2 monit                                              ║"
echo "╚══════════════════════════════════════════════════════════╝"
