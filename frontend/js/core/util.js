export const $ = (id) => document.getElementById(id);

export const esc = (s) =>
  String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// Caja de error común: el mensaje para el usuario y, si existe, el detalle
// técnico plegado. Acepta un ErrorApi, cualquier Error o un texto.
export function cajaError(err) {
  const mensaje = typeof err === "string" ? err : err?.message || "Ocurrió un error.";
  const detalle = err?.detalle
    ? `<details class="err-mas"><summary>Ver detalle técnico</summary><pre>${esc(err.detalle)}</pre></details>`
    : "";
  return `<div class="err-box" role="alert"><div>${esc(mensaje)}</div>${detalle}</div>`;
}

export const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

export function formatoBytes(n) {
  const u = ["B", "kB", "MB", "GB", "TB"];
  let v = Number(n) || 0, i = 0;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return (i ? v.toLocaleString("es-CL", { maximumFractionDigits: 1 }) : v) + " " + u[i];
}
