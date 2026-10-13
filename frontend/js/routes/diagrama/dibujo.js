import { nMetodo, explicar } from "../../core/indices-info.js";
import { $, esc, formatoBytes } from "../../core/util.js";
import {
  CAB, FILA, IX_H, IX_GAP, IX_TOP, IX_INDENT,
  estado, claveIx, colsDe, num, cortar, tipoCorto,
} from "./estado.js";
import { construir } from "./layout.js";
import { aplicarZoom } from "./zoom.js";

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

export function pintar() {
  const modelo = estado.modelo = construir(estado.datos);
  const dims = estado.dims = { w: modelo.W, h: modelo.H };
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
      estado.seleccion = carta.dataset.t;
      estado.ixSel = carta.dataset.k === estado.ixSel ? null : carta.dataset.k;
    } else if (tabla) {
      estado.seleccion = tabla.dataset.k !== estado.seleccion ? tabla.dataset.k : null;
      estado.ixSel = null;
    } else { estado.seleccion = null; estado.ixSel = null; }
    aplicarSeleccion();
  });
  aplicarZoom();
  aplicarSeleccion();
}

function aplicarSeleccion() {
  const svg = $("diag-lienzo").querySelector("svg"); if (!svg) return;
  const { modelo, seleccion } = estado;
  if (estado.ixSel && !modelo.indicesPorK.has(estado.ixSel)) estado.ixSel = null;
  const ixSel = estado.ixSel;
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
  const { modelo, seleccion, ixSel } = estado;
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
    (estado.mostrarIx ? ` · ${nIx} ${nIx === 1 ? "índice" : "índices"}` : "");
}
