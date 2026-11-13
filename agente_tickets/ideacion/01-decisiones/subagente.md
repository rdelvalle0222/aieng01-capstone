# Subagente Verificador

## Definición

**Rol:** Segunda firma de solo lectura que valida exactitud de IDs, antigüedades (días_pendientes) y sumas antes de que la respuesta llegue al coordinador.

**Herramientas:** 
- `buscar_tickets(id)` — obtiene ticket original y valida que existe
- `calcular_prioridades(empresa)` — recalcula días_pendientes desde fecha_apertura

**Flujo:** Orquestador genera borrador → Verificador recibe borrador + datos JSON → Verifica cada dato → Aprueba o rechaza con errores específicos.

**Formato de entrega:** 
```json
{
  "validado": true/false,
  "errores": [
    {"campo": "id", "ticket": "TK-XXX", "encontrado": true/false},
    {"campo": "dias_pendientes", "ticket": "TK-XXX", "esperado": 32, "obtenido": 32, "match": true/false},
    {"campo": "suma_por_tecnico", "tecnico": "Técnico 1", "esperado": 5, "obtenido": 5, "match": true/false}
  ]
}
```

---

## Ejemplo de Tarea Autocontenida: TK-002

**INPUT (sin ver conversación original):**
```json
{
  "borrador_orquestador": {
    "tickets_encontrados": [
      {
        "id": "TK-002",
        "empresa": "Empresa B",
        "dias_pendientes": 32,
        "prioridad": "Crítica",
        "tecnico": "Técnico 2"
      }
    ],
    "consulta_original": "Tickets críticos de Empresa B"
  },
  "datos_referencia_json": {
    "TK-002": {
      "id": "TK-002",
      "empresa": "Empresa B",
      "estado": "En curso (asignado)",
      "fecha_apertura": "2026-10-10",
      "tecnico": "Técnico 2",
      "titulo": "Error de conexión base de datos módulo de facturación",
      "seguimiento": "CRÍTICO - Sin resolver por 32 días. Requiere atención inmediata."
    }
  },
  "hoy": "2026-11-11"
}
```

**PROCESO:**
1. Verifica que TK-002 existe en JSON → ✓
2. Valida días: hoy (2026-11-11) - fecha_apertura (2026-10-10) = 32 días → ✓
3. Valida prioridad: 32 > 30 → Crítica → ✓
4. Valida empresa y técnico → ✓

**OUTPUT:**
```json
{
  "validado": true,
  "errores": []
}
```
→ Verificador aprueba. Respuesta del orquestador es exacta.

---

## Si hubiera error (ejemplo):

Si orquestador hubiera puesto dias_pendientes: 20 (incorrecto):

**OUTPUT:**
```json
{
  "validado": false,
  "errores": [
    {
      "campo": "dias_pendientes",
      "ticket": "TK-002",
      "esperado": 32,
      "obtenido": 20,
      "match": false,
      "mensaje": "Cálculo incorrecto: 2026-11-11 - 2026-10-10 = 32 días, no 20"
    }
  ]
}
```
→ Orquestador recibe rechazo, reintenta.
