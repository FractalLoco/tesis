import * as api from "../core/api.js";
import { obtener as sesionActual, esDemo } from "../core/session.js";
import { prediccionDemo } from "../core/demo.js";
import * as historial from "../core/historial.js";
import { $, activarCopiar, cajaError, cajaSQL, copiar, esc } from "../core/util.js";

const TIPO = "prediccion";
// Ejemplo según la base: en modo demo usa sus tablas inventadas; con una base
// real, el esquema tipo TPC-H del proyecto (sql/base_de_prueba.sql y el modelo).
const EJEMPLO_DEMO = "SELECT p.id, c.nombre, p.total\nFROM pedidos p\nJOIN clientes c ON c.id = p.cliente_id\nWHERE p.estado = 'pendiente'\nORDER BY p.fecha DESC\nLIMIT 50;";
const EJEMPLO_TPCH = "SELECT o_orderkey, o_totalprice\nFROM orders\nWHERE o_totalprice > 80000\nORDER BY o_totalprice DESC\nLIMIT 50;";
const ejemplo = () => (esDemo() ? EJEMPLO_DEMO : EJEMPLO_TPCH);

const dbname = () => (sesionActual() || {}).dbname || "";
const num = (n) => Number(n).toLocaleString("es-CL", { maximumFractionDigits: 2 });

// Se incrementa al salir de la ruta: si "predecir" responde después de eso,
// no toca el DOM (que el router ya reemplazó por el de otra pantalla).
let vigencia = 0;

export function render(app) {
  vigencia++;
  app.innerHTML = `
    <div class="pagina-cab">
      <h2>Predicción de índice</h2>
      <p class="muted">Pega una consulta (o aprieta el botón con el ejemplo) y te decimos qué índices crear, con el SQL
        listo para copiar. Lo decide el modelo de ML junto con reglas sobre el plan; la consulta no se ejecuta
        y ningún índice se crea solo.</p>
    </div>
    <div class="editor-sql">
      <textarea id="pi-sql" rows="6" spellcheck="false" placeholder="${esc(ejemplo())}"></textarea>
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

  $("pi-ejemplo").onclick = () => { $("pi-sql").value = ejemplo(); };
  $("pi-ejecutar").onclick = ejecutar;
  $("pi-limpiar").onclick = () => { historial.limpiar(TIPO, dbname()); pintarHistorial(); };
  pintarHistorial();
}

export function cleanup() { vigencia++; }

async function ejecutar() {
  // Sin texto se usa el ejemplo que se ve en el cuadro.
  if (!$("pi-sql").value.trim()) $("pi-sql").value = ejemplo();
  const sql = $("pi-sql").value.trim();
  const token = vigencia;
  const boton = $("pi-ejecutar");
  boton.disabled = true;
  $("pi-estado").textContent = "Analizando el plan estimado…";
  $("pi-error").innerHTML = "";
  try {
    // Reglas y modelo (V2) a la vez. Si el modelo falla, quedan las reglas.
    const [reglas, modelo] = await Promise.all([
      esDemo() ? prediccionDemo(sql) : api.predecirIndices(sql),
      esDemo() ? null : api.version2(sql).catch(() => null),
    ]);
    if (token !== vigencia) return;
    const lista = combinar(reglas, modelo);
    pintarResultado(lista, reglas, modelo);
    historial.agregar(TIPO, dbname(), { sql, n: lista.filter((x) => x.crear).length });
    pintarHistorial();
  } catch (err) {
    if (token !== vigencia) return;
    $("pi-error").innerHTML = cajaError(err);
    $("pi-resultado").innerHTML = "";
  } finally {
    if (token === vigencia) { boton.disabled = false; $("pi-estado").textContent = ""; }
  }
}

// Une lo de las reglas con lo del modelo por (tabla, columna). Se recomienda crear
// lo que el modelo recomienda y lo que solo vieron las reglas (el modelo no mira
// ORDER BY ni tablas chicas); si el modelo lo evaluó y predice poca mejora, no.
function combinar(reglas, modelo) {
  const items = new Map();
  for (const r of reglas.recomendaciones || []) {
    items.set(`${r.tabla}.${r.columna}`, { ...r, mejora: null, crear: true });
  }
  if (modelo?.disponible) {
    for (const c of modelo.candidatos) {
      const k = `${c.tabla}.${c.columna}`;
      const previo = items.get(k) || { tabla: c.tabla, columna: c.columna, sql_sugerido: c.sql_sugerido,
        motivos: [c.uso === "filtro" ? "Se usa para filtrar (WHERE) y no tiene índice." : "Se usa para unir tablas (JOIN) y no tiene índice."] };
      items.set(k, { ...previo, mejora: c.mejora_pct, mb: c.mb, crear: c.recomendado });
    }
  }
  return [...items.values()].sort((a, b) => (b.crear - a.crear) || ((b.mejora ?? -1) - (a.mejora ?? -1)));
}

// Tabla de opciones: cada índice con su casilla. Vienen marcados los recomendados;
// la caja de arriba junta los marcados para copiarlos de una vez.
function pintarResultado(lista, reglas, modelo) {
  if (!lista.length) {
    $("pi-resultado").innerHTML = `<div class="empty">No hace falta ningún índice nuevo: la consulta ya está cubierta por los índices actuales.</div>`;
    return;
  }
  const filas = lista.map((r, i) => `
    <tr class="${r.crear ? "ver-elegido" : ""}">
      <td><input type="checkbox" class="pi-marca" data-i="${i}" ${r.crear ? "checked" : ""} aria-label="Elegir ${esc(r.tabla)}.${esc(r.columna)}"></td>
      <td><code>${esc(r.tabla)}.${esc(r.columna)}</code></td>
      <td>${etiqueta(r)}</td>
      <td>${r.mb != null ? `${num(r.mb)} MB` : "—"}</td>
      <td class="pi-motivo">${esc((r.motivos || [])[0] || "")}${(r.motivos || []).length > 1
        ? `<div class="muted mini">${(r.motivos || []).slice(1).map(esc).join("<br>")}</div>` : ""}</td>
      <td><code class="pi-sql">${esc(r.sql_sugerido)}</code></td>
      <td><button type="button" class="ghost mini-boton pi-copiar-uno" data-i="${i}">Copiar</button></td>
    </tr>`).join("");
  $("pi-resultado").innerHTML = `
    ${cajaSQL("pi-copiar", "", "")}
    <div class="tabla-wrap ver-tabla"><table class="data">
      <thead><tr><th></th><th>Índice en</th><th>Mejora</th><th>Tamaño</th><th>Por qué</th><th>SQL</th><th></th></tr></thead>
      <tbody>${filas}</tbody></table></div>
    <p class="muted mini">${modelo?.disponible
      ? "Marca los índices que quieras y copia el bloque de arriba. La mejora la predice el modelo de índices (V2); vienen marcados los que superan 10 %."
      : esc(reglas.nota || "")}</p>`;
  const marcas = [...document.querySelectorAll(".pi-marca")];
  const actualizar = () => {
    const elegidos = marcas.filter((m) => m.checked).map((m) => lista[m.dataset.i]);
    $("pi-copiar").textContent = elegidos.length
      ? elegidos.map((x) => x.sql_sugerido).join("\n")
      : "-- Marca al menos un índice en la tabla.";
    $("pi-copiar-titulo").textContent = elegidos.length
      ? `${elegidos.length} ${elegidos.length === 1 ? "índice elegido" : "índices elegidos"}`
      : "Ningún índice elegido";
    marcas.forEach((m) => m.closest("tr").classList.toggle("ver-elegido", m.checked));
  };
  marcas.forEach((m) => { m.onchange = actualizar; });
  document.querySelectorAll(".pi-copiar-uno").forEach((b) => {
    b.onclick = () => copiar(lista[b.dataset.i].sql_sugerido, b);
  });
  activarCopiar($("pi-resultado"));
  actualizar();
}

function etiqueta(r) {
  if (r.mejora == null) return '<span class="pill-ok">por reglas</span>';
  return r.crear ? `<span class="pill-ok">${num(r.mejora)} % más rápido</span>`
    : `<span class="pill-no">${num(r.mejora)} % (poco)</span>`;
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
