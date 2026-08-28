import pytest
import requests
from unittest.mock import MagicMock
from app.config import AppConfig
from app.scraper import (
    get_competencia_data,
    InvalidStructureError,
    ScraperError,
    SnapshotData,
)

@pytest.fixture
def mock_config():
    return AppConfig(
        username="test",
        password="pwd",
        edition_uuid="uuid-test",
        sede_name="BICU, Puerto Cabezas",
        base_url="http://test",
        login_url="http://test/",
        dashboard_url="http://test/dash",
        participantes_url="http://test/part",
        equipos_url="http://test/eq",
        api_datos_url="http://test/api/datos",
        api_sedes_url="http://test/api/sedes",
        request_timeout=5,
        user_agent="test-agent",
        smtp_host="localhost",
        smtp_port=587,
        smtp_username="test@test.com",
        smtp_password="pwd",
        alert_email="alert@test.com"
    )

@pytest.fixture
def mock_session():
    return MagicMock(spec=requests.Session)


def test_respuesta_json_valida_y_sede_encontrada(mock_session, mock_config):
    # Mock para datos
    mock_response_datos = MagicMock()
    mock_response_datos.json.return_value = {
        "ok": True,
        "indicadores": {
            "inscritos": 10,
            "participantes": 5,
        }
    }
    
    # Mock para sedes
    mock_response_sedes = MagicMock()
    mock_response_sedes.json.return_value = {
        "ok": True,
        "resultados": [
            {"nombre": "Sede Falsa", "data": 1},
            {"nombre": "BICU, Puerto Cabezas", "inscritos": 10},
        ]
    }
    
    # Configurar el side_effect para que devuelva la respuesta correcta según la URL
    def get_side_effect(url, *args, **kwargs):
        if url == mock_config.api_datos_url:
            return mock_response_datos
        elif url == mock_config.api_sedes_url:
            return mock_response_sedes
        raise ValueError(f"URL no esperada: {url}")
        
    mock_session.get.side_effect = get_side_effect
    
    snapshot = get_competencia_data(mock_session, mock_config)
    
    assert snapshot.indicadores.inscritos == 10
    assert snapshot.indicadores.participantes == 5
    assert snapshot.indicadores.mentores == 0 # Default
    assert snapshot.sede_data is not None
    assert snapshot.sede_data.nombre == "BICU, Puerto Cabezas"
    assert snapshot.sede_data.raw_data["inscritos"] == 10
    assert len(snapshot.errores) == 0


def test_respuesta_ok_false(mock_session, mock_config, caplog):
    mock_response_datos = MagicMock()
    mock_response_datos.json.return_value = {
        "ok": False,
        "indicadores": {"inscritos": 1}
    }
    mock_response_sedes = MagicMock()
    mock_response_sedes.json.return_value = {"ok": True, "resultados": []}
    
    mock_session.get.side_effect = lambda url, **kw: mock_response_datos if "datos" in url else mock_response_sedes
    
    snapshot = get_competencia_data(mock_session, mock_config)
    
    assert snapshot.indicadores.inscritos == 1
    assert "ok=False" in caplog.text


def test_estructura_inesperada(mock_session, mock_config):
    mock_response_datos = MagicMock()
    # JSON sin la clave 'indicadores'
    mock_response_datos.json.return_value = {"ok": True, "data": {}}
    mock_response_sedes = MagicMock()
    mock_response_sedes.json.return_value = {"ok": True, "resultados": []}
    
    mock_session.get.side_effect = lambda url, **kw: mock_response_datos if "datos" in url else mock_response_sedes
    
    snapshot = get_competencia_data(mock_session, mock_config)
    
    assert len(snapshot.errores) == 1
    assert "no contiene las claves" in snapshot.errores[0]


def test_error_http(mock_session, mock_config):
    # Simulamos un 403 Forbidden
    response = requests.Response()
    response.status_code = 403
    mock_session.get.side_effect = requests.HTTPError("Forbidden", response=response)
    
    snapshot = get_competencia_data(mock_session, mock_config)
    
    assert len(snapshot.errores) == 2 # Uno por datos, otro por sedes
    assert "403 Forbidden" in snapshot.errores[0]


def test_sede_no_encontrada(mock_session, mock_config):
    mock_response_datos = MagicMock()
    mock_response_datos.json.return_value = {"ok": True, "indicadores": {}}
    
    mock_response_sedes = MagicMock()
    mock_response_sedes.json.return_value = {
        "ok": True,
        "resultados": [{"nombre": "Otra Sede"}]
    }
    
    mock_session.get.side_effect = lambda url, **kw: mock_response_datos if "datos" in url else mock_response_sedes
    
    snapshot = get_competencia_data(mock_session, mock_config)
    
    assert snapshot.sede_data is None


def test_arrays_vacios(mock_session, mock_config):
    mock_response_datos = MagicMock()
    mock_response_datos.json.return_value = {"ok": True, "indicadores": {}}
    
    mock_response_sedes = MagicMock()
    # Resultados vacío
    mock_response_sedes.json.return_value = {"ok": True, "resultados": []}
    
    mock_session.get.side_effect = lambda url, **kw: mock_response_datos if "datos" in url else mock_response_sedes
    
    snapshot = get_competencia_data(mock_session, mock_config)
    
    assert snapshot.sede_data is None
    assert len(snapshot.errores) == 0
