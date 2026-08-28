"""
main.py — Orquestador principal del Monitor de Rally.

FASE 1: Carga configuración → autentica → scrapea → muestra resumen seguro.

NO envía alertas.
NO compara snapshots previos.
NO imprime credenciales ni tokens.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from .auth import AuthenticationError, login
from .config import AppConfig, load_config
from .scraper import SnapshotData, get_competencia_data, IndicadoresAPI, SedeAPI
from .detector import detectar_cambios, ChangeEvent
from .notifier import send_notification
import argparse

# ---------------------------------------------------------------------------
# Configuración del logging
# ---------------------------------------------------------------------------

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def configurar_logging(nivel: str = "INFO") -> None:
    """
    Configura el sistema de logging con nivel y formato definidos.

    Args:
        nivel: Nivel de log (DEBUG, INFO, WARNING, ERROR).
    """
    nivel_num = getattr(logging, nivel.upper(), logging.INFO)

    # Usar StreamHandler con encoding utf-8 explícito para evitar UnicodeEncodeError
    # en terminales Windows con codepage cp1252
    handler = logging.StreamHandler(sys.stdout)
    try:
        handler.stream.reconfigure(encoding="utf-8")  # Python 3.7+
    except AttributeError:
        pass  # fallback silencioso si reconfigure no está disponible

    logging.basicConfig(
        level=nivel_num,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[handler],
    )


# ---------------------------------------------------------------------------
# Ruta del snapshot
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = REPO_ROOT / "data" / "snapshot.json"


# ---------------------------------------------------------------------------
# Cargar y Guardar snapshot
# ---------------------------------------------------------------------------

def cargar_snapshot_anterior() -> SnapshotData | None:
    """
    Carga el snapshot anterior desde data/snapshot.json si existe.
    Si no existe o está corrupto, retorna None.
    """
    if not SNAPSHOT_PATH.exists():
        return None
        
    try:
        with SNAPSHOT_PATH.open("r", encoding="utf-8") as f:
            datos = json.load(f)
            
        ind_data = datos.get("indicadores", {})
        sede_raw = datos.get("sede_data")
        
        snapshot = SnapshotData(
            indicadores=IndicadoresAPI(
                inscritos=ind_data.get("inscritos", 0),
                participantes=ind_data.get("participantes", 0),
                mentores=ind_data.get("mentores", 0),
                jurados=ind_data.get("jurados", 0),
                equipos=ind_data.get("equipos", 0),
                equipos_abiertos=ind_data.get("equipos_abiertos", 0),
                equipos_conformados=ind_data.get("equipos_conformados", 0),
            )
        )
        if sede_raw:
            snapshot.sede_data = SedeAPI(nombre=datos.get("sede", ""), raw_data=sede_raw)
            
        return snapshot
    except Exception as exc:
        logging.getLogger(__name__).warning("No se pudo cargar snapshot anterior: %s", exc)
        return None


def guardar_snapshot(snapshot: SnapshotData, config: AppConfig) -> None:
    """
    Guarda los datos extraídos en data/snapshot.json.

    SEGURIDAD: no guarda credenciales, cookies ni tokens.

    Args:
        snapshot: Datos extraídos en el ciclo de scraping.
        config: Configuración de la aplicación.
    """
    timestamp = datetime.now(tz=timezone.utc).isoformat()

    datos = {
        "edition_uuid": config.edition_uuid,
        "sede": config.sede_name,
        "timestamp": timestamp,
        "indicadores": {
            "inscritos": snapshot.indicadores.inscritos,
            "participantes": snapshot.indicadores.participantes,
            "mentores": snapshot.indicadores.mentores,
            "jurados": snapshot.indicadores.jurados,
            "equipos": snapshot.indicadores.equipos,
            "equipos_abiertos": snapshot.indicadores.equipos_abiertos,
            "equipos_conformados": snapshot.indicadores.equipos_conformados,
        },
        "sede_data": snapshot.sede_data.raw_data if snapshot.sede_data else None,
    }

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SNAPSHOT_PATH.open("w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)

    logging.getLogger(__name__).info(
        "Snapshot guardado en: %s", SNAPSHOT_PATH
    )


# ---------------------------------------------------------------------------
# Resumen seguro en consola (sin emojis — compatible con Windows cp1252)
# ---------------------------------------------------------------------------


def mostrar_resumen(snapshot: SnapshotData, config: AppConfig, eventos: list[ChangeEvent]) -> None:
    """
    Muestra un resumen limpio y seguro en consola.

    Nunca imprime credenciales, cookies ni tokens.
    Sin emojis para compatibilidad con Windows cp1252.

    Args:
        snapshot: Datos del ciclo de scraping.
        config: Configuración de la aplicación.
    """
    sep = "=" * 60
    ind = snapshot.indicadores

    lines = [
        "",
        sep,
        "=== MONITOR RALLY ===",
        "",
        "  Edicion: IV Rally Nacional de Innovacion - Nicaragua Innova 2026",
        f"  Sede: {config.sede_name}",
        "",
        "  API: OK",
        "  Login: OK",
        "",
        f"  Inscritos: {ind.inscritos}",
        f"  Participantes: {ind.participantes}",
        f"  Mentores: {ind.mentores}",
        f"  Jurados: {ind.jurados}",
        f"  Equipos: {ind.equipos}",
        f"  Equipos abiertos: {ind.equipos_abiertos}",
        f"  Equipos conformados: {ind.equipos_conformados}",
        "",
        f"  Sede {config.sede_name.split(',')[0]}:",
    ]
    
    if snapshot.sede_data:
        # Simplificación de lo que hay.
        lines.append("  Encontrada con registros")
    else:
        lines.append("  Sin registros actualmente")

    if snapshot.errores:
        lines += [
            "",
            f"[ERRORES DURANTE CONSULTA API: {len(snapshot.errores)}]",
        ]
        for i, err in enumerate(snapshot.errores, 1):
            lines.append(f"  {i}. {err}")

    lines += ["", sep]
    lines += ["", "=== DETECTOR ===", ""]
    lines.append(f"Eventos detectados: {len(eventos)}")

    for ev in eventos:
        lines.append("")
        lines.append(f"  Tipo: {ev.tipo}")
        if ev.campo:
            lines.append(f"  Campo: {ev.campo}")
        if ev.incremento is not None:
            lines.append(f"  Incremento: +{ev.incremento}")
        else:
            lines.append(f"  Anterior: {ev.anterior}")
            lines.append(f"  Actual: {ev.actual}")
        lines.append(f"  Sede: {ev.sede}")

    lines += ["", sep, ""]

    output = "\n".join(lines)
    sys.stdout.write(output + "\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------


def main() -> int:
    """
    Orquestador principal de la Fase 1.

    Returns:
        Código de salida (0 = éxito, 1 = error).
    """
    configurar_logging("INFO")
    logger = logging.getLogger(__name__)

    logger.info("=== Monitor Rally - FASE 1 iniciando ===")

    # 1. Cargar configuración
    try:
        config: AppConfig = load_config()
    except EnvironmentError as exc:
        logger.error("Error de configuracion: %s", exc)
        sys.stdout.write(
            "\nERROR: Variables de entorno no configuradas.\n"
            "  Crea un archivo .env basado en .env.example y completa:\n"
            "    RALLY_USERNAME=tu_usuario\n"
            "    RALLY_PASSWORD=tu_contrasena\n\n"
        )
        return 1

    # 1.5 Test Email flag
    parser = argparse.ArgumentParser(description="Monitor del Rally de Innovación")
    parser.add_argument("--test-email", action="store_true", help="Enviar correo de prueba y salir")
    args, _ = parser.parse_known_args()
    
    if args.test_email:
        logger.info("Ejecutando en modo --test-email. Enviando correo de prueba...")
        evento_prueba = ChangeEvent(
            tipo="TEST_CORREO",
            campo="test",
            anterior=0,
            actual=1,
            incremento=1,
            sede=config.sede_name
        )
        exito = send_notification([evento_prueba], config)
        if exito:
            logger.info("Correo de prueba enviado con éxito.")
        else:
            logger.error("Falló el envío del correo de prueba.")
        return 0 if exito else 1

    # 2. Autenticar
    try:
        session = login(config)
    except AuthenticationError as exc:
        logger.error("Fallo de autenticacion: %s", exc)
        sys.stdout.write(
            "\nAUTENTICACION FALLIDA.\n"
            "  Causas posibles:\n"
            "  - Credenciales incorrectas en .env\n"
            "  - La plataforma esta caida o devuelve error\n"
            "  - El formulario de login cambio (revisa auth.py)\n"
            "  - HTTP 403: sesion bloqueada o CSRF invalido\n"
            "  - HTTP 404: URL de login incorrecta\n"
            f"  Detalle: {exc}\n\n"
        )
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error inesperado en autenticacion.")
        sys.stdout.write(f"\nError inesperado: {exc}\n\n")
        return 1

    # 2.5 Cargar snapshot anterior (Fase 2)
    snapshot_anterior = cargar_snapshot_anterior()

    # 3. Ejecutar scraping
    logger.info("Consultando APIs del dashboard...")
    snapshot = get_competencia_data(session, config)

    # 3.5 Detectar eventos
    eventos = detectar_cambios(snapshot_anterior, snapshot, config.sede_name)

    # 4. Notificar si hay cambios reales
    if eventos:
        logger.info("Se detectaron %d eventos. Notificando por correo...", len(eventos))
        exito = send_notification(eventos, config)
        if not exito:
            logger.error("Fallo al enviar notificación. Abortando para no perder el evento.")
            sys.exit(1)
    else:
        logger.info("No se detectaron cambios. Omitiendo notificación.")

    # 5. Guardar snapshot actual (Debe ir después de notificar para asegurar que la
    # notificación no se pierda permanentemente si el programa crashea durante el envío)
    try:
        guardar_snapshot(snapshot, config)
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo guardar el snapshot: %s", exc)
        sys.exit(1)

    # 6. Mostrar resumen en consola
    mostrar_resumen(snapshot, config, eventos)

    logger.info("=== Monitor Rally - completado ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
