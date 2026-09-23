# Ejemplos de API (generados desde la instancia demo, sin secretos)

Base v2: `http://127.0.0.1:8090/api.php/v2` · Base heredada: `http://127.0.0.1:8090/apirest.php` · Generado por `scripts/verify_api.py`.

Los valores `<...>` son placeholders: se leen de `.env`, nunca del repositorio. Los tokens largos se reemplazan por `<token>`.

## Sintaxis de consulta (API v2)

- `filter`: RSQL, p.ej. `external_id==GSPN-DEMO-000101`, `serial==R58NDEMO0001`, `name=="Galaxy A55 5G"`, `name=like=*Galaxy*`, `id=gt=10`.
- `sort`: `propiedad:asc|desc`, varias separadas por coma. `start` y `limit` para paginar; la respuesta trae `Content-Range: inicio-fin/total`.
- Cabecera opcional `GLPI-API-Version: 2.3` para fijar versión; `GLPI-Entity` y `GLPI-Entity-Recursive: true` para cambiar de entidad.

## Resultado de la verificación

| ref externa | id | estado GLPI | validación | estado demo | serie GLPI | lote Odoo | total | factura habilitable | motivo |
|---|---|---|---|---|---|---|---|---|---|
| GSPN-DEMO-000101 | 3 | Closed | Accepted | APROBADO | R58NDEMO0001 | R58NDEMO0001 | 970.00 | sí | OK |
| GSPN-DEMO-000102 | 4 | Solved | Accepted | APROBADO | R58NDEMO0002 | R58NDEM00002 | 260.00 | no | serie GLPI != lote Odoo |
| GSPN-DEMO-000103 | 5 | Pending | Refused | RECHAZADO | R58NDEMO0003 | R58NDEMO0003 | 640.00 | no | estado demo = RECHAZADO |

## Llamadas

### Obtener token OAuth2 (grant password)

`POST http://127.0.0.1:8090/api.php/token`

Solicitud:
```json
{
  "grant_type": "password",
  "client_id": "<GLPI_OAUTH_CLIENT_ID>",
  "client_secret": "<GLPI_OAUTH_CLIENT_SECRET>",
  "username": "<GLPI_INTEGRATION_USER>",
  "password": "<GLPI_INTEGRATION_PASSWORD>",
  "scope": "api"
}
```

Respuesta (recortada):
```json
{
  "token_type": "Bearer",
  "expires_in": 3600,
  "access_token": "<token>",
  "refresh_token": "<token>"
}
```

Luego cada llamada lleva `Authorization: Bearer <access_token>`.

### Buscar ticket por referencia externa GSPN-DEMO-000101

`GET http://127.0.0.1:8090/api.php/v2/Assistance/Ticket?filter=external_id==GSPN-DEMO-000101`

Respuesta (recortada):
```json
[
  {
    "id": 3,
    "name": "Cambio de pantalla Galaxy S24 Ultra (orden GSPN-DEMO-000101)",
    "content": "Orden externa: GSPN-DEMO-000101\nSíntoma reportado: pantalla con líneas verdes tras caída.\nSerie declarada en la orden: R58NDEMO0001\nEquipo en garantía de fábrica; daño físico no cubierto (servicio con cargo).",
    "is_deleted": false,
    "urgency": 3,
    "impact": 3,
    "priority": 3,
    "actiontime": 5400,
    "begin_waiting_date": "2026-09-23T18:41:05+00:00",
    "waiting_duration": 0,
    "resolution_duration": 1933865,
    "close_duration": 1933865,
    "resolution_date": null,
    "date_creation": "2026-09-23T18:41:04+00:00",
    "date_mod": "2026-09-23T18:41:05+00:00",
    "date": "2026-09-01T09:30:00+00:00",
    "date_solve": "2026-09-23T18:41:05+00:00",
    "date_close": "2026-09-23T18:41:05+00:00",
    "type": 1,
    "external_id": "GSPN-DEMO-000101",
    "take_into_account_date": "2026-09-23T18:41:04+00:00",
    "take_into_account_duration": 1933864,
    "sla_waiting_duration": 0,
    "ola_waiting_duration": 0,
    "ola_ttr_begin_date": null,
    "ola_tto_begin_date": null,
    "internal_resolution_date": null,
    "internal_take_into_account_date": null,
    "global_validation": 3,
    "status": {
      "id": 6,
      "name": "Closed"
    },
    "user_recipient": {
      "id": 7,
      "name": "gspn_integration"
    },
    "user_editor": {
      "id": 7,
      "name": "gspn_integration"
    },
    "category": {
      "id": 2,
      "name": "Servicio técnico Samsung (demo)"
    },
    "location": null,
    "request_type": {
      "id": 1,
      "name": "Helpdesk"
    },
    "sla_ttr": null,
    "sla_tto": null,
    "ola_ttr": null,
    "ola_tto": null,
    "sla_level_ttr": null,
    "ola_level_ttr": null,
    "entity": {
      "id": 0,
      "name": "Root entity",
      "completename": "Root entity"
    },
    "costs": [
      {
        "id": 2
      },
      {
        "id": 3
      }
    ],
    "team": [
      {
        "role": "requester",
        "name": "cliente.rquispe",
        "realname": "Quispe Demo",
        "firstname": "Rosa",
        "display_name": "Quispe Demo Rosa",
        "id": 10,
        "href": "/front/user.form.php?id=10",
        "type": "User"
      },
      {
        "role": "assigned",
        "name": "tecnico.demo",
        "realname": "Rojas Demo",
        "firstname": "Carla",
        "display_name": "Rojas Demo Carla",
        "id": 9,
        "href": "/front/user.form.php?id=9",
        "type": "User"
      }
    ]
  }
]
```

### Equipo vinculado al ticket 3 (API heredada; la v2.3 no expone Item_Ticket)

`GET http://127.0.0.1:8090/apirest.php/Ticket/3/Item_Ticket`

Respuesta (recortada):
```json
[
  {
    "id": 2,
    "itemtype": "Phone",
    "items_id": 3,
    "tickets_id": 3,
    "links": [
      {
        "rel": "Phone",
        "href": "http://localhost/api.php/v1/Phone/3"
      },
      {
        "rel": "Ticket",
        "href": "http://localhost/api.php/v1/Ticket/3"
      }
    ]
  }
]
```

Cabecera: `Session-Token: <session_token>` (obtenido con `GET /apirest.php/initSession` y `Authorization: user_token <token>`).

### Equipo R58NDEMO0001

`GET http://127.0.0.1:8090/api.php/v2/Assets/Phone/3`

Respuesta (recortada):
```json
{
  "id": 3,
  "name": "SM-S928B-DEMO-001",
  "comment": "Equipo ficticio de la demo (serie inventada).",
  "is_recursive": false,
  "contact": null,
  "contact_num": null,
  "serial": "R58NDEMO0001",
  "otherserial": "IMEI-350000000000011",
  "is_deleted": false,
  "date_creation": "2026-09-23T18:41:04+00:00",
  "date_mod": "2026-09-23T18:41:05+00:00",
  "uuid": null,
  "brand": null,
  "number_line": null,
  "have_headset": false,
  "have_hp": false,
  "is_global": false,
  "is_template": false,
  "template_name": null,
  "ticket_tco": 970,
  "is_dynamic": false,
  "last_inventory_update": null,
  "status": {
    "id": 2,
    "name": "Operativo (demo)"
  },
  "entity": {
    "id": 0,
    "name": "Root entity",
    "completename": "Root entity"
  },
  "manufacturer": {
    "id": 2,
    "name": "Samsung"
  },
  "user": {
    "id": 10,
    "name": "cliente.rquispe"
  },
  "user_tech": null,
  "location": null,
  "type": null,
  "model": {
    "id": 2,
    "name": "Galaxy S24 Ultra"
  },
  "group": [],
  "group_tech": [],
  "autoupdatesystem": null,
  "power_supply": null
}
```

### Garantía del equipo R58NDEMO0001

`GET http://127.0.0.1:8090/api.php/v2/Assets/Phone/3/Infocom`

Respuesta (recortada):
```json
{
  "id": 2,
  "itemtype": "Phone",
  "items_id": 3,
  "comment": null,
  "is_recursive": false,
  "date_buy": "2026-01-15",
  "date_use": null,
  "date_order": null,
  "date_delivery": null,
  "date_inventory": null,
  "date_warranty": "2026-01-15",
  "date_decommission": null,
  "warranty_info": "Garantía de fábrica 24 meses (demo). Daño físico no cubierto.",
  "warranty_value": 0,
  "warranty_duration": 24,
  "order_number": null,
  "delivery_number": null,
  "immo_number": null,
  "invoice_number": null,
  "value": 4200,
  "amortization_type": "0",
  "amortization_time": 0,
  "amortization_coeff": 0,
  "entity": {
    "id": 0,
    "name": "Root entity"
  },
  "budget": null,
  "supplier": null,
  "business_criticity": null
}
```

### Línea de tiempo del ticket 3 (diagnóstico, trabajo, aprobación, solución)

`GET http://127.0.0.1:8090/api.php/v2/Assistance/Ticket/3/Timeline`

Respuesta (recortada):
```json
[
  {
    "type": "Followup",
    "item": {
      "id": 2,
      "itemtype": "Ticket",
      "items_id": 3,
      "content": "DIAGNÓSTICO: panel AMOLED dañado por impacto; batería, placa y cámaras OK. Cobertura: garantía vigente pero daño físico NO cubierto. Se emite presupuesto al cliente: S/ 970.00.",
      "is_private": false,
      "date": "2026-09-23T18:41:04+00:00",
      "date_creation": "2026-09-23T18:41:04+00:00",
      "date_mod": "2026-09-23T18:41:04+00:00",
      "timeline_position": 1,
      "source_item_id": 0,
      "source_of_item_id": 0,
      "user": {
        "id": 7,
        "name": "gspn_integration"
      },
      "user_editor": null,
      "request_type": null
    }
  },
  {
    "type": "Task",
    "item": {
      "id": 2,
      "uuid": "b857d18c-348f-44b5-a8b1-919aa2fdd53c",
      "content": "TRABAJO REALIZADO: reemplazo de panel AMOLED (repuesto GH82-DEMO-0101), calibración táctil y prueba funcional completa.",
      "is_private": false,
      "date": "2026-09-23T18:41:05+00:00",
      "date_creation": "2026-09-23T18:41:05+00:00",
      "date_mod": "2026-09-23T18:41:05+00:00",
      "duration": 5400,
      "planned_begin": null,
      "planned_end": null,
      "state": 2,
      "timeline_position": 1,
      "tickets_id": 3,
      "source_item_id": 0,
      "source_of_item_id": 0,
      "user": {
        "id": 7,
        "name": "gspn_integration"
      },
      "user_editor": null,
      "user_tech": {
        "id": 9,
        "name": "tecnico.demo"
      },
      "group_tech": null,
      "category": null
    }
  },
  {
    "type": "Solution",
    "item": {
      "id": 2,
      "itemtype": "Ticket",
      "items_id": 3,
      "content": "Equipo reparado, probado y entregado al cliente. Prueba funcional OK.",
      "status": 2,
      "date_creation": "2026-09-23T18:41:05+00:00",
      "date_mod": "2026-09-23T18:41:05+00:00",
      "date_approval": null,
      "type": null,
      "user": {
        "id": 7,
        "name": "gspn_integration"
      },
      "user_editor": null,
      "approver": null,
      "approval_followup": null
    }
  },
  {
    "type": "Validation",
    "item": {
      "id": 3,
      "requested_approver_type": "User",
      "requested_approver_id": 7,
      "submission_comment": "Presupuesto S/ 970.00 enviado al cliente para aprobación.",
      "approval_comment": "Cliente aprobó el presupuesto (demo).",
      "status": 3,
      "submission_date": "2026-09-23T18:41:05+00:00",
      "approval_date": "2026-09-23T18:41:05+00:00",
      "timeline_position": 1,
      "tickets_id": 3,
      "requester": {
        "id": 7,
        "name": "gspn_integration"
      },
      "approver": null
    }
  }
]
```

### Costos del ticket 3 (repuestos y mano de obra)

`GET http://127.0.0.1:8090/api.php/v2/Assistance/Ticket/3/Cost`

Respuesta (recortada):
```json
[
  {
    "id": 2,
    "name": "Repuesto: Panel AMOLED GH82-DEMO-0101",
    "comment": null,
    "date_begin": "2026-09-01T00:00:00+00:00",
    "date_end": "2026-09-01T00:00:00+00:00",
    "duration": 0,
    "cost_time": 0,
    "cost_fixed": 0,
    "cost_material": 850,
    "ticket": {
      "id": 3,
      "name": "Cambio de pantalla Galaxy S24 Ultra (orden GSPN-DEMO-000101)"
    },
    "budget": null,
    "entity": {
      "id": 0,
      "name": "Root entity"
    }
  },
  {
    "id": 3,
    "name": "Mano de obra: 1.5 h taller",
    "comment": null,
    "date_begin": "2026-09-01T00:00:00+00:00",
    "date_end": "2026-09-01T00:00:00+00:00",
    "duration": 5400,
    "cost_time": 0,
    "cost_fixed": 120,
    "cost_material": 0,
    "ticket": {
      "id": 3,
      "name": "Cambio de pantalla Galaxy S24 Ultra (orden GSPN-DEMO-000101)"
    },
    "budget": null,
    "entity": {
      "id": 0,
      "name": "Root entity"
    }
  }
]
```

### Actores del ticket 3 (cliente solicitante, técnico asignado)

`GET http://127.0.0.1:8090/api.php/v2/Assistance/Ticket/3/TeamMember`

Respuesta (recortada):
```json
[
  {
    "role": "requester",
    "name": "cliente.rquispe",
    "realname": "Quispe Demo",
    "firstname": "Rosa",
    "display_name": "Quispe Demo Rosa",
    "id": 10,
    "href": "/front/user.form.php?id=10",
    "type": "User"
  },
  {
    "role": "assigned",
    "name": "tecnico.demo",
    "realname": "Rojas Demo",
    "firstname": "Carla",
    "display_name": "Rojas Demo Carla",
    "id": 9,
    "href": "/front/user.form.php?id=9",
    "type": "User"
  }
]
```

### Buscar ticket por referencia externa GSPN-DEMO-000102

`GET http://127.0.0.1:8090/api.php/v2/Assistance/Ticket?filter=external_id==GSPN-DEMO-000102`

Respuesta (recortada):
```json
[
  {
    "id": 4,
    "name": "Reemplazo de batería Galaxy A55 (orden GSPN-DEMO-000102)",
    "content": "Orden externa: GSPN-DEMO-000102\nSíntoma reportado: batería se descarga en 2 horas.\nSerie declarada en la orden: R58NDEMO0002\nNOTA DEMO: en Odoo el lote/serie registrado para este equipo difiere (ver data/odoo_side.json).",
    "is_deleted": false,
    "urgency": 3,
    "impact": 3,
    "priority": 3,
    "actiontime": 2700,
    "begin_waiting_date": "2026-09-23T18:41:06+00:00",
    "waiting_duration": 0,
    "resolution_duration": 1582866,
    "close_duration": 0,
    "resolution_date": null,
    "date_creation": "2026-09-23T18:41:05+00:00",
    "date_mod": "2026-09-23T18:41:06+00:00",
    "date": "2026-09-05T11:00:00+00:00",
    "date_solve": "2026-09-23T18:41:06+00:00",
    "date_close": null,
    "type": 1,
    "external_id": "GSPN-DEMO-000102",
    "take_into_account_date": "2026-09-23T18:41:05+00:00",
    "take_into_account_duration": 1582865,
    "sla_waiting_duration": 0,
    "ola_waiting_duration": 0,
    "ola_ttr_begin_date": null,
    "ola_tto_begin_date": null,
    "internal_resolution_date": null,
    "internal_take_into_account_date": null,
    "global_validation": 3,
    "status": {
      "id": 5,
      "name": "Solved"
    },
    "user_recipient": {
      "id": 7,
      "name": "gspn_integration"
    },
    "user_editor": {
      "id": 7,
      "name": "gspn_integration"
    },
    "category": {
      "id": 2,
      "name": "Servicio técnico Samsung (demo)"
    },
    "location": null,
    "request_type": {
      "id": 1,
      "name": "Helpdesk"
    },
    "sla_ttr": null,
    "sla_tto": null,
    "ola_ttr": null,
    "ola_tto": null,
    "sla_level_ttr": null,
    "ola_level_ttr": null,
    "entity": {
      "id": 0,
      "name": "Root entity",
      "completename": "Root entity"
    },
    "costs": [
      {
        "id": 4
      },
      {
        "id": 5
      }
    ],
    "team": [
      {
        "role": "requester",
        "name": "cliente.andina",
        "realname": "Paredes (Comercial Andina SAC demo)",
        "firstname": "Luis",
        "display_name": "Paredes (Comercial Andina SAC demo) Luis",
        "id": 11,
        "href": "/front/user.form.php?id=11",
        "type": "User"
      },
      {
        "role": "assigned",
        "name": "tecnico.demo",
        "realname": "Rojas Demo",
        "firstname": "Carla",
        "display_name": "Rojas Demo Carla",
        "id": 9,
        "href": "/front/user.form.php?id=9",
        "type": "User"
      }
    ]
  }
]
```

### Equipo vinculado al ticket 4 (API heredada; la v2.3 no expone Item_Ticket)

`GET http://127.0.0.1:8090/apirest.php/Ticket/4/Item_Ticket`

Respuesta (recortada):
```json
[
  {
    "id": 3,
    "itemtype": "Phone",
    "items_id": 4,
    "tickets_id": 4,
    "links": [
      {
        "rel": "Phone",
        "href": "http://localhost/api.php/v1/Phone/4"
      },
      {
        "rel": "Ticket",
        "href": "http://localhost/api.php/v1/Ticket/4"
      }
    ]
  }
]
```

Cabecera: `Session-Token: <session_token>` (obtenido con `GET /apirest.php/initSession` y `Authorization: user_token <token>`).

### Equipo R58NDEMO0002

`GET http://127.0.0.1:8090/api.php/v2/Assets/Phone/4`

Respuesta (recortada):
```json
{
  "id": 4,
  "name": "SM-A556E-DEMO-002",
  "comment": "Equipo ficticio de la demo (serie inventada).",
  "is_recursive": false,
  "contact": null,
  "contact_num": null,
  "serial": "R58NDEMO0002",
  "otherserial": "IMEI-350000000000022",
  "is_deleted": false,
  "date_creation": "2026-09-23T18:41:04+00:00",
  "date_mod": "2026-09-23T18:41:06+00:00",
  "uuid": null,
  "brand": null,
  "number_line": null,
  "have_headset": false,
  "have_hp": false,
  "is_global": false,
  "is_template": false,
  "template_name": null,
  "ticket_tco": 260,
  "is_dynamic": false,
  "last_inventory_update": null,
  "status": {
    "id": 3,
    "name": "En taller (demo)"
  },
  "entity": {
    "id": 0,
    "name": "Root entity",
    "completename": "Root entity"
  },
  "manufacturer": {
    "id": 2,
    "name": "Samsung"
  },
  "user": {
    "id": 11,
    "name": "cliente.andina"
  },
  "user_tech": null,
  "location": null,
  "type": null,
  "model": {
    "id": 3,
    "name": "Galaxy A55 5G"
  },
  "group": [],
  "group_tech": [],
  "autoupdatesystem": null,
  "power_supply": null
}
```

### Garantía del equipo R58NDEMO0002

`GET http://127.0.0.1:8090/api.php/v2/Assets/Phone/4/Infocom`

Respuesta (recortada):
```json
{
  "id": 3,
  "itemtype": "Phone",
  "items_id": 4,
  "comment": null,
  "is_recursive": false,
  "date_buy": "2026-03-01",
  "date_use": null,
  "date_order": null,
  "date_delivery": null,
  "date_inventory": null,
  "date_warranty": "2026-03-01",
  "date_decommission": null,
  "warranty_info": "Garantía de fábrica 12 meses (demo).",
  "warranty_value": 0,
  "warranty_duration": 12,
  "order_number": null,
  "delivery_number": null,
  "immo_number": null,
  "invoice_number": null,
  "value": 1600,
  "amortization_type": "0",
  "amortization_time": 0,
  "amortization_coeff": 0,
  "entity": {
    "id": 0,
    "name": "Root entity"
  },
  "budget": null,
  "supplier": null,
  "business_criticity": null
}
```

### Línea de tiempo del ticket 4 (diagnóstico, trabajo, aprobación, solución)

`GET http://127.0.0.1:8090/api.php/v2/Assistance/Ticket/4/Timeline`

Respuesta (recortada):
```json
[
  {
    "type": "Followup",
    "item": {
      "id": 3,
      "itemtype": "Ticket",
      "items_id": 4,
      "content": "DIAGNÓSTICO: batería con 61% de salud; hinchazón leve. Fuera de cobertura por uso (política demo). Presupuesto: S/ 260.00.",
      "is_private": false,
      "date": "2026-09-23T18:41:05+00:00",
      "date_creation": "2026-09-23T18:41:05+00:00",
      "date_mod": "2026-09-23T18:41:05+00:00",
      "timeline_position": 1,
      "source_item_id": 0,
      "source_of_item_id": 0,
      "user": {
        "id": 7,
        "name": "gspn_integration"
      },
      "user_editor": null,
      "request_type": null
    }
  },
  {
    "type": "Task",
    "item": {
      "id": 3,
      "uuid": "db4c8e37-6b83-445b-a85d-8de254c19fd6",
      "content": "TRABAJO REALIZADO: reemplazo de batería (repuesto GH82-DEMO-0202), sellado y prueba de carga.",
      "is_private": false,
      "date": "2026-09-23T18:41:05+00:00",
      "date_creation": "2026-09-23T18:41:05+00:00",
      "date_mod": "2026-09-23T18:41:05+00:00",
      "duration": 2700,
      "planned_begin": null,
      "planned_end": null,
      "state": 2,
      "timeline_position": 1,
      "tickets_id": 4,
      "source_item_id": 0,
      "source_of_item_id": 0,
      "user": {
        "id": 7,
        "name": "gspn_integration"
      },
      "user_editor": null,
      "user_tech": {
        "id": 9,
        "name": "tecnico.demo"
      },
      "group_tech": null,
      "category": null
    }
  },
  {
    "type": "Solution",
    "item": {
      "id": 3,
      "itemtype": "Ticket",
      "items_id": 4,
      "content": "Batería reemplazada. Prueba de carga OK.",
      "status": 2,
      "date_creation": "2026-09-23T18:41:06+00:00",
      "date_mod": "2026-09-23T18:41:06+00:00",
      "date_approval": null,
      "type": null,
      "user": {
        "id": 7,
        "name": "gspn_integration"
      },
      "user_editor": null,
      "approver": null,
      "approval_followup": null
    }
  },
  {
    "type": "Validation",
    "item": {
      "id": 4,
      "requested_approver_type": "User",
      "requested_approver_id": 7,
      "submission_comment": "Presupuesto S/ 260.00 enviado al cliente.",
      "approval_comment": "Cliente aprobó el presupuesto (demo).",
      "status": 3,
      "submission_date": "2026-09-23T18:41:06+00:00",
      "approval_date": "2026-09-23T18:41:06+00:00",
      "timeline_position": 1,
      "tickets_id": 4,
      "requester": {
        "id": 7,
        "name": "gspn_integration"
      },
      "approver": null
    }
  }
]
```

### Costos del ticket 4 (repuestos y mano de obra)

`GET http://127.0.0.1:8090/api.php/v2/Assistance/Ticket/4/Cost`

Respuesta (recortada):
```json
[
  {
    "id": 4,
    "name": "Repuesto: Batería GH82-DEMO-0202",
    "comment": null,
    "date_begin": "2026-09-05T00:00:00+00:00",
    "date_end": "2026-09-05T00:00:00+00:00",
    "duration": 0,
    "cost_time": 0,
    "cost_fixed": 0,
    "cost_material": 190,
    "ticket": {
      "id": 4,
      "name": "Reemplazo de batería Galaxy A55 (orden GSPN-DEMO-000102)"
    },
    "budget": null,
    "entity": {
      "id": 0,
      "name": "Root entity"
    }
  },
  {
    "id": 5,
    "name": "Mano de obra: 0.75 h taller",
    "comment": null,
    "date_begin": "2026-09-05T00:00:00+00:00",
    "date_end": "2026-09-05T00:00:00+00:00",
    "duration": 2700,
    "cost_time": 0,
    "cost_fixed": 70,
    "cost_material": 0,
    "ticket": {
      "id": 4,
      "name": "Reemplazo de batería Galaxy A55 (orden GSPN-DEMO-000102)"
    },
    "budget": null,
    "entity": {
      "id": 0,
      "name": "Root entity"
    }
  }
]
```

### Actores del ticket 4 (cliente solicitante, técnico asignado)

`GET http://127.0.0.1:8090/api.php/v2/Assistance/Ticket/4/TeamMember`

Respuesta (recortada):
```json
[
  {
    "role": "requester",
    "name": "cliente.andina",
    "realname": "Paredes (Comercial Andina SAC demo)",
    "firstname": "Luis",
    "display_name": "Paredes (Comercial Andina SAC demo) Luis",
    "id": 11,
    "href": "/front/user.form.php?id=11",
    "type": "User"
  },
  {
    "role": "assigned",
    "name": "tecnico.demo",
    "realname": "Rojas Demo",
    "firstname": "Carla",
    "display_name": "Rojas Demo Carla",
    "id": 9,
    "href": "/front/user.form.php?id=9",
    "type": "User"
  }
]
```

### Buscar ticket por referencia externa GSPN-DEMO-000103

`GET http://127.0.0.1:8090/api.php/v2/Assistance/Ticket?filter=external_id==GSPN-DEMO-000103`

Respuesta (recortada):
```json
[
  {
    "id": 5,
    "name": "Tablet no enciende Galaxy Tab S9 (orden GSPN-DEMO-000103)",
    "content": "Orden externa: GSPN-DEMO-000103\nSíntoma reportado: no enciende ni carga.\nSerie declarada en la orden: R58NDEMO0003\nEquipo fuera de garantía.",
    "is_deleted": false,
    "urgency": 4,
    "impact": 3,
    "priority": 4,
    "actiontime": 0,
    "begin_waiting_date": "2026-09-23T18:41:07+00:00",
    "waiting_duration": 0,
    "resolution_duration": 0,
    "close_duration": 0,
    "resolution_date": null,
    "date_creation": "2026-09-23T18:41:06+00:00",
    "date_mod": "2026-09-23T18:41:07+00:00",
    "date": "2026-09-10T16:15:00+00:00",
    "date_solve": null,
    "date_close": null,
    "type": 1,
    "external_id": "GSPN-DEMO-000103",
    "take_into_account_date": "2026-09-23T18:41:06+00:00",
    "take_into_account_duration": 1131966,
    "sla_waiting_duration": 0,
    "ola_waiting_duration": 0,
    "ola_ttr_begin_date": null,
    "ola_tto_begin_date": null,
    "internal_resolution_date": null,
    "internal_take_into_account_date": null,
    "global_validation": 4,
    "status": {
      "id": 4,
      "name": "Pending"
    },
    "user_recipient": {
      "id": 7,
      "name": "gspn_integration"
    },
    "user_editor": {
      "id": 7,
      "name": "gspn_integration"
    },
    "category": {
      "id": 2,
      "name": "Servicio técnico Samsung (demo)"
    },
    "location": null,
    "request_type": {
      "id": 1,
      "name": "Helpdesk"
    },
    "sla_ttr": null,
    "sla_tto": null,
    "ola_ttr": null,
    "ola_tto": null,
    "sla_level_ttr": null,
    "ola_level_ttr": null,
    "entity": {
      "id": 0,
      "name": "Root entity",
      "completename": "Root entity"
    },
    "costs": [
      {
        "id": 6
      }
    ],
    "team": [
      {
        "role": "requester",
        "name": "cliente.jmendoza",
        "realname": "Mendoza Demo",
        "firstname": "Jorge",
        "display_name": "Mendoza Demo Jorge",
        "id": 12,
        "href": "/front/user.form.php?id=12",
        "type": "User"
      },
      {
        "role": "assigned",
        "name": "tecnico.demo",
        "realname": "Rojas Demo",
        "firstname": "Carla",
        "display_name": "Rojas Demo Carla",
        "id": 9,
        "href": "/front/user.form.php?id=9",
        "type": "User"
      }
    ]
  }
]
```

### Equipo vinculado al ticket 5 (API heredada; la v2.3 no expone Item_Ticket)

`GET http://127.0.0.1:8090/apirest.php/Ticket/5/Item_Ticket`

Respuesta (recortada):
```json
[
  {
    "id": 4,
    "itemtype": "Phone",
    "items_id": 5,
    "tickets_id": 5,
    "links": [
      {
        "rel": "Phone",
        "href": "http://localhost/api.php/v1/Phone/5"
      },
      {
        "rel": "Ticket",
        "href": "http://localhost/api.php/v1/Ticket/5"
      }
    ]
  }
]
```

Cabecera: `Session-Token: <session_token>` (obtenido con `GET /apirest.php/initSession` y `Authorization: user_token <token>`).

### Equipo R58NDEMO0003

`GET http://127.0.0.1:8090/api.php/v2/Assets/Phone/5`

Respuesta (recortada):
```json
{
  "id": 5,
  "name": "SM-X710-DEMO-003",
  "comment": "Equipo ficticio de la demo (serie inventada).",
  "is_recursive": false,
  "contact": null,
  "contact_num": null,
  "serial": "R58NDEMO0003",
  "otherserial": "IMEI-350000000000033",
  "is_deleted": false,
  "date_creation": "2026-09-23T18:41:04+00:00",
  "date_mod": "2026-09-23T18:41:06+00:00",
  "uuid": null,
  "brand": null,
  "number_line": null,
  "have_headset": false,
  "have_hp": false,
  "is_global": false,
  "is_template": false,
  "template_name": null,
  "ticket_tco": 640,
  "is_dynamic": false,
  "last_inventory_update": null,
  "status": {
    "id": 3,
    "name": "En taller (demo)"
  },
  "entity": {
    "id": 0,
    "name": "Root entity",
    "completename": "Root entity"
  },
  "manufacturer": {
    "id": 2,
    "name": "Samsung"
  },
  "user": {
    "id": 12,
    "name": "cliente.jmendoza"
  },
  "user_tech": null,
  "location": null,
  "type": null,
  "model": {
    "id": 4,
    "name": "Galaxy Tab S9"
  },
  "group": [],
  "group_tech": [],
  "autoupdatesystem": null,
  "power_supply": null
}
```

### Garantía del equipo R58NDEMO0003

`GET http://127.0.0.1:8090/api.php/v2/Assets/Phone/5/Infocom`

Respuesta (recortada):
```json
{
  "id": 4,
  "itemtype": "Phone",
  "items_id": 5,
  "comment": null,
  "is_recursive": false,
  "date_buy": "2024-05-10",
  "date_use": null,
  "date_order": null,
  "date_delivery": null,
  "date_inventory": null,
  "date_warranty": "2024-05-10",
  "date_decommission": null,
  "warranty_info": "Garantía vencida (demo).",
  "warranty_value": 0,
  "warranty_duration": 12,
  "order_number": null,
  "delivery_number": null,
  "immo_number": null,
  "invoice_number": null,
  "value": 2300,
  "amortization_type": "0",
  "amortization_time": 0,
  "amortization_coeff": 0,
  "entity": {
    "id": 0,
    "name": "Root entity"
  },
  "budget": null,
  "supplier": null,
  "business_criticity": null
}
```

### Línea de tiempo del ticket 5 (diagnóstico, trabajo, aprobación, solución)

`GET http://127.0.0.1:8090/api.php/v2/Assistance/Ticket/5/Timeline`

Respuesta (recortada):
```json
[
  {
    "type": "Followup",
    "item": {
      "id": 4,
      "itemtype": "Ticket",
      "items_id": 5,
      "content": "DIAGNÓSTICO: placa base con daño en circuito de carga (PMIC). Fuera de garantía. Presupuesto: S/ 640.00. Se solicita aprobación del cliente.",
      "is_private": false,
      "date": "2026-09-23T18:41:06+00:00",
      "date_creation": "2026-09-23T18:41:06+00:00",
      "date_mod": "2026-09-23T18:41:06+00:00",
      "timeline_position": 1,
      "source_item_id": 0,
      "source_of_item_id": 0,
      "user": {
        "id": 7,
        "name": "gspn_integration"
      },
      "user_editor": null,
      "request_type": null
    }
  },
  {
    "type": "Validation",
    "item": {
      "id": 5,
      "requested_approver_type": "User",
      "requested_approver_id": 7,
      "submission_comment": "Presupuesto S/ 640.00 enviado al cliente.",
      "approval_comment": "Cliente rechaza el presupuesto; solicita devolución sin reparar (demo).",
      "status": 4,
      "submission_date": "2026-09-23T18:41:06+00:00",
      "approval_date": "2026-09-23T18:41:06+00:00",
      "timeline_position": 1,
      "tickets_id": 5,
      "requester": {
        "id": 7,
        "name": "gspn_integration"
      },
      "approver": null
    }
  }
]
```

### Costos del ticket 5 (repuestos y mano de obra)

`GET http://127.0.0.1:8090/api.php/v2/Assistance/Ticket/5/Cost`

Respuesta (recortada):
```json
[
  {
    "id": 6,
    "name": "Presupuesto: Placa base GH82-DEMO-0303 (no ejecutado)",
    "comment": null,
    "date_begin": "2026-09-10T00:00:00+00:00",
    "date_end": "2026-09-10T00:00:00+00:00",
    "duration": 0,
    "cost_time": 0,
    "cost_fixed": 120,
    "cost_material": 520,
    "ticket": {
      "id": 5,
      "name": "Tablet no enciende Galaxy Tab S9 (orden GSPN-DEMO-000103)"
    },
    "budget": null,
    "entity": {
      "id": 0,
      "name": "Root entity"
    }
  }
]
```

### Actores del ticket 5 (cliente solicitante, técnico asignado)

`GET http://127.0.0.1:8090/api.php/v2/Assistance/Ticket/5/TeamMember`

Respuesta (recortada):
```json
[
  {
    "role": "requester",
    "name": "cliente.jmendoza",
    "realname": "Mendoza Demo",
    "firstname": "Jorge",
    "display_name": "Mendoza Demo Jorge",
    "id": 12,
    "href": "/front/user.form.php?id=12",
    "type": "User"
  },
  {
    "role": "assigned",
    "name": "tecnico.demo",
    "realname": "Rojas Demo",
    "firstname": "Carla",
    "display_name": "Rojas Demo Carla",
    "id": 9,
    "href": "/front/user.form.php?id=9",
    "type": "User"
  }
]
```
