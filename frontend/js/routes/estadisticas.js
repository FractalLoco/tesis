import * as api from "../core/api.js";
import { esDemo } from "../core/session.js";
import { estadisticasDemo } from "../core/demo.js";
import { $ } from "../core/util.js";

let timer = null;
const CADA_MS = 3000, UMBRAL_MS = 50, MAX = 40;
const historial = [];

export function render(app) {
  app.innerHTML = `
    <div class="stats-head"><span class="live-dot"></span><b>Monitoreo en vivo</b> <span class="muted mini">actualizando cada 3 s</span></div>
    <div class="chart-card"><h3>Tiempo de respuesta</h3><div class="sub">últimas mediciones (ms)</div><canvas id="chart-respuesta"></canvas></div>
    <div id="stats-grid" class="stats-grid"></div>`;
  historial.length = 0;
  tick();
  timer = setInterval(tick, CADA_MS);
}

export function cleanup() { if (timer) { clearInterval(timer); timer = null; } }

async function tick() {
  let d;
  try { d = esDemo() ? estadisticasDemo() : await api.estadisticas(); }
  catch { d = estadisticasDemo(); }
  const alerta = d.tiempo_respuesta_ms > UMBRAL_MS;
  historial.push(d.tiempo_respuesta_ms);
  if (historial.length > MAX) historial.shift();
  pintar(d, alerta);
  dibujar();
}

function tarjeta(l, v, u = "", alerta = false) {
  return `<div class="stat-card"><div class="stat-label">${l}</div>
    <div class="stat-value${alerta ? " alerta" : ""}">${v}${u ? ` <small>${u}</small>` : ""}</div></div>`;
}

function pintar(d, alerta) {
  $("stats-grid").innerHTML = [
    tarjeta("Tiempo de respuesta", d.tiempo_respuesta_ms, "ms", alerta),
    tarjeta("Cache hit ratio", d.cache_hit_ratio, "%"),
    tarjeta("Conexiones activas", d.conexiones),
    tarjeta("Bloques leídos", (d.blks_read).toLocaleString("es-CL")),
    tarjeta("Bloques en cache", (d.blks_hit).toLocaleString("es-CL")),
    tarjeta("Filas devueltas", (d.tup_returned).toLocaleString("es-CL")),
  ].join("");
}

function dibujar() {
  const cv = $("chart-respuesta"); if (!cv || !historial.length) return;
  const dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth || 600, h = cv.clientHeight || 140;
  cv.width = w * dpr; cv.height = h * dpr;
  const ctx = cv.getContext("2d"); ctx.scale(dpr, dpr); ctx.clearRect(0, 0, w, h);
  const pad = 8, max = Math.max(UMBRAL_MS, ...historial) * 1.15;
  const x = (i) => pad + (i * (w - pad * 2)) / Math.max(1, MAX - 1);
  const y = (v) => h - pad - (v / max) * (h - pad * 2);
  ctx.setLineDash([4, 4]); ctx.strokeStyle = "#dc2626"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(pad, y(UMBRAL_MS)); ctx.lineTo(w - pad, y(UMBRAL_MS)); ctx.stroke(); ctx.setLineDash([]);
  ctx.strokeStyle = "#2563eb"; ctx.lineWidth = 2; ctx.beginPath();
  historial.forEach((v, i) => { const px = x(i), py = y(v); i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); });
  ctx.stroke();
  const li = historial.length - 1, lv = historial[li];
  ctx.fillStyle = lv > UMBRAL_MS ? "#dc2626" : "#2563eb";
  ctx.beginPath(); ctx.arc(x(li), y(lv), 3, 0, Math.PI * 2); ctx.fill();
}
