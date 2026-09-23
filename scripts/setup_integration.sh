#!/usr/bin/env bash
# Configura la cuenta de integración, el perfil mínimo y el cliente OAuth dentro del contenedor GLPI,
# y guarda los secretos en .env (nunca los imprime). Idempotente.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "falta .env (copia .env.example)"; exit 1; }
set -a; . ./.env; set +a
: "${GLPI_INTEGRATION_USER:?}" "${GLPI_INTEGRATION_PASSWORD:?}"
docker compose cp scripts/glpi_admin_setup.php glpi:/tmp/glpi_admin_setup.php >/dev/null
tech=$(python3 -c 'import json; print(next(u["username"] for u in json.load(open("data/seed.json"))["users"] if u.get("kind")=="technician"))')
json=$(docker compose exec -T glpi php /tmp/glpi_admin_setup.php "$GLPI_INTEGRATION_USER" "$GLPI_INTEGRATION_PASSWORD" "$tech")
cid=$(printf '%s' "$json" | python3 -c 'import sys,json; print(json.load(sys.stdin)["oauth"]["client_id"])')
csec=$(printf '%s' "$json" | python3 -c 'import sys,json; print(json.load(sys.stdin)["oauth"]["client_secret"])')
utok=$(printf '%s' "$json" | python3 -c 'import sys,json; print(json.load(sys.stdin)["user"]["api_token"])')
steps=$(printf '%s' "$json" | python3 -c 'import sys,json; print(",".join(json.load(sys.stdin)["steps"]))')
setvar() { local k="$1" v="$2"; if grep -q "^$k=" .env; then sed -i.bak -E "s#^$k=.*#$k=$v#" .env && rm -f .env.bak; else echo "$k=$v" >> .env; fi; }
setvar GLPI_OAUTH_CLIENT_ID "$cid"
setvar GLPI_OAUTH_CLIENT_SECRET "$csec"
setvar GLPI_LEGACY_USER_TOKEN "$utok"
chmod 600 .env
echo "setup OK. pasos: $steps. Secretos guardados en .env (no mostrados)."
