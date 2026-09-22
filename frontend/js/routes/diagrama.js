import * as api from "../core/api.js";
import { esDemo } from "../core/session.js";
import { diagramaDemo, indicesDemo } from "../core/demo.js";
import { nMetodo, explicar } from "../core/indices-info.js";
import { $, esc, formatoBytes } from "../core/util.js";

const CAB = 38, FILA = 25, PIE = 8, MARGEN = 56, SEP_X = 150, SEP_Y = 34;
const IX_H = 58, IX_GAP = 8, IX_TOP = 18, IX_INDENT = 22;

let datos = null;
let indices = [];
let soloClaves = false;
let mostrarIx = true;
let zoom = 1;
let seleccion = null;     // clave de la tabla seleccionada
let ixSel = null;         // clave del índice seleccionado (dentro de la tabla seleccionada)
let dims = { w: 0, h: 0 };
let modelo = null;

const clave = (e, t) => `${e}.${t}`;
const claveIx = (i) => `${i.esquema}.${i.indice}`;
const colsDe = (i) => (i.cols_tabla && i.cols_tabla.length ? i.cols_tabla : i.columnas);
const nombreTabla = (t) => (t.esquema === "public" ? t.tabla : `${t.esquema}.${t.tabla}`);
const num = (n) => Number(n).toLocaleString("es-CL");
const cortar = (s, max) => (s.length > max ? s.slice(0, Math.max(1, max - 1)) + "…" : s);

const TIPOS = { "character varying": "varchar", "timestamp without time zone": "timestamp",
  "timestamp with time zone": "timestamptz", "double precision": "double", "time without time zone": "time",
  "character": "char" };

function tipoCorto(t) {
  let s = String(t);
  for (const [largo, corto] of Object.entries(TIPOS)) if (s.startsWith(largo)) { s = corto + s.slice(largo.length); break; }
  return cortar(s, 20);
}

export async function render(app) {
  soloClaves = false; mostrarIx = true; zoom = 1; seleccion = null; ixSel = null; modelo = null;
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
    soloClaves = !soloClaves;
    $("btn-claves").classList.toggle("activo", soloClaves);
    pintar();
  };
  $("btn-indices").onclick = () => {
    mostrarIx = !mostrarIx;
    if (!mostrarIx) ixSel = null;
    $("btn-indices").classList.toggle("activo", mostrarIx);
    pintar();
  };
  $("z-menos").onclick = () => { zoom = Math.max(0.25, zoom - 0.15); aplicarZoom(); };
  $("z-mas").onclick = () => { zoom = Math.min(2, zoom + 0.15); aplicarZoom(); };
  $("z-ajustar").onclick = ajustar;

  try {
    if (esDemo()) { datos = diagramaDemo(); indices = indicesDemo(); }
    else {
      const [d, ix] = await Promise.all([api.obtenerDiagrama(), api.listarIndices()]);
      datos = d; indices = ix.indices || [];
    }
  } catch (err) {
    $("diag-resumen").textContent = "No se pudo cargar el diagrama.";
    $("diag-lienzo").innerHTML =
      `<div class="err-box">${esc(err.message)}</div><p style="padding:0 12px"><button id="diag-reintentar" class="ghost">Reintentar</button></p>`;
    $("diag-reintentar").onclick = () => render(app);
    return;
  }
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

/* ---------- Layout ---------- */

function construir(d) {
  const refs = new Set();
  d.relaciones.forEach((r) => r.hacia.columnas.forEach((c) => refs.add(clave(r.hacia.esquema, r.hacia.tabla) + "|" + c)));

  const porTabla = new Map();
  const indicesPorK = new Map();
  if (mostrarIx) {
    for (const i of indices) {
      const k = clave(i.esquema, i.tabla);
      if (!porTabla.has(k)) porTabla.set(k, []);
      porTabla.get(k).push(i);
      indicesPorK.set(claveIx(i), i);
    }
  }

  const nodos = new Map();
  for (const t of d.tablas) {
    const k = clave(t.esquema, t.tabla);
    const ixs = porTabla.get(k) || [];
    const indexadas = new Set(ixs.flatMap(colsDe));
    const filas = t.columnas.filter((c) => !soloClaves || c.pk || c.fk || refs.has(k + "|" + c.nombre) || indexadas.has(c.nombre));
    const nombre = nombreTabla(t);
    const ancho = Math.min(420, Math.max(ixs.length ? 260 : 210, nombre.length * 8.6 + 96,
      ...filas.map((c) => 48 + c.nombre.length * 7.4 + 24 + tipoCorto(c.tipo).length * 6.4 + 14)));
    const hT = CAB + Math.max(1, filas.length) * FILA + PIE;
    const h = hT + (ixs.length ? IX_TOP + ixs.length * IX_H + (ixs.length - 1) * IX_GAP : 0);
    nodos.set(k, { k, t, nombre, filas, ixs, w: Math.round(ancho), hT, h, x: 0, y: 0, suelto: false });
  }

  const aristas = d.relaciones.map((r) => ({
    nombre: r.nombre, hijo: clave(r.desde.esquema, r.desde.tabla), padre: clave(r.hacia.esquema, r.hacia.tabla),
    cH: r.desde.columnas, cP: r.hacia.columnas,
  })).filter((e) => nodos.has(e.hijo) && nodos.has(e.padre));

  const conectado = new Set();
  aristas.forEach((e) => { if (e.hijo !== e.padre) { conectado.add(e.hijo); conectado.add(e.padre); } });

  // Capa de cada tabla: las referenciadas (padres) quedan a la izquierda de quienes las referencian.
  const nivel = new Map([...conectado].map((k) => [k, 0]));
  for (let it = 0; it < nivel.size; it++) {
    let cambio = false;
    for (const e of aristas) {
      if (e.hijo === e.padre) continue;
      const n = Math.min(nivel.get(e.padre) + 1, nivel.size - 1);
      if (n > nivel.get(e.hijo)) { nivel.set(e.hijo, n); cambio = true; }
    }
    if (!cambio) break;
  }
  const columnas = Array.from({ length: Math.max(-1, ...nivel.values()) + 1 }, () => []);
  [...nivel.keys()].sort().forEach((k) => columnas[nivel.get(k)].push(k));

  // Las relaciones que saltan varias capas pasan por "puntos ficticios" (uno por capa intermedia)
  // que se ordenan como si fueran tablas: así la línea esquiva a las tablas del medio.
  const fict = new Map();
  const dim = (k) => nodos.get(k) || fict.get(k);
  const vecinos = new Map([...conectado].map((k) => [k, []]));
  const unir = (a, b) => { vecinos.get(a).push(b); vecinos.get(b).push(a); };
  aristas.forEach((e, i) => {
    e.via = [];
    if (e.hijo === e.padre) return;
    let previo = e.padre;
    for (let L = nivel.get(e.padre) + 1; L < nivel.get(e.hijo); L++) {
      const k = `~${i}~${L}`;
      fict.set(k, { k, h: 16, w: 0, x: 0, y: 0, capa: L });
      columnas[L].push(k);
      vecinos.set(k, []);
      unir(previo, k);
      e.via.push(k);
      previo = k;
    }
    unir(previo, e.hijo);
  });
  ordenar(columnas, vecinos, dim);

  const altoCol = columnas.map((col) => col.reduce((s, k) => s + dim(k).h, 0) + Math.max(0, col.length - 1) * SEP_Y);
  const alto0 = Math.max(0, ...altoCol);
  const colInfo = [];
  let x = MARGEN;
  columnas.forEach((col, i) => {
    if (!col.length) return;
    let y = MARGEN + (alto0 - altoCol[i]) / 2;
    col.forEach((k) => { const n = dim(k); n.x = x; n.y = y; y += n.h + SEP_Y; });
    const w = Math.max(40, ...col.map((k) => dim(k).w));
    colInfo[i] = { x, w };
    x += w + SEP_X;
  });
  let W = columnas.length ? x - SEP_X + MARGEN : MARGEN * 2;
  let H = MARGEN * 2 + alto0;

  // Tablas sin relaciones: en una cuadrícula debajo del diagrama.
  const sueltos = [...nodos.keys()].filter((k) => !conectado.has(k)).sort();
  let etiquetaSueltos = null;
  if (sueltos.length) {
    const maxW = Math.max(W, 980);
    let y = MARGEN, cx = MARGEN, altoFila = 0;
    if (columnas.length) { etiquetaSueltos = { x: MARGEN, y: H - MARGEN + 26 }; y = H - MARGEN + 44; }
    for (const k of sueltos) {
      const n = nodos.get(k);
      n.suelto = true;
      if (cx + n.w > maxW - MARGEN && cx > MARGEN) { cx = MARGEN; y += altoFila + SEP_Y; altoFila = 0; }
      n.x = cx; n.y = y; cx += n.w + 40; altoFila = Math.max(altoFila, n.h);
      W = Math.max(W, cx - 40 + MARGEN);
    }
    H = y + altoFila + MARGEN;
  }
  return { nodos, aristas, fict, colInfo, indicesPorK, W: Math.round(W), H: Math.round(H), etiquetaSueltos };
}

// Reduce cruces de líneas: ordena cada capa según la altura media de sus vecinos (baricentro).
function ordenar(columnas, vecinos, dim) {
  const pos = new Map();
  const asignar = () => columnas.forEach((col) => {
    let y = 0;
    col.forEach((k) => { const h = dim(k).h; pos.set(k, y + h / 2); y += h + SEP_Y; });
  });
  asignar();
  for (let pasada = 0; pasada < 6; pasada++) {
    const idx = columnas.map((_, i) => i);
    if (pasada % 2) idx.reverse();
    for (const i of idx) {
      const bc = new Map(columnas[i].map((k) => {
        const v = vecinos.get(k) || [];
        return [k, v.length ? v.reduce((s, n) => s + pos.get(n), 0) / v.length : pos.get(k)];
      }));
      columnas[i].sort((a, b) => bc.get(a) - bc.get(b) || a.localeCompare(b));
      asignar();
    }
  }
}

/* ---------- Dibujo (SVG) ---------- */

function yFila(n, col) {
  const i = n.filas.findIndex((c) => c.nombre === col);
  return n.y + (i < 0 ? CAB / 2 : CAB + i * FILA + FILA / 2);
}

// Tarjeta de un índice (con sus características) que cuelga debajo de su tabla.
function svgIndice(n, ix, i) {
  const w = n.w - IX_INDENT - 8;
  const y = n.hT + IX_TOP + i * (IX_H + IX_GAP);
  const marcas = [[nMetodo(ix.metodo), "m-" + ix.metodo]];
  if (ix.es_primary) marcas.push(["PK", "pk"]);
  else if (ix.es_unique) marcas.push(["UNIQUE", "uq"]);
  if (ix.parcial) marcas.push(["PARCIAL", "pa"]);
  if (ix.expresion) marcas.push(["EXPR", "ex"]);
  if (ix.incluye.length) marcas.push(["INCLUDE", "in"]);
  if (!ix.valido) marcas.push(["INVÁLIDO", "mal"]);
  let bx = 10, badges = "";
  for (const [texto, cls] of marcas) {
    const bw = Math.round(texto.length * 5.9 + 12);
    if (bx + bw > w - 8) break;
    badges += `<g transform="translate(${bx} 24)"><rect class="ix-b ${cls}" width="${bw}" height="14" rx="7"/>` +
      `<text class="ix-bt ${cls}" x="${bw / 2}" y="10.5" text-anchor="middle">${esc(texto)}</text></g>`;
    bx += bw + 4;
  }
  const uso = `${formatoBytes(ix.bytes)} · ${num(ix.usos)} ${Number(ix.usos) === 1 ? "uso" : "usos"}`;
  const izq = cortar(ix.columnas.join(", "), Math.floor((w - 20 - uso.length * 5.7) / 5.9));
  const tip = `${ix.indice}\n${explicar(ix)}\n\n${ix.definicion}`;
  return `
    <g class="idx-card" data-k="${esc(claveIx(ix))}" data-t="${esc(n.k)}" transform="translate(${IX_INDENT} ${y})">
      <title>${esc(tip)}</title>
      <rect class="ix-caja" width="${w}" height="${IX_H}" rx="9"/>
      <text class="ix-nom" x="10" y="16">${esc(cortar(ix.indice, Math.floor((w - 20) / 6.4)))}</text>
      ${badges}
      <text class="ix-dato" x="10" y="52">${esc(izq)}</text>
      <text class="ix-dato" x="${w - 10}" y="52" text-anchor="end">${esc(uso)}</text>
    </g>`;
}

// Conector del índice hacia cada columna de la tabla que cubre (riel a la izquierda de la tabla).
function svgRiel(n, ix, i) {
  const ys = colsDe(ix).map((c) => n.filas.findIndex((f) => f.nombre === c))
    .filter((j) => j >= 0).map((j) => CAB + j * FILA + FILA / 2);
  if (!ys.length) return "";
  const rx = -(12 + (i % 6) * 6);
  const cy = n.hT + IX_TOP + i * (IX_H + IX_GAP) + IX_H / 2;
  let d = `M${IX_INDENT} ${cy}H${rx}V${Math.min(...ys)}`;
  ys.forEach((y) => { d += `M${rx} ${y}H0`; });
  return `<g class="rail" data-k="${esc(claveIx(ix))}"><path d="${d}"/>` +
    ys.map((y) => `<circle cx="0" cy="${y}" r="3"/>`).join("") + "</g>";
}

function svgNodo(n) {
  const ty = FILA / 2 + 4;
  const filas = n.filas.length
    ? n.filas.map((c, i) => `
        <g class="fila" data-col="${esc(c.nombre)}" transform="translate(0 ${CAB + i * FILA})">
          <rect class="fila-bg" x="1" y="0" width="${n.w - 2}" height="${FILA}"/>
          ${i ? `<line class="sep" x1="1" x2="${n.w - 1}" y1="0" y2="0"/>` : ""}
          <text class="ins ${c.pk ? "pk" : "fk"}" x="12" y="${ty}">${c.pk ? "PK" : c.fk ? "FK" : ""}</text>
          <text class="c-nom${c.pk ? " pk" : ""}" x="42" y="${ty}">${esc(c.nombre)}</text>
          <text class="c-tipo" x="${n.w - 12}" y="${ty}" text-anchor="end">${esc(tipoCorto(c.tipo))}</text>
        </g>`).join("")
    : `<text class="c-tipo" x="12" y="${CAB + 17}">(sin columnas clave)</text>`;
  const filasTxt = n.t.filas_est >= 0 ? `${n.t.filas_est.toLocaleString("es-CL")} filas` : "";
  return `
    <g class="nodo-t" data-k="${esc(n.k)}" transform="translate(${n.x} ${n.y})">
      <title>${esc(n.nombre)} · ${n.t.columnas.length} columnas${filasTxt ? " · " + filasTxt : ""}${n.ixs.length ? " · " + n.ixs.length + " índices" : ""}</title>
      <rect class="caja" width="${n.w}" height="${n.hT}" rx="10"/>
      <path class="cab${n.suelto ? " aislada" : ""}" d="M0 ${CAB}V10Q0 0 10 0H${n.w - 10}Q${n.w} 0 ${n.w} 10V${CAB}Z"/>
      <text class="t-nombre" x="12" y="${CAB / 2 + 5}">${esc(n.nombre)}</text>
      <text class="t-filas" x="${n.w - 12}" y="${CAB / 2 + 4}" text-anchor="end">${esc(filasTxt)}</text>
      ${filas}
      ${n.ixs.map((ix, i) => svgRiel(n, ix, i)).join("")}
      ${n.ixs.map((ix, i) => svgIndice(n, ix, i)).join("")}
    </g>`;
}

function curvaPorPuntos(pts) {
  let d = `M${pts[0][0]} ${pts[0][1]}`;
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1], [x1, y1] = pts[i], c = (x1 - x0) / 2;
    d += `C${x0 + c} ${y0} ${x1 - c} ${y1} ${x1} ${y1}`;
  }
  return d;
}

function svgArista(e, m) {
  const nodos = m.nodos;
  const h = nodos.get(e.hijo), p = nodos.get(e.padre);
  const yh = yFila(h, e.cH[0]), yp = yFila(p, e.cP[0]);
  let xp, xh, dp, dh, c;
  if (h === p) { xp = xh = h.x + h.w; dp = dh = 1; c = 46; }
  else if (p.x + p.w <= h.x) { xp = p.x + p.w; dp = 1; xh = h.x; dh = -1; c = Math.max(40, (xh - xp) / 2); }
  else if (h.x + h.w <= p.x) { xp = p.x; dp = -1; xh = h.x + h.w; dh = 1; c = Math.max(40, (xp - xh) / 2); }
  else { xp = p.x + p.w; dp = 1; xh = h.x + h.w; dh = 1; c = 60; }
  let d = `M${xp} ${yp}C${xp + dp * c} ${yp} ${xh + dh * c} ${yh} ${xh} ${yh}`;
  if (e.via.length) {
    xp = p.x + p.w; xh = h.x; dp = 1; dh = -1;
    const pts = [[xp, yp]];
    e.via.forEach((k) => {
      const f = m.fict.get(k), ci = m.colInfo[f.capa], yc = f.y + f.h / 2;
      pts.push([ci.x - 10, yc], [ci.x + ci.w + 10, yc]);
    });
    pts.push([xh, yh]);
    d = curvaPorPuntos(pts);
  }
  const ax = xh + dh * 11;
  const marcas = `M${xp + dp * 9} ${yp - 6}V${yp + 6}` +
    `M${ax} ${yh}L${xh} ${yh - 6}M${ax} ${yh}L${xh} ${yh}M${ax} ${yh}L${xh} ${yh + 6}`;
  return `
    <g class="arista" data-h="${esc(e.hijo)}" data-p="${esc(e.padre)}">
      <title>${esc(`${h.nombre}(${e.cH.join(", ")}) → ${p.nombre}(${e.cP.join(", ")})`)}</title>
      <path class="linea" d="${d}"/><path class="marca" d="${marcas}"/><path class="area" d="${d}"/>
    </g>`;
}

function pintar() {
  modelo = construir(datos);
  dims = { w: modelo.W, h: modelo.H };
  const { nodos, aristas, etiquetaSueltos } = modelo;
  $("diag-lienzo").innerHTML =
    `<svg class="diag-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${dims.w} ${dims.h}" width="${dims.w}" height="${dims.h}">
       ${etiquetaSueltos ? `<text class="grupo-etq" x="${etiquetaSueltos.x}" y="${etiquetaSueltos.y}">Tablas sin relaciones</text>` : ""}
       <g>${aristas.map((e) => svgArista(e, modelo)).join("")}</g>
       <g>${[...nodos.values()].map(svgNodo).join("")}</g>
     </svg>`;
  $("diag-lienzo").querySelector("svg").addEventListener("click", (ev) => {
    const carta = ev.target.closest(".idx-card");
    const tabla = ev.target.closest(".nodo-t");
    if (carta) {
      seleccion = carta.dataset.t;
      ixSel = carta.dataset.k === ixSel ? null : carta.dataset.k;
    } else if (tabla) {
      seleccion = tabla.dataset.k !== seleccion ? tabla.dataset.k : null;
      ixSel = null;
    } else { seleccion = null; ixSel = null; }
    aplicarSeleccion();
  });
  aplicarZoom();
  aplicarSeleccion();
}

function aplicarSeleccion() {
  const svg = $("diag-lienzo").querySelector("svg"); if (!svg) return;
  if (ixSel && !modelo.indicesPorK.has(ixSel)) ixSel = null;
  svg.classList.toggle("sel-activa", !!seleccion);
  const rel = new Set();
  svg.querySelectorAll(".arista").forEach((a) => {
    const on = !!seleccion && (a.dataset.h === seleccion || a.dataset.p === seleccion);
    a.classList.toggle("rel", on);
    if (on) { rel.add(a.dataset.h); rel.add(a.dataset.p); }
  });
  const cubiertas = ixSel ? new Set(colsDe(modelo.indicesPorK.get(ixSel))) : null;
  svg.querySelectorAll(".nodo-t").forEach((n) => {
    const es = n.dataset.k === seleccion;
    n.classList.toggle("sel", es);
    n.classList.toggle("rel", rel.has(n.dataset.k) && !es);
    n.classList.toggle("tiene-ix", es && !!ixSel);
    n.querySelectorAll(".idx-card, .rail").forEach((e) => e.classList.toggle("sel-ix", es && e.dataset.k === ixSel));
    n.querySelectorAll(".fila").forEach((f) => f.classList.toggle("cubierta", es && !!cubiertas && cubiertas.has(f.dataset.col)));
  });
  actualizarInfo();
}

function actualizarInfo() {
  const el = $("diag-info");
  if (!seleccion) { el.textContent = "Toca una tabla para resaltar sus relaciones, o un índice para ver qué columnas cubre."; return; }
  if (ixSel) {
    const ix = modelo.indicesPorK.get(ixSel);
    el.innerHTML = `Índice <b>${esc(ix.indice)}</b> · ${esc(nMetodo(ix.metodo))} · cubre: ${colsDe(ix).map((c) => `<b>${esc(c)}</b>`).join(", ")}` +
      ` · ${esc(formatoBytes(ix.bytes))} · usado ${num(ix.usos)} ${Number(ix.usos) === 1 ? "vez" : "veces"}`;
    return;
  }
  const nombre = (k) => modelo.nodos.get(k).nombre;
  const hacia = [...new Set(modelo.aristas.filter((e) => e.hijo === seleccion && e.padre !== seleccion).map((e) => nombre(e.padre)))];
  const desde = [...new Set(modelo.aristas.filter((e) => e.padre === seleccion && e.hijo !== seleccion).map((e) => nombre(e.hijo)))];
  const lista = (a) => a.length ? a.map((x) => `<b>${esc(x)}</b>`).join(", ") : "ninguna";
  const nIx = modelo.nodos.get(seleccion).ixs.length;
  el.innerHTML = `<b>${esc(nombre(seleccion))}</b> · referencia a: ${lista(hacia)} · referenciada por: ${lista(desde)}` +
    (mostrarIx ? ` · ${nIx} ${nIx === 1 ? "índice" : "índices"}` : "");
}

/* ---------- Zoom ---------- */

function aplicarZoom() {
  const svg = $("diag-lienzo").querySelector("svg");
  if (svg) { svg.setAttribute("width", Math.round(dims.w * zoom)); svg.setAttribute("height", Math.round(dims.h * zoom)); }
  $("z-val").textContent = Math.round(zoom * 100) + "%";
}

function ajustar() {
  const ancho = $("diag-lienzo").clientWidth - 4;
  zoom = Math.max(0.25, Math.min(1, ancho / dims.w));
  aplicarZoom();
}
