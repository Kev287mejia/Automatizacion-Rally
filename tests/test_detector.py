import pytest

from app.scraper import SnapshotData, IndicadoresAPI, SedeAPI
from app.detector import detectar_cambios, ChangeEvent

SEDE_NAME = "BICU, Puerto Cabezas"

def crear_snapshot(
    inscritos=0,
    participantes=0,
    mentores=0,
    jurados=0,
    equipos=0,
    equipos_abiertos=0,
    equipos_conformados=0,
    sede_data=None
):
    """Helper para crear un snapshot con los datos proporcionados."""
    snapshot = SnapshotData(
        indicadores=IndicadoresAPI(
            inscritos=inscritos,
            participantes=participantes,
            mentores=mentores,
            jurados=jurados,
            equipos=equipos,
            equipos_abiertos=equipos_abiertos,
            equipos_conformados=equipos_conformados,
        )
    )
    if sede_data is not None:
        snapshot.sede_data = SedeAPI(nombre=SEDE_NAME, raw_data=sede_data)
    return snapshot


def test_primer_snapshot():
    actual = crear_snapshot(inscritos=5)
    eventos = detectar_cambios(None, actual, SEDE_NAME)
    assert len(eventos) == 0


def test_sin_cambios():
    anterior = crear_snapshot(inscritos=5)
    actual = crear_snapshot(inscritos=5)
    eventos = detectar_cambios(anterior, actual, SEDE_NAME)
    assert len(eventos) == 0


def test_nuevo_inscrito():
    anterior = crear_snapshot(inscritos=0)
    actual = crear_snapshot(inscritos=1)
    eventos = detectar_cambios(anterior, actual, SEDE_NAME)
    
    assert len(eventos) == 1
    ev = eventos[0]
    assert ev.tipo == "NUEVO_INSCRITO"
    assert ev.campo == "inscritos"
    assert ev.anterior == 0
    assert ev.actual == 1
    assert ev.incremento == 1
    assert ev.sede == SEDE_NAME


def test_nuevo_participante():
    anterior = crear_snapshot(participantes=2)
    actual = crear_snapshot(participantes=5)
    eventos = detectar_cambios(anterior, actual, SEDE_NAME)
    
    assert len(eventos) == 1
    assert eventos[0].tipo == "NUEVO_PARTICIPANTE"
    assert eventos[0].incremento == 3


def test_nuevo_mentor():
    anterior = crear_snapshot(mentores=1)
    actual = crear_snapshot(mentores=2)
    eventos = detectar_cambios(anterior, actual, SEDE_NAME)
    
    assert len(eventos) == 1
    assert eventos[0].tipo == "NUEVO_MENTOR"


def test_nuevo_jurado():
    anterior = crear_snapshot(jurados=3)
    actual = crear_snapshot(jurados=4)
    eventos = detectar_cambios(anterior, actual, SEDE_NAME)
    
    assert len(eventos) == 1
    assert eventos[0].tipo == "NUEVO_JURADO"


def test_nuevo_equipo():
    anterior = crear_snapshot(equipos=0)
    actual = crear_snapshot(equipos=1)
    eventos = detectar_cambios(anterior, actual, SEDE_NAME)
    
    assert len(eventos) == 1
    assert eventos[0].tipo == "NUEVO_EQUIPO"


def test_equipo_conformado():
    anterior = crear_snapshot(equipos_abiertos=2, equipos_conformados=0)
    actual = crear_snapshot(equipos_abiertos=1, equipos_conformados=1)
    eventos = detectar_cambios(anterior, actual, SEDE_NAME)
    
    # Solo debe detectar EQUIPO_CONFORMADO
    assert len(eventos) == 1
    assert eventos[0].tipo == "EQUIPO_CONFORMADO"
    assert eventos[0].campo == "equipos_conformados"
    assert eventos[0].incremento == 1


def test_cambio_datos_bicu():
    anterior = crear_snapshot(sede_data=None)
    actual = crear_snapshot(sede_data={"inscritos": 10})
    eventos = detectar_cambios(anterior, actual, SEDE_NAME)
    
    assert len(eventos) == 1
    assert eventos[0].tipo == "DATOS_SEDE_DISPONIBLES"
    assert eventos[0].actual == {"inscritos": 10}

    # Siguiente cambio real
    anterior_2 = crear_snapshot(sede_data={"inscritos": 10})
    actual_2 = crear_snapshot(sede_data={"inscritos": 15})
    eventos_2 = detectar_cambios(anterior_2, actual_2, SEDE_NAME)
    
    assert len(eventos_2) == 1
    assert eventos_2[0].tipo == "CAMBIO_SEDE"
    assert eventos_2[0].anterior == {"inscritos": 10}
    assert eventos_2[0].actual == {"inscritos": 15}


def test_none_a_none_y_cero_a_cero():
    # En la nueva implementación None no es posible (usa defaults a 0),
    # pero podemos probar que el comportamiento base sea consistente.
    anterior = SnapshotData() # Todo 0 o defaults
    actual = SnapshotData()
    eventos = detectar_cambios(anterior, actual, SEDE_NAME)
    assert len(eventos) == 0


def test_valores_iguales_estructuras_equivalentes():
    anterior = crear_snapshot(sede_data={"a": 1, "b": 2})
    actual = crear_snapshot(sede_data={"b": 2, "a": 1}) # Orden distinto dict python 3.7+ o misma data
    eventos = detectar_cambios(anterior, actual, SEDE_NAME)
    # Como los diccionarios se comparan por contenido y no orden, no debería haber evento
    assert len(eventos) == 0


def test_multiples_cambios_simultaneos():
    anterior = crear_snapshot(inscritos=1, equipos=0)
    actual = crear_snapshot(inscritos=3, equipos=1)
    eventos = detectar_cambios(anterior, actual, SEDE_NAME)
    
    assert len(eventos) == 2
    tipos = [e.tipo for e in eventos]
    assert "NUEVO_INSCRITO" in tipos
    assert "NUEVO_EQUIPO" in tipos


def test_datos_invalidos_o_inesperados():
    # En esta versión, si la API devuelve algo que no es dict no llega al SnapshotData
    # Sin embargo probaremos si el usuario metió un str en sede_data por error
    anterior = crear_snapshot(sede_data={"k": "v"})
    actual = crear_snapshot(sede_data="esto_es_invalido_pero_detectado")
    eventos = detectar_cambios(anterior, actual, SEDE_NAME)
    
    assert len(eventos) == 1
    assert eventos[0].tipo == "CAMBIO_SEDE"
