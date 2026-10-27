# Optimización de consultas SQL en PostgreSQL con Machine Learning

[![CI](https://github.com/FractalLoco/tesis/actions/workflows/ci.yml/badge.svg)](https://github.com/FractalLoco/tesis/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white)
![LightGBM](https://img.shields.io/badge/ML-LightGBM-9ACD32)
![Licencia MIT](https://img.shields.io/badge/licencia-MIT-green)

Sistema **externo y desacoplado** que apoya al optimizador de PostgreSQL con modelos de
**Machine Learning supervisado**: recomienda el **orden de los JOIN**, sugiere **índices** y
muestra el **rendimiento** de la base. Se conecta en **solo lectura**: no modifica datos ni
el motor, y todo el cálculo ocurre en su propio servidor.

> Proyecto de **investigación con desarrollo de software** · Taller de Desarrollo ·
> Ingeniería de Ejecución en Computación e Informática · Universidad del Bío-Bío.

---

## Contenido

- [Qué hace](#qué-hace)
- [Arquitectura](#arquitectura)
- [Puesta en marcha](#puesta-en-marcha)
- [Pruebas](#pruebas)
- [Modelo de Machine Learning](#modelo-de-machine-learning)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Forma de trabajo](#forma-de-trabajo)
- [Novedades](#novedades)

---

## Qué hace

| Pantalla | Ruta | Para qué sirve |
|---|---|---|
| Conexión | `/conexion` | Ingresar host, puerto, base, usuario y clave de PostgreSQL |
| Validación | `/validando` | Revisa paso a paso la conexión, el catálogo, los índices y los permisos |
| Datos de la tabla | `/tablas` | Lista las tablas y muestra una vista previa de cada una, por partes |
| Índices | `/indices` | Todos los índices de la base, con su tamaño y uso |
| Diagrama de tablas | `/diagrama` | Tablas, relaciones (claves foráneas) e índices conectados |
| Estadísticas SQL | `/estadisticas` | Monitoreo en vivo: tiempo de respuesta, caché, conexiones |
| Optimización de consulta | `/optimizacion` | Plan real (`EXPLAIN ANALYZE`) y orden de JOIN recomendado por el modelo |
| Predicción de índice | `/prediccion` | Sugiere índices (`CREATE INDEX`) a partir del plan estimado |

Solo se aceptan consultas de lectura (`SELECT`, `WITH`, …) de una sola sentencia: cualquier
`INSERT`, `UPDATE`, `DELETE` o DDL se rechaza antes de llegar a la base.

## Arquitectura

```
 Navegador                    Servidor de análisis (este proyecto)            Base objetivo
┌────────────┐   HTTP   ┌──────────────────────────────────────────┐  solo   ┌────────────┐
│  frontend  │ ───────▶ │ backend (FastAPI) ─▶ analizador ─▶ modelo │ ──────▶ │ PostgreSQL │
│  (JS, SPA) │ ◀─────── │   rutas /api/...     EXPLAIN,      ML    │ lectura │            │
└────────────┘          │                      catálogo            │ ◀────── └────────────┘
                        └──────────────────────────────────────────┘
```

- La base objetivo solo atiende lecturas livianas (catálogo y `EXPLAIN`): no ejecuta nada del
  análisis ni del modelo.
- Un solo proceso sirve la API (`/api/...`) y el frontend, detrás de un único puerto.

## Puesta en marcha

Requisitos: **Python 3.12+** y un **PostgreSQL** al que conectarse.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # completar las credenciales de solo lectura
.venv/bin/python iniciar.py   # abre http://localhost:8000
```

El `.env` (no se sube al repositorio) define la base por defecto, los orígenes permitidos por
CORS y el puerto. En Linux, `lightgbm` necesita `libgomp1` (`sudo apt install libgomp1`).

**¿No tienes una base para probar?** `sql/base_de_prueba.sql` crea una con el esquema tipo
TPC-H del modelo (7 tablas, ~150 mil filas) y `sql/usuario_solo_lectura.sql` crea el usuario
de solo lectura. Los pasos están en [`docs/pruebas.md`](docs/pruebas.md#2-crear-la-base-de-prueba-para-integración-y-e2e).

## Pruebas

**69 pruebas** con `pytest`, separadas por tipo:

| Tipo | Carpeta | Cantidad | Qué prueba |
|---|---|---:|---|
| Unitarias | `tests/unitarias/` | 46 | Funciones sueltas: reglas de solo lectura, errores, lectura del plan, modelo, orden de JOIN, rutas |
| Integración (backend) | `tests/integracion/` | 14 | La API contra un PostgreSQL real: conexión, catálogo, diagrama, índices, análisis, estadísticas |
| E2E (frontend) | `tests/e2e/` | 9 | Un navegador (Playwright) usa la app: ingreso, tablas, índices, diagrama, optimización, predicción |

```bash
.venv/bin/python -m pytest                                    # todas
.venv/bin/python -m pytest tests/unitarias -v                 # solo un tipo
.venv/bin/python -m pytest tests/e2e -v --headed --slowmo 700 # viendo el navegador
```

Con `--headed` la ventana se abre maximizada, queda **20 segundos** abierta después de ingresar
y cargar la base, y unos segundos más al terminar cada prueba. Las de integración y E2E se
**omiten** si no hay base de prueba, así que en GitHub Actions corren las unitarias.
Detalle completo en [`docs/pruebas.md`](docs/pruebas.md).

## Modelo de Machine Learning

En **Optimización de consulta**, además del plan real (`EXPLAIN ANALYZE`), el backend pide varios
planes **estimados** de la misma consulta (`EXPLAIN`, sin ejecutarla), cambiando la configuración
del planificador con `SET LOCAL` en una transacción de solo lectura (`join_collapse_limit` y
`enable_hashjoin` / `enable_mergejoin` / `enable_nestloop`). El modelo estima el tiempo de cada
plan y se muestra el actual, el mejor y la mejora estimada.

| Archivo en `ml/` | Qué es |
|---|---|
| `modelo_regresion.pkl` | LightGBM que estima el tiempo de un plan (ms) a partir de 24 características del `EXPLAIN`. Lo usa la app |
| `modelo_ranking.pkl` | LightGBM que ordena planes (LambdaMART). Guardado para más adelante |
| `features.json` | Nombres y orden de las características que espera el modelo |
| `modelo_join_order_colab.ipynb` | Notebook de Google Colab que genera los datos, entrena y exporta los modelos |

- Aplica a consultas con **INNER JOIN de 3 a 5 tablas** (el rango con que se entrenó); con 6 o
  más muestra un aviso. Con LEFT/RIGHT/FULL JOIN, subconsultas, CTE o 1–2 tablas no aplica y el
  resto del análisis sigue igual. Se decide leyendo el plan, no el texto SQL.
- Si faltan los archivos de `ml/` o las librerías (`lightgbm`, `scikit-learn`, `joblib`), la app
  funciona igual, sin el bloque del modelo.
- Es un **prototipo** entrenado con un esquema sintético tipo TPC-H: en otras bases la estimación
  es orientativa hasta reentrenarlo con los benchmarks reales.

## Estructura del proyecto

```
tesis/
├── analizador/          Capa de solo lectura sobre el PostgreSQL objetivo
│   ├── conexion.py          conexión de solo lectura (la usan ambas partes)
│   ├── pagina/              datos que muestran las pantallas
│   │   ├── catalogo.py          tablas y vista previa
│   │   ├── indices.py           índices de la base
│   │   ├── diagrama.py          tablas y relaciones
│   │   ├── estadisticas.py      monitoreo en vivo
│   │   └── consola.py           ejecución de consultas de lectura
│   └── analisis/            análisis de consultas
│       ├── explain.py           captura de planes (EXPLAIN / EXPLAIN ANALYZE)
│       ├── plan_parser.py       lectura y recorrido del plan
│       ├── recomendador.py      recomendador heurístico de índices
│       ├── modelo.py            carga el modelo de ml/ y estima el tiempo de un plan
│       └── orden_join.py        variantes del plan + modelo
├── backend/             API en FastAPI: rutas (api/), esquemas (models/) y lógica (services/)
├── frontend/            Interfaz web en módulos, sin framework (ver abajo)
├── ml/                  Modelos entrenados y notebook de Colab
├── sql/                 Base de prueba y usuario de solo lectura
├── tests/               unitarias/ · integracion/ · e2e/
├── docs/                Propuesta de titulación y guía de pruebas
├── data/                Datasets generados (no versionados)
└── .github/             Integración continua (lint + pruebas en cada push y PR)
```

### Frontend por rutas

Cada pantalla es una **ruta separada** con su propio módulo (sin framework ni build):

```
frontend/js/
├── main.js              arranca el router
├── core/
│   ├── router.js            mapea cada URL a su módulo y protege las rutas
│   ├── api.js               todas las llamadas al backend
│   ├── session.js           credenciales en memoria (no se guardan en el navegador)
│   └── util.js, demo.js, pestanas.js, indices-info.js, historial.js
└── routes/
    ├── conexion.js, validando.js, tablas.js, indices.js
    ├── diagrama/            index.js, estado.js, layout.js, dibujo.js, zoom.js
    ├── estadisticas.js, optimizacion.js, prediccion.js
    └── no-disponible.js     pantalla 404 genérica
```

- Las URLs son limpias (`/tablas`, `/diagrama`, sin `#`). El backend devuelve `index.html` para
  cualquier ruta de pantalla, así que se pueden refrescar o abrir directamente; `/api/...` y los
  archivos estáticos inexistentes dan 404.
- El router protege las rutas: sin conexión activa redirige a `/conexion`.
- `historial.js` guarda en `localStorage` las consultas de `/optimizacion` y `/prediccion`,
  separadas por base de datos (nunca la contraseña).

## Forma de trabajo

- **GitHub Flow**: una rama corta por cambio desde `main` (`feat/`, `fix/`, `test/`, `docs/`,
  `refactor/`), Pull Request y fusión cuando pasa el CI.
- **Conventional Commits**: `tipo: descripción en imperativo`. Detalle en
  [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Novedades

- **Pruebas por tipo**: `tests/` se separó en unitarias, integración y E2E, con nombres más
  claros y comentarios.
- **Integración del backend**: 14 pruebas de la API contra PostgreSQL real (conexión y sus
  errores 401/404/502, tablas, vista previa, diagrama, índices, consola, análisis con el modelo,
  predicción de índices y estadísticas).
- **E2E del frontend**: 9 pruebas con Playwright que recorren las pantallas; con `--headed` se
  ven en una ventana maximizada y con pausas para seguirlas.
- **Base de prueba reproducible**: `sql/base_de_prueba.sql` y la guía `docs/pruebas.md` para
  preparar cualquier computador.

## Licencia

Distribuido bajo licencia **MIT**. Ver [`LICENSE`](LICENSE).
