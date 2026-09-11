export const $ = (id) => document.getElementById(id);

export const esc = (s) =>
  String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

export const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

export function formatoBytes(n) {
  const u = ["B", "kB", "MB", "GB", "TB"];
  let v = Number(n) || 0, i = 0;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return (i ? v.toLocaleString("es-CL", { maximumFractionDigits: 1 }) : v) + " " + u[i];
}
