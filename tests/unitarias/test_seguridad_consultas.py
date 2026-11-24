# Pruebas de lo que se ejecuta: la consola, el SQL sugerido y la base gemela.
import pytest

from analizador.identificadores import citar
from backend.errores import ErrorNegocio
from backend.services.reglas import PARA_CONSOLA, validar_consulta

def test_la_consola_rechaza_explain_analyze():
    for sql in ("EXPLAIN ANALYZE SELECT 1", "EXPLAIN (ANALYZE, BUFFERS) SELECT 1"):
        with pytest.raises(ErrorNegocio) as e:
            validar_consulta(sql, PARA_CONSOLA)
        assert e.value.codigo == "consulta_no_permitida"
        assert e.value.status == 403

def test_la_consola_acepta_explain_sin_analyze():
    validar_consulta("EXPLAIN (FORMAT JSON) SELECT 1", PARA_CONSOLA)
    validar_consulta("EXPLAIN SELECT analyze FROM t", PARA_CONSOLA)

# --- Identificadores del SQL sugerido ---

def test_identificadores_normales_no_cambian():
    assert citar("orders") == "orders"
    assert citar("o_totalprice") == "o_totalprice"

def test_identificadores_especiales_se_citan():
    assert citar("Orders") == '"Orders"'
    assert citar('mi"tabla') == '"mi""tabla"'
    assert citar("select") == '"select"'
    assert citar("con espacio") == '"con espacio"'

