"""Cliente mínimo (solo librería estándar) para la API v2 de GLPI 11 y, de forma excepcional,
para la API heredada (v1) en la única operación que la v2.3 no expone en escritura: el
enlace ticket <-> equipo (Item_Ticket).

Lee la configuración de .env (o variables de entorno). Nunca imprime secretos.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Cloudflare bloquea el UA por defecto de urllib ("Python-urllib", error 1010); se envía uno propio.
USER_AGENT = "glpi-gspn-demo/1.0 (+https://github.com/FidelC96/glpi)"


def load_env(path: Path = ROOT / ".env") -> dict[str, str]:
    env: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("GLPI_")})
    return env


class GlpiError(RuntimeError):
    def __init__(self, status: int, body: str, method: str, url: str):
        super().__init__(f"{method} {url} -> HTTP {status}: {body[:500]}")
        self.status, self.body = status, body


class GlpiV2:
    """API v2 (High-Level API). Autenticación OAuth2 grant password + Bearer."""

    def __init__(self, env: dict[str, str] | None = None):
        env = env or load_env()
        # GLPI_BASE_URL (p.ej. https://glpi-demo.dominio) tiene prioridad: en el servidor no hay puerto publicado.
        self.base = (env.get("GLPI_BASE_URL") or f"http://{env.get('GLPI_BIND', '127.0.0.1')}:{env.get('GLPI_PORT', '8090')}").rstrip("/")
        self.api = f"{self.base}/api.php/v2"
        self._env = env
        self.token: str | None = None
        self.last_headers: dict = {}

    # --- transporte -------------------------------------------------------
    def _request(self, method: str, url: str, body: dict | None = None, headers: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        h = {"Accept": "application/json", "User-Agent": USER_AGENT}
        if data is not None:
            h["Content-Type"] = "application/json"
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        h.update(headers or {})
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode()
                self.last_headers = dict(r.headers)
                return r.status, (json.loads(raw) if raw.strip() else None)
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            raise GlpiError(e.code, raw, method, url) from None

    def login(self) -> None:
        e = self._env
        status, data = self._request("POST", f"{self.base}/api.php/token", {
            "grant_type": "password",
            "client_id": e["GLPI_OAUTH_CLIENT_ID"],
            "client_secret": e["GLPI_OAUTH_CLIENT_SECRET"],
            "username": e["GLPI_INTEGRATION_USER"],
            "password": e["GLPI_INTEGRATION_PASSWORD"],
            "scope": "api",
        })
        self.token = data["access_token"]

    # --- helpers CRUD -----------------------------------------------------
    def get(self, path: str, **params):
        q = ("?" + urllib.parse.urlencode(params)) if params else ""
        _, data = self._request("GET", f"{self.api}{path}{q}")
        return data

    def search(self, path: str, rsql: str, limit: int = 50, **extra):
        """GET con filtro RSQL. Ej.: search('/Assets/Phone', 'serial==R58N0DEMO001')."""
        return self.get(path, filter=rsql, limit=limit, **extra) or []

    def find_one(self, path: str, rsql: str):
        rows = self.search(path, rsql, limit=2)
        return rows[0] if rows else None

    def post(self, path: str, body: dict):
        status, data = self._request("POST", f"{self.api}{path}", body)
        return data

    def patch(self, path: str, body: dict):
        _, data = self._request("PATCH", f"{self.api}{path}", body)
        return data

    def delete(self, path: str):
        return self._request("DELETE", f"{self.api}{path}")


class GlpiLegacy:
    """API heredada (apirest.php). Solo se usa para Item_Ticket. Autenticación por user_token."""

    def __init__(self, env: dict[str, str] | None = None):
        env = env or load_env()
        root = (env.get("GLPI_BASE_URL") or f"http://{env.get('GLPI_BIND', '127.0.0.1')}:{env.get('GLPI_PORT', '8090')}").rstrip("/")
        self.base = f"{root}/apirest.php"
        self.user_token = env["GLPI_LEGACY_USER_TOKEN"]
        self.session: str | None = None

    def _request(self, method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        h = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
        if self.session:
            h["Session-Token"] = self.session
        else:
            h["Authorization"] = f"user_token {self.user_token}"
        req = urllib.request.Request(f"{self.base}{path}", data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode()
                return r.status, (json.loads(raw) if raw.strip() else None)
        except urllib.error.HTTPError as e:
            raise GlpiError(e.code, e.read().decode(errors="replace"), method, path) from None

    def login(self):
        _, d = self._request("GET", "/initSession")
        self.session = d["session_token"]

    def logout(self):
        if self.session:
            self._request("GET", "/killSession")
            self.session = None

    def ticket_items(self, ticket_id: int) -> list[dict]:
        _, d = self._request("GET", f"/Ticket/{ticket_id}/Item_Ticket")
        return d or []

    def link_item(self, ticket_id: int, itemtype: str, items_id: int) -> dict:
        """Idempotente: si el enlace ya existe, lo devuelve sin crear otro."""
        for row in self.ticket_items(ticket_id):
            if row.get("itemtype") == itemtype and int(row.get("items_id", 0)) == items_id:
                return {"id": row["id"], "created": False}
        _, d = self._request("POST", "/Item_Ticket", {"input": {"tickets_id": ticket_id, "itemtype": itemtype, "items_id": items_id}})
        return {"id": d["id"], "created": True}
