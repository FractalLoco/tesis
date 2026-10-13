import { $ } from "../../core/util.js";
import { estado } from "./estado.js";

export function aplicarZoom() {
  const { dims, zoom } = estado;
  const svg = $("diag-lienzo").querySelector("svg");
  if (svg) { svg.setAttribute("width", Math.round(dims.w * zoom)); svg.setAttribute("height", Math.round(dims.h * zoom)); }
  $("z-val").textContent = Math.round(zoom * 100) + "%";
}

export function ajustar() {
  const ancho = $("diag-lienzo").clientWidth - 4;
  estado.zoom = Math.max(0.25, Math.min(1, ancho / estado.dims.w));
  aplicarZoom();
}
