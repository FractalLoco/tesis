// Ruta /diagrama: pinta la pantalla, carga los datos y conecta los controles.
// El cálculo de posiciones está en layout.js, el SVG en dibujo.js y el zoom en zoom.js.
import * as api from "../../core/api.js";
import { esDemo } from "../../core/session.js";
import { diagramaDemo, indicesDemo } from "../../core/demo.js";
import { $, cajaError } from "../../core/util.js";
import { estado } from "./estado.js";
import { pintar } from "./dibujo.js";
import { aplicarZoom, ajustar } from "./zoom.js";

export async function render(app) {
  Object.assign(estado, { soloClaves: false, mostrarIx: true, zoom: 1, seleccion: null, ixSel: null, modelo: null });
  app.innerHTML = `
    <div class="diag-barra">
      <div>
        <h2 class="diag-titulo">Diagrama de tablas</h2>
        <p id="diag-resumen" class="muted mini">Cargando…</p>
      </div>
      <div class="diag-controles">
        <button id="btn-indices" class="ghost activo" type="button" title="Mostrar los índices conectados a cada tabla">Mostrar índices</button>
        <button id="btn-claves" class="ghost" type="button" title="Deja solo las columnas clave (PK, FK) y las indexadas">Solo columnas relevantes</button>
        <div class="zoom">
          <button id="z-menos" class="ghost" type="button" title="Alejar">−</button>
          <span id="z-val">100%</span>
          <button id="z-mas" class="ghost" type="button" title="Acercar">+</button>
          <button id="z-ajustar" class="ghost" type="button">Ajustar</button>
        </div>
      </div>
    </div>
    <div class="diag-leyenda">
      <span><b class="ley pk">PK</b> clave primaria</span>
      <span><b class="ley fk">FK</b> clave foránea</span>
      <span class="ley-rel"><svg viewBox="0 0 60 16" width="60" height="16"><path d="M2 8H58M50 8L58 2M50 8L58 8M50 8L58 14" fill="none" stroke="#94a3b8" stroke-width="1.6"/></svg> relación: muchos → uno</span>
      <span class="ley-rel"><svg viewBox="0 0 60 16" width="60" height="16"><path d="M2 8H50" fill="none" stroke="#a78bfa" stroke-width="1.6" stroke-dasharray="4 3"/><circle cx="54" cy="8" r="3" fill="#8b5cf6"/></svg> índice → columnas que cubre</span>
    </div>
    <div id="diag-info" class="diag-info">Toca una tabla para resaltar sus relaciones, o un índice para ver qué columnas cubre.</div>
    <div id="diag-lienzo" class="diag-lienzo"><div class="empty">Cargando diagrama…</div></div>`;

  $("btn-claves").onclick = () => {
    estado.soloClaves = !estado.soloClaves;
    $("btn-claves").classList.toggle("activo", estado.soloClaves);
    pintar();
  };
  $("btn-indices").onclick = () => {
    estado.mostrarIx = !estado.mostrarIx;
    if (!estado.mostrarIx) estado.ixSel = null;
    $("btn-indices").classList.toggle("activo", estado.mostrarIx);
    pintar();
  };
  $("z-menos").onclick = () => { estado.zoom = Math.max(0.25, estado.zoom - 0.15); aplicarZoom(); };
  $("z-mas").onclick = () => { estado.zoom = Math.min(2, estado.zoom + 0.15); aplicarZoom(); };
  $("z-ajustar").onclick = ajustar;

  try {
    if (esDemo()) { estado.datos = diagramaDemo(); estado.indices = indicesDemo(); }
    else {
      const [d, ix] = await Promise.all([api.obtenerDiagrama(), api.listarIndices()]);
      estado.datos = d; estado.indices = ix.indices || [];
    }
  } catch (err) {
    $("diag-resumen").textContent = "No se pudo cargar el diagrama.";
    $("diag-lienzo").innerHTML =
      `${cajaError(err)}<p style="padding:0 12px"><button id="diag-reintentar" class="ghost">Reintentar</button></p>`;
    $("diag-reintentar").onclick = () => render(app);
    return;
  }
  const { datos, indices } = estado;
  if (!datos.tablas.length) {
    $("diag-resumen").textContent = "La base de datos no tiene tablas.";
    $("diag-lienzo").innerHTML = '<div class="empty">No hay tablas para dibujar.</div>';
    return;
  }
  const nt = datos.tablas.length, nr = datos.relaciones.length, ni = indices.length;
  $("diag-resumen").textContent =
    `${nt} ${nt === 1 ? "tabla" : "tablas"} · ${nr} ${nr === 1 ? "relación" : "relaciones"} · ${ni} ${ni === 1 ? "índice" : "índices"}` +
    (nr ? "" : " — no se encontraron claves foráneas entre las tablas");
  pintar();
  ajustar();
}
