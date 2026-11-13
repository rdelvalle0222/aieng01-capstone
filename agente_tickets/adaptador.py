"""
Adaptador: ejecuta guardrail entrada → agente.py → guardrail salida.
Guarda trazas en resultados/ y costos en usage_log.jsonl.
"""

import json
import sys
from pathlib import Path

import anyio
from trazas import Traza
from guardrails import revisar_entrada, revisar_salida
from claude_agent_sdk import query, ResultMessage
from agente import opciones

DIR_RESULTADOS = Path(__file__).parent / "resultados"
RUTA_USAGE_LOG = Path(__file__).parent / "usage_log.jsonl"


async def correr_agente(pregunta: str, traza: Traza) -> tuple[str, dict]:
    """Ejecuta el agente y devuelve (respuesta, metadata)."""
    respuesta = ""
    metadata = {"turnos": 0, "input_tokens": 0, "output_tokens": 0, "costo_usd": 0.0}
    with traza.span("modelo", "agente") as span:
        async for msg in query(prompt=pregunta, options=opciones()):
            if isinstance(msg, ResultMessage):
                metadata["turnos"] = msg.num_turns
                if hasattr(msg, "usage") and msg.usage:
                    if isinstance(msg.usage, dict):
                        metadata["input_tokens"] = msg.usage.get("input_tokens", 0)
                        metadata["output_tokens"] = msg.usage.get("output_tokens", 0)
                    else:
                        metadata["input_tokens"] = getattr(msg.usage, "input_tokens", 0)
                        metadata["output_tokens"] = getattr(msg.usage, "output_tokens", 0)
                metadata["costo_usd"] = msg.total_cost_usd if msg.total_cost_usd else 0.0
                # Extrae el resultado de texto: ResultMessage puede tener output_text
                respuesta = str(getattr(msg, "output_text", "")) or str(getattr(msg, "result", ""))
            else:
                # Para otros tipos de mensajes, extraer texto si existe
                if hasattr(msg, "content"):
                    respuesta += "\n".join(
                        b.text if isinstance(b, str) else getattr(b, "text", "")
                        for b in msg.content if (hasattr(b, "text") or isinstance(b, str))
                    )
            span.update(metadata)
    return respuesta, metadata


async def adaptador(pregunta: str, sin_guardrails: bool = False) -> None:
    """Flujo completo con guardrails y trazas."""
    traza = Traza(pregunta, guardar=True)

    # 1. Guardrail de entrada
    with traza.span("guardrail", "entrada") as span:
        decision_entrada = revisar_entrada(pregunta)
        span["permitido"] = decision_entrada.permitir
        span["motivo"] = decision_entrada.motivo
        span["hallazgos"] = decision_entrada.hallazgos

    if not decision_entrada.permitir and not sin_guardrails:
        print(f"\n[GUARDRAIL ENTRADA] Bloqueado")
        print(f"  Motivo: {decision_entrada.motivo}")
        print(f"  Respuesta: {decision_entrada.texto}\n")
        traza.evento("guardrail", "entrada_bloqueado", motivo=decision_entrada.motivo)
        traza.cerrar(bloqueado_entrada=True)
        ruta = DIR_RESULTADOS / f"{traza.id}.txt"
        DIR_RESULTADOS.mkdir(exist_ok=True)
        ruta.write_text(decision_entrada.texto, encoding="utf-8")
        ruta_traza = DIR_RESULTADOS.parent / "trazas" / f"{traza.id}.jsonl"
        print(f"✅ Traza guardada: {ruta_traza}")
        return

    # 2. Ejecutar agente
    print(f"\n[AGENTE] Procesando: {pregunta[:50]}...")
    pregunta_a_procesar = decision_entrada.texto
    respuesta, metadata_agente = await correr_agente(pregunta_a_procesar, traza)
    print(f"[AGENTE] Respuesta: {respuesta[:100]}...\n")

    # 3. Guardrail de salida
    with traza.span("guardrail", "salida") as span:
        decision_salida = revisar_salida(respuesta)
        span["permitido"] = decision_salida.permitir
        span["motivo"] = decision_salida.motivo
        span["hallazgos"] = decision_salida.hallazgos

    if not decision_salida.permitir and not sin_guardrails:
        print(f"[GUARDRAIL SALIDA] Bloqueado")
        print(f"  Motivo: {decision_salida.motivo}")
        print(f"  Respuesta segura: {decision_salida.texto}\n")
        respuesta = decision_salida.texto
        traza.evento("guardrail", "salida_bloqueado", motivo=decision_salida.motivo)

    # 4. Guardar traza y costo
    ruta_traza = traza.cerrar()
    print(f"✅ Traza guardada: {ruta_traza}")

    # 5. Guardar resultado
    ruta_resultado = DIR_RESULTADOS / f"{traza.id}.txt"
    DIR_RESULTADOS.mkdir(exist_ok=True)
    ruta_resultado.write_text(respuesta, encoding="utf-8")

    # 6. Registrar costo en usage_log.jsonl
    registro_costo = {
        "traza_id": traza.id,
        "pregunta": pregunta[:100],
        "tokens_entrada": metadata_agente.get("input_tokens", 0),
        "tokens_salida": metadata_agente.get("output_tokens", 0),
        "costo_usd": metadata_agente.get("costo_usd", 0.0),
    }

    with open(RUTA_USAGE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro_costo) + "\n")

    print(f"📊 Costo: {registro_costo['costo_usd']:.4f} USD")
    print(f"   Tokens entrada: {registro_costo['tokens_entrada']}, salida: {registro_costo['tokens_salida']}")


if __name__ == "__main__":
    pregunta = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "¿Cuántos tickets críticos tiene la Empresa A?"
    sin_guardrails = "--sin-guardrails" in sys.argv

    print("=" * 70)
    print(f"  Pregunta: {pregunta}")
    print(f"  Guardrails: {'desactivados' if sin_guardrails else 'activados'}")
    print("=" * 70)

    anyio.run(adaptador, pregunta, sin_guardrails)
