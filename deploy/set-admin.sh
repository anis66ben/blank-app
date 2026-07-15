#!/usr/bin/env bash
# Déclare le ou les administrateurs Telegram sans éditeur de texte.
# Usage : bash deploy/set-admin.sh 123456789        (plusieurs : "111,222")
set -euo pipefail
ID="${1:?Usage : bash deploy/set-admin.sh VOTRE_ID_TELEGRAM (obtenu via /monid)}"
sed -i "s|^ADMIN_TELEGRAM_IDS=.*|ADMIN_TELEGRAM_IDS=$ID|" /opt/rencontre/.env
systemctl restart rencontre-bot
echo "✅ Admin(s) déclaré(s) : $ID — essayez /admin dans Telegram."
