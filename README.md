# Demo: mantenimiento Odoo ↔ sistema externo (GLPI como simulador tipo GSPN)

**Qué es:** un GLPI 11 local con datos 100 % ficticios que simula un sistema externo de órdenes
de servicio (estilo GSPN de Samsung) para diseñar y probar el conector hacia Odoo.

**Qué no es:** no es una integración con GSPN ni con ninguna API de Samsung. No hay acceso a
GSPN. No se conecta a ningún Odoo real ni emite facturas.

## Componentes

| Pieza | Detalle |
|---|---|
| GLPI | imagen oficial `glpi/glpi:11.0.9` (API v2.3), volumen `glpi_gspn_data` |
| Base de datos | `mariadb:11.4.13` (LTS), volumen `glpi_gspn_db`, sin puerto publicado |
| Exposición | solo `127.0.0.1:8090` (variable `GLPI_BIND`/`GLPI_PORT` en `.env`) |
| Cuenta de integración | usuario `gspn_integration`, perfil "Integración GSPN (demo)" con permisos mínimos |
| Autenticación | API v2: OAuth2 grant `password` + Bearer, scope `api`; API heredada: `user_token` (solo para dos operaciones) |

## Puesta en marcha

```bash
cp .env.example .env      # y edita contraseñas (o genera con: openssl rand -hex 24)
docker compose up -d       # GLPI se auto-instala (~40 s)
./scripts/setup_integration.sh   # habilita APIs, crea perfil, cuenta, cliente OAuth y técnico ficticio; guarda secretos en .env
python3 scripts/seed_demo.py     # carga datos ficticios (idempotente: puedes repetirlo)
python3 scripts/verify_api.py    # consulta por API y regenera docs/API_EJEMPLOS.md
```

Interfaz web: `http://127.0.0.1:8090` (cuentas por defecto de GLPI: `glpi/glpi`, `tech/tech`,
`normal/normal`, `post-only/postonly`; cámbialas si la red de pruebas es compartida).
Documentación interactiva de la API v2: `http://127.0.0.1:8090/api.php/doc` (Swagger) y
`http://127.0.0.1:8090/api.php/getting-started`.

Solo Python 3 estándar (sin dependencias) y `docker compose`.

## Casos cargados

| Referencia externa | Caso | Equipo (serie ficticia) | Estado GLPI | Validación | Resultado esperado en Odoo |
|---|---|---|---|---|---|
| GSPN-DEMO-000101 | servicio correcto y aprobado | Galaxy S24 Ultra, R58NDEMO0001 | Closed | Accepted | factura habilitable (S/ 970.00) |
| GSPN-DEMO-000102 | serie diferente entre sistemas | Galaxy A55 5G, R58NDEMO0002 (Odoo tiene R58NDEM00002) | Solved | Accepted | bloqueado por serie |
| GSPN-DEMO-000103 | pendiente / rechazado | Galaxy Tab S9, R58NDEMO0003 | Pending | Refused | sin factura |

Además, 20 tickets **pendientes de aprobación** (GSPN-DEMO-000104 a 000123): estado Pending,
validación Waiting, motivo de pendiente alternado ("Esperando aprobación del cliente" / "Esperando repuesto"),
un equipo distinto cada uno y 10 clientes adicionales. Sirven para probar el flujo de aprobación desde Odoo.

Clientes ficticios: Rosa Quispe Demo, Luis Paredes (Comercial Andina SAC demo), Jorge Mendoza
Demo. Técnica ficticia: Carla Rojas Demo (`tecnico.demo`, perfil Technician). La "ficha Odoo"
simulada está en `data/odoo_side.json`.

## Documentos

- `docs/ESTADOS.md`: estados reales de GLPI y su correspondencia con los estados de la demo.
- `docs/MAPEO_GLPI_ODOO.md`: mapeo de campos GLPI → Odoo y lo que no existe de forma nativa.
- `docs/API_EJEMPLOS.md`: solicitudes y respuestas reales (sin secretos) para construir el conector o herramientas MCP.

## Configuración manual imprescindible (y cómo se automatizó)

Todo lo que GLPI no permite hacer con la cuenta de integración se hace **una vez** dentro del
contenedor con `scripts/glpi_admin_setup.php` (lo ejecuta `setup_integration.sh`):

1. Habilitar la API v2 (`enable_hlapi`) y la heredada (`enable_api`). Equivale a Setup > General > API.
2. Crear el perfil "Integración GSPN (demo)" (clon recortado de Technician). Equivale a Administration > Profiles.
3. Crear el usuario de integración y asignarle el perfil. Equivale a Administration > Users.
4. Crear el cliente OAuth (grant `password`, scope `api`). Equivale a Setup > OAuth clients.
5. Generar el token de API heredada del usuario. Equivale a Preferences > Remote access keys.
6. Crear el técnico ficticio con perfil Technician: GLPI impide que una cuenta otorgue un perfil con
   más derechos que el suyo, así que no puede hacerlo la cuenta de integración por API.

## Permisos de la cuenta de integración

Derechos distintos de cero del perfil (verificable en `glpi_profilerights`): `ticket` (leer, crear,
actualizar, asignar; sin borrar), `followup`, `task`, `ticketcost`, `ticketvalidation` (crear y
validar), `phone`, `infocom`, `dropdown`, `state`, `itilcategory`, `pendingreason`, `user` (leer,
crear, actualizar; sin borrar ni importar), `entity` (leer), `password_update`, `personalization`.
Sin acceso a configuración, perfiles, clientes OAuth, otros activos ni borrado.

## Límites encontrados en la API v2.3 (documentados, no inventados)

- No hay ruta para vincular un equipo a un ticket (`Item_Ticket`) ni para leer ese vínculo:
  se usa la API heredada `apirest.php` (`/Item_Ticket`, `/Ticket/{id}/Item_Ticket`).
- El motivo de pendiente de un ticket solo se lee en v2; se escribe con `/PendingReason_Item` heredado.
- Asignar solicitante o técnico exige el derecho ASSIGN del ticket (la API llama a `canAssign()`).
- `Ticket.status` figura como solo lectura en el esquema, pero `PATCH {"status": 4}` funciona.
- Una validación solo la puede resolver su aprobador: por eso la demo pide la validación a la
  propia cuenta de integración.

## Seguridad y datos

- `.env` está en `.gitignore`; `.env.example` no contiene valores reales.
- Los secretos nunca se imprimen: los scripts los leen de `.env`; `verify_api.py` reemplaza tokens.
- El servicio escucha solo en loopback. Para una red de pruebas autorizada cambia `GLPI_BIND`.
- Todos los nombres, series, IMEI, teléfonos e importes son inventados.

## Parar y borrar

```bash
docker compose down           # conserva datos
docker compose down -v        # borra también los volúmenes (GLPI y base de datos)
```

## Despliegue en servidor (elune) sin publicar puertos

En el servidor nginx corre como contenedor en la red Docker `odoo-network` y ya tiene 80/443
abiertos para los Odoo. GLPI se une a esa red y **no publica ningún puerto** en el host
(ni siquiera en loopback); MariaDB queda solo en la red privada del stack.

```bash
git clone <repo> /home/debian/glpi-demo && cd /home/debian/glpi-demo
cp .env.example .env            # completar: contraseñas (openssl rand -hex 24), GLPI_URL_BASE=https://glpi-demo.rapi.tech
docker compose -f docker-compose.yml -f docker-compose.server.yml up -d
./scripts/setup_integration.sh   # también fija url_base a GLPI_URL_BASE
python3 scripts/seed_demo.py && python3 scripts/verify_api.py
```

nginx: copiar `deploy/nginx/glpi-demo.conf.example` a `/home/debian/nginx/sites-available/glpi-demo.conf`,
enlazar en `sites-enabled`, emitir el certificado con certbot (webroot `/home/debian/nginx/certbot/www`,
igual que los Odoo) y recargar (`docker exec nginx nginx -t && docker exec nginx nginx -s reload`).
Como el 443 es público, el bloque restringe el acceso por IP (`allow/deny`); ajustar la lista.

Comprobación posterior: `./scripts/check_server.sh` debe mostrar `glpi_gspn_app` sin puertos publicados,
y desde fuera de las IPs permitidas `curl -I https://glpi-demo.rapi.tech` debe devolver 403.
Nota: los scripts `seed`/`verify` se conectan por `GLPI_BIND:GLPI_PORT`; en el servidor, sin puerto publicado,
ejecútalos apuntando a la URL pública (`GLPI_BASE_URL=https://glpi-demo.rapi.tech`) o desde un contenedor de la red.
