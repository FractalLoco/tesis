"""Modelo de Machine Learning que estima el tiempo de ejecución de un plan.

Es un LGBMRegressor entrenado en Colab (ver ml/modelo_join_order_colab.ipynb)
con planes estimados de PostgreSQL (EXPLAIN sin ANALYZE). Predice log1p(ms), así
que al resultado se le aplica expm1.

Los archivos se cargan la primera vez que se usan. Si faltan, o si lightgbm no
se puede importar en el servidor, el modelo queda "no disponible" y el resto de
la aplicación funciona igual.
"""
import json
import logging
import math
from functools import lru_cache
from pathlib import Path

from analizador.plan_parser import raiz, recorrer

log = logging.getLogger("analizador.modelo")

DIR_ML = Path(__file__).resolve().parent.parent / "ml"
ARCHIVO_MODELO = DIR_ML / "modelo_regresion.pkl"
ARCHIVO_FEATURES = DIR_ML / "features.json"

# Tipos de nodo que se cuentan, en el mismo orden que en el notebook.
NODOS = ["Seq Scan", "Index Scan", "Index Only Scan", "Bitmap Heap Scan", "Bitmap Index Scan",
         "Nested Loop", "Hash Join", "Merge Join", "Hash", "Sort", "Aggregate", "Materialize", "Gather"]

class ModeloNoDisponible(RuntimeError):
    pass

def extraer_features(plan, n_tablas: int) -> dict:
    """Características de un plan estimado, con la misma lógica del notebook.

    El orden de las claves es el de ml/features.json (lo verifica un test)."""
    root = raiz(plan)
    cont = {f"n_{nt}": 0 for nt in NODOS}
    agg = {"n_nodos": 0, "prof_max": 0, "filas_est_sum": 0.0, "costo_sum": 0.0, "ancho_sum": 0.0, "n_scans": 0}
    for n, prof in recorrer(root):
        nt = n.get("Node Type", "")
        if nt in NODOS:
            cont[f"n_{nt}"] += 1
        agg["n_nodos"] += 1
        agg["prof_max"] = max(agg["prof_max"], prof)
        agg["filas_est_sum"] += n.get("Plan Rows", 0) or 0
        agg["costo_sum"] += n.get("Total Cost", 0) or 0
        agg["ancho_sum"] += n.get("Plan Width", 0) or 0
        if "Scan" in nt:
            agg["n_scans"] += 1
    f = {**cont, **agg}
    f["raiz_costo"] = root.get("Total Cost", 0)
    f["raiz_costo_ini"] = root.get("Startup Cost", 0)
    f["raiz_filas_est"] = root.get("Plan Rows", 0)
    f["raiz_ancho"] = root.get("Plan Width", 0)
    f["n_tablas"] = n_tablas
    return f

@lru_cache(maxsize=1)
def _cargar():
    try:
        import joblib
        modelo = joblib.load(ARCHIVO_MODELO)
        nombres = json.loads(ARCHIVO_FEATURES.read_text(encoding="utf-8"))
        # Sin scikit-learn el .pkl carga, pero falla al predecir: se prueba aquí.
        modelo.predict([[0.0] * len(nombres)])
    except Exception as exc:
        log.warning("Modelo de ML no disponible: %s", exc)
        return None
    esperadas = getattr(modelo, "n_features_in_", len(nombres))
    if esperadas != len(nombres):
        log.warning("Modelo de ML no disponible: espera %s características y features.json tiene %s",
                    esperadas, len(nombres))
        return None
    return modelo, nombres

def disponible() -> bool:
    return _cargar() is not None

def predecir_ms(plan, n_tablas: int) -> float:
    """Tiempo de ejecución estimado (ms) para un plan estimado."""
    cargado = _cargar()
    if cargado is None:
        raise ModeloNoDisponible("El modelo de ML no está disponible.")
    modelo, nombres = cargado
    f = extraer_features(plan, n_tablas)
    fila = [[float(f[nombre]) for nombre in nombres]]
    return max(0.0, math.expm1(float(modelo.predict(fila)[0])))
