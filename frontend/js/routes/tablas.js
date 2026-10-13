import * as api from "../core/api.js";
import { esDemo } from "../core/session.js";
import { tablasDemo, datosTablaDemo } from "../core/demo.js";
import { $, cajaError, esc } from "../core/util.js";
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
    tablas = esDemo() ? tablasDemo() : (await api.listarTablas()).tablas || [];
  } catch (err) {
    // Sin datos de ejemplo de respaldo: si la base falla, se muestra el error real.
    if (token !== vigencia) return;
    $("acordeon-tablas").innerHTML =
      `${cajaError(err)}<p><button id="tablas-reintentar" class="ghost">Reintentar</button></p>`;
    $("tablas-reintentar").onclick = () => {
      $("acordeon-tablas").innerHTML = '<div class="empty">Cargando…</div>';
      cargar(token);
    };
    return;
  }
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
    mostrarTabla(body, esquema, tabla, data);
    item.dataset.cargado = "1";
  } catch (err) { if (token === vigencia) body.innerHTML = cajaError(err); }
}

// Para no agobiar con información, la vista previa se muestra por partes:
// pocas filas por página y solo las primeras columnas (el resto, a pedido).
const FILAS_POR_PAGINA = 10;
const COLS_VISIBLES = 6;

function mostrarTabla(body, esquema, tabla, data) {
  const vista = { pagina: 0, todasLasCols: false };
  const pintarVista = () => { body.innerHTML = tablaHTML(esquema, tabla, data, vista); };
  body.onclick = (e) => {
    const accion = e.target.closest("[data-accion]")?.dataset.accion;
    if (accion === "anterior") vista.pagina--;
    else if (accion === "siguiente") vista.pagina++;
    else if (accion === "columnas") vista.todasLasCols = !vista.todasLasCols;
    else return;
    pintarVista();
  };
  pintarVista();
}

function tablaHTML(esquema, tabla, data, vista) {
  const cols = data.columnas || [];
  const filas = data.filas || [];
  const nCols = vista.todasLasCols ? cols.length : Math.min(cols.length, COLS_VISIBLES);
  const paginas = Math.max(1, Math.ceil(filas.length / FILAS_POR_PAGINA));
  const desde = vista.pagina * FILAS_POR_PAGINA;
  const visibles = filas.slice(desde, desde + FILAS_POR_PAGINA);

  const rango = filas.length ? `filas ${desde + 1}–${desde + visibles.length} de ${filas.length}` : "sin filas";
  const info = `<div class="muted mini tabla-info">${esc(esquema)}.${esc(tabla)} · ${cols.length} columnas · ${rango} (vista previa)</div>`;
  const thead = "<tr>" + cols.slice(0, nCols).map((c) => `<th>${esc(c.nombre)}<span class="coltype">${esc(c.tipo)}</span></th>`).join("") + "</tr>";
  const tbody = visibles.map((fila) => "<tr>" +
    fila.slice(0, nCols).map((v) => `<td title="${esc(v)}">${esc(v)}</td>`).join("") + "</tr>").join("");

  const ocultas = cols.length - COLS_VISIBLES;
  const btnCols = ocultas > 0
    ? `<button class="ghost" type="button" data-accion="columnas">${vista.todasLasCols
      ? "Mostrar menos columnas"
      : `Mostrar ${ocultas} ${ocultas === 1 ? "columna" : "columnas"} más`}</button>`
    : "";
  const paginador = paginas > 1
    ? `<div class="paginador">
        <button class="ghost" type="button" data-accion="anterior"${vista.pagina === 0 ? " disabled" : ""}>Anterior</button>
        <span class="muted mini">Página ${vista.pagina + 1} de ${paginas}</span>
        <button class="ghost" type="button" data-accion="siguiente"${vista.pagina >= paginas - 1 ? " disabled" : ""}>Siguiente</button>
      </div>`
    : "";
  const barra = btnCols || paginador ? `<div class="tabla-barra">${btnCols}${paginador}</div>` : "";
  return info + `<div class="tabla-wrap"><table class="data"><thead>${thead}</thead><tbody>${tbody}</tbody></table></div>` + barra;
}
