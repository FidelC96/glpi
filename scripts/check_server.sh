#!/usr/bin/env bash
# Inventario de SOLO LECTURA del servidor antes de desplegar la demo GLPI.
# No modifica nada: reporta contenedores y puertos publicados, sockets en escucha del host,
# nginx, firewall, subredes Docker y si el puerto elegido para GLPI está libre.
# Uso: ./scripts/check_server.sh [puerto_glpi]   (por defecto 8090)
set -u
PORT="${1:-${GLPI_PORT:-8090}}"
ok()   { printf '  \033[32mOK\033[0m   %s\n' "$*"; }
warn() { printf '  \033[33mAVISO\033[0m %s\n' "$*"; }
bad()  { printf '  \033[31mRIESGO\033[0m %s\n' "$*"; }
hr()   { printf '\n== %s ==\n' "$*"; }

hr "Sistema"
echo "  host: $(hostname)  |  $(uname -sr)  |  usuario: $(id -un)"
if command -v docker >/dev/null 2>&1; then
  echo "  docker: $(docker version --format '{{.Server.Version}}' 2>/dev/null || echo 'sin acceso al daemon')  |  compose: $(docker compose version --short 2>/dev/null || echo 'no disponible')"
else
  bad "docker no está instalado o no está en PATH"; exit 1
fi
command -v python3 >/dev/null 2>&1 && ok "python3 $(python3 -V 2>&1 | cut -d' ' -f2) disponible (necesario para seed/verify)" || warn "python3 no disponible: los scripts seed/verify no podrán correr en este host"

hr "Contenedores y puertos publicados (todos los proyectos)"
printf '  %-32s %-12s %s\n' "CONTENEDOR" "ESTADO" "PUERTOS PUBLICADOS (host -> contenedor)"
exposed_public=0
while IFS='|' read -r name state ports; do
  printf '  %-32s %-12s %s\n' "$name" "$state" "${ports:-(ninguno)}"
  case "$ports" in
    *0.0.0.0:*|*\[::\]:*|*:::*) exposed_public=$((exposed_public+1));;
  esac
done < <(docker ps -a --format '{{.Names}}|{{.State}}|{{.Ports}}')
if [ "$exposed_public" -gt 0 ]; then
  bad "$exposed_public contenedor(es) publican puertos en 0.0.0.0 / [::] (alcanzables desde fuera; Docker se salta ufw en esos puertos)"
else
  ok "ningún contenedor publica puertos en todas las interfaces"
fi

hr "Puerto elegido para GLPI: $PORT"
if docker ps --format '{{.Names}} {{.Ports}}' | grep -v '^glpi_gspn_' | grep -qE "[:.]${PORT}->"; then
  bad "el puerto $PORT ya lo publica un contenedor; usa otro GLPI_PORT"
elif (command -v ss >/dev/null && ss -tln 2>/dev/null | grep -qE "[:.]${PORT}\s") || (command -v lsof >/dev/null && lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1); then
  bad "el puerto $PORT está en escucha en el host; usa otro GLPI_PORT"
else
  ok "puerto $PORT libre"
fi
for p in 8069 8072 5432 3306 80 443; do
  if docker ps --format '{{.Ports}}' | grep -qE "[:.]${p}->" ; then echo "  info: $p publicado por un contenedor"; fi
done

hr "Sockets en escucha del host (quién escucha en qué IP)"
if command -v ss >/dev/null 2>&1; then
  ss -tlnp 2>/dev/null | awk 'NR>1{printf "  %-28s %s\n",$4,$6}' | sort -u
  if ss -tln 2>/dev/null | awk 'NR>1{print $4}' | grep -qE '^(0\.0\.0\.0|\*|\[::\]):(3306|5432|8069|8090)$'; then
    bad "hay bases de datos o apps escuchando en todas las interfaces (3306/5432/8069/8090)"
  fi
elif command -v lsof >/dev/null 2>&1; then
  lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | awk 'NR>1{printf "  %-28s %s\n",$9,$1}' | sort -u
else
  warn "ni ss ni lsof disponibles"
fi

hr "nginx"
if command -v nginx >/dev/null 2>&1; then
  ok "nginx instalado en el host: $(nginx -v 2>&1)"
  echo "  server_name definidos:"; grep -rhoE 'server_name[^;]+;' /etc/nginx/ 2>/dev/null | sort -u | sed 's/^/    /' || true
  echo "  listen definidos:";      grep -rhoE 'listen[^;]+;'      /etc/nginx/ 2>/dev/null | sort -u | sed 's/^/    /' || true
elif docker ps --format '{{.Names}} {{.Image}}' | grep -qiE 'nginx|traefik|caddy'; then
  warn "hay un proxy como contenedor: $(docker ps --format '{{.Names}} ({{.Image}})' | grep -iE 'nginx|traefik|caddy' | tr '\n' ' ') -> GLPI deberá colgarse de ese proxy, no levantar otro en 443"
else
  warn "no se detecta nginx ni otro proxy; habrá que instalarlo o añadirlo al compose"
fi

hr "Firewall"
if command -v ufw >/dev/null 2>&1; then
  st=$(sudo -n ufw status 2>/dev/null || ufw status 2>/dev/null || echo "sin permiso para leer ufw")
  echo "$st" | sed 's/^/  /' | head -25
  echo "$st" | grep -q "Status: active" && ok "ufw activo (recuerda: no protege puertos publicados por Docker)" || warn "ufw inactivo o no legible"
elif command -v firewall-cmd >/dev/null 2>&1; then
  firewall-cmd --list-all 2>/dev/null | sed 's/^/  /' | head -20
else
  warn "sin ufw/firewalld detectado"
fi
if command -v iptables >/dev/null 2>&1; then
  n=$(sudo -n iptables -S DOCKER-USER 2>/dev/null | grep -vc '^-P\|^-N' || echo 0)
  echo "  reglas en cadena DOCKER-USER: ${n:-0} (0 = Docker acepta todo hacia los puertos que publica)"
fi

hr "Redes Docker (subredes; evitar solape con la VPN)"
for net in $(docker network ls --format '{{.Name}}'); do
  sub=$(docker network inspect "$net" --format '{{range .IPAM.Config}}{{.Subnet}} {{end}}' 2>/dev/null)
  printf '  %-36s %s\n' "$net" "${sub:-(sin subred)}"
done

hr "Recursos"
if command -v free >/dev/null 2>&1; then free -h | sed 's/^/  /'; fi
df -h / 2>/dev/null | sed 's/^/  /'
docker system df 2>/dev/null | sed 's/^/  /'

hr "Resumen"
echo "  La demo GLPI publicará SOLO 127.0.0.1:$PORT (la base de datos no publica puertos)."
echo "  Lo que aparece arriba como RIESGO existe hoy, sin GLPI; decidir aparte si se corrige."
