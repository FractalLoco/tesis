# Pruebas del proyecto

Las pruebas se corren con **pytest** desde la raíz del repositorio y están separadas por tipo:

| Carpeta | Tipo | Qué prueba | Necesita |
|---|---|---|---|
| `tests/unitarias/` | Unitarias | Funciones sueltas del analizador y el backend (54) | Nada más que Python |
| `tests/integracion/` | Integración (backend) | La API conectada a un PostgreSQL real (18) | Base de prueba + `.env` |
| `tests/e2e/` | E2E (frontend) | Un navegador usa la aplicación completa (12) | Base de prueba + `.env` + Playwright |

Si falta la base de prueba, las de integración y E2E se **omiten** (no fallan). Así pasa en
GitHub Actions, donde solo corren las unitarias.

## 1. Preparar el computador

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install pytest httpx pytest-playwright
.venv/bin/python -m playwright install chromium
```

En Linux, `lightgbm` necesita la librería del sistema `libgomp1` (`sudo apt install libgomp1`).

## 2. Crear la base de prueba (para integración y E2E)

Con PostgreSQL instalado, como un usuario que pueda crear bases:

```bash
createdb optimizacion
psql -d optimizacion -f sql/base_de_prueba.sql
```

Después, crear el usuario de solo lectura con `sql/usuario_solo_lectura.sql`, cambiando
`mi_base` por `optimizacion` y poniendo una clave. Por último, copiar `.env.example` a `.env`
y completar `DB_PASSWORD` con esa clave (el resto de los valores ya apunta a `optimizacion`
con el usuario `analizador_ro`). Con `PRECARGAR_CONEXION=true` la pantalla de conexión llega
llena con esa base y la contraseña se puede dejar en blanco.

## 3. Correr las pruebas

Todas:

```bash
.venv/bin/python -m pytest
```

Por tipo:

```bash
.venv/bin/python -m pytest tests/unitarias -v
.venv/bin/python -m pytest tests/integracion -v
.venv/bin/python -m pytest tests/e2e -v
```

Una sola prueba (`archivo::nombre`):

```bash
.venv/bin/python -m pytest -v tests/unitarias/test_leer_plan.py::test_cuenta_los_operadores_del_plan
```

### Ver el navegador en las pruebas E2E

```bash
.venv/bin/python -m pytest tests/e2e -v --headed --slowmo 700
```

- `--headed` muestra la ventana del navegador.
- `--slowmo 700` espera 700 ms entre cada acción, para alcanzar a seguirlas.
- Con `--headed`, después de ingresar y cargar la base la ventana queda 20 segundos abierta,
  y 3 segundos más al terminar cada prueba (ver `tests/e2e/conftest.py`).

Las E2E tardan más que el resto porque cada una ingresa a la base desde cero (con la animación
de validación incluida).

## Qué hace cada prueba

Algunas pruebas usan `parametrize` y se repiten con varios valores: por eso hay 34 funciones
unitarias pero pytest cuenta 54 casos.

### Unitarias (`tests/unitarias/`)

**`test_validar_consultas.py`**: regla de solo lectura (`validar_consulta`)
- `test_acepta_select_y_quita_el_punto_y_coma_final`: acepta un `SELECT` y le quita el `;` final.
- `test_acepta_with_y_select_entre_parentesis`: acepta `WITH ... SELECT` y `(SELECT) UNION (SELECT)`.
- `test_punto_y_coma_dentro_de_textos_o_comentarios_no_cuenta`: un `;` dentro de un texto o comentario no separa sentencias.
- `test_select_for_update_dentro_de_with_no_es_falso_positivo`: no rechaza por error una consulta válida con `WITH`.
- `test_rechaza_consulta_vacia_o_solo_comentarios`: una consulta vacía o solo con comentarios se rechaza.
- `test_rechaza_varias_sentencias_juntas`: `SELECT 1; DELETE ...` se rechaza (evita colar una escritura).
- `test_rechaza_consultas_que_modifican_datos`: rechaza `DELETE`, `UPDATE` y un `DELETE` escondido en un `WITH`.
- `test_solo_la_consola_acepta_show_y_explain`: `SHOW` y `EXPLAIN` se permiten solo en la consola.

**`test_configuracion_conexion.py`**: datos de conexión y uso de la clave del `.env`
- `test_sin_datos_usa_todo_el_env`: sin datos de la pantalla se usa la base y la clave del `.env`.
- `test_la_clave_escrita_siempre_se_respeta`: si se escribe una contraseña, se usa esa.
- `test_clave_en_blanco_usa_la_del_env_si_esta_activo_y_es_la_misma_base`: con `PRECARGAR_CONEXION` activo, la clave en blanco usa la del `.env`.
- `test_clave_en_blanco_no_usa_la_del_env_si_esta_desactivado`: con la opción desactivada, la clave en blanco queda en blanco.
- `test_la_clave_del_env_nunca_se_envia_a_otra_base`: si cambia el servidor, el puerto, la base o el usuario, la clave del `.env` no se envía.

**`test_traducir_errores.py`**: errores de PostgreSQL convertidos en mensajes claros
- `test_traduce_un_sqlstate_conocido`: el código `42601` se convierte en "error de sintaxis" (HTTP 400).
- `test_traduce_por_la_clase_del_sqlstate`: un código desconocido se traduce por su clase (`22` = datos inválidos).
- `test_reconoce_clave_incorrecta_aunque_venga_mal_codificada`: detecta la clave incorrecta aunque el mensaje en español venga sin tildes.
- `test_reconoce_servidor_inalcanzable`: si el host no existe, responde "servidor inalcanzable".
- `test_deja_solo_la_parte_util_del_mensaje`: limpia el texto técnico largo de psycopg y deja solo la causa.

**`test_leer_plan.py`**: lectura del plan de `EXPLAIN`
- `test_cuenta_los_operadores_del_plan`: cuenta las operaciones del árbol del plan y reconoce la raíz.

**`test_modelo_ml.py`**: modelo de Machine Learning
- `test_features_en_el_mismo_orden_que_features_json`: genera las 24 características en el orden que espera el modelo.
- `test_features_iguales_a_las_del_notebook`: la app calcula las características igual que el notebook de entrenamiento.
- `test_cuenta_bien_los_nodos_del_plan`: los conteos (Seq Scan, Hash Join, profundidad, costos) son correctos.
- `test_predice_milisegundos_positivos`: el modelo carga y predice un tiempo positivo en ms.
- `test_sin_archivo_del_modelo_queda_no_disponible`: si falta el archivo del modelo, la app sigue funcionando sin él.

**`test_orden_join.py`**: recomendación del orden de JOIN
- `test_decide_si_el_modelo_aplica`: aplica con INNER JOIN de 3 a 5 tablas; no aplica con LEFT JOIN, CTE, subconsultas o menos de 3 tablas.
- `test_seis_tablas_aplica_pero_con_aviso`: con 6 tablas estima, pero avisa que está fuera del rango entrenado.
- `test_bitmap_index_scan_no_cuenta_como_otra_tabla`: un recorrido por índice no se cuenta como una tabla más.
- `test_elige_la_variante_mas_rapida`: entre varios planes elige el de menor tiempo y calcula bien el % de mejora.
- `test_descarta_planes_con_un_metodo_desactivado`: descarta planes con costo inflado artificialmente.
- `test_si_no_aplica_no_llama_al_modelo`: si la consulta no aplica, no gasta tiempo prediciendo.
- `test_sin_modelo_no_se_conecta_a_la_base`: sin modelo disponible no hace consultas innecesarias.

**`test_rutas_frontend.py`**: cómo el backend sirve el frontend
- `test_las_pantallas_devuelven_la_pagina`: `/`, `/conexion`, `/tablas`, `/diagrama` y `/optimizacion` devuelven la página.
- `test_rutas_de_api_o_archivos_que_no_existen_dan_404`: una ruta de API o un archivo que no existe da 404.
- `test_los_archivos_js_se_sirven_como_javascript`: los `.js` se entregan con el tipo correcto.

### Integración del backend (`tests/integracion/`)

**`test_api_conexion.py`**: `/api/conectar`
- `test_conecta_y_detecta_usuario_de_solo_lectura`: conecta, encuentra las 7 tablas y confirma que el usuario es de solo lectura.
- `test_clave_incorrecta_responde_401`: con una clave mala responde 401 (no autorizado).
- `test_base_que_no_existe_responde_404`: con una base que no existe responde 404.
- `test_puerto_sin_servidor_responde_502`: si no hay PostgreSQL en ese puerto responde 502 (servidor inalcanzable).
- `test_conexion_por_defecto_desactivada_no_entrega_datos`: sin `PRECARGAR_CONEXION`, `/api/conexion-por-defecto` no entrega datos.
- `test_conexion_por_defecto_activa_entrega_la_base_pero_nunca_la_clave`: con la opción activa entrega la base y el usuario, nunca la contraseña.
- `test_con_precarga_entra_con_la_clave_en_blanco`: con la opción activa se conecta con la clave en blanco.
- `test_sin_precarga_la_clave_en_blanco_responde_401`: sin la opción, la clave en blanco responde 401.

**`test_api_catalogo.py`**: estructura de la base
- `test_lista_las_7_tablas_de_la_base`: `/api/tablas` devuelve las 7 tablas.
- `test_vista_previa_de_una_tabla`: `/api/tabla` trae las columnas y las filas de `nation`, respetando el límite.
- `test_vista_previa_de_tabla_inexistente_responde_400`: una tabla que no existe responde 400 con un mensaje claro.
- `test_diagrama_trae_tablas_y_relaciones`: `/api/diagrama` trae 7 tablas y 7 relaciones (por ejemplo customer → nation).
- `test_indices_de_la_base`: `/api/indices` trae los 16 índices de la base.

**`test_api_analisis.py`**: consultas y análisis
- `test_la_consola_devuelve_filas`: `/api/consulta` ejecuta un `SELECT` y devuelve sus filas.
- `test_la_consola_rechaza_un_delete`: un `DELETE` responde 403 (prohibido).
- `test_analiza_consulta_de_4_tablas_con_el_modelo`: `/api/analizar` ejecuta `EXPLAIN ANALYZE` y el modelo recomienda un orden de JOIN.
- `test_prediccion_sugiere_indice_para_un_filtro_sin_indice`: `/api/prediccion-indices` sugiere `CREATE INDEX` para `o_totalprice`.
- `test_estadisticas_de_la_base`: `/api/estadisticas` devuelve conexiones y el porcentaje de caché.

### E2E del frontend (`tests/e2e/`)

**`test_ingreso_navegador.py`**: ingreso a la aplicación
- `test_ingresa_y_muestra_las_tablas`: llena el formulario, entra y ve las 7 tablas con su cantidad de filas.
- `test_clave_incorrecta_muestra_el_error`: con una clave mala la pantalla de validación muestra el error.
- `test_salir_vuelve_a_la_pantalla_de_conexion`: "Salir de la base de datos" vuelve al formulario de ingreso.
- `test_formulario_precargado_entra_sin_escribir_la_clave`: con `PRECARGAR_CONEXION` el formulario llega lleno y entra sin escribir la contraseña.

**`test_pantallas_navegador.py`**: pantallas que muestran la base
- `test_abrir_una_tabla_muestra_sus_filas`: al abrir `nation` se ve su vista previa (filas 1–10 de 25, con CHILE).
- `test_la_pantalla_de_indices_lista_los_indices`: la pestaña Índices muestra los 16 índices.
- `test_el_diagrama_muestra_tablas_y_relaciones`: el diagrama dibuja 7 tablas y 7 relaciones.

**`test_analisis_navegador.py`**: pantallas de análisis
- `test_optimizacion_muestra_el_plan_y_la_recomendacion`: analiza una consulta de 4 tablas y muestra el tiempo real, el plan y la recomendación del modelo.
- `test_prediccion_sugiere_un_indice`: escribe una consulta y la página sugiere el `CREATE INDEX`.
- `test_consulta_que_modifica_datos_muestra_error`: un `DELETE` muestra el aviso de que solo se permiten consultas de lectura.
- `test_el_ejemplo_de_optimizacion_funciona_con_la_base`: el botón "Usar ejemplo" de Optimización analiza una consulta real de 4 tablas.
- `test_el_ejemplo_de_prediccion_sugiere_un_indice`: el botón "Usar ejemplo" de Predicción termina en una sugerencia de `CREATE INDEX`.
