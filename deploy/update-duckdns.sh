#!/usr/bin/env bash
# Met à jour l'IP du domaine DuckDNS lecture-facture.duckdns.org
# Utilise DUCKDNS_TOKEN et PUBLIC_HOST depuis le fichier .env à la racine du projet.
# Usage : depuis la racine du projet : ./deploy/update-duckdns.sh

set -e
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Fichier .env absent. Créez-le avec PUBLIC_HOST=lecture-facture.duckdns.org et DUCKDNS_TOKEN=votre_token"
  exit 1
fi

source .env 2>/dev/null || true
DOMAIN="${PUBLIC_HOST:-lecture-facture.duckdns.org}"
# Sous-domaine DuckDNS (sans .duckdns.org)
SUB="${DOMAIN%%.duckdns.org}"
TOKEN="${DUCKDNS_TOKEN:-}"

if [ -z "$TOKEN" ]; then
  echo "DUCKDNS_TOKEN non défini dans .env. Ajoutez: DUCKDNS_TOKEN=votre_token_duckdns"
  exit 1
fi

# Récupérer l'IP publique (celle du serveur qui exécute ce script)
IP=$(curl -s -4 --max-time 5 "https://api.ipify.org" 2>/dev/null || echo "")
if [ -z "$IP" ]; then
  echo "Impossible de récupérer l'IP publique."
  exit 1
fi

URL="https://www.duckdns.org/update?domains=${SUB}&token=${TOKEN}&ip=${IP}"
RESPONSE=$(curl -s -4 --max-time 10 "$URL" 2>/dev/null || echo "error")

if echo "$RESPONSE" | grep -q "OK"; then
  echo "DuckDNS mis à jour: $DOMAIN -> $IP"
else
  echo "Erreur DuckDNS: $RESPONSE"
  exit 1
fi
