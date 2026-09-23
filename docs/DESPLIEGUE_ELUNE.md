# Despliegue en elune: de `git clone` a https://glpi-demo.rapi.tech

Requisitos ya presentes en elune: Docker con Compose v2 (mínimo 2.24 por el `!reset` del override),
python3, nginx como contenedor en la red `odoo-network`, certbot con webroot en `/home/debian/nginx/certbot/www`.
Todo se ejecuta como `root` en `/home/debian`.

## 0. DNS (en Cloudflare)

Registro **A** `glpi-demo` → IP pública de elune, modo **DNS only** (nube gris) para que nginx
vea la IP real del visitante y funcione la lista `allow/deny`. Comprobar desde cualquier equipo:

```bash
dig +short glpi-demo.rapi.tech      # debe devolver la IP de elune, no una de Cloudflare
```

## 1. Clonar y configurar

```bash
cd /home/debian
git clone https://github.com/FidelC96/glpi.git glpi-demo
cd glpi-demo
cp .env.example .env
sed -i "s|^GLPI_DB_PASSWORD=.*|GLPI_DB_PASSWORD=$(openssl rand -hex 24)|" .env
sed -i "s|^GLPI_INTEGRATION_PASSWORD=.*|GLPI_INTEGRATION_PASSWORD=$(openssl rand -hex 24)|" .env
chmod 600 .env
grep -E '^(GLPI_URL_BASE|GLPI_BASE_URL|PROXY_NETWORK)=' .env   # deben decir glpi-demo.rapi.tech y odoo-network
export COMPOSE_FILE=docker-compose.yml:docker-compose.server.yml   # para que TODOS los comandos usen el override
```

## 2. Inventario previo (solo lectura)

```bash
./scripts/check_server.sh
```

Debe decir que `python3` está disponible y no debe aparecer ningún RIESGO nuevo. Ignora el aviso
del puerto 8090: en el servidor no se publica ningún puerto.

## 3. Levantar GLPI

```bash
docker compose up -d
docker compose ps        # glpi_gspn_app SIN puertos; glpi_gspn_db solo "3306/tcp" interno
docker compose logs -f glpi   # esperar "apache2 entered RUNNING state" (~1 min); Ctrl+C
# GLPI responde dentro de la red de nginx (no desde el host):
docker run --rm --network odoo-network curlimages/curl:latest -s -o /dev/null -w '%{http_code}\n' http://glpi_gspn_app/
```

Esperado: `200` (o `302`). Confirmar que no hay puerto nuevo en el host: `ss -tlnp | grep -E '8090|3306'` no devuelve nada.

## 4. nginx, paso 1: solo puerto 80 para emitir el certificado

El bloque final tiene TLS, pero el certificado aún no existe y `nginx -t` fallaría. Primero un bloque temporal solo con el reto ACME:

```bash
cat > /home/debian/nginx/sites-available/glpi-demo.conf <<'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name glpi-demo.rapi.tech;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 404; }
}
EOF
ln -s ../sites-available/glpi-demo.conf /home/debian/nginx/sites-enabled/glpi-demo.conf
docker exec nginx nginx -t && docker exec nginx nginx -s reload
```

Emitir el certificado con el certbot existente (mismo webroot que los Odoo):

```bash
docker exec certbot certbot certonly --webroot -w /var/www/html -d glpi-demo.rapi.tech \
  --email ai@rapi.tech --agree-tos --no-eff-email --non-interactive
ls /home/debian/nginx/certbot/letsencrypt/live/glpi-demo.rapi.tech/   # fullchain.pem y privkey.pem
```

## 5. nginx, paso 2: bloque definitivo con TLS y lista de IPs

```bash
cp deploy/nginx/glpi-demo.conf.example /home/debian/nginx/sites-available/glpi-demo.conf
nano /home/debian/nginx/sites-available/glpi-demo.conf   # editar las líneas allow: tu IP de oficina/casa y la VPN
docker exec nginx nginx -t && docker exec nginx nginx -s reload
```

Para saber tu IP pública desde tu PC: `curl -s ifconfig.me`. Deja la línea `allow 172.18.0.0/16;`
(es el propio servidor entrando por nginx para correr los scripts).

## 6. Cuenta de integración, datos ficticios y verificación

```bash
./scripts/setup_integration.sh   # habilita APIs, perfil mínimo, cuenta, OAuth, técnico, y fija url_base
python3 scripts/seed_demo.py     # entra por https://glpi-demo.rapi.tech (GLPI_BASE_URL); idempotente
python3 scripts/verify_api.py    # tabla de los 3 casos y regenera docs/API_EJEMPLOS.md
```

Si `seed_demo.py` falla con 403 o conexión rechazada, el servidor no se está viendo a sí mismo por
nginx: revisa que `allow 172.18.0.0/16;` esté en el bloque y que `dig +short glpi-demo.rapi.tech`
funcione desde elune.

## 7. Cerrar cuentas por defecto de GLPI

```bash
docker compose exec glpi php bin/console user:disable tech
docker compose exec glpi php bin/console user:disable normal
docker compose exec glpi php bin/console user:disable post-only
```

Y cambiar la contraseña de `glpi` desde la web: entrar con `glpi/glpi` → Preferences → Password.

## 8. Comprobación final de exposición

```bash
docker ps --format '{{.Names}}\t{{.Ports}}' | grep glpi_gspn      # app sin puertos; db solo 3306/tcp interno
./scripts/check_server.sh                                          # sin RIESGO nuevo
curl -sI https://glpi-demo.rapi.tech/ | head -1                     # desde IP permitida: HTTP 200/302
curl -sI https://glpi-demo.rapi.tech/api.php/v2 | head -1           # 401 (API activa, exige token)
```

Desde una IP no permitida (por ejemplo datos del móvil): `curl -sI https://glpi-demo.rapi.tech/` → `403`.

## Operación

```bash
cd /home/debian/glpi-demo && export COMPOSE_FILE=docker-compose.yml:docker-compose.server.yml
docker compose logs -f glpi          # logs
docker compose restart glpi          # reiniciar app
docker compose down                  # parar (conserva datos)
docker compose down -v               # borrar todo, incluidos volúmenes
git pull && docker compose up -d     # actualizar
```

Renovación del certificado: la hace el contenedor `certbot` existente igual que para los Odoo; tras
renovar, `docker exec nginx nginx -s reload`.
