"""
Guardrails de entrada y salida para el agente de triage de tickets.

Entrada: bloquea inyecciones y órdenes prohibidas (cerrar, borrar, reasignar).
Salida: valida que cada ID T-xxxx exista en datos/tickets.json y anonimización.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

RUTA_DATOS = Path(__file__).parent / "datos" / "tickets.json"


@dataclass
class Decision:
    permitir: bool
    texto: str
    motivo: str = ""
    hallazgos: list[str] = field(default_factory=list)


RESPUESTA_BLOQUEO_ENTRADA = (
    "No puedo ejecutar esa acción. Solo puedo consultar y reportar."
)

# ── Entrada ───────────────────────────────────────────────────────────────────
PATRONES_INYECCION = [
    r"ignora\w*\s+(todas?\s+)?(las\s+|tus\s+)?(instrucciones|reglas)",
    r"olvida\w*\s+(todas?\s+)?(las\s+|tus\s+)?(instrucciones|reglas)",
    r"haz\s+caso\s+omiso",
]

PATRONES_PROHIBIDOS = [
    r"\bcierr[ao]s?\b.*ticket",
    r"\bborr[ao]s?\b.*ticket",
    r"\breasign[ao]s?\b.*ticket",
    r"\bcierra\b",
    r"\bborrar\b",
]


def detectar_inyeccion(texto: str) -> str | None:
    """Devuelve el patrón que coincidió, o None."""
    t = texto.lower()
    for p in PATRONES_INYECCION:
        if re.search(p, t):
            return p
    return None


def detectar_accion_prohibida(texto: str) -> str | None:
    """Devuelve el patrón que coincidió, o None. Pero permite pasado: '¿cuántos se cerraron?'"""
    t = texto.lower()
    # Si está en pasado o pregunta ("se cerraron", "fueron cerrados"), dejar pasar
    if re.search(r"(se\s+)?cerr\w+\w*\s+(ya|hace|hace\s+poco|ayer|en)", t) or "¿" in texto:
        return None
    for p in PATRONES_PROHIBIDOS:
        if re.search(p, t):
            return p
    return None


def revisar_entrada(texto: str) -> Decision:
    patron = detectar_inyeccion(texto)
    if patron:
        return Decision(False, RESPUESTA_BLOQUEO_ENTRADA, f"inyección detectada ({patron})", ["inyeccion"])

    patron = detectar_accion_prohibida(texto)
    if patron:
        return Decision(False, RESPUESTA_BLOQUEO_ENTRADA, f"acción prohibida ({patron})", ["accion_prohibida"])

    return Decision(True, texto, "entrada válida", [])


# ── Salida ─────────────────────────────────────────────────────────────────────
RE_IDS = re.compile(r"\b(?:T|TK)-\d+\b")  # Busca T-xxxx o TK-xxxx


def cargar_ids_validos() -> set[str]:
    """Carga los IDs válidos del JSON."""
    try:
        with open(RUTA_DATOS, encoding="utf-8") as f:
            datos = json.load(f)
            return {t["id"] for t in datos.get("tickets", [])}
    except Exception:
        return set()


def ids_no_respaldados(respuesta: str, ids_validos: set[str]) -> list[str]:
    """IDs T-xxxx o TK-xxxx que aparecen en la respuesta pero no en datos/tickets.json.
    Rechaza también TK-xxxx aunque sea sintácticamente correcto porque el JSON solo usa T-xxxx."""
    encontrados = RE_IDS.findall(respuesta)
    no_respaldados = []
    for id_ticket in encontrados:
        # Rechaza TK-xxxx como formato inválido (debería ser T-xxxx)
        if id_ticket.startswith("TK-"):
            if id_ticket not in no_respaldados:
                no_respaldados.append(id_ticket)
        elif id_ticket not in ids_validos and id_ticket not in no_respaldados:
            no_respaldados.append(id_ticket)
    return no_respaldados


def detectar_nombres_no_anonimizados(respuesta: str) -> list[str]:
    """Detecta nombres de personas o empresas sin anonimizar.
    Whitelist: técnicos y empresas anonimizadas están permitidas."""
    hallazgos = []

    # Patrones sospechosos: nombres comunes en minúscula seguidos de apellido
    # Pero permitimos "Técnico 1", "Empresa A", etc.
    patron = r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b"
    matches = re.findall(patron, respuesta)

    whitelist = {"Técnico", "Empresa"}
    for m in matches:
        primero = m.split()[0]
        if primero not in whitelist:
            hallazgos.append(m)

    return hallazgos


def revisar_salida(respuesta: str) -> Decision:
    ids_validos = cargar_ids_validos()
    hallazgos = []

    sin_respaldo = ids_no_respaldados(respuesta, ids_validos)
    if sin_respaldo:
        hallazgos.append(f"ids sin respaldo: {sin_respaldo}")

    nombres = detectar_nombres_no_anonimizados(respuesta)
    if nombres:
        hallazgos.append(f"nombres no anonimizados: {nombres}")

    if hallazgos:
        respuesta_segura = (
            "No pude verificar completamente esos datos. Por favor, "
            "verifica directamente con el sistema de tickets."
        )
        return Decision(False, respuesta_segura, "; ".join(hallazgos), hallazgos)

    return Decision(True, respuesta, "salida validada", [])
