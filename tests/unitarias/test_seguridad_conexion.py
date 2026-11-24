# Pruebas de los datos de conexión: un solo servidor y nombres sin caracteres raros.
import pytest
from pydantic import ValidationError

from backend.models.schemas import Conexion

@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "db.interna", "::1"])
def test_acepta_un_solo_host_valido(host):
    assert Conexion(dbname="b", user="u", host=host).host == host

@pytest.mark.parametrize("host", ["a,b", "a b", "/var/run/postgresql", "a\nb"])
def test_rechaza_listas_espacios_y_sockets(host):
    with pytest.raises(ValidationError):
        Conexion(dbname="b", user="u", host=host)

@pytest.mark.parametrize(("campo", "valor"), [
    ("dbname", "base\x00mal"),
    ("user", "usuario con espacio"),
    ("password", "clave\x00mal"),
])
def test_rechaza_caracteres_nul_y_nombres_malformados(campo, valor):
    datos = {"dbname": "base", "user": "usuario", "password": "", "host": "localhost"}
    datos[campo] = valor
    with pytest.raises(ValidationError):
        Conexion(**datos)
