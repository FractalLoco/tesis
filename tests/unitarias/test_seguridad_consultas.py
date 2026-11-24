# Pruebas de lo que se ejecuta: la consola, el SQL sugerido y la base gemela.
import pytest

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

