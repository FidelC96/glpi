#!/usr/bin/env python3
"""Carga reproducible e idempotente de los datos ficticios de la demo en GLPI.

Usa la API v2 (OAuth2) para todo, salvo dos operaciones que la API v2.3 no expone en
escritura y que van por la API heredada (apirest.php):
  - enlace ticket <-> equipo (Item_Ticket)
  - motivo de pendiente del ticket (PendingReason_Item)
Ejecutar dos veces no duplica clientes, equipos ni tickets: cada objeto se busca por su
clave natural (username, serial, external_id, name) antes de crearlo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glpi_api import GlpiError, GlpiLegacy, GlpiV2, load_env  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEED = json.loads((ROOT / "data" / "seed.json").read_text())
VALIDATION_STATUS = {"waiting": 2, "accepted": 3, "refused": 4}
TICKET_STATUS_NAMES = {1: "New", 2: "Processing (assigned)", 3: "Processing (planned)", 4: "Pending", 5: "Solved", 6: "Closed", 10: "Approval"}

created: list[str] = []
reused: list[str] = []


def note(kind: str, what: str, was_created: bool):
    (created if was_created else reused).append(f"{kind}: {what}")


# --------------------------------------------------------------------------- helpers
def rsql_str(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def ensure_dropdown(g: GlpiV2, path: str, name: str, extra: dict | None = None) -> dict:
    row = g.find_one(path, f"name=={rsql_str(name)}")
    if row:
        note(path.rsplit("/", 1)[-1], name, False)
        return row
    g.post(path, {"name": name, **(extra or {})})
    row = g.find_one(path, f"name=={rsql_str(name)}")
    note(path.rsplit("/", 1)[-1], name, True)
    return row


def ensure_user(g: GlpiV2, u: dict) -> dict:
    row = g.find_one("/Administration/User", f"username=={u['username']}")
    body = {"realname": u["realname"], "firstname": u["firstname"], "is_active": True,
            "comment": u.get("comment", ""), "phone": u.get("phone", "")}
    if row:
        g.patch(f"/Administration/User/{row['id']}", body)
        note("User", u["username"], False)
    else:
        g.post("/Administration/User", {"username": u["username"], **body})
        row = g.find_one("/Administration/User", f"username=={u['username']}")
        note("User", u["username"], True)
    return row


def check_profile_user(legacy: GlpiLegacy, user_id: int, username: str):
    """Solo verifica. GLPI no permite que una cuenta otorgue un perfil con más derechos que el suyo,
    por eso el perfil Technician del técnico ficticio lo asigna scripts/setup_integration.sh (paso administrativo)."""
    _, existing = legacy._request("GET", f"/User/{user_id}/Profile_User")
    if existing:
        note("Profile_User", f"{username} tiene perfil id={existing[0]['profiles_id']}", False)
    else:
        print(f"AVISO: {username} no tiene perfil asignado; ejecuta scripts/setup_integration.sh", file=sys.stderr)


def ensure_phone(g: GlpiV2, p: dict, ids: dict) -> dict:
    row = g.find_one("/Assets/Phone", f"serial=={p['serial']}")
    body = {"name": p["name"], "serial": p["serial"], "otherserial": p["otherserial"],
            "manufacturer": {"id": ids["manufacturer"]}, "model": {"id": ids["models"][p["model"]]},
            "status": {"id": ids["states"][p["state"]]}, "user": {"id": ids["users"][p["owner"]]},
            "comment": "Equipo ficticio de la demo (serie inventada)."}
    if row:
        g.patch(f"/Assets/Phone/{row['id']}", body)
        note("Phone", p["serial"], False)
    else:
        g.post("/Assets/Phone", body)
        row = g.find_one("/Assets/Phone", f"serial=={p['serial']}")
        note("Phone", p["serial"], True)
    # Garantía (Infocom): POST si no existe, PATCH si existe.
    w = p["warranty"]
    inf = {"date_buy": w["date_buy"], "date_warranty": w["date_warranty"], "warranty_duration": w["months"],
           "warranty_info": w.get("info", ""), "value": p.get("value", 0)}
    try:
        g.get(f"/Assets/Phone/{row['id']}/Infocom")
        g.patch(f"/Assets/Phone/{row['id']}/Infocom", inf)
        note("Infocom", p["serial"], False)
    except GlpiError as e:
        if e.status != 404:
            raise
        g.post(f"/Assets/Phone/{row['id']}/Infocom", inf)
        note("Infocom", p["serial"], True)
    return row


def timeline(g: GlpiV2, tid: int, kind: str) -> list[dict]:
    try:
        return [t["item"] for t in (g.get(f"/Assistance/Ticket/{tid}/Timeline/{kind}") or [])]
    except GlpiError as e:
        if e.status == 404:
            return []
        raise


def ensure_team(g: GlpiV2, tid: int, user_id: int, role: str):
    members = g.get(f"/Assistance/Ticket/{tid}/TeamMember") or []
    if any(m.get("id") == user_id and m.get("role") == role and m.get("type") == "User" for m in members):
        note("TeamMember", f"ticket {tid} {role}", False)
        return
    g.post(f"/Assistance/Ticket/{tid}/TeamMember", {"type": "User", "id": user_id, "role": role})
    note("TeamMember", f"ticket {tid} {role}", True)


def ensure_ticket(g: GlpiV2, legacy: GlpiLegacy, t: dict, ids: dict) -> dict:
    ext = t["external_id"]
    row = g.find_one("/Assistance/Ticket", f"external_id=={ext}")
    base = {"name": t["name"], "content": t["content"], "external_id": ext, "type": t["type"], "urgency": t["urgency"],
            "date": t["date"], "category": {"id": ids["category"]}}
    if row:
        g.patch(f"/Assistance/Ticket/{row['id']}", base)
        note("Ticket", ext, False)
    else:
        g.post("/Assistance/Ticket", base)
        row = g.find_one("/Assistance/Ticket", f"external_id=={ext}")
        note("Ticket", ext, True)
    tid = row["id"]

    # Actores (solicitante = cliente, asignado = técnico)
    ensure_team(g, tid, ids["users"][t["customer"]], "requester")
    ensure_team(g, tid, ids["users"][t["technician"]], "assigned")

    # Equipo vinculado (API heredada: Item_Ticket)
    phone_id = ids["phones"][t["phone_serial"]]
    r = legacy.link_item(tid, "Phone", phone_id)
    note("Item_Ticket", f"ticket {tid} <-> Phone {phone_id}", r["created"])

    # Diagnóstico = seguimiento
    if not any(f["content"] == t["diagnosis"] for f in timeline(g, tid, "Followup")):
        g.post(f"/Assistance/Ticket/{tid}/Timeline/Followup", {"content": t["diagnosis"], "is_private": False})
        note("Followup", ext, True)
    else:
        note("Followup", ext, False)

    # Trabajo realizado = tarea (con duración en segundos y técnico)
    if t.get("work"):
        if not any(k["content"] == t["work"]["content"] for k in timeline(g, tid, "Task")):
            g.post(f"/Assistance/Ticket/{tid}/Timeline/Task", {"content": t["work"]["content"], "duration": t["work"]["minutes"] * 60,
                                                              "state": 2, "user_tech": {"id": ids["users"][t["technician"]]}})
            note("Task", ext, True)
        else:
            note("Task", ext, False)

    # Repuestos y mano de obra = costos del ticket
    existing_costs = {c["name"] for c in (g.get(f"/Assistance/Ticket/{tid}/Cost") or [])}
    for c in t["costs"]:
        if c["name"] in existing_costs:
            note("Cost", c["name"], False)
            continue
        g.post(f"/Assistance/Ticket/{tid}/Cost", {"name": c["name"], "cost_material": c["cost_material"], "cost_fixed": c["cost_fixed"],
                                                  "cost_time": 0, "duration": c["minutes"] * 60,
                                                  "date_begin": t["date"][:10], "date_end": t["date"][:10]})
        note("Cost", c["name"], True)

    # Aprobación = validación (la cuenta de integración registra la decisión del cliente/sistema externo)
    vals = timeline(g, tid, "Validation")
    want = VALIDATION_STATUS[t["approval"]["status"]]
    if not vals:
        g.post(f"/Assistance/Ticket/{tid}/Timeline/Validation", {"requested_approver_type": "User", "requested_approver_id": ids["me"],
                                                                 "submission_comment": t["approval"]["submission_comment"]})
        vals = timeline(g, tid, "Validation")
        note("Validation", ext, True)
    else:
        note("Validation", ext, False)
    v = vals[0]
    if v["status"] != want:
        g.patch(f"/Assistance/Ticket/{tid}/Timeline/Validation/{v['id']}", {"status": want, "approval_comment": t["approval"]["approval_comment"]})

    # Solución (cierra el trabajo; GLPI pasa el ticket a Solved automáticamente)
    if t.get("solution"):
        if not timeline(g, tid, "Solution"):
            g.post(f"/Assistance/Ticket/{tid}/Timeline/Solution", {"content": t["solution"]})
            note("Solution", ext, True)
        else:
            note("Solution", ext, False)

    # Motivo de pendiente (API heredada: PendingReason_Item)
    if t.get("pending_reason"):
        prid = ids["pending_reasons"][t["pending_reason"]]
        _, existing = legacy._request("GET", f"/Ticket/{tid}/PendingReason_Item")
        if not existing:
            legacy._request("POST", "/PendingReason_Item", {"input": {"itemtype": "Ticket", "items_id": tid, "pendingreasons_id": prid}})
            note("PendingReason_Item", ext, True)
        else:
            note("PendingReason_Item", ext, False)

    # Estado final (idempotente: siempre se fija al final)
    g.patch(f"/Assistance/Ticket/{tid}", {"status": t["final_status"]})
    return g.get(f"/Assistance/Ticket/{tid}")


# --------------------------------------------------------------------------- main
def main() -> int:
    env = load_env()
    g = GlpiV2(env); g.login()
    legacy = GlpiLegacy(env); legacy.login()
    try:
        ids: dict = {"models": {}, "states": {}, "users": {}, "phones": {}, "pending_reasons": {}}
        me = g.find_one("/Administration/User", f"username=={env['GLPI_INTEGRATION_USER']}")
        ids["me"] = me["id"]

        ids["manufacturer"] = ensure_dropdown(g, "/Dropdowns/Manufacturer", SEED["manufacturer"])["id"]
        for m in SEED["phone_models"]:
            ids["models"][m["name"]] = ensure_dropdown(g, "/Dropdowns/PhoneModel", m["name"], {"product_number": m["product_number"]})["id"]
        for s in SEED["states"]:
            ids["states"][s] = ensure_dropdown(g, "/Dropdowns/State", s)["id"]
        cat = SEED["itil_category"]
        ids["category"] = ensure_dropdown(g, "/Dropdowns/ITILCategory", cat["name"], {"code": cat["code"], "is_incident_visible": True, "is_request_visible": True})["id"]
        for pr in SEED["pending_reasons"]:
            ids["pending_reasons"][pr] = ensure_dropdown(g, "/Assistance/PendingReason", pr)["id"]

        for u in SEED["users"]:
            row = ensure_user(g, u)
            ids["users"][u["username"]] = row["id"]
            if u.get("profile"):
                check_profile_user(legacy, row["id"], u["username"])

        for p in SEED["phones"]:
            ids["phones"][p["serial"]] = ensure_phone(g, p, ids)["id"]

        results = []
        for t in SEED["tickets"]:
            tk = ensure_ticket(g, legacy, t, ids)
            results.append((t["external_id"], t["case"], tk["id"], tk["status"]["name"], tk["global_validation"]))
    finally:
        legacy.logout()

    print("\n== Resultado ==")
    print(f"creados: {len(created)} | reutilizados: {len(reused)}")
    for line in created:
        print("  +", line)
    print("\n== Tickets ==")
    for ext, case, tid, status, gv in results:
        print(f"  {ext}  id={tid:<3} caso={case:<32} estado={status:<22} global_validation={gv}")
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out" / "seed_ids.json").write_text(json.dumps(ids, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except GlpiError as e:
        print("ERROR API:", e, file=sys.stderr)
        sys.exit(1)
