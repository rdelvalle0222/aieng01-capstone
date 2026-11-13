# Agente de Triage de Tickets MDA (capstone)

## El caso (las 3 líneas para el facilitador)

- **Quién lo usa:** el coordinador de soporte de TI que atiende los tickets del ERP de varias empresas.
- **Qué le pide al agente:** que le diga qué tickets abiertos son críticos, cuáles dependen de un proveedor externo y cómo está repartida la carga entre los técnicos, y que le arme un informe corto de pendientes.
- **Cómo se sabe que lo resolvió:** el informe lista los tickets correctos (los mismos que salen al calcularlos directo sobre los datos), con su prioridad y días pendientes, sin inventar tickets y sin mostrar datos sensibles.

> Datos: 42 tickets **simulados** en `datos/tickets.json` (empresas, técnicos y proveedores inventados).
> No se usa el Excel real de la empresa.

## Herramientas del servidor MCP (`server.py`, servidor "tickets")

Salen de las funciones del proyecto Organizador_MDA. Todas calculan los días con
`fecha_corte` del JSON (no con la fecha de hoy), para que los evals den siempre lo mismo.

| Herramienta | Qué hace | Viene de |
|---|---|---|
| `buscar_tickets(empresa?, estado?, id?)` | Lista tickets filtrados, o el detalle de uno | `lectura_excel.py`, `analisis_tickets.py` |
| `calcular_prioridades(empresa?)` | Tickets en espera con días pendientes y prioridad (Baja ≤5, Media ≤15, Alta ≤30, Crítica >30) | `prioridades.py` |
| `tickets_por_proveedor(proveedor)` | Tickets abiertos cuyo seguimiento menciona al proveedor | `historial_soluciones.py` |
| `carga_por_tecnico()` | Tickets en espera por técnico y por grupo | `responsables.py` |

En el agente se llaman `mcp__tickets__buscar_tickets`, `mcp__tickets__calcular_prioridades`, etc.

## Subagente

**`verificador`**: antes de entregar el informe, contrasta cada ID y número con los datos.
- Herramientas: solo `mcp__tickets__buscar_tickets` y `mcp__tickets__calcular_prioridades`.
- Responde: `OK`, o qué no cuadra y por qué.
- Por qué aquí: evita que el orquestador invente o mezcle tickets. Tiene un contexto aislado y solo puede leer.

## Guardrails (después del taller)

- **Entrada:** detectar pedidos de modificar datos ("cierra", "borra", "marca como resuelto") y frases de inyección. El agente responde que solo consulta.
- **Salida:** ocultar contraseñas y números de cédula (regex) antes de mostrar la respuesta (caso T-1040).

## Golden set

`golden_set.json`: 10 casos, 3 de ellos adversariales.
- g08: inyección escondida en un ticket (T-1041).
- g09: dato sensible (T-1040).
- g10: fuera de alcance ("cierra todos los tickets").

Hay que pasarlo al formato que trae el `golden_set.json` de la plantilla.
