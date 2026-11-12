import * as api from "../core/api.js";
import { obtener as sesionActual, esDemo } from "../core/session.js";
import { analizarDemo } from "../core/demo.js";
import * as historial from "../core/historial.js";
import { $, activarCopiar, cajaError, cajaSQL, esc } from "../core/util.js";

const TIPO = "optimizacion";
// Ejemplo según la base: en modo demo usa sus tablas inventadas; con una base
// real, el esquema tipo TPC-H del proyecto (sql/base_de_prueba.sql y el modelo).
const EJEMPLO_DEMO = "SELECT p.id, c.nombre, p.total\nFROM pedidos p\nJOIN clientes c ON c.id = p.cliente_id\nWHERE p.estado = 'pendiente'\nORDER BY p.fecha DESC\nLIMIT 50;";
// Con una base real, el esquema tipo TPC-H del proyecto (sql/base_de_prueba.sql).
// "Usar ejemplo" va rotando: una pesada (5 tablas, agrupa y ordena en disco), una
// donde el modelo sí encuentra mejoras y la de 4 tablas con un solo país.
const EJEMPLOS_TPCH = [
  { nombre: "pesada: 5 tablas, agrupa y ordena todo",
    sql: `SELECT c.c_name                     AS cliente,
       s.s_name                     AS proveedor,
       count(DISTINCT o.o_orderkey) AS pedidos,
       count(DISTINCT p.p_brand)    AS marcas,
       sum(l.l_extendedprice)       AS ventas,
       avg(l.l_quantity)            AS cantidad_promedio
FROM lineitem l
JOIN orders   o ON o.o_orderkey = l.l_orderkey
JOIN customer c ON c.c_custkey  = o.o_custkey
JOIN part     p ON p.p_partkey  = l.l_partkey
JOIN supplier s ON s.s_suppkey  = l.l_suppkey
WHERE o.o_orderdate BETWEEN DATE '2022-01-01' AND DATE '2024-06-30'
  AND l.l_quantity BETWEEN 5 AND 45
  AND p.p_size > 3
  AND c.c_acctbal > 0
GROUP BY c.c_name, s.s_name
HAVING sum(l.l_extendedprice) > 1000
ORDER BY ventas DESC, pedidos DESC
LIMIT 100;` },
  { nombre: "ventas por país: el modelo encuentra índices y otro plan",
    sql: `SELECT n.n_name                     AS pais,
       count(DISTINCT o.o_orderkey) AS pedidos,
       sum(l.l_extendedprice)       AS ventas
FROM customer c
JOIN orders   o ON o.o_custkey   = c.c_custkey
JOIN lineitem l ON l.l_orderkey  = o.o_orderkey
JOIN part     p ON p.p_partkey   = l.l_partkey
JOIN nation   n ON n.n_nationkey = c.c_nationkey
WHERE o.o_orderdate >= DATE '2023-01-01'
  AND o.o_orderdate <  DATE '2023-07-01'
  AND l.l_quantity > 40
  AND p.p_size BETWEEN 10 AND 20
  AND c.c_acctbal > 5000
GROUP BY n.n_name
ORDER BY ventas DESC
LIMIT 10;` },
  { nombre: "4 tablas, un solo país",
    sql: "SELECT count(*)\nFROM lineitem\nJOIN orders ON orders.o_orderkey = lineitem.l_orderkey\nJOIN customer ON customer.c_custkey = orders.o_custkey\nJOIN nation ON nation.n_nationkey = customer.c_nationkey\nWHERE nation.n_name = 'GERMANY';" },
];
const ejemplo = () => (esDemo() ? EJEMPLO_DEMO : EJEMPLOS_TPCH[0].sql);
let siguienteEjemplo = 0;

function usarEjemplo() {
  if (esDemo()) { $("op-sql").value = EJEMPLO_DEMO; return; }
  const e = EJEMPLOS_TPCH[siguienteEjemplo];
  $("op-sql").value = e.sql;
  $("op-estado").textContent = `Ejemplo ${siguienteEjemplo + 1} de ${EJEMPLOS_TPCH.length}: ${e.nombre}`;
  siguienteEjemplo = (siguienteEjemplo + 1) % EJEMPLOS_TPCH.length;
}

const dbname = () => (sesionActual() || {}).dbname || "";
const num = (n) => (n == null ? "—" : Number(n).toLocaleString("es-CL", { maximumFractionDigits: 2 }));

// Se incrementa al salir de la ruta: si "analizar" responde después de eso,
// no toca el DOM (que el router ya reemplazó por el de otra pantalla).
let vigencia = 0;

export function render(app) {
  vigencia++;
  app.innerHTML = `
    <div class="pagina-cab">
      <h2>Optimización de consulta</h2>
      <p class="muted">Pega una consulta de solo lectura: te devolvemos la consulta optimizada lista para copiar
        y te explicamos, paso a paso, qué hizo PostgreSQL y cuánto demoró de verdad.</p>
    </div>
    <div class="editor-sql">
      <textarea id="op-sql" rows="6" spellcheck="false" placeholder="${esc(ejemplo())}"></textarea>
      <div class="editor-barra">
        <button id="op-ejecutar" type="button">Analizar plan</button>
        <button id="op-ejemplo" type="button" class="ghost">Usar ejemplo</button>
        <span id="op-estado" class="editor-estado"></span>
      </div>
    </div>
    <div id="op-error"></div>
    <div id="op-resultado"></div>
    <div class="hist-cab">
      <h3>Historial de esta sesión</h3>
      <button id="op-limpiar" class="ghost" type="button">Limpiar historial</button>
    </div>
    <div id="op-historial"></div>`;

  $("op-ejemplo").onclick = usarEjemplo;
  $("op-ejecutar").onclick = ejecutar;
  $("op-limpiar").onclick = () => { historial.limpiar(TIPO, dbname()); pintarHistorial(); };
  pintarHistorial();
}

export function cleanup() { vigencia++; }

async function ejecutar() {
  // Sin texto se usa el ejemplo que se ve en el cuadro.
  if (!$("op-sql").value.trim()) $("op-sql").value = ejemplo();
  const sql = $("op-sql").value.trim();
  const token = vigencia;
  const boton = $("op-ejecutar");
  boton.disabled = true;
  $("op-estado").textContent = "Ejecutando EXPLAIN ANALYZE…";
  $("op-error").innerHTML = "";
  try {
    const resultado = esDemo() ? analizarDemo(sql) : await api.analizar(sql);
    if (token !== vigencia) return;
    pintarResultado(resultado, sql);
    historial.agregar(TIPO, dbname(), {
      sql,
      costo: resultado.analisis?.costo_total_estimado,
      filas: resultado.analisis?.filas_estimadas,
      tiempo: resultado.analisis?.tiempo_real_ms,
    });
    pintarHistorial();
  } catch (err) {
    if (token !== vigencia) return;
    $("op-error").innerHTML = cajaError(err);
    $("op-resultado").innerHTML = "";
  } finally {
    if (token === vigencia) { boton.disabled = false; $("op-estado").textContent = ""; }
  }
}

function pintarResultado(r, sql) {
  const a = r.analisis || {};
  const ml = r.recomendacion_ml || {};
  const pasos = a.arbol ? pasosDelPlan(a.arbol) : [];
  estado = { sql, v1: ml, v2: undefined, v3: undefined };
  $("op-resultado").innerHTML = `
    <div class="stats-grid plan-resumen">
      <div class="stat-card"><div class="stat-label">Tiempo real</div><div class="stat-value">${num(a.tiempo_real_ms)} <small>ms</small></div></div>
      <div class="stat-card"><div class="stat-label">Filas que devuelve</div><div class="stat-value">${num(a.arbol?.filas_reales)}</div></div>
      <div class="stat-card"><div class="stat-label">Pasos</div><div class="stat-value">${num(pasos.length)}</div></div>
    </div>
    <div class="sub-titulo">Consulta optimizada</div>
    <p class="muted mini">Cópiala y pégala tal cual en tu cliente SQL (psql, DBeaver, pgAdmin).</p>
    ${cajaSQL("op-opt", sqlOptimizado(), esDemo() ? "modo demo: sin modelo" : "calculando con el modelo…")}
    <div class="sub-titulo">Plan de ejecución</div>
    <p class="muted mini">Lo que hizo PostgreSQL para responder, en orden.</p>
    ${pasos.length ? veredicto(pasos, a.tiempo_real_ms) + `<ol class="pasos">${pasos.map(pasoHTML).join("")}</ol>`
      : '<div class="empty">Sin datos del plan.</div>'}
    <details class="version plan-tecnico">
      <summary><span class="ver-nombre">Ver plan técnico (para expertos)</span>
        <span class="ver-res">costo estimado ${num(a.costo_total_estimado)} · ${num(a.n_operadores)} operadores</span></summary>
      <div class="ver-cuerpo"><div class="plan-arbol">${a.arbol ? nodoHTML(a.arbol, a.tiempo_real_ms) : ""}</div></div>
    </details>
    <div class="sub-titulo">Detalle del modelo</div>
    <details class="version">
      <summary><span class="ver-tag">V1</span><span class="ver-nombre">Elegir el plan (orden de JOIN)</span>
        <span class="ver-res">${esc(resumenV1(ml))}</span></summary>
      <div class="ver-cuerpo">${ml.disponible ? bloqueML(ml) : '<span class="muted">Modelo no disponible.</span>'}</div>
    </details>
    <details class="version" id="v2">
      <summary><span class="ver-tag">V2</span><span class="ver-nombre">Índices recomendados por el modelo</span>
        <span class="ver-res" id="v2-res">${esDemo() ? "no disponible en modo demo" : "calculando…"}</span></summary>
      <div class="ver-cuerpo" id="v2-cuerpo"></div>
    </details>
    <details class="version" id="v3">
      <summary><span class="ver-tag">V3</span><span class="ver-nombre">Índices y plan juntos (base gemela)</span>
        <span class="ver-res" id="v3-res">${esDemo() ? "no disponible en modo demo" : "calculando…"}</span></summary>
      <div class="ver-cuerpo" id="v3-cuerpo"></div>
    </details>
    <p class="muted mini">Ningún índice se crea solo: tú decides si corres el <code>CREATE INDEX</code>.</p>`;
  activarCopiar($("op-resultado"));
  if (!esDemo()) cargarVersiones(sql);
}

// Lo que va en la caja "Consulta optimizada". Prioridad: la V3 (índices y plan
// elegidos juntos); si no está, los índices de la V2 más el plan de la V1.
let estado = {};

function sqlOptimizado() {
  const { sql, v1, v2, v3 } = estado;
  if (v3?.disponible) return v3.sql_optimizado;
  const indices = v2?.disponible ? v2.indices_sql : [];
  const consulta = v1?.sql_optimizado || `${sql.replace(/;\s*$/, "")};`;
  return indices.length
    ? ["-- Índices recomendados (se crean una sola vez)", ...indices, "", consulta].join("\n")
    : consulta;
}

function tituloOptimizado() {
  const { v1, v2, v3 } = estado;
  if (v3?.disponible) {
    return v3.indices.length || v3.cambia_plan
      ? `Índices y plan elegidos por el modelo (V3) · ${num(v3.mejora_pct)} % más rápido (estimado)`
      : "Tu consulta ya está bien: el modelo no encontró nada que la mejore";
  }
  const espera = v2 === undefined || v3 === undefined ? " · afinando…" : "";
  const nIdx = v2?.disponible ? v2.indices_sql.length : 0;
  const cambiaPlan = v1?.aplica && !v1.mejor_es_actual;
  if (!nIdx && !cambiaPlan) return `Tu consulta ya está bien: el modelo no encontró nada que la mejore${espera}`;
  const partes = [];
  if (nIdx) partes.push(`${nIdx} ${nIdx === 1 ? "índice" : "índices"} (V2)`);
  if (cambiaPlan) partes.push("cambio de plan (V1)");
  return partes.join(" + ") + espera;
}

function refrescarOptimizado() {
  if (!$("op-opt")) return;
  $("op-opt").textContent = sqlOptimizado();
  $("op-opt-titulo").textContent = tituloOptimizado();
}

function resumenV1(ml) {
  if (!ml.disponible) return "modelo no disponible";
  if (!ml.aplica) return "no aplica a esta consulta";
  return ml.mejor_es_actual ? "el plan de PostgreSQL ya es el mejor" : `${num(ml.mejora_pct)} % más rápido (estimado)`;
}

// V2 y V3 se piden apenas termina el análisis. La V3 puede demorar la primera vez
// (arma la base gemela); mientras tanto la caja muestra lo de V1 y V2.
function cargarVersiones(sql) {
  const token = vigencia;
  const fallo = (id) => (err) => {
    if (token !== vigencia) return;
    $(`${id}-res`).textContent = "error";
    $(`${id}-cuerpo`).innerHTML = cajaError(err);
    estado[id] = null;
    refrescarOptimizado();
  };
  api.version2(sql)
    .then((r) => { if (token === vigencia) { estado.v2 = r; pintarV2(r); refrescarOptimizado(); } })
    .catch(fallo("v2"));
  const pedirV3 = (reconstruir) => {
    $("v3-res").textContent = reconstruir ? "armando la base gemela de nuevo…" : "calculando… (la primera vez arma la base gemela)";
    $("v3-cuerpo").innerHTML = "";
    api.version3(sql, reconstruir)
      .then((r) => { if (token === vigencia) { estado.v3 = r; pintarV3(r, pedirV3); refrescarOptimizado(); } })
      .catch(fallo("v3"));
  };
  pedirV3(false);
}

const ms = (v) => `${num(v)} <small>ms</small>`;

function noDisponible(id, r) {
  $(`${id}-res`).textContent = "no disponible";
  $(`${id}-cuerpo`).innerHTML = `<div class="recom-pendiente"><span class="muted">${esc(r.motivo || "Faltan los modelos en ml/.")}</span></div>`;
}

function pintarV2(r) {
  if (!r.disponible) return noDisponible("v2", r);
  const recomendados = r.candidatos.filter((c) => c.recomendado);
  $("v2-res").textContent = recomendados.length
    ? `${recomendados.length} ${recomendados.length === 1 ? "índice" : "índices"} · ${num(r.mejora_pct)} % más rápido (estimado)`
    : (r.candidatos.length ? "ningún índice vale la pena" : "no hay columnas candidatas");
  const filas = r.candidatos.map((c) => `
    <tr class="${c.recomendado ? "ver-elegido" : ""}">
      <td>${c.recomendado ? "✔" : ""}</td>
      <td><code>${esc(c.tabla)}.${esc(c.columna)}</code></td>
      <td>${c.uso === "filtro" ? "filtro (WHERE)" : "unión (JOIN)"}</td>
      <td>${num(c.mejora_pct)} %</td>
      <td>${num(c.mb)} MB</td>
      <td title="${esc(c.sql_sugerido)}"><code>${esc(c.sql_sugerido)}</code></td>
    </tr>`).join("");
  $("v2-cuerpo").innerHTML = `
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-label">Tiempo estimado actual</div><div class="stat-value">${ms(r.tiempo_actual_ms)}</div></div>
      <div class="stat-card"><div class="stat-label">Con los índices recomendados</div><div class="stat-value">${ms(r.tiempo_con_indices_ms)}</div></div>
      <div class="stat-card"><div class="stat-label">Espacio de los índices</div><div class="stat-value">${num(r.mb_recomendados)} <small>MB aprox.</small></div></div>
    </div>
    ${r.candidatos.length ? `<div class="tabla-wrap ver-tabla"><table class="data">
      <thead><tr><th></th><th>Columna</th><th>Se usa en</th><th>Mejora predicha</th><th>Tamaño aprox.</th><th>SQL</th></tr></thead>
      <tbody>${filas}</tbody></table></div>`
      : '<div class="empty">La consulta no tiene columnas sin índice en filtros o uniones.</div>'}
    <p class="muted mini">El modelo predice cuánto mejora la consulta con cada índice. Se recomiendan los que mejoran
      más de 10 %. La consulta no se ejecuta.</p>`;
}

function pintarV3(r, pedirV3) {
  if (!r.disponible) return noDisponible("v3", r);
  $("v3-res").textContent = r.indices.length || r.cambia_plan
    ? `${r.indices.length} ${r.indices.length === 1 ? "índice" : "índices"}${r.cambia_plan ? " + cambio de plan" : ""} · ${num(r.mejora_pct)} % más rápido (estimado)`
    : "dejar todo como está";
  const g = r.gemela || {};
  $("v3-cuerpo").innerHTML = `
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-label">Tiempo estimado actual</div><div class="stat-value">${ms(r.tiempo_actual_ms)}</div></div>
      <div class="stat-card"><div class="stat-label">Con índices y plan elegidos</div><div class="stat-value">${ms(r.tiempo_final_ms)}</div></div>
      <div class="stat-card"><div class="stat-label">Espacio de los índices</div><div class="stat-value">${num(r.mb)} <small>MB aprox.</small></div></div>
    </div>
    ${r.gemela_mismo_plan ? "" : '<div class="disabled-note">La base gemela no arma exactamente el mismo plan que tu servidor: toma la estimación con más cuidado.</div>'}
    <p class="muted mini">Se probaron ${num(r.candidatos_evaluados)} columnas como índices hipotéticos junto con las variantes
      del plan, en una base gemela con las mismas estadísticas que tu base (armada
      ${g.recien_armada ? `recién ahora, ${num(g.segundos_en_armar)} s` : `hace ${num(g.edad_min)} min`}). En tu servidor solo se leyó.
      <button type="button" class="ghost mini-boton" id="v3-rehacer">Volver a armar la gemela</button></p>`;
  $("v3-rehacer").onclick = () => pedirV3(true);
}

// Estimación del modelo de ML (regresión LightGBM) sobre variantes del plan.
function bloqueML(ml) {
  if (!ml.aplica) return `<span class="muted">${esc(ml.motivo)}</span>`;
  return `
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-label">Tiempo estimado actual</div><div class="stat-value">${ms(ml.tiempo_actual_ms)}</div></div>
      <div class="stat-card"><div class="stat-label">Mejor tiempo estimado</div><div class="stat-value">${ms(ml.tiempo_mejor_ms)}</div></div>
      <div class="stat-card"><div class="stat-label">Mejora estimada</div><div class="stat-value">${num(ml.mejora_pct)} <small>%</small></div></div>
    </div>
    ${ml.aviso ? `<div class="disabled-note">${esc(ml.aviso)}</div>` : ""}
    <p class="muted mini">${ml.mejor_es_actual
      ? "El plan que elige PostgreSQL ya es el más rápido entre las variantes evaluadas."
      : "Una variante del plan sería más rápida: está aplicada en la consulta optimizada."}
      Se evaluaron ${num(ml.variantes_evaluadas)} ${ml.variantes_evaluadas === 1 ? "variante" : "variantes"} solo con EXPLAIN.</p>`;
}

// --- Plan en palabras simples ---

// Pasos en el orden en que se ejecutan: primero los hijos, después el nodo.
// El tiempo de EXPLAIN es por vuelta (loops); bajo un Gather las "vueltas" son
// procesos que corren a la vez, así que ahí no se multiplica.
function pasosDelPlan(raiz) {
  const total = (n, paralelo) => (n.tiempo_total_ms || 0) * (paralelo ? 1 : n.loops || 1);
  const pasos = [];
  (function visitar(n, paralelo) {
    const enHijos = paralelo || /Gather/.test(n.tipo || "");
    (n.hijos || []).forEach((h) => visitar(h, enHijos));
    const hijos = (n.hijos || []).reduce((s, h) => s + total(h, enHijos), 0);
    // Filas en total (todas las vueltas), no las de una vuelta como muestra EXPLAIN.
    const vueltas = paralelo ? 1 : n.loops || 1;
    const nTot = { ...n, filas_reales: n.filas_reales == null ? null : n.filas_reales * vueltas };
    pasos.push({ n, propio: Math.max(0, total(n, paralelo) - hijos), texto: frase(nTot) });
  })(raiz, false);
  return pasos;
}

function tablasDe(n) {
  const t = [];
  (function visitar(x) {
    if (x.relacion && !t.includes(x.relacion)) t.push(x.relacion);
    (x.hijos || []).forEach(visitar);
  })(n);
  if (!t.length) return "el resultado anterior";
  const b = t.map((x) => `<b>${esc(x)}</b>`);
  return b.length === 1 ? b[0] : `${b.slice(0, -1).join(", ")} y ${b[b.length - 1]}`;
}

const filas = (n) => `${num(n.filas_reales ?? n.filas_estimadas)} ${(n.filas_reales ?? n.filas_estimadas) === 1 ? "fila" : "filas"}`;

function frase(n) {
  const t = n.relacion ? `<b>${esc(n.relacion)}</b>` : "";
  const ix = n.indice ? `<code>${esc(n.indice)}</code>` : "un índice";
  const [a, b] = (n.hijos || []).map(tablasDe);
  switch (n.tipo) {
    case "Seq Scan":
      return n.filtro
        ? { texto: `Revisa la tabla ${t} completa, fila por fila, y se queda con ${filas(n)}.`,
            consejo: n.filas_eliminadas_filtro > 1000 ? `Descartó ${num(n.filas_eliminadas_filtro)} filas: un índice podría evitar revisarlas.` : "" }
        : { texto: `Lee la tabla ${t} completa (${filas(n)}).` };
    case "Index Scan": return { texto: `Busca directo en ${t} usando el índice ${ix} y encuentra ${filas(n)}.` };
    case "Index Only Scan": return { texto: `Responde solo con el índice ${ix}, sin abrir la tabla ${t} (${filas(n)}).` };
    case "Bitmap Index Scan": return { texto: `Usa el índice ${ix} para ubicar las filas que sirven.` };
    case "Bitmap Heap Scan": return { texto: `Lee de ${t} solo las filas que marcó el índice (${filas(n)}).` };
    case "Hash": return { texto: `Arma una lista en memoria con ${tablasDe(n)} para buscar rápido.` };
    case "Hash Join": return { texto: `Junta ${a} con ${b} usando esa lista en memoria → ${filas(n)}.` };
    case "Nested Loop": return { texto: `Por cada fila de ${a}, busca las que coinciden en ${b} → ${filas(n)}.` };
    case "Merge Join": return { texto: `Junta ${a} con ${b} recorriéndolas en orden → ${filas(n)}.` };
    case "Sort": case "Incremental Sort":
      return { texto: `Ordena ${filas(n)}${n.orden?.length ? ` por <code>${esc(n.orden.join(", "))}</code>` : ""}.` };
    case "Aggregate": case "HashAggregate": case "GroupAggregate":
      return { texto: `Calcula el resultado (conteos, sumas o grupos) → ${filas(n)}.` };
    case "Limit": return { texto: `Se queda con las primeras ${filas(n)}.` };
    case "Gather": case "Gather Merge": return { texto: "Junta lo que hicieron varios procesos en paralelo." };
    case "Memoize": return { texto: "Recuerda búsquedas ya hechas para no repetirlas." };
    case "Materialize": return { texto: `Guarda en memoria ${tablasDe(n)} para reusarlas.` };
    case "Unique": return { texto: "Quita las filas repetidas." };
    case "Append": return { texto: "Junta los resultados de varias partes." };
    case "Result": return { texto: "Calcula valores sin leer tablas." };
    case "CTE Scan": case "Subquery Scan": return { texto: `Lee el resultado de una subconsulta (${filas(n)}).` };
    default: return { texto: `Paso interno de PostgreSQL (${esc(n.tipo || "?")}).` };
  }
}

function veredicto(pasos, totalMs) {
  const lento = pasos.reduce((m, p, i) => (p.propio > pasos[m].propio ? i : m), 0);
  const pct = totalMs ? Math.round((100 * pasos[lento].propio) / totalMs) : 0;
  pasos.forEach((p) => { p.pct = totalMs ? Math.round((100 * p.propio) / totalMs) : 0; });
  pasos[lento].lento = pct >= 25;
  return `<div class="veredicto">PostgreSQL respondió en <b>${num(totalMs)} ms</b> con ${pasos.length} pasos.
    ${pct >= 25 ? `Lo que más demora es el <b>paso ${lento + 1}</b> (${pct} % del tiempo).` : "Ningún paso se lleva la mayor parte del tiempo."}</div>`;
}

function pasoHTML(p) {
  return `<li class="paso${p.lento ? " lento" : ""}">
    <div class="paso-texto">${p.texto.texto}
      ${p.lento && p.texto.consejo ? `<div class="paso-consejo">${esc(p.texto.consejo)}</div>` : ""}</div>
    <div class="paso-tiempo"><span class="paso-barra"><span style="width:${Math.min(100, p.pct)}%"></span></span>
      ${num(p.propio)} ms${p.lento ? " · el más lento" : ""}</div>
  </li>`;
}

// --- Plan técnico (árbol de EXPLAIN) ---

function categoria(tipo) {
  if (/Index/i.test(tipo)) return "ix";
  if (/Seq Scan/i.test(tipo)) return "scan";
  if (/Join|Nested Loop|Hash|Merge/i.test(tipo)) return "join";
  if (/Sort/i.test(tipo)) return "sort";
  return "otro";
}

function nodoHTML(n, tiempoTotalRaiz) {
  const lento = tiempoTotalRaiz && n.tiempo_total_ms != null && n.tiempo_total_ms >= tiempoTotalRaiz * 0.25;
  const partes = [];
  if (n.relacion) partes.push(`en <b>${esc(n.relacion)}</b>${n.alias && n.alias !== n.relacion ? ` (${esc(n.alias)})` : ""}`);
  if (n.indice) partes.push(`usando índice <code>${esc(n.indice)}</code>`);
  const detalle = [];
  if (n.filtro) detalle.push(["Filtro", n.filtro]);
  if (n.cond_join) detalle.push(["Condición", n.cond_join]);
  if (n.orden && n.orden.length) detalle.push(["Orden", n.orden.join(", ")]);
  if (n.filas_eliminadas_filtro) detalle.push(["Filas descartadas por el filtro", num(n.filas_eliminadas_filtro)]);
  return `
    <div class="plan-nodo${lento ? " lento" : ""}">
      <div class="plan-cab">
        <span class="plan-tag plan-${categoria(n.tipo)}">${esc(n.tipo || "?")}</span>
        <span class="plan-rel">${partes.join(" ")}</span>
        <span class="plan-costo">costo ${num(n.costo_total)} · ${num(n.filas_estimadas)} filas est. · ${num(n.filas_reales)} filas reales · ${num(n.tiempo_total_ms)} ms</span>
      </div>
      ${detalle.length ? `<div class="plan-detalle">${detalle.map(([k, v]) => `<div><span>${esc(k)}:</span> <code>${esc(v)}</code></div>`).join("")}</div>` : ""}
      ${n.hijos && n.hijos.length ? `<div class="plan-hijos">${n.hijos.map((h) => nodoHTML(h, tiempoTotalRaiz)).join("")}</div>` : ""}
    </div>`;
}

function recortar(s, max) {
  const t = String(s || "").replace(/\s+/g, " ").trim();
  return t.length > max ? t.slice(0, max - 1) + "…" : t;
}

function pintarHistorial() {
  const lista = historial.listar(TIPO, dbname());
  const cont = $("op-historial");
  if (!lista.length) { cont.innerHTML = '<div class="empty">Todavía no analizaste ninguna consulta en esta base de datos.</div>'; return; }
  cont.innerHTML = lista.map((e) => `
    <div class="historial-item" data-id="${esc(e.id)}">
      <div class="historial-sql">${esc(recortar(e.sql, 140))}</div>
      <div class="historial-meta">
        <span>${esc(new Date(e.ts).toLocaleString("es-CL"))}</span>
        <span>costo ${num(e.costo)} · ${num(e.tiempo)} ms</span>
      </div>
      <div class="historial-acciones">
        <button class="ghost hist-usar" type="button">Volver a usar</button>
        <button class="ghost hist-eliminar" type="button">Eliminar</button>
      </div>
    </div>`).join("");
  cont.querySelectorAll(".historial-item").forEach((item) => {
    const id = item.dataset.id;
    const entrada = lista.find((e) => e.id === id);
    item.querySelector(".hist-usar").onclick = () => { $("op-sql").value = entrada.sql; ejecutar(); };
    item.querySelector(".hist-eliminar").onclick = () => { historial.eliminar(TIPO, dbname(), id); pintarHistorial(); };
  });
}
