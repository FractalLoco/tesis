import * as session from "./session.js";
import { $, esperar } from "./util.js";

import * as conexion from "../routes/conexion.js";
import * as validando from "../routes/validando.js";
import * as tablas from "../routes/tablas.js";
import * as indices from "../routes/indices.js";
import * as diagrama from "../routes/diagrama.js";
import * as estadisticas from "../routes/estadisticas.js";
import * as noDisponible from "../routes/no-disponible.js";
// "optimizacion.js" y "prediccion.js" ya están construidas y probadas (editor SQL,
// plan de ejecución, recomendaciones, historial); el navbar las deja apuntando a
// 404 por ahora a pedido del usuario, listas para reactivar cambiando estas dos
// líneas en RUTAS más abajo por: import * as optimizacion from "../routes/optimizacion.js";
// y lo mismo para prediccion.js.

const RUTAS = {
  "/conexion":     { modulo: conexion,     requiereConexion: false, navbar: false },
  "/validando":    { modulo: validando,    requiereConexion: true,  navbar: false },
  "/tablas":       { modulo: tablas,       requiereConexion: true,  navbar: true, titulo: "Datos de la tabla" },
  "/indices":      { modulo: indices,      requiereConexion: true,  navbar: true, titulo: "Índices", navActivo: "/tablas" },
  "/diagrama":     { modulo: diagrama,     requiereConexion: true,  navbar: true, titulo: "Diagrama de tablas", ancho: true },
  "/estadisticas": { modulo: estadisticas, requiereConexion: true,  navbar: true, titulo: "Estadísticas SQL" },
  "/optimizacion": { modulo: noDisponible, requiereConexion: true,  navbar: true, titulo: "Optimización de consulta" },
  "/prediccion":   { modulo: noDisponible, requiereConexion: true,  navbar: true, titulo: "Predicción de índice" },
};

let rutaActual = null;

// Navegación con la History API: la URL queda limpia (/tablas, /diagrama...),
// sin "#". El backend devuelve index.html para estas rutas (ver backend/main.py),
// así que también se pueden refrescar o abrir directamente.
// "reemplazar" se usa en las redirecciones, para no dejar entradas que el botón
// Atrás volvería a redirigir.
export function irA(ruta, { reemplazar = false } = {}) {
  if (window.location.pathname !== ruta) {
    history[reemplazar ? "replaceState" : "pushState"](null, "", ruta);
  }
  render();
}

function rutaActualUrl() {
  const p = window.location.pathname;
  return RUTAS[p] ? p : (session.estaConectado() ? "/tablas" : "/conexion");
}

async function render() {
  const ruta = rutaActualUrl();
  if (ruta !== window.location.pathname) return irA(ruta, { reemplazar: true });
  const def = RUTAS[ruta];

  if (def.requiereConexion && !session.estaConectado()) {
    return irA("/conexion", { reemplazar: true });
  }

  // rutaActual se actualiza ANTES de esperar a que la ruta cargue sus datos:
  // si el usuario navega otra vez mientras esta carga sigue en curso (por
  // ejemplo, justo tras un redirect automático), la siguiente llamada a
  // render() ya ve el estado correcto y limpia la ruta que corresponde.
  if (rutaActual && rutaActual.modulo.cleanup) rutaActual.modulo.cleanup();
  rutaActual = def;

  pintarNavbar(def, ruta);

  const app = $("app");
  app.innerHTML = "";
  app.className = "app-container" + (def.ancho ? " ancho" : "");
  await def.modulo.render(app, { ruta, titulo: def.titulo });
}

function pintarNavbar(def, ruta) {
  const nav = $("navbar");
  if (!def.navbar) { nav.classList.add("hidden"); return; }
  nav.classList.remove("hidden");
  const activa = def.navActivo || ruta;
  nav.querySelectorAll("a.nav-item").forEach((a) =>
    a.classList.toggle("active", a.getAttribute("href") === activa));
}

async function refrescar() {
  const btn = $("btn-refrescar");
  btn.disabled = true;
  btn.classList.add("girando");
  await Promise.all([render(), esperar(700)]);
  btn.classList.remove("girando");
  btn.disabled = false;
}

// Los enlaces internos (<a href="/tablas">) navegan sin recargar la página.
// Ctrl/Cmd + clic o clic central siguen abriendo una pestaña nueva.
function interceptarEnlaces(e) {
  const a = e.target.closest("a[href^='/']");
  if (!a || a.target || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
  const ruta = a.getAttribute("href");
  if (!RUTAS[ruta]) return;
  e.preventDefault();
  irA(ruta);
}

export function iniciarRouter() {
  // Enlaces antiguos con "#/ruta" se convierten a la ruta limpia.
  if (window.location.hash.startsWith("#/")) {
    history.replaceState(null, "", window.location.hash.slice(1));
  }
  window.addEventListener("popstate", render);
  document.addEventListener("click", interceptarEnlaces);
  $("btn-refrescar").addEventListener("click", refrescar);
  $("nav-salir").addEventListener("click", () => session.limpiar());
  render();
}
