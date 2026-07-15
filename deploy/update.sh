#!/usr/bin/env bash
# Met à jour le code et redémarre les services.  Usage : sudo bash deploy/update.sh
set -euo pipefail
APP_DIR="/opt/rencontre"
BRANCH="claude/muslim-matchmaking-telegram-0onyu1"

git -C "$APP_DIR" fetch origin "$BRANCH"
git -C "$APP_DIR" reset --hard "origin/$BRANCH"
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
chown -R rencontre:rencontre "$APP_DIR"
systemctl restart rencontre-bot rencontre-webadmin
echo "Mise à jour terminée."
systemctl --no-pager status rencontre-bot rencontre-webadmin | grep -E "●|Active:"
