import * as api from "../core/api.js";
import * as session from "../core/session.js";
import { irA } from "../core/router.js";
import { $, esc, esperar } from "../core/util.js";

const ICONO_OK = '<svg viewBox="0 0 24 24"><path d="M5.5 12.5l4.2 4.2L18.5 7.8"/></svg>';
const ICONO_ERR = '<svg viewBox="0 0 24 24"><path d="M7 7l10 10M17 7L7 17"/></svg>';

// Tiempos de la animación (ms). Cada paso dura al menos "min" aunque la
// respuesta real llegue antes; si el servidor tarda más, se espera la respuesta.
const PAUSA_ENTRE_PASOS_MS = 250;
const PAUSA_FINAL_MS = 2000;

const plural = (n, uno, varios) => `${n.toLocaleString("es-CL")} ${n === 1 ? uno : varios}`;

function pasos(resumen) {
  return [
    { id: "backend", label: "Backend disponible", min: 1100,
      msg: "Despertando el servicio de análisis…",
      run: async () => { await api.health(); return "Servicio activo"; } },
    { id: "conexion", label: "Conexión con PostgreSQL", min: 1800,
      msg: "Abriendo un canal seguro hacia tu base de datos…",
      run: async () => {
        const r = await api.conectar(session.obtener());
        resumen.version = (String(r.version).match(/PostgreSQL [\d.]+/) || ["PostgreSQL"])[0];
        return resumen.version;
      } },
    { id: "tablas", label: "Lectura del catálogo de tablas", min: 1400,
      msg: "Leyendo las tablas y sus columnas…",
      run: async () => {
        const n = ((await api.listarTablas()).tablas || []).length;
        resumen.tablas = n;
        return plural(n, "tabla encontrada", "tablas encontradas");
      } },
    { id: "indices", label: "Lectura de los índices", min: 1300,
      msg: "Revisando los índices disponibles…",
      run: async () => {
        const n = ((await api.listarIndices()).indices || []).length;
        resumen.indices = n;
        return plural(n, "índice detectado", "índices detectados");
      } },
    { id: "relaciones", label: "Relaciones entre tablas", min: 1300,
      msg: "Mapeando las relaciones para el diagrama…",
      run: async () => {
        const n = ((await api.obtenerDiagrama()).relaciones || []).length;
        resumen.relaciones = n;
        return plural(n, "relación encontrada", "relaciones encontradas");
      } },
    { id: "stats", label: "Permisos de estadísticas (solo lectura)", min: 1200,
      msg: "Comprobando permisos y estadísticas en vivo…",
      run: async () => `Respuesta en ${(await api.estadisticas()).tiempo_respuesta_ms} ms` },
  ];
}

// Se incrementa al salir de la ruta o al reintentar: corta cualquier ejecución anterior.
let ejecucion = 0;
let raf = 0;
const anim = { actual: 0, objetivo: 0, activo: false, i: 0, n: 1, t0: 0, min: 1 };

export function render(app) {
  const cfg = session.obtener() || {};
  app.innerHTML = `
    <div id="carga-card" class="carga-card">
      <div id="escena" class="escena">
        <div class="nodo">
          <div class="nodo-caja"><span class="carga-logo">ML·SQL</span></div>
          <span class="nodo-etq">Optimizador</span>
        </div>
        <div class="enlace"><i class="paquete"></i><i class="paquete"></i><i class="paquete"></i></div>
        <div class="nodo">
          <div class="nodo-caja">
            <svg id="db-svg" class="db-svg" viewBox="0 0 64 72" data-nivel="0">
              <path class="db-cuerpo" d="M8 14v44c0 6 11.6 10 24 10s24-4 24-10V14"/>
              <path class="db-banda b3" d="M8 44c0 6 11.6 10 24 10s24-4 24-10"/>
              <path class="db-banda b2" d="M8 29c0 6 11.6 10 24 10s24-4 24-10"/>
              <ellipse class="db-tapa" cx="32" cy="14" rx="24" ry="9"/>
            </svg>
          </div>
          <span class="nodo-etq" title="${esc(cfg.dbname || "")}">${esc(cfg.dbname || "Base de datos")}</span>
        </div>
      </div>
      <h2 id="carga-titulo" class="carga-titulo">Conectando con tu base de datos</h2>
      <p id="carga-sub" class="carga-sub">Iniciando…</p>
      <div class="progreso">
        <div class="progreso-pista"><div id="barra" class="progreso-barra"></div></div>
        <span id="pct" class="progreso-pct">0%</span>
      </div>
      <ul id="carga-lista" class="carga-lista"></ul>
      <div id="carga-final" class="carga-final"></div>
      <div id="carga-error" class="carga-error"></div>
      <div id="carga-acciones" class="carga-acciones"></div>
    </div>`;
  ejecutar();
}

export function cleanup() {
  ejecucion++;
  detenerBucle();
}

function pintarLista(items) {
  $("carga-lista").innerHTML = items.map((p, i) =>
    `<li id="paso-${p.id}" class="paso" style="--i:${i}">
       <span class="paso-ic"></span>
       <span class="paso-cuerpo"><span class="paso-txt">${esc(p.label)}</span><span class="paso-det"></span></span>
     </li>`).join("");
  $("carga-error").innerHTML = "";
  $("carga-acciones").innerHTML = "";
  $("carga-final").className = "carga-final";
  $("carga-final").innerHTML = "";
}

function estado(id, tipo, detalle = "") {
  const li = $("paso-" + id); if (!li) return;
  li.className = "paso paso-" + tipo;
  li.querySelector(".paso-ic").innerHTML = tipo === "ok" ? ICONO_OK : tipo === "err" ? ICONO_ERR : "";
  li.querySelector(".paso-det").textContent = detalle;
}

function marcarEscena(clase) {
  const e = $("escena"); if (!e) return;
  e.classList.remove("ok", "err");
  if (clase) e.classList.add(clase);
}

function bucle() {
  if (anim.activo) {
    const t = Math.min(0.96, (performance.now() - anim.t0) / anim.min);
    anim.objetivo = (anim.i + t) / anim.n;
  }
  anim.actual += (anim.objetivo - anim.actual) * 0.1;
  if (Math.abs(anim.objetivo - anim.actual) < 0.0004) anim.actual = anim.objetivo;
  const pct = Math.round(anim.actual * 100);
  const barra = $("barra"), txt = $("pct");
  if (barra) barra.style.width = (anim.actual * 100).toFixed(2) + "%";
  if (txt) txt.textContent = pct + "%";
  raf = requestAnimationFrame(bucle);
}

function iniciarBucle(n) {
  detenerBucle();
  Object.assign(anim, { actual: 0, objetivo: 0, activo: false, i: 0, n });
  raf = requestAnimationFrame(bucle);
}

function detenerBucle() {
  if (raf) cancelAnimationFrame(raf);
  raf = 0;
  anim.activo = false;
}

async function ejecutar() {
  const token = ++ejecucion;
  const vivo = () => token === ejecucion;
  const resumen = {};
  const items = pasos(resumen);
  const dbname = (session.obtener() || {}).dbname || "";

  pintarLista(items);
  marcarEscena(null);
  $("db-svg").dataset.nivel = "0";
  $("carga-card").classList.remove("saliendo", "falla");
  $("carga-titulo").textContent = "Conectando con tu base de datos";
  iniciarBucle(items.length);

  for (let i = 0; i < items.length; i++) {
    const paso = items[i];
    estado(paso.id, "load");
    $("carga-sub").textContent = paso.msg;
    Object.assign(anim, { i, t0: performance.now(), min: paso.min, activo: true });
    try {
      const [detalle] = await Promise.all([paso.run(), esperar(paso.min)]);
      if (!vivo()) return;
      anim.activo = false;
      anim.objetivo = (i + 1) / items.length;
      estado(paso.id, "ok", detalle);
      $("db-svg").dataset.nivel = String(Math.ceil((3 * (i + 1)) / items.length));
      await esperar(PAUSA_ENTRE_PASOS_MS);
      if (!vivo()) return;
    } catch (err) {
      if (!vivo()) return;
      detenerBucle();
      estado(paso.id, "err");
      return fallo(paso, err);
    }
  }
  await confirmar(resumen, dbname, vivo);
}

async function confirmar(resumen, dbname, vivo) {
  anim.objetivo = 1;
  await esperar(500);
  if (!vivo()) return;
  marcarEscena("ok");
  $("carga-titulo").textContent = "¡Conexión establecida!";
  $("carga-sub").textContent = `Tu base de datos «${dbname}» está lista para analizar.`;
  const chips = [resumen.version, plural(resumen.tablas, "tabla", "tablas"),
    plural(resumen.indices, "índice", "índices"), plural(resumen.relaciones, "relación", "relaciones"),
    "Solo lectura"];
  $("carga-final").innerHTML =
    `<svg class="final-check" viewBox="0 0 52 52"><circle cx="26" cy="26" r="23"/><path d="M15 27l8 8 15-17"/></svg>
     <div class="final-chips">${chips.map((c) => `<span>${esc(c)}</span>`).join("")}</div>`;
  $("carga-final").classList.add("mostrar");

  await esperar(PAUSA_FINAL_MS);
  if (!vivo()) return;
  $("carga-sub").textContent = "Abriendo el panel…";
  $("carga-card").classList.add("saliendo");
  await esperar(450);
  if (!vivo()) return;
  detenerBucle();
  session.setDemo(false);
  irA("/tablas");
}

function fallo(paso, err) {
  marcarEscena("err");
  $("carga-card").classList.add("falla");
  $("carga-titulo").textContent = "No se pudo conectar";
  $("carga-sub").textContent = "Algo falló al validar tu base de datos.";
  const pistas = {
    backend:    "¿Está corriendo el backend? Ejecuta <code>python iniciar.py</code>.",
    conexion:   "Revisa IP/host, puerto, base, usuario y contraseña.",
    tablas:     "El usuario conecta pero no puede leer las tablas. Dale <code>GRANT SELECT</code> (ver sql/usuario_solo_lectura.sql).",
    indices:    "No se pudo leer el catálogo de índices. Revisa que el usuario tenga <code>GRANT SELECT</code> sobre las tablas.",
    relaciones: "No se pudieron leer las relaciones (claves foráneas) entre las tablas.",
    stats:      "Falta permiso de estadísticas: <code>GRANT pg_read_all_stats TO tu_usuario;</code> (opcional).",
  };
  $("carga-error").innerHTML =
    `<div class="err-title">Falló: ${esc(paso.label)}</div>
     <div class="err-detail">${esc(err.message)}</div>
     <div class="err-hint">${pistas[paso.id] || ""}</div>`;
  $("carga-acciones").innerHTML =
    `<button id="btn-reintentar">Reintentar</button>
     <button id="btn-volver" class="ghost">Volver</button>
     <button id="btn-demo" class="ghost">Continuar en modo demo</button>`;
  $("btn-reintentar").onclick = () => ejecutar();
  $("btn-volver").onclick = () => irA("/conexion");
  $("btn-demo").onclick = () => { session.setDemo(true); irA("/tablas"); };
}
