import * as api from "../core/api.js";
import { esDemo } from "../core/session.js";
import { indicesDemo } from "../core/demo.js";
import { $, esc, formatoBytes } from "../core/util.js";
import { sinUso, nMetodo, explicar } from "../core/indices-info.js";
import { pestanasDatos } from "../core/pestanas.js";

const FILTROS = {
  todos:     { etiqueta: "Todos",         ok: () => true },
  primary:   { etiqueta: "Primarios",     ok: (i) => i.es_primary },
  unique:    { etiqueta: "Únicos",        ok: (i) => i.es_unique && !i.es_primary },
  parcial:   { etiqueta: "Parciales",     ok: (i) => i.parcial },
  expresion: { etiqueta: "Por expresión", ok: (i) => i.expresion },
  sinuso:    { etiqueta: "Sin uso",       ok: (i) => sinUso(i) },
};

let todos = [];
let filtro = "todos";
let texto = "";
let orden = { campo: "tabla", dir: 1 };

const num = (n) => Number(n).toLocaleString("es-CL");

export async function render(app) {
  app.innerHTML = `
    ${pestanasDatos("/indices")}
    <div class="pagina-cab">
      <h2>Índices de la base de datos</h2>
      <p class="muted">Un índice es una guía que le permite a PostgreSQL encontrar filas sin recorrer toda la tabla.
        Aquí se ven todos juntos, separados de las tablas.</p>
    </div>
    <div id="idx-resumen" class="stats-grid idx-resumen"></div>
    <div class="search-bar">
      <svg class="search-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
      <input id="idx-buscar" type="text" placeholder="Buscar por índice, tabla o columna..." />
    </div>
    <div id="idx-chips" class="chips"></div>
    <div id="idx-contenido"><div class="empty">Cargando índices…</div></div>`;
  filtro = "todos"; texto = ""; orden = { campo: "tabla", dir: 1 };
  $("idx-buscar").oninput = (e) => { texto = e.target.value.trim().toLowerCase(); pintarTabla(); };
  await cargar();
}

async function cargar() {
  try {
    todos = esDemo() ? indicesDemo() : (await api.listarIndices()).indices || [];
  } catch (err) {
    $("idx-contenido").innerHTML =
      `<div class="err-box">${esc(err.message)}</div><p><button id="idx-reintentar" class="ghost">Reintentar</button></p>`;
    $("idx-reintentar").onclick = async () => { $("idx-contenido").innerHTML = '<div class="empty">Cargando índices…</div>'; await cargar(); };
    return;
  }
  pintarResumen();
  pintarChips();
  pintarTabla();
}

function tarjeta(etiqueta, valor, nota = "") {
  return `<div class="stat-card"><div class="stat-label">${etiqueta}</div>
    <div class="stat-value">${valor}</div>${nota ? `<div class="stat-nota">${nota}</div>` : ""}</div>`;
}

function pintarResumen() {
  const bytes = todos.reduce((s, i) => s + Number(i.bytes), 0);
  const tablas = new Set(todos.map((i) => i.esquema + "." + i.tabla)).size;
  const libres = todos.filter(sinUso).length;
  $("idx-resumen").innerHTML = [
    tarjeta("Índices", num(todos.length), "en toda la base"),
    tarjeta("Tamaño total", formatoBytes(bytes), "ocupado por los índices"),
    tarjeta("Tablas indexadas", num(tablas)),
    tarjeta("Sin uso registrado", num(libres), "no únicos, nunca leídos"),
  ].join("");
}

function pintarChips() {
  const items = Object.entries(FILTROS).map(([k, f]) => ({ k, etiqueta: f.etiqueta, n: todos.filter(f.ok).length }));
  const metodos = [...new Set(todos.map((i) => i.metodo))].sort();
  metodos.forEach((m) => items.push({ k: "m:" + m, etiqueta: nMetodo(m), n: todos.filter((i) => i.metodo === m).length }));
  $("idx-chips").innerHTML = items
    .filter((c) => c.k === "todos" || c.n > 0)
    .map((c) => `<button class="chip${c.k === filtro ? " activo" : ""}" data-f="${esc(c.k)}">${esc(c.etiqueta)} <b>${c.n}</b></button>`)
    .join("");
  $("idx-chips").querySelectorAll(".chip").forEach((b) => b.onclick = () => {
    filtro = b.dataset.f; pintarChips(); pintarTabla();
  });
}

function cumpleFiltro(i) {
  if (filtro.startsWith("m:")) return i.metodo === filtro.slice(2);
  return FILTROS[filtro].ok(i);
}

function visibles() {
  const lista = todos.filter((i) => cumpleFiltro(i) &&
    (!texto || [i.indice, i.tabla, i.columnas.join(" "), i.metodo].join(" ").toLowerCase().includes(texto)));
  const { campo, dir } = orden;
  const clave = (i) => campo === "bytes" || campo === "usos" ? Number(i[campo]) : String(i[campo]).toLowerCase();
  return lista.map((i, n) => [i, n]).sort(([a, na], [b, nb]) => {
    const ka = clave(a), kb = clave(b);
    return (ka < kb ? -1 : ka > kb ? 1 : 0) * dir || na - nb;
  }).map(([i]) => i);
}

function etiquetas(i) {
  const t = [];
  if (i.es_primary) t.push('<span class="idx-tag idx-pk">PRIMARY</span>');
  else if (i.es_unique) t.push('<span class="idx-tag idx-uq">UNIQUE</span>');
  if (i.parcial) t.push('<span class="idx-tag idx-parcial">PARCIAL</span>');
  if (i.expresion) t.push('<span class="idx-tag idx-expr">EXPRESIÓN</span>');
  if (i.incluye.length) t.push('<span class="idx-tag">INCLUDE</span>');
  if (!i.valido) t.push('<span class="idx-tag idx-mal">INVÁLIDO</span>');
  return t.join("");
}

function detalle(i) {
  const dato = (k, v) => `<div class="idx-dato"><span>${k}</span><b>${v}</b></div>`;
  return `<div class="idx-panel">
    <div class="idx-que"><h4>¿Qué hace este índice?</h4><p>${esc(explicar(i))}</p></div>
    <div class="idx-datos">
      ${dato("Tipo", esc(nMetodo(i.metodo)))}
      ${dato("Columnas indexadas", i.columnas.map((c) => `<code>${esc(c)}</code>`).join(" "))}
      ${i.incluye.length ? dato("Columnas incluidas", i.incluye.map((c) => `<code>${esc(c)}</code>`).join(" ")) : ""}
      ${i.parcial ? dato("Condición", `<code>${esc(i.predicado)}</code>`) : ""}
      ${dato("Tamaño", `${esc(formatoBytes(i.bytes))} <small>(${num(i.bytes)} bytes)</small>`)}
      ${dato("Veces usado", num(i.usos))}
      ${dato("Filas leídas por el índice", num(i.lecturas))}
    </div>
    <pre class="idx-sql">${esc(i.definicion)}</pre>
  </div>`;
}

const COLUMNAS = [
  { campo: "indice", etiqueta: "Índice" },
  { campo: "tabla", etiqueta: "Tabla" },
  { campo: "metodo", etiqueta: "Tipo" },
  { campo: null, etiqueta: "Columnas" },
  { campo: "bytes", etiqueta: "Tamaño", num: true },
  { campo: "usos", etiqueta: "Usos", num: true },
];

function pintarTabla() {
  const lista = visibles();
  const cont = $("idx-contenido");
  if (!lista.length) { cont.innerHTML = '<div class="empty">Ningún índice coincide con la búsqueda o el filtro.</div>'; return; }

  const flecha = (c) => c.campo === orden.campo ? (orden.dir === 1 ? " ▲" : " ▼") : "";
  const thead = COLUMNAS.map((c) => c.campo
    ? `<th class="ordenable${c.num ? " num" : ""}" data-campo="${c.campo}">${c.etiqueta}${flecha(c)}</th>`
    : `<th>${c.etiqueta}</th>`).join("");

  const filas = lista.map((i, n) => `
    <tr class="idx-fila" data-n="${n}">
      <td><span class="chev">&#9656;</span> <span class="idx-nom">${esc(i.indice)}</span><div class="idx-tags">${etiquetas(i)}</div></td>
      <td>${esc(i.esquema !== "public" ? i.esquema + "." : "")}${esc(i.tabla)}</td>
      <td><span class="metodo m-${esc(i.metodo)}">${esc(nMetodo(i.metodo))}</span></td>
      <td>${i.columnas.map((c) => `<code class="col-pill">${esc(c)}</code>`).join(" ")}</td>
      <td class="num">${esc(formatoBytes(i.bytes))}</td>
      <td class="num${sinUso(i) ? " sin-uso" : ""}">${num(i.usos)}</td>
    </tr>
    <tr class="idx-detalle" hidden><td colspan="${COLUMNAS.length}">${detalle(i)}</td></tr>`).join("");

  cont.innerHTML = `
    <div class="tabla-wrap idx-wrap"><table class="data idx-tabla"><thead><tr>${thead}</tr></thead><tbody>${filas}</tbody></table></div>
    <div class="muted mini idx-pie">Mostrando ${lista.length} de ${todos.length} índices · toca una fila para ver qué hace.</div>`;

  cont.querySelectorAll("th.ordenable").forEach((th) => th.onclick = () => {
    const campo = th.dataset.campo;
    orden = { campo, dir: orden.campo === campo ? -orden.dir : 1 };
    pintarTabla();
  });
  cont.querySelectorAll("tr.idx-fila").forEach((tr) => tr.onclick = () => {
    const abierta = tr.classList.toggle("abierta");
    tr.nextElementSibling.hidden = !abierta;
  });
}
