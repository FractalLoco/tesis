# Optimización de consultas SQL en PostgreSQL con Machine Learning

**Tema de investigación:** la **optimización de consultas SQL** en PostgreSQL,
apoyando al optimizador del motor con modelos de **Machine Learning supervisado**
para la selección del orden de los JOIN y la recomendación de índices, mediante un
analizador externo y desacoplado.

## Estructura del proyecto

```
tesis/
├── analizador/    Conexión de solo lectura a PostgreSQL y captura de datos
├── ml/            Modelo de Machine Learning entrenado (orden de JOIN) y su notebook
├── backend/       API (FastAPI) que orquesta el analizador y sirve el frontend
├── frontend/      Interfaz web (HTML/CSS/JS por módulos)
├── sql/           Scripts SQL de apoyo
├── data/          Datasets generados (ignorado por git)
├── tests/         Pruebas
├── docs/          Documentación (propuesta)
└── .github/       Integración continua (GitHub Actions)
```

## Qué contiene cada carpeta (por el momento)

- **`analizador/`** — capa de solo lectura sobre el PostgreSQL objetivo, en dos partes:
  ```
  analizador/
  ├── conexion.py        conexión de solo lectura (la usan ambas partes)
  ├── pagina/            datos que muestran las pantallas
  │   ├── catalogo.py        tablas y vista previa (Datos de la tabla)
  │   ├── indices.py         índices de la base (Índices)
  │   ├── diagrama.py        tablas y relaciones (Diagrama de tablas)
  │   ├── estadisticas.py    monitoreo en vivo (Estadísticas SQL)
  │   └── consola.py         ejecución de consultas de lectura
  └── analisis/          análisis de consultas
      ├── explain.py         captura de planes (EXPLAIN / EXPLAIN ANALYZE)
      ├── plan_parser.py     lectura y recorrido del plan
      ├── recomendador.py    recomendador heurístico de índices (Predicción de índice)
      ├── modelo.py          carga el modelo de ml/ y estima el tiempo de un plan
      └── orden_join.py      variantes del plan + modelo (Optimización de consulta)
  ```
- **`ml/`** — modelo de Machine Learning entrenado en Google Colab:
  - `modelo_regresion.pkl`: LightGBM que estima el tiempo de un plan (ms) a partir de su
    plan estimado (`EXPLAIN`). Es el que usa la pantalla "Optimización de consulta".
  - `modelo_ranking.pkl`: LightGBM que ordena planes (LambdaMART). Guardado para más adelante;
    hoy no se usa.
  - `features.json`: nombres y orden de las características que espera el modelo.
  - `modelo_join_order_colab.ipynb`: notebook que genera los datos, entrena y exporta los modelos.
- **`backend/`** — servidor API en FastAPI que coordina el analizador y sirve el frontend;
  rutas separadas por dominio, esquemas de datos y servicios.
- **`frontend/`** — interfaz web en módulos: ingreso de datos de la base,
  explorador de tablas, índices, diagrama de relaciones y estadísticas de la base de datos.
- **`sql/`** — scripts SQL (por ejemplo, creación del usuario de solo lectura).
- **`data/`** — datasets generados durante el trabajo (no versionados).
- **`tests/`** — pruebas del proyecto.
- **`docs/`** — documentación, incluida la propuesta de titulación.
- **`.github/`** — flujo de integración continua (CI).

## Configuración (.env)

El proyecto incluye un archivo `.env.example`. Para que funcione, cópialo como
`.env` y cambia las credenciales por las de tu base de datos:

```bash
cp .env.example .env
```

## Modelo de Machine Learning (orden de JOIN)

En "Optimización de consulta", además del plan real (`EXPLAIN ANALYZE`), el backend pide
varios planes **estimados** de la misma consulta (`EXPLAIN`, sin ejecutarla), cambiando la
configuración del planificador con `SET LOCAL` en una transacción de solo lectura
(`join_collapse_limit` y `enable_hashjoin` / `enable_mergejoin` / `enable_nestloop`). El modelo
estima el tiempo de cada plan y se muestra el actual, el mejor y la mejora estimada.

- Aplica a consultas con INNER JOIN de 3 a 5 tablas (el rango con que se entrenó); con 6 o más
  se muestra un aviso. Con LEFT/RIGHT/FULL JOIN, subconsultas, CTE o 1–2 tablas no aplica, y el
  resto del análisis sigue igual. Se decide leyendo el plan, no el texto SQL.
- Si faltan los archivos de `ml/` o las librerías (`lightgbm`, `scikit-learn`, `joblib`), la app
  funciona igual, sin el bloque del modelo. En Linux, `lightgbm` necesita la librería del
  sistema `libgomp1` (`sudo apt install libgomp1`).
- Es un prototipo entrenado con un esquema sintético tipo TPC-H: en otras bases la estimación es
  orientativa hasta reentrenarlo con los benchmarks reales.

## Licencia

Distribuido bajo licencia **MIT**. Ver el archivo [`LICENSE`](LICENSE).

---

> Proyecto de **investigación** desarrollado para la asignatura **Taller de Desarrollo**,
> carrera de Ingeniería de Ejecución en Computación e Informática, Universidad del Bío-Bío.

## Frontend por rutas (SPA con router)

Cada pantalla es una **ruta separada** con su propio módulo (buenas prácticas, sin
framework ni build):

```
frontend/js/
  main.js              arranca el router
  core/
    router.js          mapea cada URL (/ruta, History API) a su módulo y protege las rutas
    api.js             todas las llamadas al backend
    session.js         credenciales en memoria (no se guardan en el navegador)
    util.js, demo.js, pestanas.js, indices-info.js, historial.js
  routes/
    conexion.js        /conexion      (ingresar datos de la base)
    validando.js       /validando     (validación paso a paso con ticks)
    tablas.js          /tablas        (Datos de la tabla · pestaña Tablas)
    indices.js         /indices       (Datos de la tabla · pestaña Índices, separada de las tablas)
    diagrama/          /diagrama      (diagrama de tablas, relaciones e índices conectados)
      index.js         entrada de la ruta: pantalla, carga de datos y controles
      estado.js        estado compartido y medidas del dibujo
      layout.js        posiciones de tablas e índices (capas y orden de cada capa)
      dibujo.js        SVG de tablas, índices y relaciones; selección
      zoom.js          zoom y "Ajustar"
    estadisticas.js    /estadisticas  (monitoreo en vivo)
    optimizacion.js    /optimizacion  (plan de ejecución EXPLAIN ANALYZE + historial)
    prediccion.js      /prediccion    (recomendación heurística de índices + historial)
    no-disponible.js   pantalla 404 genérica (hoy ninguna ruta la usa)
```

`historial.js` guarda en `localStorage` las consultas analizadas en `/optimizacion`
y `/prediccion`, separadas por base de datos (nunca se guarda la contraseña).

El router protege las rutas: si no hay conexión activa, redirige a `/conexion`.

Las URLs son limpias (`/tablas`, `/diagrama`, sin `#`). El backend devuelve
`index.html` para cualquier ruta de pantalla, así que se pueden refrescar o abrir
directamente; `/api/...` y los archivos estáticos inexistentes siguen dando 404.
