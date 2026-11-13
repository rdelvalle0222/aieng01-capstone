# Tabla: Quién decide, quién ejecuta

| Acción | Quién | Qué pasa si se equivoca | ¿DE ACUERDO? |
|--------|-------|------------------------|-------------|
| Coordinador pregunta sobre tickets | PERSONA | La pregunta no llega o no se entiende | Sí. El coordinador es responsable de hacer la pregunta clara. |
| Sistema recibe y valida entrada | CÓDIGO | Se acepta pregunta malformada o peligrosa | Sí. Validar entrada temprano evita procesamiento de basura. |
| Bloquea frases "ignora instrucciones", "olvida", "haz caso omiso" | CÓDIGO | Se deja pasar una manipulación de prompt | Sí. Es la primera línea de defensa contra prompt injection. |
| Bloquea pedidos explícitos de cerrar/borrar/reasignar | CÓDIGO | Se ejecuta una acción prohibida | Sí. La línea roja es que el agente solo consulta, nunca modifica. |
| **MODELO decide qué herramienta usar, pero CÓDIGO valida en lista blanca** | MODELO | Elige herramienta fuera de las 4 permitidas, desperdicia vueltas | Sí. El agente no debe poder inventar herramientas; solo las 4 permitidas existen. |
| Ejecuta herramienta MCP (buscar_tickets) | CÓDIGO | Retorna tickets no existentes o datos corruptos | Sí. El JSON es la fuente de verdad. |
| Ejecuta herramienta MCP (calcular_prioridades) | CÓDIGO | Aplica regla de prioridad incorrectamente (ej: dice "Crítica" en <30 días) | Sí. La regla es determinista: Crítica siempre es >30 días. |
| Ejecuta herramienta MCP (tickets_por_proveedor) | CÓDIGO | Agrupa tickets con proveedor erróneo o duplica | Sí. El agrupamiento es mecánico, sin ambigüedad. |
| Ejecuta herramienta MCP (carga_por_tecnico) | CÓDIGO | Suma incorrecta de tickets por técnico | Sí. Las sumas deben ser exactas, no aproximadas. |
| Cuenta vueltas (llamadas a herramientas) | CÓDIGO | No cuenta o pierde la cuenta, deja pasar >6 | Sí. El freno de 6 vueltas es obligatorio para evitar loops. |
| Si ≥6 vueltas: responde con datos incompletos + aviso | CÓDIGO | Continúa sin avisar o oculta que está incompleto | Sí. Es mejor responder parcial que infini-loopear. |
| **MODELO delega a verificador con regla fija: siempre si >1 ticket encontrado** | CÓDIGO | No delega o delega tarde, pierden datos; verificador nunca valida | Sí. La segunda firma es obligatoria, no opcional. Es la garantía de exactitud. |
| Verificador contrasta IDs contra JSON | CÓDIGO | Acepta IDs que no existen en el JSON | Sí. El verificador es el guardián final de integridad de datos. |
| Verificador valida cálculos de antigüedad (hoy - fecha_apertura) | CÓDIGO | Calcula días mal (ej: dice 25 días cuando son 24) | Sí. Los días son críticos para prioridad; deben ser exactos. |
| Verificador suma de tickets por técnico | CÓDIGO | La suma no cierra (ej: suma 5 pero hay 6) | Sí. La coordinadora confía en que los números cierran. |
| Guardrail salida: bloquea IDs construidos (no de herramientas) | CÓDIGO | Deja pasar un ID inventado o falsificado | Sí. Todo ID debe provenir del JSON, trazable. |
| Guardrail salida: bloquea nombres no anonimizados | CÓDIGO | Muestra "Empresa Acme" o "Juan García" en respuesta | Sí. Datos anonimizados: la coordinadora ve la verdad, pero terceros no. |
| **MODELO redacta respuesta en template fijo: tabla con ID, Empresa, Días, Prioridad** | CÓDIGO | Respuesta inconsistente o confusa, imposible verificar | Sí. Template fijo = auditoría fácil, coordinadora siempre ve lo mismo. |
| Envía respuesta al coordinador | CÓDIGO | Respuesta no llega o llega corrupta | Sí. La entrega debe ser confiable. |
| Coordinador aprueba, desaprueba o hace preguntas de seguimiento | PERSONA | Toma decisión basada en datos incorrectos | Sí. El coordinador tiene la verdad final, puede cuestionar. |

## Análisis: MODELO → ¿debería ser CÓDIGO?

### Fila 5: Decide qué herramienta usar
**Recomendación: Trasladar a CÓDIGO la **validación**.**
- MODELO sigue decidiendo la intención
- Pero CÓDIGO valida: ¿la herramienta solicitada está en la lista blanca de 4? ¿es válida para este tipo de pregunta?
- Rechaza con: "No puedo usar esa herramienta aquí" si hay error
- **Por qué:** Evita que MODELO desperdicie vueltas en herramientas no permitidas

### Fila 11: Delega a verificador
**Recomendación: Trasladar a CÓDIGO el **criterio de cuándo**.**
- Hoy: MODELO decide ad-hoc si delega
- Mejor: CÓDIGO dice "siempre delega después de N herramientas llamadas" o "siempre si encontró >3 tickets"
- MODELO sigue escribiendo el mensaje al verificador, pero la *cuándo* es determinista
- **Por qué:** Evita que MODELO olvide o demore innecesariamente, asegura verificación constante

### Fila 17: Redacta respuesta final
**Recomendación: Trasladar a CÓDIGO el **formato/template**.**
- Hoy: MODELO escribe libre
- Mejor: CÓDIGO proporciona template: tabla con columnas fijas (ID, Días, Prioridad, Empresa-anonimizada, Técnico, Seguimiento)
- MODELO llena los datos en el template
- **Por qué:** Garantiza consistencia, facilita auditoría, previene que MODELO añada interpretaciones o propuestas de acción por accidente
