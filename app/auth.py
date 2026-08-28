"""
auth.py — Autenticación segura mediante requests.Session.

Flujo completo:
    1. GET a la página de login → obtener CSRF token
    2. POST username + password + csrfmiddlewaretoken
    3. Verificación REAL de que el login fue exitoso:
       - No redirigió de vuelta al login
       - Existe cookie de sesión Django ('sessionid')
       - Se puede acceder a una página protegida

IMPORTANTE:
    - Nunca se imprime la contraseña.
    - Nunca se imprimen cookies ni tokens.
    - Un HTTP 200 al POST NO es suficiente para confirmar login.
"""

import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config import AppConfig

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Excepción lanzada cuando la autenticación falla por cualquier motivo."""


def _extract_csrf_token(html: str) -> Optional[str]:
    """
    Extrae el CSRF token de un formulario Django estándar.

    Django incluye el token en:
        <input type="hidden" name="csrfmiddlewaretoken" value="...">

    Args:
        html: Contenido HTML de la página de login.

    Returns:
        El valor del CSRF token, o None si no se encuentra.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Método 1: input hidden estándar de Django
    csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
    if csrf_input and csrf_input.get("value"):
        return str(csrf_input["value"])

    # Método 2: cookie csrftoken (fallback)
    # No aplica aquí (se extrae de la cookie en _get_csrf_from_cookie)
    logger.warning(
        "No se encontró el campo csrfmiddlewaretoken en el HTML del login. "
        "La estructura del formulario puede haber cambiado."
    )
    return None


def _get_csrf_from_cookie(session: requests.Session) -> Optional[str]:
    """
    Extrae el CSRF token desde la cookie 'csrftoken' de la sesión.

    Django puede establecer el token via cookie además del formulario.

    Args:
        session: Sesión HTTP activa.

    Returns:
        Valor del CSRF token desde cookie, o None si no existe.
    """
    csrf_cookie = session.cookies.get("csrftoken")
    if csrf_cookie:
        return csrf_cookie
    return None


def _session_appears_authenticated(
    session: requests.Session,
    login_url: str,
    protected_url: str,
    timeout: int,
) -> tuple[bool, str]:
    """
    Verifica de forma exhaustiva que la sesión esté realmente autenticada.

    Comprobaciones realizadas:
        1. Existe cookie 'sessionid' en la sesión.
        2. Al acceder a una URL protegida, no redirige al login.

    Args:
        session: Sesión HTTP con cookies post-login.
        login_url: URL del login (para detectar redirecciones indeseadas).
        protected_url: URL protegida para verificar acceso.
        timeout: Timeout HTTP en segundos.

    Returns:
        Tupla (autenticado: bool, motivo: str).
    """
    # Verificación 1: cookie de sesión Django
    session_cookie_names = {"sessionid", "session"}
    found_session_cookies = {
        name
        for name in session_cookie_names
        if session.cookies.get(name) is not None
    }

    if not found_session_cookies:
        return False, "No se encontró cookie de sesión (sessionid) después del login."

    # Verificación 2: acceso a página protegida sin redirección al login
    try:
        probe = session.get(
            protected_url,
            timeout=timeout,
            allow_redirects=True,
        )
        probe.raise_for_status()

        # Detección de no-autenticado basada en CONTENIDO, no en URL.
        # Razón: la URL de login ES la homepage (/), por lo que comparar URLs
        # generaría falsos positivos. En cambio, si la página protegida devuelve
        # un formulario con campo password, significa que no estamos autenticados.
        if 'type="password"' in probe.text or "type='password'" in probe.text:
            return (
                False,
                "La pagina protegida contiene un formulario de login. "
                "Las credenciales pueden ser incorrectas.",
            )

    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response else "desconocido"
        if status == 403:
            return False, f"HTTP 403 al verificar acceso protegido: {protected_url}"
        if status == 404:
            return False, f"HTTP 404: URL de verificación no existe: {protected_url}"
        return False, f"HTTP {status} al verificar autenticación: {exc}"

    except requests.RequestException as exc:
        return False, f"Error de red al verificar autenticación: {exc}"

    return True, "Autenticación verificada correctamente."


def login(config: AppConfig) -> requests.Session:
    """
    Crea una sesión HTTP autenticada contra la plataforma Rally.

    Flujo completo:
        GET login → extraer CSRF → POST credenciales → verificar sesión real

    Args:
        config: Configuración de la aplicación (AppConfig).

    Returns:
        requests.Session autenticada y lista para hacer scraping.

    Raises:
        AuthenticationError: Si el login falla por cualquier motivo.
        requests.RequestException: Si hay un error de red irrecuperable.
    """
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-NI,es;q=0.9,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
        }
    )

    # ------------------------------------------------------------------ #
    # PASO 1: GET login → obtener CSRF token
    # ------------------------------------------------------------------ #
    logger.info("Iniciando autenticación. Obteniendo página de login...")
    try:
        login_get = session.get(
            config.login_url,
            timeout=config.request_timeout,
            allow_redirects=True,
        )
        login_get.raise_for_status()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response else "?"
        raise AuthenticationError(
            f"No se pudo obtener la página de login (HTTP {status}): {config.login_url}"
        ) from exc
    except requests.RequestException as exc:
        raise AuthenticationError(
            f"Error de red al acceder al login: {exc}"
        ) from exc

    # Extraer CSRF del HTML
    csrf_token = _extract_csrf_token(login_get.text)

    # Fallback: desde cookie
    if not csrf_token:
        csrf_token = _get_csrf_from_cookie(session)

    if not csrf_token:
        raise AuthenticationError(
            "No se pudo obtener el CSRF token. "
            "El formulario de login puede haber cambiado o la plataforma está caída."
        )

    logger.debug("CSRF token obtenido (valor OMITIDO en logs por seguridad).")

    # ------------------------------------------------------------------ #
    # PASO 2: POST credenciales
    # ------------------------------------------------------------------ #
    logger.info("Enviando credenciales al servidor...")

    # Detectar si el formulario tiene un campo 'next' (Django lo usa frecuentemente)
    soup = BeautifulSoup(login_get.text, "html.parser")
    next_input = soup.find("input", {"name": "next"})
    next_value = next_input["value"] if next_input and next_input.get("value") else ""

    post_data: dict[str, str] = {
        "username": config.username,
        "password": config.password,
        "csrfmiddlewaretoken": csrf_token,
    }
    if next_value:
        post_data["next"] = next_value

    try:
        login_post = session.post(
            config.login_url,
            data=post_data,
            timeout=config.request_timeout,
            allow_redirects=True,
            headers={
                "Referer": config.login_url,
                "Origin": config.base_url,
            },
        )
        login_post.raise_for_status()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response else "?"
        # Un 403 post-login puede indicar CSRF inválido
        if status == 403:
            raise AuthenticationError(
                "HTTP 403 al enviar credenciales. "
                "Posible CSRF token inválido o IP bloqueada."
            ) from exc
        raise AuthenticationError(
            f"HTTP {status} al enviar credenciales de login."
        ) from exc
    except requests.RequestException as exc:
        raise AuthenticationError(
            f"Error de red al enviar credenciales: {exc}"
        ) from exc

    logger.info(
        "POST de login completado. URL final: %s | Status: %s",
        login_post.url,
        login_post.status_code,
    )

    # ------------------------------------------------------------------ #
    # PASO 3: Verificar autenticación real
    # ------------------------------------------------------------------ #
    logger.info("Verificando autenticación en página protegida...")

    authenticated, reason = _session_appeared_authenticated_safe(
        session=session,
        login_url=config.login_url,
        protected_url=config.dashboard_url,
        timeout=config.request_timeout,
    )

    if not authenticated:
        raise AuthenticationError(
            f"Autenticación fallida: {reason} "
            "Verifica RALLY_USERNAME y RALLY_PASSWORD en tu archivo .env."
        )

    logger.info("✓ Autenticación exitosa. Sesión lista.")
    return session


def _session_appeared_authenticated_safe(
    session: requests.Session,
    login_url: str,
    protected_url: str,
    timeout: int,
) -> tuple[bool, str]:
    """
    Wrapper seguro de _session_appears_authenticated.
    Captura cualquier excepción inesperada y la convierte en (False, motivo).
    """
    try:
        return _session_appears_authenticated(
            session=session,
            login_url=login_url,
            protected_url=protected_url,
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"Error inesperado al verificar autenticación: {exc}"
