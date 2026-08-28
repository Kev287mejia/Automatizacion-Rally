import pytest
from unittest.mock import patch, MagicMock
import smtplib

from app.config import AppConfig
from app.detector import ChangeEvent
from app.notifier import send_notification

@pytest.fixture
def mock_config():
    return AppConfig(
        username="test", password="pwd", edition_uuid="uuid-test",
        sede_name="BICU, Puerto Cabezas", base_url="http://test", login_url="http://test/",
        dashboard_url="http://test/dash", participantes_url="http://test/part",
        equipos_url="http://test/eq", api_datos_url="http://test/api/datos",
        api_sedes_url="http://test/api/sedes", request_timeout=5, user_agent="test",
        smtp_host="smtp.test.com", smtp_port=587, smtp_username="user@test.com",
        smtp_password="password123", alert_email="alert@test.com"
    )

def test_lista_vacia_no_envia_correo(mock_config):
    with patch("smtplib.SMTP") as mock_smtp:
        resultado = send_notification([], mock_config)
        
        assert resultado is True
        mock_smtp.assert_not_called()


@patch("smtplib.SMTP")
def test_un_evento_genera_email(mock_smtp_class, mock_config):
    mock_smtp_instance = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance
    
    eventos = [ChangeEvent(tipo="NUEVO_INSCRITO", campo="inscritos", anterior=0, actual=1, incremento=1, sede="BICU")]
    
    resultado = send_notification(eventos, mock_config)
    
    assert resultado is True
    # Verificamos conexión
    mock_smtp_class.assert_called_with("smtp.test.com", 587, timeout=5)
    # Verificamos protocolo TLS y Login
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_with("user@test.com", "password123")
    # Verificamos envío
    mock_smtp_instance.send_message.assert_called_once()
    
    # Comprobar contenido del mensaje
    msg = mock_smtp_instance.send_message.call_args[0][0]
    assert msg['Subject'] == "[RALLY] Cambios detectados — BICU"
    assert "NUEVO INSCRITO" in msg.get_content()
    assert "Anterior: 0" in msg.get_content()
    assert "Incremento: +1" in msg.get_content()


@patch("smtplib.SMTP")
def test_multiples_eventos_un_solo_email(mock_smtp_class, mock_config):
    mock_smtp_instance = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance
    
    eventos = [
        ChangeEvent(tipo="NUEVO_INSCRITO", campo="inscritos", anterior=0, actual=1, incremento=1, sede="BICU"),
        ChangeEvent(tipo="EQUIPO_CONFORMADO", campo="equipos_conformados", anterior=0, actual=1, incremento=1, sede="BICU")
    ]
    
    resultado = send_notification(eventos, mock_config)
    
    assert resultado is True
    mock_smtp_instance.send_message.assert_called_once()  # Sólo un correo
    
    msg = mock_smtp_instance.send_message.call_args[0][0]
    content = msg.get_content()
    assert "Se detectaron 2 cambios" in content
    assert "NUEVO INSCRITO" in content
    assert "EQUIPO CONFORMADO" in content


@patch("smtplib.SMTP")
def test_configuracion_invalida(mock_smtp_class, mock_config):
    # Rompemos la configuración intencionalmente
    bad_config = AppConfig(
        username="test", password="pwd", edition_uuid="uuid-test",
        sede_name="BICU", base_url="http://test", login_url="http://test/",
        dashboard_url="http://test/dash", participantes_url="http://test/part",
        equipos_url="http://test/eq", api_datos_url="http://test/api/datos",
        api_sedes_url="http://test/api/sedes", request_timeout=5, user_agent="test",
        smtp_host="", smtp_port=587, smtp_username="", smtp_password="", alert_email=""
    )
    
    eventos = [ChangeEvent(tipo="TEST", campo="t", anterior=0, actual=1, incremento=1, sede="BICU")]
    
    resultado = send_notification(eventos, bad_config)
    
    assert resultado is False
    mock_smtp_class.assert_not_called()


@patch("smtplib.SMTP")
def test_error_conexion(mock_smtp_class, mock_config, caplog):
    mock_smtp_class.side_effect = smtplib.SMTPConnectError(421, "Connection refused")
    
    eventos = [ChangeEvent(tipo="TEST", campo="t", anterior=0, actual=1, incremento=1, sede="BICU")]
    
    resultado = send_notification(eventos, mock_config)
    
    assert resultado is False
    assert "No se pudo conectar al servidor SMTP" in caplog.text


@patch("smtplib.SMTP")
def test_error_autenticacion(mock_smtp_class, mock_config, caplog):
    mock_smtp_instance = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance
    mock_smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, "Auth failed")
    
    eventos = [ChangeEvent(tipo="TEST", campo="t", anterior=0, actual=1, incremento=1, sede="BICU")]
    
    resultado = send_notification(eventos, mock_config)
    
    assert resultado is False
    assert "Fallo de autenticación" in caplog.text
    # Probar que no hay credenciales en el log
    assert "password123" not in caplog.text


@patch("smtplib.SMTP")
def test_asunto_y_cuerpo_caracteres_especiales(mock_smtp_class, mock_config):
    mock_smtp_instance = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance
    
    # Evento con tildes y eñes
    eventos = [ChangeEvent(tipo="CAMBIO_SEDE", campo="sede_data", anterior={"año": 2025}, actual={"año": 2026}, sede="León, España")]
    
    resultado = send_notification(eventos, mock_config)
    
    assert resultado is True
    msg = mock_smtp_instance.send_message.call_args[0][0]
    assert msg['Subject'] == "[RALLY] Cambios detectados — León, España"
    assert "2026" in msg.get_content()
