#!/usr/bin/env python3
"""Verifica por API que cada ticket de la demo se puede consultar con su equipo, serie,
referencia externa, estado, costos, aprobación y garantía; compara con la ficha simulada de
Odoo (data/odoo_side.json) y decide si la factura PODRÍA habilitarse (no la emite).

Genera docs/API_EJEMPLOS.md con solicitudes y respuestas reales, sin secretos.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glpi_api import GlpiLegacy, GlpiV2, load_env  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEED = json.loads((ROOT / "data" / "seed.json").read_text())
ODOO = json.loads((ROOT / "data" / "odoo_side.json").read_text())
STATUS = {1: "New", 2: "Processing (assigned)", 3: "Processing (planned)", 4: "Pending", 5: "Solved", 6: "Closed", 10: "Approval"}
VALIDATION = {1: "None", 2: "Waiting", 3: "Accepted", 4: "Refused"}
DEMO_STATE = {  # correspondencia estado GLPI -> estado de la demo (ver docs/ESTADOS.md)
    ("Closed", "Accepted"): "APROBADO",
    ("Solved", "Accepted"): "APROBADO",
    ("Pending", "Refused"): "RECHAZADO",
    ("Pending", "Waiting"): "PENDIENTE",
}

examples: list[str] = []


def sanitize(obj) -> str:
    txt = json.dumps(obj, indent=2, ensure_ascii=False)
    txt = re.sub(r"[0-9a-f]{40,}", "<token>", txt)
    return txt


def ex(title: str, method: str, url: str, body: dict | None, response, note: str = ""):
    block = [f"### {title}", "", f"`{method} {url}`"]
    if body is not None:
        block += ["", "Solicitud:", "```json", sanitize(body), "```"]
    block += ["", "Respuesta (recortada):", "```json", sanitize(response)[:3000], "```"]
    if note:
        block += ["", note]
    examples.append("\n".join(block) + "\n")


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    return date(d.year + y, m + 1, min(d.day, 28))


def main() -> int:
    env = load_env()
    g = GlpiV2(env); g.login()
    legacy = GlpiLegacy(env); legacy.login()
    base = g.api
    token_body = {"grant_type": "password", "client_id": "<GLPI_OAUTH_CLIENT_ID>", "client_secret": "<GLPI_OAUTH_CLIENT_SECRET>",
                  "username": "<GLPI_INTEGRATION_USER>", "password": "<GLPI_INTEGRATION_PASSWORD>", "scope": "api"}
    ex("Obtener token OAuth2 (grant password)", "POST", f"{g.base}/api.php/token", token_body,
       {"token_type": "Bearer", "expires_in": 3600, "access_token": "<token>", "refresh_token": "<token>"},
       "Luego cada llamada lleva `Authorization: Bearer <access_token>`.")

    rows = []
    for t in SEED["tickets"]:
        ext = t["external_id"]
        url = f"{base}/Assistance/Ticket?filter=external_id=={ext}"
        tk = g.search("/Assistance/Ticket", f"external_id=={ext}")[0]
        ex(f"Buscar ticket por referencia externa {ext}", "GET", url, None, [tk])
        tid = tk["id"]

        items = legacy.ticket_items(tid)
        ex(f"Equipo vinculado al ticket {tid} (API heredada; la v2.3 no expone Item_Ticket)", "GET",
           f"{legacy.base}/Ticket/{tid}/Item_Ticket", None, items, "Cabecera: `Session-Token: <session_token>` (obtenido con `GET /apirest.php/initSession` y `Authorization: user_token <token>`).")
        phone = g.get(f"/Assets/Phone/{items[0]['items_id']}")
        ex(f"Equipo {phone['serial']}", "GET", f"{base}/Assets/Phone/{phone['id']}", None, phone)
        infocom = g.get(f"/Assets/Phone/{phone['id']}/Infocom")
        ex(f"Garantía del equipo {phone['serial']}", "GET", f"{base}/Assets/Phone/{phone['id']}/Infocom", None, infocom)
        timeline = g.get(f"/Assistance/Ticket/{tid}/Timeline")
        ex(f"Línea de tiempo del ticket {tid} (diagnóstico, trabajo, aprobación, solución)", "GET", f"{base}/Assistance/Ticket/{tid}/Timeline", None, timeline)
        costs = g.get(f"/Assistance/Ticket/{tid}/Cost")
        ex(f"Costos del ticket {tid} (repuestos y mano de obra)", "GET", f"{base}/Assistance/Ticket/{tid}/Cost", None, costs)
        team = g.get(f"/Assistance/Ticket/{tid}/TeamMember")
        ex(f"Actores del ticket {tid} (cliente solicitante, técnico asignado)", "GET", f"{base}/Assistance/Ticket/{tid}/TeamMember", None, team)

        material = sum(float(c["cost_material"] or 0) for c in costs)
        labor = sum(float(c["cost_fixed"] or 0) for c in costs)
        wd = date.fromisoformat(infocom["date_warranty"])
        warranty_until = add_months(wd, int(infocom["warranty_duration"] or 0))
        in_warranty = warranty_until >= date.today()
        status = tk["status"]["name"]; gval = VALIDATION.get(tk["global_validation"], "?")
        demo_state = DEMO_STATE.get((status, gval), "REVISAR")
        odoo_lot = ODOO["lots"][ext]["lot_name"]
        serial_ok = phone["serial"] == odoo_lot
        invoice_ok = demo_state == "APROBADO" and serial_ok
        requester = next((m["name"] for m in team if m["role"] == "requester"), "-")
        rows.append({"external_id": ext, "ticket_id": tid, "caso": t["case"], "cliente": requester, "equipo": phone["name"],
                     "serie_glpi": phone["serial"], "lote_odoo": odoo_lot, "serie_coincide": serial_ok,
                     "estado_glpi": status, "validacion": gval, "estado_demo": demo_state,
                     "repuestos": material, "mano_obra": labor, "total": material + labor,
                     "garantia_hasta": warranty_until.isoformat(), "en_garantia": in_warranty,
                     "factura_habilitable": invoice_ok,
                     "motivo": "OK" if invoice_ok else ("serie GLPI != lote Odoo" if not serial_ok else f"estado demo = {demo_state}")})
    legacy.logout()

    print(f"{'ref externa':18}{'id':4}{'estado GLPI':12}{'valid.':10}{'demo':11}{'serie GLPI':14}{'lote Odoo':14}{'total':>9}  factura  motivo")
    for r in rows:
        print(f"{r['external_id']:18}{r['ticket_id']:<4}{r['estado_glpi']:12}{r['validacion']:10}{r['estado_demo']:11}{r['serie_glpi']:14}{r['lote_odoo']:14}{r['total']:>9.2f}  {'SI' if r['factura_habilitable'] else 'NO':7}  {r['motivo']}")

    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out" / "verify_result.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    header = ["# Ejemplos de API (generados desde la instancia demo, sin secretos)", "",
              f"Base v2: `{base}` · Base heredada: `{legacy.base}` · Generado por `scripts/verify_api.py`.", "",
              "Los valores `<...>` son placeholders: se leen de `.env`, nunca del repositorio. Los tokens largos se reemplazan por `<token>`.", "",
              "## Sintaxis de consulta (API v2)", "",
              "- `filter`: RSQL, p.ej. `external_id==GSPN-DEMO-000101`, `serial==R58NDEMO0001`, `name==\"Galaxy A55 5G\"`, `name=like=*Galaxy*`, `id=gt=10`.",
              "- `sort`: `propiedad:asc|desc`, varias separadas por coma. `start` y `limit` para paginar; la respuesta trae `Content-Range: inicio-fin/total`.",
              "- Cabecera opcional `GLPI-API-Version: 2.3` para fijar versión; `GLPI-Entity` y `GLPI-Entity-Recursive: true` para cambiar de entidad.", "",
              "## Resultado de la verificación", "", "| ref externa | id | estado GLPI | validación | estado demo | serie GLPI | lote Odoo | total | factura habilitable | motivo |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        header.append(f"| {r['external_id']} | {r['ticket_id']} | {r['estado_glpi']} | {r['validacion']} | {r['estado_demo']} | {r['serie_glpi']} | {r['lote_odoo']} | {r['total']:.2f} | {'sí' if r['factura_habilitable'] else 'no'} | {r['motivo']} |")
    header += ["", "## Llamadas", ""]
    (ROOT / "docs" / "API_EJEMPLOS.md").write_text("\n".join(header) + "\n" + "\n".join(examples))
    print(f"\nEscrito docs/API_EJEMPLOS.md ({len(examples)} ejemplos) y out/verify_result.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
