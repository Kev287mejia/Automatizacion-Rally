"""
config.py — Configuración central del monitor.

Lee todas las credenciales y URLs exclusivamente desde variables de entorno.
NUNCA contiene valores reales. NUNCA imprime credenciales.
"""

import os
import logging
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Cargar .env si existe (útil en desarrollo local)
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppConfig:
    """Configuración inmutable cargada desde variables de entorno."""

    # --- Credenciales (NUNCA se imprimen ni se loguean) ---
    username: str
    password: str

    # --- Identificadores de edición y sede ---
    edition_uuid: str
    sede_name: str

    # --- URLs base ---
    base_url: str
    login_url: str
    dashboard_url: str
    participantes_url: str
    equipos_url: str
    api_datos_url: str
    api_sedes_url: str

    # --- Configuración HTTP ---
    # --- Configuración HTTP ---
    request_timeout: int
    user_agent: str

    # --- Configuración de Correo (Fase 3) ---
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    alert_email: str


def load_config() -> AppConfig:
    """
    Carga y valida la configuración desde variables de entorno.

    Variables obligatorias:
        RALLY_USERNAME  — usuario registrado en la plataforma
        RALLY_PASSWORD  — contraseña del usuario

    Variables opcionales (tienen valores por defecto):
        RALLY_BASE_URL
        RALLY_EDITION_UUID
        RALLY_SEDE_NAME
        RALLY_REQUEST_TIMEOUT
        RALLY_USER_AGENT

    Raises:
        EnvironmentError: Si faltan variables obligatorias.
    """
    missing: list[str] = []

    username = os.getenv("RALLY_USERNAME", "")
    password = os.getenv("RALLY_PASSWORD", "")

    if not username:
        missing.append("RALLY_USERNAME")
    if not password:
        missing.append("RALLY_PASSWORD")

    if missing:
        raise EnvironmentError(
            f"Variables de entorno requeridas no encontradas: {', '.join(missing)}. "
            "Crea un archivo .env basado en .env.example."
        )

    base_url = os.getenv(
        "RALLY_BASE_URL",
        "https://apprally.nicaraguainnova.gob.ni",
    ).rstrip("/")

    edition_uuid = os.getenv(
        "RALLY_EDITION_UUID",
        "4f13f9a9-8bfc-44a3-99ac-a578e9908c9b",
    )

    sede_name = os.getenv(
        "RALLY_SEDE_NAME",
        "BICU, Puerto Cabezas",
    )

    timeout_raw = os.getenv("RALLY_REQUEST_TIMEOUT", "30")
    try:
        request_timeout = int(timeout_raw)
    except ValueError:
        logger.warning(
            "RALLY_REQUEST_TIMEOUT='%s' no es un entero válido; usando 30s.",
            timeout_raw,
        )
        request_timeout = 30

    user_agent = os.getenv(
        "RALLY_USER_AGENT",
        "RallyMonitor/1.0 (monitor-academico; contacto@ejemplo.com)",
    )

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    alert_email = os.getenv("ALERT_EMAIL", "")

    config = AppConfig(
        username=username,
        password=password,
        edition_uuid=edition_uuid,
        sede_name=sede_name,
        base_url=base_url,
        login_url=f"{base_url}/",
        dashboard_url=f"{base_url}/competencia/dashboard/",
        participantes_url=f"{base_url}/competencia/participantes/",
        equipos_url=f"{base_url}/competencia/equipos/",
        api_datos_url=f"{base_url}/competencia/dashboard/datos/",
        api_sedes_url=f"{base_url}/competencia/dashboard/sedes/",
        request_timeout=request_timeout,
        user_agent=user_agent,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        alert_email=alert_email,
    )

    # Log de confirmación SIN revelar credenciales
    logger.info(
        "Configuración cargada. Usuario: %s | Edición: %s | Sede: %s | Base URL: %s",
        "[REDACTED]",
        config.edition_uuid,
        config.sede_name,
        config.base_url,
    )

    return config
