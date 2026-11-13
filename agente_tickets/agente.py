"""
Agente de triage de tickets de soporte con verificador (subagente).

Ejecuta:
    python agente.py "¿Cuántos tickets críticos en espera tiene la Empresa A?"
    python agente.py "¿Qué carga tiene el Técnico 1?"
"""

import os
import sys
from pathlib import Path

import anyio
from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultError,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

from sdk_config import MODELO, proveedor

AQUI = Path(__file__).parent

SYSTEM = """Asistente de triage de tickets de soporte TI. Solo consultas, sin modificaciones.

Reglas:
- Responde SOLO datos de tus herramientas. Nunca inventes IDs ni cifras.
- Cita IDs (ej. T-1023) y días pendientes. MUY CONCISO.
- Solo reporta hechos. Nunca sugieras reasignar, cerrar ni modificar.
- Con 2+ tickets: usa verificador para validar IDs y antigüedad.
- Responde 1-5 viñetas, español, sin explicaciones."""

SERVIDORES = {
    "tickets": {"type": "stdio", "command": "python3", "args": [str(AQUI / "server.py")]},
}

HERRAMIENTAS = [
    "mcp__tickets__buscar_tickets",
    "mcp__tickets__calcular_prioridades",
    "mcp__tickets__tickets_por_proveedor",
    "mcp__tickets__carga_por_tecnico",
]

AGENTES = {
    "verificador": AgentDefinition(
        description="Úsalo antes de entregar un informe con varios tickets, "
                    "para contrastar IDs, días y prioridades con los datos.",
        prompt="Eres el verificador de tickets. Recibes un borrador de respuesta. "
               "Con tus herramientas compruebas que cada ID exista y que sus días "
               "y prioridad coincidan. Devuelves 'OK' o la lista de lo que no "
               "cuadra y por qué. No redactas la respuesta final.",
        tools=["mcp__tickets__buscar_tickets", "mcp__tickets__calcular_prioridades"],
        model="inherit",
    ),
}


def opciones(**extra) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=MODELO,
        system_prompt=SYSTEM,
        mcp_servers=SERVIDORES,
        agents=AGENTES,
        tools=["Agent"],
        allowed_tools=HERRAMIENTAS + ["Agent"],
        setting_sources=[],
        max_turns=int(os.environ.get("MAX_TURNOS", "6")),
        max_budget_usd=float(os.environ.get("PRESUPUESTO_USD", "0.50")),
        cwd=str(AQUI),
        **extra,
    )


def mostrar(m) -> None:
    """La traza: qué herramienta pidió el modelo, cómo salió y, al final, turnos y costo."""
    if isinstance(m, AssistantMessage):
        for b in m.content:
            if isinstance(b, ToolUseBlock):
                print(f"  [tool] {b.name}({b.input})", flush=True)
            elif isinstance(b, TextBlock) and b.text.strip():
                print(f"\nAgente: {b.text.strip()}", flush=True)
    elif isinstance(m, UserMessage) and isinstance(m.content, list):
        for b in m.content:
            if isinstance(b, ToolResultBlock):
                print(f"    → {'error' if b.is_error else 'ok'}", flush=True)
    elif isinstance(m, ResultMessage):
        costo = f"USD {m.total_cost_usd:.4f}" if m.total_cost_usd is not None else "s/d"
        print(f"\n[resultado] {m.subtype} · turnos={m.num_turns} · costo≈{costo} · {m.duration_ms / 1000:.1f}s", flush=True)


async def correr(mision: str) -> None:
    try:
        async for m in query(prompt=mision, options=opciones()):
            mostrar(m)
    except ResultError as exc:
        # Cuando un freno corta (max_turns, max_budget_usd), el SDK entrega el ResultMessage con ese subtype
        # y ADEMÁS termina con ResultError. Es el freno funcionando: se reporta, no se muestra una traza.
        print(f"[freno] {exc}", flush=True)


if __name__ == "__main__":
    mision = " ".join(sys.argv[1:]) or "¿Cuántos tickets críticos en espera tiene la Empresa A?"
    print("=" * 70)
    print(f"  Misión: {mision}")
    print(f"  {proveedor()} · {MODELO}")
    print("=" * 70)
    anyio.run(correr, mision)
