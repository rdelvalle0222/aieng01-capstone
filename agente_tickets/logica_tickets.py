"""
Lógica de negocio del agente de tickets.

Son las mismas reglas del proyecto Organizador_MDA (prioridades.py,
responsables.py, historial_soluciones.py), pero:
  - leen los tickets SIMULADOS de datos/tickets.json (no el Excel real), y
  - DEVUELVEN diccionarios en vez de imprimir, para que el agente los lea.
"""
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

RUTA_DATOS = Path(__file__).parent / "datos" / "tickets.json"

ESTADO_ESPERA = "En espera"
ESTADO_CURSO = "En curso (asignado)"
ESTADOS_VALIDOS = [ESTADO_ESPERA, ESTADO_CURSO]
PROVEEDORES_VALIDOS = ["Proveedor 1", "Proveedor 2"]


def cargar_datos():
    with open(RUTA_DATOS, encoding="utf-8") as archivo:
        datos = json.load(archivo)
    fecha_corte = datetime.strptime(datos["fecha_corte"], "%Y-%m-%d")
    return datos["tickets"], fecha_corte


def dias_pendientes(ticket, fecha_corte):
    # Igual que en Organizador_MDA: se compara solo la fecha, sin la hora.
    apertura = datetime.strptime(ticket["fecha_apertura"][:10], "%Y-%m-%d")
    return (fecha_corte - apertura).days


def prioridad(dias):
    # Misma regla de prioridades.py
    if dias <= 5:
        return "Baja"
    if dias <= 15:
        return "Media"
    if dias <= 30:
        return "Alta"
    return "Critica"


def _empresas(tickets):
    return sorted({t["empresa"] for t in tickets})


def _resumen(ticket, fecha_corte):
    dias = dias_pendientes(ticket, fecha_corte)
    return {
        "id": ticket["id"],
        "titulo": ticket["titulo"],
        "empresa": ticket["empresa"],
        "estado": ticket["estado"],
        "dias_pendientes": dias,
        "prioridad": prioridad(dias) if ticket["estado"] == ESTADO_ESPERA else None,
        "tecnico": ticket["tecnico"],
    }


def buscar_tickets(empresa=None, estado=None, id=None):
    tickets, fecha_corte = cargar_datos()

    if id:
        for t in tickets:
            if t["id"].upper() == id.strip().upper():
                detalle = _resumen(t, fecha_corte)
                detalle.update({
                    "categoria": t["categoria"],
                    "grupo": t["grupo"],
                    "fecha_apertura": t["fecha_apertura"],
                    "descripcion": t["descripcion"],
                    "seguimiento": t["seguimiento"],
                })
                return {"ok": True, "ticket": detalle}
        return {"ok": False, "error": f"No existe el ticket '{id}'. Los IDs tienen la forma T-1000."}

    empresas_validas = {e.lower() for e in _empresas(tickets)}
    if empresa and empresa.lower() not in empresas_validas:
        return {"ok": False,
                "error": f"Empresa '{empresa}' no encontrada. Usa una de: {', '.join(_empresas(tickets))}."}
    if estado and estado not in ESTADOS_VALIDOS:
        return {"ok": False, "error": f"Estado inválido. Usa uno de: {ESTADOS_VALIDOS}."}

    resultado = [
        _resumen(t, fecha_corte) for t in tickets
        if (not empresa or t["empresa"].lower() == empresa.lower())
        and (not estado or t["estado"] == estado)
    ]
    conteo = Counter(t["estado"] for t in resultado)
    return {
        "ok": True,
        "total": len(resultado),
        "en_espera": conteo.get(ESTADO_ESPERA, 0),
        "en_curso": conteo.get(ESTADO_CURSO, 0),
        "tickets": resultado,
    }


def calcular_prioridades(empresa=None):
    tickets, fecha_corte = cargar_datos()

    empresas_validas = {e.lower() for e in _empresas(tickets)}
    if empresa and empresa.lower() not in empresas_validas:
        return {"ok": False,
                "error": f"Empresa '{empresa}' no encontrada. Usa una de: {', '.join(_empresas(tickets))}."}

    pendientes = [
        _resumen(t, fecha_corte) for t in tickets
        if t["estado"] == ESTADO_ESPERA
        and (not empresa or t["empresa"].lower() == empresa.lower())
    ]
    pendientes.sort(key=lambda t: t["dias_pendientes"], reverse=True)
    return {
        "ok": True,
        "fecha_corte": fecha_corte.strftime("%Y-%m-%d"),
        "regla": "Baja <=5 dias, Media <=15, Alta <=30, Critica >30",
        "por_prioridad": dict(Counter(t["prioridad"] for t in pendientes)),
        "tickets": pendientes,
    }


def tickets_por_proveedor(proveedor):
    tickets, fecha_corte = cargar_datos()

    nombre = next((p for p in PROVEEDORES_VALIDOS if p.lower() == proveedor.strip().lower()), None)
    if not nombre:
        return {"ok": False, "error": f"Proveedor desconocido. Usa uno de: {PROVEEDORES_VALIDOS}."}

    encontrados = [
        _resumen(t, fecha_corte) for t in tickets
        if t["estado"] in ESTADOS_VALIDOS
        and nombre.lower() in (t["seguimiento"] + " " + t["descripcion"]).lower()
    ]
    return {"ok": True, "proveedor": nombre, "total": len(encontrados), "tickets": encontrados}


def carga_por_tecnico():
    tickets, _ = cargar_datos()
    pendientes = [t for t in tickets if t["estado"] == ESTADO_ESPERA]

    # Contar técnicos: si un ticket tiene "Técnico 1, Técnico 2" cuenta como 1 para cada uno
    contador_tecnicos = Counter()
    for t in pendientes:
        tecnicos = [tech.strip() for tech in (t["tecnico"] or "").split(",")]
        for tech in tecnicos:
            if tech:
                contador_tecnicos[tech] += 1

    return {
        "ok": True,
        "tickets_en_espera": len(pendientes),
        "por_tecnico": dict(contador_tecnicos.most_common()),
        "por_grupo": dict(Counter(t["grupo"] or "Sin grupo asignado" for t in pendientes).most_common()),
    }
