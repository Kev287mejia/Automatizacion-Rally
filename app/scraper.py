"""
scraper.py — Extracción de datos del Rally Nacional de Innovación vía API JSON.

FASE 1: Consumo directo de los endpoints descubiertos:
- /competencia/dashboard/datos/
- /competencia/dashboard/sedes/

POLÍTICA DE DATOS:
- Se consume exclusivamente JSON.
- Se valida la estructura base ('ok', 'indicadores', 'tablas').
- Si la sede no tiene datos o los arrays vienen vacíos (común antes del evento), no es un error.
- Se manejan excepciones limpiamente sin exponer credenciales.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Any

import requests

from .config import AppConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Estructuras de datos
# ---------------------------------------------------------------------------


@dataclass
class IndicadoresAPI:
    """Indicadores extraídos de la API."""
    inscritos: int = 0
    participantes: int = 0
    mentores: int = 0
    jurados: int = 0
    equipos: int = 0
    equipos_abiertos: int = 0
    equipos_conformados: int = 0


@dataclass
class SedeAPI:
    """Datos de una sede específica."""
    nombre: str = ""
    # Guardamos los datos completos de la sede si existen para futura normalización/detector
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class SnapshotData:
    """Datos limpios listos para normalización y consola."""
    indicadores: IndicadoresAPI = field(default_factory=IndicadoresAPI)
    sede_data: Optional[SedeAPI] = None
    errores: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Errores personalizados
# ---------------------------------------------------------------------------


class ScraperError(Exception):
    """Error general durante el scraping/consumo de API."""
    pass


class InvalidStructureError(ScraperError):
    """El JSON de la API no tiene la estructura esperada."""
    pass


# ---------------------------------------------------------------------------
# Funciones principales
# ---------------------------------------------------------------------------


def _fetch_json(
    session: requests.Session, url: str, params: dict, label: str, timeout: int
) -> dict:
    """
    Realiza un GET y devuelve el JSON analizado. Maneja errores limpiamente.
    """
    logger.info("[%s] Consultando API: %s", label, url)
    try:
        response = session.get(url, params=params, timeout=timeout)
        response.raise_for_status()

        # Validación simple de Content-Type si está presente (evita parsear HTML como JSON)
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower() and content_type:
            logger.warning("[%s] Content-Type no es application/json: %s", label, content_type)

        data = response.json()
        logger.info("✓ [%s] HTTP 200 — JSON válido obtenido", label)
        return data

    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        msg = f"HTTP {status} al consultar {label} ({url})"
        if status == 403:
            msg = f"HTTP 403 Forbidden. Sesión bloqueada, CSRF inválido o sin permisos para {label}"
        elif status == 404:
            msg = f"HTTP 404 Not Found. El endpoint {url} no existe."
        elif status == 429:
            msg = f"HTTP 429 Too Many Requests. Límite de peticiones excedido para {label}."
        logger.error(msg)
        raise ScraperError(msg) from exc
    except requests.Timeout as exc:
        msg = f"Timeout ({timeout}s) al consultar {label}"
        logger.error(msg)
        raise ScraperError(msg) from exc
    except requests.exceptions.JSONDecodeError as exc:
        msg = f"La respuesta de {label} no es un JSON válido"
        logger.error(msg)
        raise ScraperError(msg) from exc
    except requests.RequestException as exc:
        msg = f"Error de red al consultar {label}: {exc}"
        logger.error(msg)
        raise ScraperError(msg) from exc


def get_competencia_data(session: requests.Session, config: AppConfig) -> SnapshotData:
    """
    Obtiene los datos de competencia consumiendo las APIs JSON directamente.

    Args:
        session: requests.Session previamente autenticada (login).
        config: Configuración de la app.

    Returns:
        SnapshotData con los indicadores y datos de sede encontrados.
    """
    snapshot = SnapshotData()
    errores = []

    # 1. Parámetros base para las peticiones
    params_datos = {
        "edicion": config.edition_uuid,
        "institucion": "",
        "sede": "",  # Queremos todos los datos globales primero
    }
    
    params_sedes = {
        "edicion": config.edition_uuid,
    }

    # 2. Consultar API de Indicadores
    try:
        datos_json = _fetch_json(
            session, config.api_datos_url, params_datos, "API Datos", config.request_timeout
        )
        
        # Validar estructura base (falla rápido si la API cambió)
        if "ok" not in datos_json or "indicadores" not in datos_json:
            raise InvalidStructureError("El JSON de API Datos no contiene las claves 'ok' o 'indicadores'")
            
        if not datos_json.get("ok"):
            logger.warning("La API de Datos devolvió ok=False. Los datos pueden estar incompletos.")
            
        ind_raw = datos_json.get("indicadores", {})
        
        snapshot.indicadores = IndicadoresAPI(
            inscritos=ind_raw.get("inscritos", 0),
            participantes=ind_raw.get("participantes", 0),
            mentores=ind_raw.get("mentores", 0),
            jurados=ind_raw.get("jurados", 0),
            equipos=ind_raw.get("equipos", 0),
            equipos_abiertos=ind_raw.get("equipos_abiertos", 0),
            equipos_conformados=ind_raw.get("equipos_conformados", 0),
        )

    except Exception as exc:
        msg = f"Error obteniendo Indicadores: {exc}"
        logger.error(msg)
        errores.append(msg)

    # 3. Consultar API de Sedes
    try:
        sedes_json = _fetch_json(
            session, config.api_sedes_url, params_sedes, "API Sedes", config.request_timeout
        )
        
        if "ok" not in sedes_json or "resultados" not in sedes_json:
             raise InvalidStructureError("El JSON de API Sedes no contiene las claves 'ok' o 'resultados'")
             
        resultados = sedes_json.get("resultados", [])
        
        # Buscar nuestra sede específica
        sede_encontrada = None
        target_name = config.sede_name.lower().strip()
        
        for sede in resultados:
            if not isinstance(sede, dict):
                continue
            nombre = sede.get("nombre", "") or sede.get("name", "")
            if target_name in str(nombre).lower():
                sede_encontrada = sede
                break
                
        if sede_encontrada:
            logger.info("✓ Sede '%s' encontrada en los resultados", config.sede_name)
            snapshot.sede_data = SedeAPI(
                nombre=config.sede_name,
                raw_data=sede_encontrada
            )
        else:
            if not resultados:
                logger.info("Sede '%s' no encontrada: el array de sedes está vacío actualmente", config.sede_name)
            else:
                logger.info("Sede '%s' no encontrada en las %d sedes devueltas", config.sede_name, len(resultados))
            
    except Exception as exc:
        msg = f"Error obteniendo Sedes: {exc}"
        logger.error(msg)
        errores.append(msg)

    snapshot.errores = errores
    return snapshot
