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
- [Seguridad](#seguridad)
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
| Optimización de consulta | `/optimizacion` | Plan real (`EXPLAIN ANALYZE`) y las tres versiones del modelo en filas desplegables: V1 (plan), V2 (índices) y V3 (índices y plan juntos) |
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
CORS y el puerto. Con `PRECARGAR_CONEXION=true` la pantalla de conexión llega llena con esa base
y basta con apretar **Ingresar**: la contraseña se toma del `.env` y nunca viaja al navegador ni se
envía a otro servidor. Es para trabajar en local; en un servidor público conviene dejarlo en `false`.
En Linux, `lightgbm` necesita `libgomp1` (`sudo apt install libgomp1`).

**Para la V3** hace falta un PostgreSQL **propio de la aplicación** (no el de la base objetivo) con
HypoPG, donde se arma la base gemela. En el mismo equipo de la app, por ejemplo:

```bash
sudo apt install postgresql-17-hypopg
sudo -u postgres psql -d template1 -c "CREATE EXTENSION hypopg"   # así cada base nueva ya la trae
sudo -u postgres createuser --createdb gemela   # y ponerle clave con \password gemela
```

y en el `.env`: `GEMELA_DSN=host=localhost dbname=postgres user=gemela password=...`. Sin
`GEMELA_DSN` la V3 aparece como "no disponible" y el resto funciona igual.

**¿No tienes una base para probar?** `sql/base_de_prueba.sql` crea una con el esquema tipo
TPC-H del modelo (7 tablas, ~150 mil filas) y `sql/usuario_solo_lectura.sql` crea el usuario
de solo lectura. Los pasos están en [`docs/pruebas.md`](docs/pruebas.md#2-crear-la-base-de-prueba-para-integración-y-e2e).

### Con Docker

Levanta todo de una vez, sin instalar Python ni PostgreSQL. Son dos contenedores:
- uno con PostgreSQL 17 + HypoPG, que trae la base de prueba y el usuario de solo lectura ya creados;
- otro con la aplicación, con la V1, la V2 y la V3 funcionando.

```bash
docker compose up --build -d   # la primera vez tarda unos minutos (arma las imágenes y la base)
```

La página queda en http://localhost:8020 y la pantalla de conexión llega llena: basta con
apretar **Ingresar**. Por defecto solo se abre en el mismo equipo; con `DOCKER_IP=0.0.0.0` en el
`.env` también se abre desde la red: `http://IP_DE_ESTE_PC:8020`.

En Windows también se puede hacer doble clic en `arrancar_docker.bat`: abre Docker Desktop si
está cerrado, abre el puerto en el firewall (la primera vez), levanta todo abierto a la red y
muestra las direcciones.

- Para apagarlo: `docker compose down`.
- Con `docker compose down -v` también se borra la base; la próxima vez se crea de nuevo.
- Los contenedores tienen `restart: unless-stopped`: vuelven solos cuando arranca Docker.
- Las claves por defecto son solo para uso local. Se cambian en el `.env` (ver `.env.example`).

#### En un servidor

Solo necesita Docker con Compose v2:

```bash
git clone https://github.com/FractalLoco/tesis.git && cd tesis
cp .env.example .env    # claves DOCKER_CLAVE_*, DOCKER_CORS, DOCKER_IP=0.0.0.0 y DOCKER_PRECARGAR=false
docker compose up --build -d
docker compose ps       # los dos contenedores deben salir "healthy"
```

La app queda en `http://IP_DEL_SERVIDOR:8020` (el puerto se cambia con `DOCKER_PUERTO`).
La base solo escucha en `127.0.0.1`, así que no queda expuesta. Para actualizar:
`git pull && docker compose up --build -d`.

## Seguridad

La API no tiene login: está pensada para usarse en el mismo equipo, en una red de confianza o
por VPN. Las protecciones:

- **Solo lectura**: la consulta se valida antes de ejecutarse (`backend/services/reglas.py`) y la
  conexión abre en modo solo lectura, con límites de tiempo por consulta y por bloqueo. Se fijan
  al abrir la sesión, así que un `ROLLBACK` no los quita (`analizador/conexion.py`).
- **La clave del `.env` nunca sale del servidor**: con la precarga activa solo se usa hacia la
  misma base del `.env`, y nunca se envía al navegador.
- **Servidor de destino**: un solo host por TCP; se rechazan listas de hosts y rutas de socket.
- **Consola**: no admite `EXPLAIN ANALYZE`, porque ejecutaría la consulta.
- **SQL sugerido**: los nombres de tablas y columnas van citados cuando hace falta.
- **Base gemela**: de la base analizada solo se copian tipos de columna e índices simples.
- **Respuestas**: cabeceras de seguridad (CSP, `X-Frame-Options`, `nosniff`), sin caché en la API,
  valores enormes recortados y, con `MOSTRAR_DETALLE_TECNICO=false`, sin detalles de PostgreSQL.
- **Exposición**: `iniciar.py` y Docker escuchan solo en el mismo equipo salvo que se indique
  `BIND_HOST` / `DOCKER_IP`.

## Pruebas

**126 pruebas** con `pytest`, separadas por tipo:

| Tipo | Carpeta | Cantidad | Qué prueba |
|---|---|---:|---|
| Unitarias | `tests/unitarias/` | 88 | Funciones sueltas: reglas de solo lectura, datos de conexión, errores, lectura del plan, modelo, orden de JOIN, rutas, recomendador de índices, notebook V1/V2/V3, V2 y V3 en la app, protecciones de seguridad |
| Integración (backend) | `tests/integracion/` | 25 | La API contra un PostgreSQL real: conexión, precarga, catálogo, diagrama, índices, análisis, estadísticas |
| E2E (frontend) | `tests/e2e/` | 13 | Un navegador (Playwright) usa la app: ingreso, precarga, tablas, índices, diagrama, optimización, predicción |

```bash
.venv/bin/python -m pytest                                    # todas
.venv/bin/python -m pytest tests/unitarias -v                 # solo un tipo
.venv/bin/python -m pytest tests/e2e -v --headed --slowmo 700 # viendo el navegador
```

Con `--headed` la ventana se abre maximizada, queda **20 segundos** abierta después de ingresar
y cargar la base, y unos segundos más al terminar cada prueba. Las de integración y E2E se
**omiten** si no hay base de prueba, así que en GitHub Actions corren las unitarias.
Detalle completo en [`docs/pruebas.md`](docs/pruebas.md). Para correrlas en Google Colab con
varias bases de distinto tamaño y sesgo está `tests/pruebas_colab.ipynb`.

## Modelo de Machine Learning

En **Optimización de consulta**, además del plan real (`EXPLAIN ANALYZE`), el backend pide varios
planes **estimados** de la misma consulta (`EXPLAIN`, sin ejecutarla), cambiando la configuración
del planificador con `SET LOCAL` en una transacción de solo lectura (`join_collapse_limit` y
`enable_hashjoin` / `enable_mergejoin` / `enable_nestloop`). El modelo estima el tiempo de cada
plan y se muestra el actual, el mejor y la mejora estimada.

Los resultados aparecen en tres filas desplegables:

| Versión | Qué decide | Cómo lo hace en la página |
|---|---|---|
| **V1** | El plan (orden y métodos de JOIN) | Varias variantes con `SET LOCAL` y `EXPLAIN`; el modelo estima el tiempo de cada una y elige la más rápida |
| **V2** | Qué índices crear | Busca en el plan las columnas de filtros y uniones sin índice (sin claves primarias ni tablas de menos de 1.000 filas). Con el plan y `pg_stats` arma 10 características por columna y `modelo_indices.pkl` predice cuánto mejora la consulta. Recomienda las que mejoran más de 10 % |
| **V3** | Índices y plan juntos | Arma una **base gemela** con las mismas estadísticas que la base objetivo, en el PostgreSQL de la app. Ahí prueba los candidatos de la V2 como índices hipotéticos (HypoPG) junto con las variantes del plan, combina los dos modelos con los pesos aprendidos y agrega un índice solo si baja el tiempo más del corte aprendido (10 %) |

Ninguna versión ejecuta la consulta ni crea índices en la base objetivo: entregan el
`CREATE INDEX` para que el usuario decida. La gemela se reutiliza por un día y se puede volver a
armar con un botón.

| Archivo en `ml/` | Qué es |
|---|---|
| `modelo_regresion.pkl` | LightGBM que estima el tiempo de un plan (ms) a partir de 24 características del `EXPLAIN`. Lo usa la app |
| `modelo_ranking.pkl` | LightGBM que ordena planes (LambdaMART). Guardado para más adelante |
| `features.json` | Nombres y orden de las características que espera el modelo |
| `modelo_join_order_colab.ipynb` | Notebook de Google Colab que genera los datos, entrena y exporta los modelos |
| `modelo_v3.pkl` | LightGBM de la versión nueva que estima el tiempo de un plan, entrenado con planes con y sin índices. Lo usan la V2 y la V3 |
| `modelo_indices.pkl` | LightGBM que predice cuánto mejora una consulta con un índice en una columna (V2 y V3) |
| `parametros_v2_v3.json` | Lo aprendido en validación: umbral, corte y pesos de la combinación, más el orden de las características |
| `modelo_ml_v1_v2_v3.ipynb` | Notebook de Colab de la versión nueva: 5 bases sintéticas, 300 consultas. V1 elige el plan, V2 recomienda índices, V3 decide índices y plan juntos en una base gemela con HypoPG (solo lectura sobre el servidor). Termina comparando con reglas típicas de una persona |

- Aplica a consultas con **INNER JOIN de 3 a 5 tablas** (el rango con que se entrenó); con 6 o
  más muestra un aviso. Con LEFT/RIGHT/FULL JOIN, subconsultas, CTE o 1–2 tablas no aplica y el
  resto del análisis sigue igual. Se decide leyendo el plan, no el texto SQL.
- Los tres archivos de la V2 y la V3 los genera el bloque 15 de `modelo_ml_v1_v2_v3.ipynb` (en
  Colab se descargan solos; se copian a `ml/`).
- Si faltan los archivos de `ml/` o las librerías (`lightgbm`, `scikit-learn`, `joblib`), la app
  funciona igual, sin el bloque del modelo.
- Es un **prototipo** entrenado con un esquema sintético tipo TPC-H: en otras bases la estimación
  es orientativa hasta reentrenarlo con los benchmarks reales.

## Estructura del proyecto

```
tesis/
├── analizador/          Capa de solo lectura sobre el PostgreSQL objetivo
│   ├── conexion.py          conexión de solo lectura (la usan ambas partes)
│   ├── identificadores.py   cita nombres de tablas y columnas en el SQL sugerido
│   ├── pagina/              datos que muestran las pantallas
│   │   ├── catalogo.py          tablas y vista previa
│   │   ├── indices.py           índices de la base
│   │   ├── diagrama.py          tablas y relaciones
│   │   ├── estadisticas.py      monitoreo en vivo
│   │   ├── consola.py           ejecución de consultas de lectura
│   │   └── texto.py             valores como texto, recortando los enormes
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
- **Conexión precargada**: con `PRECARGAR_CONEXION=true` la pantalla de conexión llega llena con la
  base del `.env`. Además, la contraseña del `.env` ya no se envía nunca a un servidor distinto al
  configurado (antes, una clave en blanco hacia otro host usaba la del `.env`).
- **Ejemplos que funcionan**: "Usar ejemplo" en Optimización y Predicción usa el esquema tipo TPC-H
  del proyecto (con una base real) o las tablas de ejemplo (en modo demo).
- **Base de prueba reproducible**: `sql/base_de_prueba.sql` y la guía `docs/pruebas.md` para
  preparar cualquier computador.

## Licencia

Distribuido bajo licencia **MIT**. Ver [`LICENSE`](LICENSE).
