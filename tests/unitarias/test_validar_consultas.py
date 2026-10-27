# Pruebas de validar_consulta: la regla que deja pasar solo consultas de lectura.
# Es la que cumple la promesa del sistema de no modificar nunca la base del usuario.
import pytest

from backend.errores import ErrorNegocio
from backend.services.reglas import PARA_CONSOLA, validar_consulta

def codigo_de(sql, permitidas=None):
    """Valida una consulta que DEBE ser rechazada y devuelve el código del error.
    pytest.raises hace que la prueba falle si la consulta no lanza ErrorNegocio."""
    with pytest.raises(ErrorNegocio) as e:
        validar_consulta(sql) if permitidas is None else validar_consulta(sql, permitidas)
    return e.value.codigo

# --- Consultas que se aceptan ---

def test_acepta_select_y_quita_el_punto_y_coma_final():
    assert validar_consulta("  SELECT * FROM t;  ") == "SELECT * FROM t"

def test_acepta_with_y_select_entre_parentesis():
    validar_consulta("WITH x AS (SELECT 1) SELECT * FROM x")
    validar_consulta("(SELECT 1) UNION (SELECT 2)")

def test_punto_y_coma_dentro_de_textos_o_comentarios_no_cuenta():
    # Un ";" dentro de un texto o comentario no separa sentencias.
    validar_consulta("SELECT 'a;b', \"col;rara\" FROM t -- fin; de linea")
    validar_consulta("SELECT $$texto; con punto y coma$$ /* otro; */")

def test_select_for_update_dentro_de_with_no_es_falso_positivo():
    validar_consulta("WITH x AS (SELECT * FROM t) SELECT * FROM x FOR UPDATE")

# --- Consultas que se rechazan ---

def test_rechaza_consulta_vacia_o_solo_comentarios():
    assert codigo_de("   ") == "consulta_vacia"
    assert codigo_de("-- nada") == "consulta_vacia"

def test_rechaza_varias_sentencias_juntas():
    # Así alguien podría intentar desactivar el modo solo lectura y luego borrar.
    assert codigo_de("SET default_transaction_read_only = off; DELETE FROM t") == "varias_sentencias"
    assert codigo_de("SELECT 1; SELECT 2") == "varias_sentencias"

def test_rechaza_consultas_que_modifican_datos():
    assert codigo_de("DELETE FROM t") == "consulta_no_permitida"
    assert codigo_de("update t set a = 1") == "consulta_no_permitida"   # también en minúscula
    # Un DELETE escondido dentro de un WITH también se detecta.
    assert codigo_de("WITH x AS (DELETE FROM t RETURNING *) SELECT * FROM x") == "consulta_no_permitida"

def test_solo_la_consola_acepta_show_y_explain():
    validar_consulta("SHOW work_mem", PARA_CONSOLA)
    assert codigo_de("SHOW work_mem") == "consulta_no_permitida"
