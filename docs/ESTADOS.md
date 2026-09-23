# Estados: GLPI real vs estados de la demo

GLPI **no** tiene un estado nativo llamado "validado", "aprobado" ni "facturable". Lo que sí
existe en GLPI 11 (verificado en `src/CommonITILObject.php` y `src/CommonITILValidation.php`
de la imagen `glpi/glpi:11.0.9`):

## Estado del ticket (`Ticket.status`)

| id | Nombre en GLPI | Uso en la demo |
|---|---|---|
| 1 | New | recepción del equipo |
| 2 | Processing (assigned) | técnico asignado, en diagnóstico o reparación |
| 3 | Processing (planned) | no se usa |
| 4 | Pending | esperando decisión del cliente (con motivo de pendiente) |
| 5 | Solved | trabajo terminado (GLPI lo fija solo al registrar una solución) |
| 6 | Closed | entregado al cliente |
| 10 | Approval | esperando una validación interna (no se usa en la demo) |

## Estado de aprobación (`Ticket.global_validation`, calculado a partir de las validaciones)

| id | Nombre en GLPI | Uso en la demo |
|---|---|---|
| 1 | None | sin presupuesto enviado |
| 2 | Waiting | presupuesto enviado, sin respuesta |
| 3 | Accepted | cliente/sistema externo aprobó |
| 4 | Refused | cliente/sistema externo rechazó |

La "aprobación" se modela con una **validación de ticket** (`TicketValidation`). En la demo la
solicita y la resuelve la misma cuenta de integración (simula que el sistema externo registra la
decisión del cliente). En un flujo real la resolvería un aprobador humano o llegaría del sistema
externo.

## Correspondencia con los estados de la demo (regla del conector)

| Estado demo | Regla sobre datos GLPI | Ticket de ejemplo |
|---|---|---|
| APROBADO | `status` ∈ {Solved, Closed} **y** `global_validation` = Accepted | GSPN-DEMO-000101, GSPN-DEMO-000102 |
| PENDIENTE | `status` = Pending **y** `global_validation` ∈ {None, Waiting} | (no hay ejemplo cargado; se obtiene cambiando la validación de 000103 a Waiting) |
| RECHAZADO | `global_validation` = Refused (cualquier `status`) | GSPN-DEMO-000103 |
| REVISAR | cualquier otra combinación | — |

La factura en Odoo solo se **habilitaría** (no se emite) cuando el estado demo es APROBADO y
además la serie del equipo en GLPI coincide con el lote/serie en Odoo. Por eso
GSPN-DEMO-000102 queda bloqueado aunque esté aprobado.

## Otros estados usados

- **Estado del equipo** (`Phone.status`, desplegable `State`): valores creados por la demo
  "Operativo (demo)" y "En taller (demo)". No vienen de fábrica; se crean con el cargador.
- **Estado de la tarea** (`TicketTask.state`): 0 = información, 1 = por hacer, 2 = hecho. La demo
  registra el trabajo realizado con `state = 2`.
- **Motivo de pendiente** (`PendingReason`): "Esperando aprobación del cliente (demo)", creado por
  el cargador y asociado al ticket vía API heredada (`PendingReason_Item`).
