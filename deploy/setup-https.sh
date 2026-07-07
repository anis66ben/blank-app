#!/usr/bin/env bash
# Active le HTTPS pour l'interface admin via Caddy (certificat Let's Encrypt
# automatique). Sans domaine : utilise <IP-avec-tirets>.sslip.io.
#
# Usage : sudo bash deploy/setup-https.sh              -> https://168-231-83-29.sslip.io
#         sudo bash deploy/setup-https.sh mondomaine.fr -> https://mondomaine.fr
set -euo pipefail

APP_DIR="/opt/rencontre"
IP=$(hostname -I | awk '{print $1}')
DOMAIN="${1:-${IP//./-}.sslip.io}"
PORT=$(grep -oP '^WEBADMIN_PORT=\K\d+' "$APP_DIR/.env" 2>/dev/null || echo 8000)

echo "== Domaine : $DOMAIN — interface locale sur le port $PORT =="

# 1. L'interface n'écoute plus que sur localhost : seul Caddy (HTTPS) y accède.
if grep -q '^WEBADMIN_HOST=' "$APP_DIR/.env"; then
    sed -i 's/^WEBADMIN_HOST=.*/WEBADMIN_HOST=127.0.0.1/' "$APP_DIR/.env"
else
    echo "WEBADMIN_HOST=127.0.0.1" >> "$APP_DIR/.env"
fi
systemctl restart rencontre-webadmin

# 2. Installation de Caddy si absent (dépôt officiel).
if ! command -v caddy >/dev/null 2>&1; then
    # Vérifie que les ports 80/443 sont libres (un autre serveur web ferait conflit)
    if ss -tln | grep -qE '(:80|:443)\s'; then
        echo "ERREUR : les ports 80 et/ou 443 sont déjà utilisés par un autre service :"
        ss -tlnp | grep -E '(:80|:443)\s' || true
        echo "Dites-le à votre assistant : on branchera l'interface sur le serveur web existant."
        exit 1
    fi
    echo "== Installation de Caddy =="
    apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https curl gnupg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
        | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
        > /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq
    apt-get install -y -qq caddy
fi

# 3. Ajoute notre site au Caddyfile (sans toucher aux éventuels autres sites).
if ! grep -q "$DOMAIN" /etc/caddy/Caddyfile 2>/dev/null; then
    cat >> /etc/caddy/Caddyfile <<EOF

# --- Interface admin plateforme de rencontre ---
$DOMAIN {
    reverse_proxy 127.0.0.1:$PORT
}
EOF
fi

systemctl enable caddy >/dev/null 2>&1 || true
systemctl reload caddy 2>/dev/null || systemctl restart caddy

echo ""
echo "=================================================================="
echo " HTTPS actif. Interface admin (smartphone) :"
echo "   https://$DOMAIN"
echo " Le certificat Let's Encrypt se génère au premier accès (~10 s)."
echo " L'ancien accès http://IP:$PORT est désormais fermé (localhost only)."
echo "=================================================================="
