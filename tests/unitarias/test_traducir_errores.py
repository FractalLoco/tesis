# Pruebas de la traducción de errores de PostgreSQL a mensajes claros.
# PostgreSQL identifica cada error con un código SQLSTATE de 5 caracteres
# (ej. 42601 = error de sintaxis); la app lo convierte en un código HTTP
# y un mensaje entendible para el usuario.
import psycopg
from psycopg import errors

from backend.errores import limpiar_detalle, traducir_psycopg

def test_traduce_un_sqlstate_conocido():
    # errors.lookup crea el mismo error que lanzaría PostgreSQL.
    status, codigo, _ = traducir_psycopg(errors.lookup("42601")("syntax error"))
    assert (status, codigo) == (400, "error_sintaxis")

def test_traduce_por_la_clase_del_sqlstate():
    # Los 2 primeros caracteres son la clase: 22 = datos inválidos.
    _, codigo, _ = traducir_psycopg(errors.lookup("22P02")("invalid input"))
    assert codigo == "datos_invalidos"

def test_reconoce_clave_incorrecta_aunque_venga_mal_codificada():
    # Así llega el error de un servidor en español: sin SQLSTATE y con "�"
    # en lugar de las tildes.
    exc = psycopg.OperationalError(
        "connection failed: FATAL:  la autentificaci�n password fall� para el usuario"
    )
    status, codigo, _ = traducir_psycopg(exc)
    assert (status, codigo) == (401, "credenciales_invalidas")
    assert limpiar_detalle(str(exc)) is None

def test_reconoce_servidor_inalcanzable():
    exc = psycopg.OperationalError("failed to resolve host 'x.invalid'")
    assert traducir_psycopg(exc)[1] == "servidor_inalcanzable"

def test_deja_solo_la_parte_util_del_mensaje():
    texto = (
        'connection failed: connection to server at "127.0.0.1", port 5432 failed: '
        'FATAL:  database "x" does not exist\n'
        "Multiple connection attempts failed. All failures were:\n- host: ..."
    )
    assert limpiar_detalle(texto) == 'database "x" does not exist'
