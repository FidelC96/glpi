# Mapeo inicial GLPI → Odoo (borrador para el conector)

Sentido: GLPI (simulador del sistema externo) es la fuente de la orden de servicio; Odoo recibe y
concilia. Nada se factura automáticamente. Versiones: GLPI 11.0.9, API v2.3; Odoo 18/19 (modelos
estándar, sin módulo custom todavía).

## Campos

| Concepto | Origen en GLPI (API v2 salvo indicación) | Destino en Odoo | Estado / observación |
|---|---|---|---|
| Referencia externa | `Ticket.external_id` (columna `externalid`) | `sale.order.client_order_ref` o campo custom `x_gspn_ref` en `sale.order` / `account.move.ref` | **Nativo en GLPI**. Clave de idempotencia del conector. |
| Nº de ticket GLPI | `Ticket.id` | campo custom `x_glpi_ticket_id` | Nativo. Guardar también para trazabilidad. |
| Cliente | `Ticket` → `TeamMember` con `role = requester` → `User` (`realname`, `firstname`, `phone`) | `res.partner` | Nativo pero **débil**: GLPI modela personas como usuarios, sin RUC/DNI ni dirección fiscal. Requiere tabla de correspondencia `User.id` ↔ `partner_id` en el conector (o `registration_number` de User para el documento de identidad). |
| Empresa del cliente | no existe como tal (opcional: `Entity` o `Group`) | `res.partner` padre (`parent_id`) | **No nativo**. En la demo va en `realname`. Recomendación: usar sub-entidades de GLPI por cliente empresa si se necesita. |
| Equipo | `Item_Ticket` (API heredada) → `Phone` (`name`, `model.name`, `manufacturer.name`) | `product.product` (plantilla por modelo) + `stock.lot` | El enlace ticket-equipo **no tiene ruta de escritura ni lectura en la API v2.3**; se lee con `GET /apirest.php/Ticket/{id}/Item_Ticket`. |
| Serie | `Phone.serial` (IMEI en `Phone.otherserial`) | `stock.lot.name` | Nativo. Dato crítico: si difiere del lote Odoo, la factura se bloquea (caso 000102). |
| Diagnóstico | primer `Followup.content` del `Timeline` | `helpdesk.ticket.description` o nota en la orden (`note`) | Nativo pero **por convención**: GLPI no distingue "diagnóstico" de otros seguimientos. Convención demo: el seguimiento empieza por `DIAGNÓSTICO:`. |
| Servicio / trabajo realizado | `TicketTask.content` + `duration` (segundos) | línea de `sale.order` con producto servicio; `duration` → cantidad en horas | Nativo por convención (`TRABAJO REALIZADO:`). |
| Repuestos | `TicketCost` con `cost_material > 0` (`name`, `cost_material`) | líneas de `sale.order` con producto almacenable; `name` lleva el código de repuesto | **Parcial**: GLPI no tiene catálogo de repuestos ligado al ticket; `name` es texto libre. Alternativa: `Consumable`/`CartridgeItem` de GLPI, no usada. |
| Mano de obra | `TicketCost` con `cost_fixed > 0`; horas en `duration` | línea de servicio | Igual que arriba. `cost_time` (tarifa por hora) se deja en 0 en la demo. |
| Importe | suma de `cost_material + cost_fixed + cost_time*horas` de `/Cost` | `amount_untaxed` esperado | **Sin moneda ni impuestos en GLPI**. La moneda (PEN) y el IGV se definen en Odoo. |
| Garantía | `Infocom` del equipo: `date_warranty`, `warranty_duration` (meses), `warranty_info` | campo custom en `stock.lot` (`x_warranty_end`) o `product.template` + regla de precio | Nativo en GLPI. La cobertura real (daño físico excluido) solo está en texto (`warranty_info`). |
| Técnico | `TeamMember` con `role = assigned` → `User` | `hr.employee` / `res.users` | Nativo. Correspondencia por username. |
| Fecha de servicio | `Ticket.date` (apertura), `date_solve`, `date_close` | `date_order`, `commitment_date` | Nativo. Zona horaria: la API v2 devuelve ISO 8601 con offset. |
| Estado del servicio | `Ticket.status` + `Ticket.global_validation` | estado de la orden/factura según `docs/ESTADOS.md` | Nativo. La regla "aprobado" es del conector, no de GLPI. |
| Aprobación (quién y cuándo) | `TicketValidation.status`, `approval_date`, `approval_comment`, `approver` | campos custom de auditoría en la orden | Nativo. En la demo `approver` viene `null` porque la validación la resuelve la propia cuenta de integración. |
| Motivo de pendiente | `PendingReason` vía `GET /apirest.php/Ticket/{id}/PendingReason_Item` | etiqueta/estado en Odoo | Solo lectura en API v2 (`/Assistance/Ticket/{id}/PendingReason`); escritura por API heredada. |
| Solución | `Timeline/Solution.content` | nota de cierre | Nativo. |

## Reglas del conector propuestas

1. Idempotencia por `external_id`: una orden Odoo por referencia externa; reintentos actualizan, no duplican.
2. Bloqueo de factura: solo habilitar la factura cuando estado demo = APROBADO **y** `Phone.serial == stock.lot.name`.
   Si difiere, crear actividad/alerta en Odoo con ambas series; nunca corregir automáticamente.
3. Nada se emite: el conector prepara `sale.order` en borrador; la confirmación y la factura son manuales.
4. Trazabilidad: guardar `ticket_id`, `date_mod` de GLPI y hash de los costos para detectar cambios posteriores.

## Campos que no existen de forma nativa o requieren configuración

- Documento de identidad / RUC del cliente: usar `User.registration_number` o tabla de correspondencia.
- Empresa del cliente: sub-entidad o grupo de GLPI (configuración), o campo custom en el conector.
- Catálogo de repuestos con código: `TicketCost.name` es texto libre; se necesita convención de prefijo o el módulo de consumibles.
- Moneda, impuestos, cobertura de garantía por tipo de daño: no existen en GLPI; se definen en Odoo.
- Enlace equipo-ticket y motivo de pendiente: sin escritura en API v2.3 (usar API heredada o esperar versión posterior).
- Estado "validado"/"facturable": no existe; se deriva de `status` + `global_validation` + coincidencia de serie.
