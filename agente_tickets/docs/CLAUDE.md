# CLAUDE.md — Agente de triage de tickets de soporte

## 1. Qué es esto (la rebanada)

Agente LLM + verificador que responde preguntas del coordinador de soporte de TI sobre tickets pendientes de un ERP compartido por múltiples empresas.

## 2. El caso y quién lo usa

**Quién:** Coordinadora de soporte de TI.

**Caso:** Hoy revisa manualmente un Excel para identificar tickets críticos (por antigüedad), dependencias con proveedores y carga por técnico. El agente automatiza esa revisión consultando el ERP, responde en 2 minutos y un verificador valida que los números sean exactos.

## 3. Frase y línea roja

**Promesa:** Dada una pregunta de la coordinadora sobre tickets pendientes, mi agente responde con los IDs, días pendientes y prioridad de los tickets que aplican.

**Éxito:** En el golden set los números coinciden con los datos, no inventa tickets ni muestra datos sensibles.

**Línea roja (prohibiciones):** El agente NUNCA cierra, reasigna ni modifica tickets. Eso lo decide solo la coordinadora. El agente es de solo lectura.

## 4. Qué decide el modelo y qué ejecuta el código

**El modelo decide:**
- Qué herramienta usar (pero solo de las 4 permitidas en lista blanca)
- Cómo redactar en el template fijo (tabla: ID, Empresa, Días, Prioridad)

**El código ejecuta:**
- Valida que la herramienta solicitada esté en lista blanca (buscar_tickets, calcular_prioridades, tickets_por_proveedor, carga_por_tecnico); rechaza si no está
- Delega al verificador con regla fija: siempre si se encontraron >1 ticket (no es opcional)
- Lectura del JSON de 153 tickets
- Cálculos de antigüedad (hoy - fecha_apertura)
- Aplicación de reglas de prioridad
- Template de salida fijo: tabla con columnas ID, Empresa (anonimizada), Días pendientes, Prioridad

**Regla de prioridad (en código):**
- Baja: ≤5 días abiertos
- Media: ≤15 días abiertos
- Alta: ≤30 días abiertos
- Crítica: >30 días abiertos

## 5. Herramientas (servidor MCP)

**Servidor MCP "tickets"** (Python, local, solo lectura)

Fuente: JSON con 153 tickets anonimizados.

**4 herramientas (todas de solo lectura):**

1. `buscar_tickets(empresa, estado, id)` — filtra por empresa (A-G), estado (En espera/En curso), o ID específico. Devuelve detalle (id, empresa, estado, categoría, fecha, técnico, grupo, título, seguimiento). Usado por orquestador y verificador.

2. `calcular_prioridades(empresa opcional)` — tickets en espera con días_pendientes y prioridad (Baja ≤5 / Media ≤15 / Alta ≤30 / Crítica >30), ordenado antiguo→nuevo. Usado por orquestador y verificador.

3. `tickets_por_proveedor(proveedor)` — tickets abiertos escalados a Proveedor 1 o 2. Usado por orquestador.

4. `carga_por_tecnico()` — sin args, tickets en espera por técnico y por grupo. Usado por orquestador.

**Descartadas:** cerrar_ticket y asignar_ticket (violan la línea roja de solo lectura).

## 6. Subagente: Verificador

**Rol:** Segunda firma de solo lectura que valida exactitud de IDs, antigüedades y sumas del borrador del orquestador.

**Herramientas:** buscar_tickets, calcular_prioridades (mismas del orquestador, solo lectura).

**Flujo (secuencial, no paralelo):** Orquestador genera borrador → Verificador recibe borrador → Verifica cada dato con sus herramientas → Entrega {validado: true/false, errores: []}.

**Tarea autocontenida:** Recibe el borrador sin ver la conversación original del coordinador. Valida: cada ID existe, cada días_pendientes es exacto, cada suma por técnico cierra.

**Por qué subagente y no herramienta:** revisar es un rol distinto a responder; con contexto limpio no repite los sesgos del orquestador. Es la segunda firma antes de que la coordinadora vea un número.

**Costo:** estimado ~2 llamadas MCP + 1 inferencia (PENDIENTE medir con usage_log.jsonl).

## 7. Contexto y memoria

PENDIENTE

## 8. Guardrails, frenos y aprobación humana

**Guardrails de entrada:**
1. Bloquea frases como "ignora tus instrucciones", "olvida que...", "haz caso omiso"
2. Bloquea pedidos explícitos de cerrar, borrar o reasignar tickets
3. Rechaza con: "No puedo ejecutar esa acción. Solo puedo consultar y reportar."

**Guardrails de salida:**
1. Bloquea IDs que no provengan directamente de una herramienta MCP (rechaza IDs construidos o adivinados)
2. Bloquea nombres no anonimizados (empresas, técnicos, usuarios) y ofusca o reemplaza por seudónimos si son sensibles

**Freno (máximo 6 vueltas):**
- Si el agente alcanza 6 llamadas a herramientas sin completar, responde con lo que tiene y avisa: "No pude completar el análisis en el tiempo límite. Aquí está lo que tengo hasta ahora: [datos incompletos]"
- El verificador siempre intenta firmar incluso con datos parciales

**Verificador:**
- Rechaza si faltan IDs o los números no cierran
- Requiere corrección antes de respuesta final

## 9. Cómo sé que funcionó y cómo sé que falló

**Funcionó:**
- Golden set: coordinadora hace 3 preguntas tipo, el agente responde en <2 min, cada número coincide con datos JSON
- Verificador valida sin errores
- No inventa tickets ni duplica IDs
- No filtra por datos sensibles (no aparecen en respuesta)

**Falló:**
- Números no cuadran con el JSON
- Inventa un ticket que no existe
- Muestra datos sensibles sin ofuscación
- El verificador rechaza por discrepancia
- Propone una acción prohibida (cerrar, reasignar)

## 10. PENDIENTES

- Estructuración exacta de datos del JSON (schema de los 153 tickets)
- Selección final de preguntas del golden set (¿cuáles 3?)
- Implementación del servidor MCP en Python (stub vs. funcional)
- Prompt del verificador (criterios exactos de validación)
- Umbrales de "datos sensibles" para ofuscación
- Formato de respuesta estructurada (tabla, JSON, Markdown)

## 11. Bitácora (fecha, qué cambió y por qué)

**2026-11-11 (entrada):** Definición completa de caso, herramientas, reglas de prioridad, guardrails y verificador. Se congelaron requisitos de "solo lectura", "sin modificaciones" y "2 minutos max".

**2026-11-11 (correcciones):**
- Sección 4: Aclarado que el modelo decide *herramienta, delegación, redacción* y el código calcula prioridades (no al revés)
- Sección 8: Guardrails de entrada (bloquea "ignora instrucciones", cierres, reasignaciones) y guardrails de salida (IDs solo de herramientas, anonimización obligatoria)
- Freno: máximo 6 vueltas; al tocarlo, responde con datos incompletos y avisa

**2026-11-11 (matriz decide-o-ejecuta aprobada):**
- Sección 4: MODELO elige herramienta, pero CÓDIGO valida en lista blanca de 4 (evita que el agente invente herramientas o escape)
- Sección 4: CÓDIGO delega al verificador con regla fija (siempre si >1 ticket encontrado), no es discreción del modelo (garantiza segunda firma)
- Sección 4: MODELO redacta en template fijo (tabla: ID, Empresa, Días, Prioridad) para consistencia y auditoría fácil
- Todas las filas de la matriz en decide-o-ejecuta.md marcadas como aprobadas

**2026-11-11 (herramientas aprobadas):**
- Las 4 herramientas MCP confirmadas: buscar_tickets (SÍ), calcular_prioridades (SÍ), tickets_por_proveedor (SÍ), carga_por_tecnico (SÍ)
- buscar_tickets y calcular_prioridades usadas por orquestador Y verificador (segunda firma)
- Descartadas cerrar_ticket y asignar_ticket (violan línea roja de solo lectura)
- Análisis: ninguna es genérica disfrazada; resuelven caso normal y caso feo

**2026-11-11 (subagente Verificador definido):**
- Rol: segunda firma de solo lectura, contexto limpio, no ve conversación del coordinador
- Herramientas: buscar_tickets + calcular_prioridades
- Flujo: secuencial (NO paralelo): orquestador → borrador → Verificador valida → {validado, errores}
- Tarea autocontenida con ejemplo TK-002
