# Pruebas de lo que se ejecuta: la consola, el SQL sugerido y la base gemela.
import pytest

from analizador.analisis.gemela import _ddl_indice_seguro, _tipo_seguro
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

# --- Definiciones que se copian a la base gemela ---

def test_tipos_peligrosos_se_reemplazan_por_text():
    assert _tipo_seguro("integer") == "integer"
    assert _tipo_seguro("numeric(10,2)") == "numeric(10,2)"
    assert _tipo_seguro("text); DROP TABLE x; --") == "text"

def test_solo_se_copian_indices_simples():
    assert _ddl_indice_seguro("CREATE INDEX i ON public.t USING btree (a)")
    assert _ddl_indice_seguro("CREATE UNIQUE INDEX i ON t USING btree (a) INCLUDE (b)")
    assert not _ddl_indice_seguro("CREATE INDEX i ON t USING btree (lower(a))")
    assert not _ddl_indice_seguro("CREATE INDEX i ON t USING btree (a); DROP TABLE x")
    assert not _ddl_indice_seguro("CREATE INDEX i ON t USING btree (a) -- comentario")

