#!/usr/bin/env bash
# Installation sur un VPS Debian/Ubuntu (testé Ubuntu 22.04/24.04).
# Usage : sudo bash deploy/install.sh
set -euo pipefail

REPO_URL="https://github.com/anis66ben/blank-app.git"
BRANCH="claude/muslim-matchmaking-telegram-0onyu1"
APP_DIR="/opt/rencontre"
APP_USER="rencontre"

echo "== 1/6 Paquets système =="
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git

echo "== 2/6 Utilisateur dédié (sécurité : le bot ne tourne pas en root) =="
id -u "$APP_USER" &>/dev/null || useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"

echo "== 3/6 Code =="
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" fetch origin "$BRANCH"
    git -C "$APP_DIR" checkout "$BRANCH"
    git -C "$APP_DIR" pull origin "$BRANCH"
else
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

echo "== 4/6 Environnement Python =="
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "== 5/6 Configuration =="
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "WEBADMIN_HOST=0.0.0.0" >> "$APP_DIR/.env"
    echo ""
    echo ">>> IMPORTANT : éditez $APP_DIR/.env (nano $APP_DIR/.env) pour renseigner"
    echo ">>> TELEGRAM_BOT_TOKEN, ADMIN_PASSWORD et ADMIN_TELEGRAM_IDS, puis relancez :"
    echo ">>> systemctl restart rencontre-bot rencontre-webadmin"
fi
mkdir -p "$APP_DIR/data"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env"

echo "== 6/6 Services systemd (démarrage auto + redémarrage en cas de panne) =="
cp "$APP_DIR/deploy/rencontre-bot.service" /etc/systemd/system/
cp "$APP_DIR/deploy/rencontre-webadmin.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now rencontre-bot rencontre-webadmin

echo ""
echo "=================================================================="
echo " Installation terminée."
echo "  - Bot        : systemctl status rencontre-bot"
echo "  - Interface  : http://$(hostname -I | awk '{print $1}'):8000"
echo "  - Journaux   : journalctl -u rencontre-bot -f"
echo "  - Mise à jour: sudo bash $APP_DIR/deploy/update.sh"
echo "=================================================================="
