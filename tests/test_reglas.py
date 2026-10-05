import pytest

from backend.errores import ErrorNegocio
from backend.services.reglas import PARA_CONSOLA, validar_consulta

def codigo_de(sql, permitidas=None):
    with pytest.raises(ErrorNegocio) as e:
        validar_consulta(sql) if permitidas is None else validar_consulta(sql, permitidas)
    return e.value.codigo

def test_acepta_select_y_quita_punto_y_coma_final():
    assert validar_consulta("  SELECT * FROM t;  ") == "SELECT * FROM t"

def test_acepta_with_y_select_entre_parentesis():
    validar_consulta("WITH x AS (SELECT 1) SELECT * FROM x")
    validar_consulta("(SELECT 1) UNION (SELECT 2)")

def test_punto_y_coma_dentro_de_textos_y_comentarios_no_cuenta():
    validar_consulta("SELECT 'a;b', \"col;rara\" FROM t -- fin; de linea")
    validar_consulta("SELECT $$texto; con punto y coma$$ /* otro; */")

def test_rechaza_consulta_vacia_o_solo_comentarios():
    assert codigo_de("   ") == "consulta_vacia"
    assert codigo_de("-- nada") == "consulta_vacia"

def test_rechaza_varias_sentencias():
    assert codigo_de("SET default_transaction_read_only = off; DELETE FROM t") == "varias_sentencias"
    assert codigo_de("SELECT 1; SELECT 2") == "varias_sentencias"

def test_rechaza_escrituras():
    assert codigo_de("DELETE FROM t") == "consulta_no_permitida"
    assert codigo_de("update t set a = 1") == "consulta_no_permitida"
    assert codigo_de("WITH x AS (DELETE FROM t RETURNING *) SELECT * FROM x") == "consulta_no_permitida"

def test_select_for_update_no_es_falso_positivo_en_with():
    validar_consulta("WITH x AS (SELECT * FROM t) SELECT * FROM x FOR UPDATE")

def test_la_consola_ademas_acepta_show_y_explain():
    validar_consulta("SHOW work_mem", PARA_CONSOLA)
    assert codigo_de("SHOW work_mem") == "consulta_no_permitida"
