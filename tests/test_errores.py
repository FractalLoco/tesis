import psycopg
from psycopg import errors

from backend.errores import limpiar_detalle, traducir_psycopg

def test_traduce_por_sqlstate():
    status, codigo, _ = traducir_psycopg(errors.lookup("42601")("syntax error"))
    assert (status, codigo) == (400, "error_sintaxis")

def test_traduce_por_clase_de_sqlstate():
    _, codigo, _ = traducir_psycopg(errors.lookup("22P02")("invalid input"))
    assert codigo == "datos_invalidos"

def test_reconoce_clave_incorrecta_con_texto_mal_decodificado():
    # Así llega el error de un servidor en español: sin SQLSTATE y con "\ufffd".
    exc = psycopg.OperationalError(
        "connection failed: FATAL:  la autentificaci\ufffdn password fall\ufffd para el usuario"
    )
    status, codigo, _ = traducir_psycopg(exc)
    assert (status, codigo) == (401, "credenciales_invalidas")
    assert limpiar_detalle(str(exc)) is None

def test_reconoce_servidor_inalcanzable():
    exc = psycopg.OperationalError("failed to resolve host 'x.invalid'")
    assert traducir_psycopg(exc)[1] == "servidor_inalcanzable"

def test_limpia_prefijo_y_repeticiones_de_psycopg():
    texto = (
        'connection failed: connection to server at "127.0.0.1", port 5432 failed: '
        'FATAL:  database "x" does not exist\n'
        "Multiple connection attempts failed. All failures were:\n- host: ..."
    )
    assert limpiar_detalle(texto) == 'database "x" does not exist'
