import * as api from "../core/api.js";
import { obtener as sesionActual, esDemo } from "../core/session.js";
import { prediccionDemo } from "../core/demo.js";
import * as historial from "../core/historial.js";
import { $, esc } from "../core/util.js";

const TIPO = "prediccion";
const EJEMPLO = "SELECT p.id, c.nombre, p.total\nFROM pedidos p\nJOIN clientes c ON c.id = p.cliente_id\nWHERE p.estado = 'pendiente'\nORDER BY p.fecha DESC\nLIMIT 50;";

const dbname = () => (sesionActual() || {}).dbname || "";

// Se incrementa al salir de la ruta: si "predecir" responde después de eso,
// no toca el DOM (que el router ya reemplazó por el de otra pantalla).
let vigencia = 0;

export function render(app) {
  vigencia++;
  app.innerHTML = `
    <div class="pagina-cab">
      <h2>Predicción de índice</h2>
      <p class="muted">Pega una consulta y revisa qué columnas podrían beneficiarse de un índice nuevo, a partir de
        su plan estimado. No se crea ningún índice: solo se sugiere el SQL para que lo revises y decidas tú.</p>
    </div>
    <div class="editor-sql">
      <textarea id="pi-sql" rows="6" spellcheck="false" placeholder="${esc(EJEMPLO)}"></textarea>
      <div class="editor-barra">
        <button id="pi-ejecutar" type="button">Predecir índices</button>
        <button id="pi-ejemplo" type="button" class="ghost">Usar ejemplo</button>
        <span id="pi-estado" class="editor-estado"></span>
      </div>
    </div>
    <div id="pi-error"></div>
    <div id="pi-resultado"></div>
    <div class="hist-cab">
      <h3>Historial de esta sesión</h3>
      <button id="pi-limpiar" class="ghost" type="button">Limpiar historial</button>
    </div>
    <div id="pi-historial"></div>`;

  $("pi-ejemplo").onclick = () => { $("pi-sql").value = EJEMPLO; };
  $("pi-ejecutar").onclick = ejecutar;
  $("pi-limpiar").onclick = () => { historial.limpiar(TIPO, dbname()); pintarHistorial(); };
  pintarHistorial();
}

export function cleanup() { vigencia++; }

async function ejecutar() {
  const sql = $("pi-sql").value.trim();
  if (!sql) { $("pi-error").innerHTML = `<div class="err-box">Escribe una consulta primero.</div>`; return; }
  const token = vigencia;
  const boton = $("pi-ejecutar");
  boton.disabled = true;
  $("pi-estado").textContent = "Analizando el plan estimado…";
  $("pi-error").innerHTML = "";
  try {
    const resultado = esDemo() ? prediccionDemo(sql) : await api.predecirIndices(sql);
    if (token !== vigencia) return;
    pintarResultado(resultado);
    historial.agregar(TIPO, dbname(), { sql, n: resultado.n_recomendaciones });
    pintarHistorial();
  } catch (err) {
    if (token !== vigencia) return;
    $("pi-error").innerHTML = `<div class="err-box">${esc(err.message)}</div>`;
    $("pi-resultado").innerHTML = "";
  } finally {
    if (token === vigencia) { boton.disabled = false; $("pi-estado").textContent = ""; }
  }
}

function pintarResultado(r) {
  const lista = r.recomendaciones || [];
  let html = !lista.length
    ? `<div class="empty">No se encontraron columnas candidatas: la consulta ya parece bien cubierta por los índices actuales.</div>`
    : `<div class="recom-lista">${lista.map(recomHTML).join("")}</div>`;
  if (r.nota) html += `<p class="muted mini">${esc(r.nota)}</p>`;
  $("pi-resultado").innerHTML = html;
}

function recomHTML(r) {
  return `<div class="recom-item">
    <div class="recom-cab"><code class="col-pill">${esc(r.tabla)}.${esc(r.columna)}</code></div>
    <ul class="recom-motivos">${(r.motivos || []).map((m) => `<li>${esc(m)}</li>`).join("")}</ul>
    <pre class="idx-sql">${esc(r.sql_sugerido)}</pre>
  </div>`;
}

function recortar(s, max) {
  const t = String(s || "").replace(/\s+/g, " ").trim();
  return t.length > max ? t.slice(0, max - 1) + "…" : t;
}

function pintarHistorial() {
  const lista = historial.listar(TIPO, dbname());
  const cont = $("pi-historial");
  if (!lista.length) { cont.innerHTML = '<div class="empty">Todavía no pediste ninguna predicción en esta base de datos.</div>'; return; }
  cont.innerHTML = lista.map((e) => `
    <div class="historial-item" data-id="${esc(e.id)}">
      <div class="historial-sql">${esc(recortar(e.sql, 140))}</div>
      <div class="historial-meta">
        <span>${esc(new Date(e.ts).toLocaleString("es-CL"))}</span>
        <span>${e.n} ${e.n === 1 ? "recomendación" : "recomendaciones"}</span>
      </div>
      <div class="historial-acciones">
        <button class="ghost hist-usar" type="button">Volver a usar</button>
        <button class="ghost hist-eliminar" type="button">Eliminar</button>
      </div>
    </div>`).join("");
  cont.querySelectorAll(".historial-item").forEach((item) => {
    const id = item.dataset.id;
    const entrada = lista.find((e) => e.id === id);
    item.querySelector(".hist-usar").onclick = () => { $("pi-sql").value = entrada.sql; ejecutar(); };
    item.querySelector(".hist-eliminar").onclick = () => { historial.eliminar(TIPO, dbname(), id); pintarHistorial(); };
  });
}
