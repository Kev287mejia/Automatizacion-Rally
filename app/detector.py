"""
detector.py — Lógica de comparación de snapshots para detectar eventos.

Compara el snapshot anterior con el snapshot actual y emite eventos
estructurados si existen incrementos en los indicadores o cambios en la sede.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
import copy

from .scraper import SnapshotData


@dataclass
class ChangeEvent:
    """Representa un evento detectado al comparar dos snapshots."""
    tipo: str
    campo: str
    anterior: Any
    actual: Any
    incremento: Optional[int] = None
    sede: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def _detectar_indicadores(
    anterior: SnapshotData, actual: SnapshotData, sede_name: str
) -> list[ChangeEvent]:
    """Compara los indicadores numéricos."""
    eventos = []
    
    ind_ant = anterior.indicadores
    ind_act = actual.indicadores

    # Mapeo de campos a tipos de evento
    mapeo_basico = {
        "inscritos": "NUEVO_INSCRITO",
        "participantes": "NUEVO_PARTICIPANTE",
        "mentores": "NUEVO_MENTOR",
        "jurados": "NUEVO_JURADO",
        "equipos": "NUEVO_EQUIPO",
    }

    # Revisar campos básicos
    for campo, tipo_evento in mapeo_basico.items():
        val_ant = getattr(ind_ant, campo) or 0
        val_act = getattr(ind_act, campo) or 0

        if val_act > val_ant:
            eventos.append(
                ChangeEvent(
                    tipo=tipo_evento,
                    campo=campo,
                    anterior=val_ant,
                    actual=val_act,
                    incremento=val_act - val_ant,
                    sede=sede_name,
                )
            )

    # Lógica especial para equipos (abiertos vs conformados)
    abiertos_ant = ind_ant.equipos_abiertos or 0
    abiertos_act = ind_act.equipos_abiertos or 0
    conformados_ant = ind_ant.equipos_conformados or 0
    conformados_act = ind_act.equipos_conformados or 0

    if abiertos_act < abiertos_ant and conformados_act > conformados_ant:
        # Hubo conformación de equipo(s)
        incremento_conformados = conformados_act - conformados_ant
        eventos.append(
            ChangeEvent(
                tipo="EQUIPO_CONFORMADO",
                campo="equipos_conformados",
                anterior=conformados_ant,
                actual=conformados_act,
                incremento=incremento_conformados,
                sede=sede_name,
            )
        )
    else:
        # Si no hubo transición, reportarlos de manera individual si aumentan
        if abiertos_act > abiertos_ant:
            eventos.append(
                ChangeEvent(
                    tipo="NUEVO_EQUIPO_ABIERTO",
                    campo="equipos_abiertos",
                    anterior=abiertos_ant,
                    actual=abiertos_act,
                    incremento=abiertos_act - abiertos_ant,
                    sede=sede_name,
                )
            )
        if conformados_act > conformados_ant:
            eventos.append(
                ChangeEvent(
                    tipo="NUEVO_EQUIPO_CONFORMADO",
                    campo="equipos_conformados",
                    anterior=conformados_ant,
                    actual=conformados_act,
                    incremento=conformados_act - conformados_ant,
                    sede=sede_name,
                )
            )

    return eventos


def _detectar_sede(
    anterior: SnapshotData, actual: SnapshotData, sede_name: str
) -> list[ChangeEvent]:
    """Compara los datos detallados de la sede."""
    eventos = []
    
    sede_ant = anterior.sede_data
    sede_act = actual.sede_data

    # Caso 1: Antes era None y ahora hay datos
    if not sede_ant and sede_act:
        eventos.append(
            ChangeEvent(
                tipo="DATOS_SEDE_DISPONIBLES",
                campo="sede_data",
                anterior=None,
                actual=sede_act.raw_data,
                sede=sede_name,
            )
        )
    # Caso 2: Ambos tienen datos, evaluar si cambió
    elif sede_ant and sede_act:
        # Copiamos para no mutar el original en caso de que queramos descartar campos irrelevantes
        # Por ahora verificamos si raw_data es distinto
        if sede_ant.raw_data != sede_act.raw_data:
            eventos.append(
                ChangeEvent(
                    tipo="CAMBIO_SEDE",
                    campo="sede_data",
                    anterior=sede_ant.raw_data,
                    actual=sede_act.raw_data,
                    sede=sede_name,
                )
            )

    return eventos


def detectar_cambios(
    anterior: Optional[SnapshotData],
    actual: SnapshotData,
    sede_name: str
) -> list[ChangeEvent]:
    """
    Compara el snapshot anterior con el actual y devuelve una lista de eventos.

    Args:
        anterior: El snapshot de la última ejecución, o None si es la primera vez.
        actual: El snapshot de la ejecución actual.
        sede_name: Nombre de la sede para inyectar en los eventos.

    Returns:
        Lista de ChangeEvent detectados. Vacía si no hay cambios o si es primera ejecución.
    """
    # Primera ejecución: establecer baseline, no hay eventos
    if anterior is None:
        return []

    eventos = []
    
    # 1. Indicadores
    eventos.extend(_detectar_indicadores(anterior, actual, sede_name))
    
    # 2. Sede
    eventos.extend(_detectar_sede(anterior, actual, sede_name))
    
    # 3. Tablas detalladas (para el futuro)
    # Aquí irá la lógica para comparar las tablas detalladas de participantes y equipos.
    
    return eventos
