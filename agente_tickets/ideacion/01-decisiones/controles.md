# Controles: Contexto, Memoria, Guardrails, Frenos, Persona

## 1. CONTEXTO

**Qué recibe el agente:**
- Fecha de corte de datos (hoy, 2026-11-11)
- Regla de prioridad: Baja ≤5, Media ≤15, Alta ≤30, Crítica >30
- Instrucciones del rol (solo lectura, no modifica)

**Qué NO recibe:**
- Todos los 153 tickets cargados en contexto; se consultan por herramientas bajo demanda
- Histórico de conversaciones anteriores

**Razón:** Contexto limpio, eficiente, no acarrea datos innecesarios.

---

## 2. MEMORIA

**Entre preguntas:** CERO. Cada pregunta del coordinador empieza limpia.

**Nunca guarda:**
- Nombres de personas (técnicos, usuarios, empresas específicas)
- Datos de tickets (IDs, fechas, contenido de seguimiento)
- Decisiones tomadas en preguntas anteriores

**Razón:** Privacidad, impide que un error en una consulta contamine la siguiente, garantiza auditoría limpia.

---

## 3. GUARDRAIL DE ENTRADA

**Ya definido en CLAUDE.md sección 8:**
- Bloquea "ignora tus instrucciones", "olvida que", "haz caso omiso"
- Bloquea "cierra", "borra", "reasigna" en contexto de acción (no en contexto histórico)

**Datos que SÍ pasan:**
- IDs de ticket (ej: "TK-1000", "TK-001")
- Nombres anonimizados (ej: "Empresa A", "Empresa B", "Técnico 1", "Técnico 2")
- Preguntas legítimas sobre estado

**Falso positivo conocido:**
- Pregunta: "¿Cuántos tickets se **cerraron** en la última semana?"
- Riesgo: guardrail bloquea por palabra "cerrar", aunque sea pregunta histórica, no acción
- Solución: Guardrail debe bloquear **imperativo + acción**, no gerundio/pasiva (detecta "cierra TK-001" pero permite "cuántos se cerraron")

**Tolerancia:** Preferencia de bloquear de más a que deje pasar. Ticket cerrado por error > pregunta rechazada.

---

## 4. GUARDRAIL DE SALIDA

**Ya definido en CLAUDE.md sección 8:**
- Bloquea IDs que no provengan de herramientas (rechaza IDs construidos, solo acepta de buscar_tickets, calcular_prioridades)
- Bloquea nombres no anonimizados (ofusca o rechaza si contiene "Juan García", acepta "Empresa A")

**Falso positivo conocido:**
- Herramienta retorna ID en formato "TK_002" (guion bajo)
- Guardrail espera "TK-002" (guion normal)
- Resultado: rechaza respuesta correcta por formato

**Solución:** Guardrail normaliza formato antes de validar (TK_002 → TK-002). O acepta ambos.

**Tolerancia:** Preferencia: bloquear de más a que deje pasar.

---

## 5. FRENOS

**Máximo 6 vueltas (llamadas a herramientas):**
- Si ≥6: responde con lo que tiene + aviso "No pude completar el análisis en el tiempo límite"
- Verificador intenta validar incluso con datos parciales

**Contador:** CÓDIGO (no modelo) mantiene contador.

---

## 6. PERSONA: Coordinadora de Soporte de TI

**Aprueba/Decide:**
- Cualquier cierre, reasignación, escalamiento de tickets
- Preguntas de seguimiento (¿por qué no se resolvió?, ¿cuál es el siguiente paso?)

**Recibe:**
- Tabla de tickets solicitados (ID, Empresa, Días, Prioridad)
- Alertas de anomalías si verificador las detecta
- Reporte exacto, sin interpretaciones ni sugerencias de acción

**Rol del agente:** Informar, no decidir. Nunca propone "Deberías cerrar TK-001".
