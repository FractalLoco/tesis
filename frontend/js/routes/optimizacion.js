import * as api from "../core/api.js";
import { obtener as sesionActual, esDemo } from "../core/session.js";
import { analizarDemo } from "../core/demo.js";
import * as historial from "../core/historial.js";
import { $, cajaError, esc } from "../core/util.js";

const TIPO = "optimizacion";
// Ejemplo según la base: en modo demo usa sus tablas inventadas; con una base
// real, el esquema tipo TPC-H del proyecto (sql/base_de_prueba.sql y el modelo).
const EJEMPLO_DEMO = "SELECT p.id, c.nombre, p.total\nFROM pedidos p\nJOIN clientes c ON c.id = p.cliente_id\nWHERE p.estado = 'pendiente'\nORDER BY p.fecha DESC\nLIMIT 50;";
const EJEMPLO_TPCH = "SELECT count(*)\nFROM lineitem\nJOIN orders ON orders.o_orderkey = lineitem.l_orderkey\nJOIN customer ON customer.c_custkey = orders.o_custkey\nJOIN nation ON nation.n_nationkey = customer.c_nationkey\nWHERE nation.n_name = 'GERMANY';";
const ejemplo = () => (esDemo() ? EJEMPLO_DEMO : EJEMPLO_TPCH);

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
      <p class="muted">Pega una consulta de solo lectura y revisa su plan de ejecución real (EXPLAIN ANALYZE):
        qué operadores usa PostgreSQL, cuánto cuesta cada uno y cuánto demoró de verdad.</p>
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

  $("op-ejemplo").onclick = () => { $("op-sql").value = ejemplo(); };
  $("op-ejecutar").onclick = ejecutar;
  $("op-limpiar").onclick = () => { historial.limpiar(TIPO, dbname()); pintarHistorial(); };
  pintarHistorial();
}

export function cleanup() { vigencia++; }

async function ejecutar() {
  const sql = $("op-sql").value.trim();
  if (!sql) { $("op-error").innerHTML = cajaError("Escribe una consulta primero."); return; }
  const token = vigencia;
  const boton = $("op-ejecutar");
  boton.disabled = true;
  $("op-estado").textContent = "Ejecutando EXPLAIN ANALYZE…";
  $("op-error").innerHTML = "";
  try {
    const resultado = esDemo() ? analizarDemo(sql) : await api.analizar(sql);
    if (token !== vigencia) return;
    pintarResultado(resultado);
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

function pintarResultado(r) {
  const a = r.analisis || {};
  const rec = r.recomendaciones || {};
  const ml = r.recomendacion_ml || {};
  $("op-resultado").innerHTML = `
    <div class="stats-grid plan-resumen">
      <div class="stat-card"><div class="stat-label">Costo estimado</div><div class="stat-value">${num(a.costo_total_estimado)}</div></div>
      <div class="stat-card"><div class="stat-label">Filas estimadas</div><div class="stat-value">${num(a.filas_estimadas)}</div></div>
      <div class="stat-card"><div class="stat-label">Tiempo real</div><div class="stat-value">${num(a.tiempo_real_ms)} <small>ms</small></div></div>
      <div class="stat-card"><div class="stat-label">Operadores</div><div class="stat-value">${num(a.n_operadores)}</div></div>
    </div>
    <div class="sub-titulo">Plan de ejecución</div>
    <div class="plan-arbol">${a.arbol ? nodoHTML(a.arbol, a.tiempo_real_ms) : '<div class="empty">Sin datos del plan.</div>'}</div>
    <div class="sub-titulo">Recomendaciones</div>
    ${ml.disponible ? bloqueML(ml) : ""}
    <div class="recom-pendiente">
      ${ml.disponible ? "" : chipPendiente("Orden de JOIN", rec.orden_join)}
      ${chipPendiente("Índices", rec.indices)}
      ${chipPendiente("Diagnóstico", rec.diagnostico)}
      <p class="muted mini">La recomendación de índices ya está disponible en <a href="/prediccion">Predicción de índice</a>.
        ${ml.disponible ? "" : "El orden de JOIN por Machine Learning llegará más adelante."}</p>
    </div>`;
}

// Estimación del modelo de ML (regresión LightGBM) sobre variantes del plan.
function bloqueML(ml) {
  if (!ml.aplica) {
    return `<div class="recom-pendiente plan-resumen">
      <div class="recom-fila"><b>Orden de JOIN (modelo ML):</b> <span class="muted">${esc(ml.motivo)}</span></div>
    </div>`;
  }
  const ms = (v) => `${num(v)} <small>ms</small>`;
  return `
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-label">Tiempo estimado actual</div><div class="stat-value">${ms(ml.tiempo_actual_ms)}</div></div>
      <div class="stat-card"><div class="stat-label">Mejor tiempo estimado</div><div class="stat-value">${ms(ml.tiempo_mejor_ms)}</div></div>
      <div class="stat-card"><div class="stat-label">Mejora estimada</div><div class="stat-value">${num(ml.mejora_pct)} <small>%</small></div></div>
    </div>
    <div class="recom-pendiente plan-resumen" style="margin-top:12px">
      ${ml.aviso ? `<div class="disabled-note">${esc(ml.aviso)}</div>` : ""}
      <div class="recom-fila"><b>Orden de JOIN (modelo ML):</b> ${ml.mejor_es_actual
        ? "el plan que elige PostgreSQL ya es el más rápido entre las variantes evaluadas."
        : "una variante del plan sería más rápida."}</div>
      <div class="recom-fila"><b>Mejor variante:</b> <span class="muted">${esc(ml.descripcion)}</span></div>
      <p class="muted mini">Estimación del modelo de regresión (LightGBM) sobre ${num(ml.variantes_evaluadas)}
        ${ml.variantes_evaluadas === 1 ? "variante" : "variantes"} del plan, obtenidas solo con EXPLAIN (sin ejecutar la consulta).
        Prototipo entrenado con un esquema tipo TPC-H: en otras bases la estimación es orientativa.</p>
    </div>`;
}

function chipPendiente(etiqueta, valor) {
  return `<div class="recom-fila"><b>${esc(etiqueta)}:</b> <span class="muted">${esc(valor || "pendiente")}</span></div>`;
}

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
