#!/usr/bin/env bash
# Installation complète en UNE commande — pensée pour être lancée depuis un
# smartphone (terminal navigateur Hostinger ou appli SSH), sans éditeur.
#
#   curl -fsSL https://raw.githubusercontent.com/anis66ben/blank-app/claude/muslim-matchmaking-telegram-0onyu1/deploy/bootstrap.sh \
#     | bash -s -- "JETON_TELEGRAM" "MOT_DE_PASSE_ADMIN" [ID_TELEGRAM_ADMIN]
#
# Fait tout : installation isolée, secrets, services systemd, HTTPS.
set -euo pipefail

TOKEN="${1:?Usage : bash -s -- \"JETON_TELEGRAM\" \"MOT_DE_PASSE_ADMIN\" [ID_ADMIN]}"
PASSWORD="${2:?Mot de passe admin manquant (2e argument)}"
ADMIN_ID="${3:-}"

BRANCH="claude/muslim-matchmaking-telegram-0onyu1"
APP_DIR="/opt/rencontre"

echo "== Préparation =="
apt-get update -qq
apt-get install -y -qq git curl

if [ ! -d "$APP_DIR/.git" ]; then
    git clone -b "$BRANCH" https://github.com/anis66ben/blank-app.git "$APP_DIR"
fi

bash "$APP_DIR/deploy/install.sh"

echo "== Secrets =="
sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$TOKEN|" "$APP_DIR/.env"
sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$PASSWORD|" "$APP_DIR/.env"
if [ -n "$ADMIN_ID" ]; then
    sed -i "s|^ADMIN_TELEGRAM_IDS=.*|ADMIN_TELEGRAM_IDS=$ADMIN_ID|" "$APP_DIR/.env"
fi
chmod 600 "$APP_DIR/.env"
systemctl restart rencontre-bot rencontre-webadmin

echo "== HTTPS =="
bash "$APP_DIR/deploy/setup-https.sh"

IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=================================================================="
echo " ✅ TOUT EST INSTALLÉ"
echo "  Interface smartphone : https://${IP//./-}.sslip.io"
echo "  Bot Telegram        : envoyez /start à votre bot"
echo "  Déclarer votre ID admin plus tard (après /monid) :"
echo "    bash $APP_DIR/deploy/set-admin.sh VOTRE_ID"
echo "=================================================================="
