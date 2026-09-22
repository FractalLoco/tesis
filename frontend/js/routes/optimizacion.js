import * as api from "../core/api.js";
import { obtener as sesionActual, esDemo } from "../core/session.js";
import { analizarDemo } from "../core/demo.js";
import * as historial from "../core/historial.js";
import { $, esc } from "../core/util.js";

const TIPO = "optimizacion";
const EJEMPLO = "SELECT p.id, c.nombre, p.total\nFROM pedidos p\nJOIN clientes c ON c.id = p.cliente_id\nWHERE p.estado = 'pendiente'\nORDER BY p.fecha DESC\nLIMIT 50;";

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
      <textarea id="op-sql" rows="6" spellcheck="false" placeholder="${esc(EJEMPLO)}"></textarea>
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

  $("op-ejemplo").onclick = () => { $("op-sql").value = EJEMPLO; };
  $("op-ejecutar").onclick = ejecutar;
  $("op-limpiar").onclick = () => { historial.limpiar(TIPO, dbname()); pintarHistorial(); };
  pintarHistorial();
}

export function cleanup() { vigencia++; }

async function ejecutar() {
  const sql = $("op-sql").value.trim();
  if (!sql) { $("op-error").innerHTML = `<div class="err-box">Escribe una consulta primero.</div>`; return; }
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
    $("op-error").innerHTML = `<div class="err-box">${esc(err.message)}</div>`;
    $("op-resultado").innerHTML = "";
  } finally {
    if (token === vigencia) { boton.disabled = false; $("op-estado").textContent = ""; }
  }
}

function pintarResultado(r) {
  const a = r.analisis || {};
  const rec = r.recomendaciones || {};
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
    <div class="recom-pendiente">
      ${chipPendiente("Orden de JOIN", rec.orden_join)}
      ${chipPendiente("Índices", rec.indices)}
      ${chipPendiente("Diagnóstico", rec.diagnostico)}
      <p class="muted mini">La recomendación de índices ya está disponible en <a href="#/prediccion">Predicción de índice</a>.
        El orden de JOIN por Machine Learning llegará más adelante.</p>
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
