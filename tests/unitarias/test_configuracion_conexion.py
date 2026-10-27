# Pruebas de get_db_config: arma los datos de conexión mezclando lo que manda la
# pantalla con lo del .env. Lo importante es la contraseña: la del .env solo se
# usa si PRECARGAR_CONEXION está activo y la conexión es a la misma base del .env,
# para no enviársela nunca a otro servidor.
import pytest

from analizador import conexion

DEL_ENV = {"host": "localhost", "port": "5432", "dbname": "optimizacion", "user": "analizador_ro"}

@pytest.fixture
def env(monkeypatch):
    """Simula un .env con estos datos y una clave guardada."""
    monkeypatch.setattr(conexion, "DB_HOST", DEL_ENV["host"])
    monkeypatch.setattr(conexion, "DB_PORT", DEL_ENV["port"])
    monkeypatch.setattr(conexion, "DB_NAME", DEL_ENV["dbname"])
    monkeypatch.setattr(conexion, "DB_USER", DEL_ENV["user"])
    monkeypatch.setattr(conexion, "DB_PASSWORD", "clave-del-env")
    return monkeypatch

def test_sin_datos_usa_todo_el_env(env):
    assert conexion.get_db_config() == {**DEL_ENV, "password": "clave-del-env"}

def test_la_clave_escrita_siempre_se_respeta(env):
    env.setattr(conexion, "PRECARGAR_CONEXION", True)
    cfg = conexion.get_db_config({**DEL_ENV, "password": "otra"})
    assert cfg["password"] == "otra"

def test_clave_en_blanco_usa_la_del_env_si_esta_activo_y_es_la_misma_base(env):
    env.setattr(conexion, "PRECARGAR_CONEXION", True)
    assert conexion.get_db_config({**DEL_ENV, "password": ""})["password"] == "clave-del-env"

def test_clave_en_blanco_no_usa_la_del_env_si_esta_desactivado(env):
    env.setattr(conexion, "PRECARGAR_CONEXION", False)
    assert conexion.get_db_config({**DEL_ENV, "password": ""})["password"] == ""

@pytest.mark.parametrize("cambio", [{"host": "otro-servidor.cl"}, {"port": "5433"},
                                    {"dbname": "otra_base"}, {"user": "otro_usuario"}])
def test_la_clave_del_env_nunca_se_envia_a_otra_base(env, cambio):
    # Aunque la precarga esté activa, si cambia el servidor, el puerto, la base o
    # el usuario, la contraseña en blanco se manda en blanco.
    env.setattr(conexion, "PRECARGAR_CONEXION", True)
    cfg = conexion.get_db_config({**DEL_ENV, **cambio, "password": ""})
    assert cfg["password"] == ""
