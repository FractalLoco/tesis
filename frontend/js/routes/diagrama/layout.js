import {
  CAB, FILA, PIE, MARGEN, SEP_X, SEP_Y, IX_H, IX_GAP, IX_TOP,
  estado, clave, claveIx, colsDe, nombreTabla, tipoCorto,
} from "./estado.js";

// Calcula tamaño y posición de cada tabla, índice y relación del diagrama.
export function construir(d) {
  const refs = new Set();
  d.relaciones.forEach((r) => r.hacia.columnas.forEach((c) => refs.add(clave(r.hacia.esquema, r.hacia.tabla) + "|" + c)));

  const porTabla = new Map();
  const indicesPorK = new Map();
  if (estado.mostrarIx) {
    for (const i of estado.indices) {
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
    const filas = t.columnas.filter((c) => !estado.soloClaves || c.pk || c.fk || refs.has(k + "|" + c.nombre) || indexadas.has(c.nombre));
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
