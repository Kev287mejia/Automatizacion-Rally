"""
notifier.py — Envío de notificaciones por correo electrónico (SMTP).

Convierte eventos estructurados (ChangeEvent) en correos amigables.
Solamente se ocupa del transporte SMTP, no de la detección ni del almacenamiento.
"""

import smtplib
import logging
from email.message import EmailMessage
from datetime import datetime, timezone
from typing import List

from .config import AppConfig
from .detector import ChangeEvent


logger = logging.getLogger(__name__)


def _format_event(event: ChangeEvent) -> str:
    """Formatea un evento para el cuerpo del correo."""
    
    # Emoji por tipo de evento
    if "EQUIPO" in event.tipo:
        emoji = "🟡"
    elif "SEDE" in event.tipo or "DATOS" in event.tipo:
        emoji = "🔵"
    else:
        emoji = "🟢"
        
    lineas = [
        f"{emoji} {event.tipo.replace('_', ' ')}",
    ]
    
    if event.incremento is not None:
        lineas.append(f"Anterior: {event.anterior}")
        lineas.append(f"Actual: {event.actual}")
        lineas.append(f"Incremento: +{event.incremento}")
    else:
        # Para eventos donde no es un incremento numérico (ej. cambio de sede)
        # Omitiremos anterior si era None.
        if event.anterior is not None:
            lineas.append(f"Anterior: {event.anterior}")
        lineas.append(f"Actual: {event.actual}")

    return "\n".join(lineas)


def send_notification(events: List[ChangeEvent], config: AppConfig) -> bool:
    """
    Envía un correo con la lista de eventos detectados.
    Si la lista está vacía, no hace nada.
    
    Devuelve True si el correo se envió correctamente o si no había eventos.
    Devuelve False si ocurrió un error durante el envío.
    """
    if not events:
        logger.debug("No hay eventos para notificar. Se omite el envío de correo.")
        return True

    # Validar que la configuración esté completa antes de intentar enviar
    if not config.smtp_host or not config.smtp_username or not config.smtp_password or not config.alert_email:
        logger.error("Configuración SMTP incompleta. No se pudo enviar el correo.")
        return False

    sede_name = events[0].sede if events else config.sede_name

    # 1. Construir el correo
    msg = EmailMessage()
    msg['Subject'] = f"[RALLY] Cambios detectados — {sede_name}"
    msg['From'] = config.smtp_username
    msg['To'] = config.alert_email

    # 2. Construir el cuerpo
    body_lines = [
        "MONITOR RALLY",
        "IV Rally Nacional de Innovación — Nicaragua Innova 2026",
        "",
        f"Sede:\n{sede_name}",
        "",
        f"Se detectaron {len(events)} cambios:",
        ""
    ]

    for ev in events:
        body_lines.append(_format_event(ev))
        body_lines.append("")

    fecha = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    body_lines.append(f"Fecha:\n{fecha}")

    msg.set_content("\n".join(body_lines))

    # 3. Enviar correo
    logger.info("Enviando correo con %d eventos a %s...", len(events), config.alert_email)
    try:
        # Usamos SMTP con STARTTLS
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=config.request_timeout) as server:
            server.ehlo()
            server.starttls()
            server.login(config.smtp_username, config.smtp_password)
            server.send_message(msg)
            
        logger.info("✓ Correo enviado exitosamente.")
        return True

    except smtplib.SMTPAuthenticationError as exc:
        logger.error("Error SMTP: Fallo de autenticación. Verifica usuario/contraseña o permisos de la app.")
        return False
    except TimeoutError as exc:
        logger.error("Error SMTP: Timeout al conectar con el servidor.")
        return False
    except smtplib.SMTPConnectError as exc:
        logger.error("Error SMTP: No se pudo conectar al servidor SMTP en %s:%d.", config.smtp_host, config.smtp_port)
        return False
    except smtplib.SMTPException as exc:
        logger.error("Error SMTP: Excepción general al enviar el correo: %s", exc)
        return False
    except Exception as exc:
        logger.exception("Error inesperado al intentar enviar el correo: %s", exc)
        return False
