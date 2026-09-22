# Optimización de consultas SQL en PostgreSQL con Machine Learning

**Tema de investigación:** la **optimización de consultas SQL** en PostgreSQL,
apoyando al optimizador del motor con modelos de **Machine Learning supervisado**
para la selección del orden de los JOIN y la recomendación de índices, mediante un
analizador externo y desacoplado.

## Estructura del proyecto

```
optimizacion-sql-ml/
├── analizador/    Conexión de solo lectura a PostgreSQL y captura de datos
├── ml/            Núcleo de Machine Learning (dataset, features, modelos)
├── backend/       API (FastAPI) que orquesta el analizador y el ML
├── frontend/      Interfaz web (HTML/CSS/JS por módulos)
├── sql/           Scripts SQL de apoyo
├── benchmarks/    Espacio para los benchmarks (TPC-H / JOB)
├── data/          Datasets generados (ignorado por git)
├── tests/         Pruebas
├── docs/          Documentación (propuesta)
└── .github/       Integración continua (GitHub Actions)
```

## Qué contiene cada carpeta (por el momento)

- **`analizador/`** — capa de conexión de solo lectura al PostgreSQL objetivo:
  captura de planes (`EXPLAIN` / `EXPLAIN ANALYZE`), lectura del catálogo de tablas
  e índices, diagrama de relaciones, estadísticas de la base y un recomendador
  heurístico de índices (`recomendador.py`, sin ML todavía).
- **`ml/`** — el núcleo analítico de Machine Learning: generación del dataset,
  extracción de características y modelos (orden de JOIN e índices). *En desarrollo.*
- **`backend/`** — servidor API en FastAPI que coordina el analizador y el ML;
  rutas separadas por dominio, esquemas de datos y servicios.
- **`frontend/`** — interfaz web en módulos: ingreso de datos de la base,
  explorador de tablas, índices, diagrama de relaciones y estadísticas de la base de datos.
- **`sql/`** — scripts SQL (por ejemplo, creación del usuario de solo lectura).
- **`benchmarks/`** — espacio para montar los benchmarks TPC-H y JOB.
- **`data/`** — datasets generados durante el trabajo (no versionados).
- **`tests/`** — pruebas del proyecto.
- **`docs/`** — documentación, incluida la propuesta de titulación.
- **`.github/`** — flujo de integración continua (CI).

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
    router.js          mapea cada URL (#/ruta) a su módulo y protege las rutas
    api.js             todas las llamadas al backend
    session.js         credenciales en memoria (no se guardan en el navegador)
    util.js, demo.js, pestanas.js, indices-info.js, historial.js
  routes/
    conexion.js        #/conexion     (ingresar datos de la base)
    validando.js       #/validando    (validación paso a paso con ticks)
    tablas.js          #/tablas       (Datos de la tabla · pestaña Tablas)
    indices.js         #/indices      (Datos de la tabla · pestaña Índices, separada de las tablas)
    diagrama.js        #/diagrama     (diagrama de tablas, relaciones e índices conectados)
    estadisticas.js    #/estadisticas (monitoreo en vivo)
    optimizacion.js     #/optimizacion (plan de ejecución EXPLAIN ANALYZE + historial)
    prediccion.js       #/prediccion   (recomendación heurística de índices + historial)
```

`historial.js` guarda en `localStorage` las consultas analizadas en `#/optimizacion`
y `#/prediccion`, separadas por base de datos (nunca se guarda la contraseña).

El router protege las rutas: si no hay conexión activa, redirige a `#/conexion`.
