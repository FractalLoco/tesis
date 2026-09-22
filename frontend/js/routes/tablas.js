import * as api from "../core/api.js";
import { esDemo } from "../core/session.js";
import { tablasDemo, datosTablaDemo } from "../core/demo.js";
import { $, esc } from "../core/util.js";
import { pestanasDatos } from "../core/pestanas.js";

let tablas = [];
// Se incrementa al salir de la ruta: si una llamada async responde después de
// eso, no toca el DOM (que el router ya reemplazó por el de otra pantalla).
let vigencia = 0;

export async function render(app) {
  const token = ++vigencia;
  app.innerHTML = `
    ${pestanasDatos("/tablas")}
    <div class="search-bar">
      <svg class="search-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
      <input id="tabla-search" type="text" placeholder="Buscar tabla por nombre..." />
    </div>
    <div id="acordeon-tablas"></div>`;
  $("tabla-search").oninput = (e) => pintar(e.target.value);
  await cargar(token);
}

export function cleanup() { vigencia++; }

async function cargar(token) {
  try {
    if (esDemo()) throw new Error("demo");
    tablas = (await api.listarTablas()).tablas || [];
  } catch { tablas = tablasDemo(); }
  if (token === vigencia) pintar("");
}

function pintar(filtro) {
  const f = (filtro || "").trim().toLowerCase();
  const items = tablas.filter((t) => t.tabla.toLowerCase().includes(f));
  const cont = $("acordeon-tablas");
  if (!cont) return;
  if (!items.length) { cont.innerHTML = '<div class="empty">Sin resultados.</div>'; return; }
  cont.innerHTML = items.map((t) => `
    <div class="acc-item" data-esquema="${esc(t.esquema)}" data-tabla="${esc(t.tabla)}">
      <div class="acc-head">
        <span class="nombre"><span class="chev">&#9656;</span> ${esc(t.tabla)}</span>
        <span class="rows">${t.filas_est >= 0 ? t.filas_est.toLocaleString("es-CL") + " filas" : "—"}</span>
      </div>
      <div class="acc-body"><div class="empty">Cargando…</div></div>
    </div>`).join("");
  cont.querySelectorAll(".acc-item").forEach((item) =>
    item.querySelector(".acc-head").onclick = () => toggle(item));
}

async function toggle(item) {
  const token = vigencia;
  const abierto = item.classList.toggle("open");
  if (!abierto || item.dataset.cargado) return;
  const { esquema, tabla } = item.dataset;
  const body = item.querySelector(".acc-body");
  try {
    const data = esDemo() ? datosTablaDemo(tabla) : await api.verTabla(esquema, tabla, 100);
    if (token !== vigencia) return;
    body.innerHTML = tablaHTML(esquema, tabla, data);
    item.dataset.cargado = "1";
  } catch (err) { if (token === vigencia) body.innerHTML = `<div class="err-box">${esc(err.message)}</div>`; }
}

function tablaHTML(esquema, tabla, data) {
  const cols = data.columnas || [];
  const info = `<div class="muted mini" style="margin-bottom:8px">${esc(esquema)}.${esc(tabla)} · ${cols.length} columnas · mostrando ${data.n_filas} filas</div>`;
  const thead = "<tr>" + cols.map((c) => `<th>${esc(c.nombre)}<span class="coltype">${esc(c.tipo)}</span></th>`).join("") + "</tr>";
  const tbody = (data.filas || []).map((fila) => "<tr>" + fila.map((v) => `<td>${esc(v)}</td>`).join("") + "</tr>").join("");
  return info + `<div class="tabla-wrap"><table class="data"><thead>${thead}</thead><tbody>${tbody}</tbody></table></div>`;
}
