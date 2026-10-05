import { obtener } from "./session.js";


const BASE = "/api";

// Error de la API con el formato normalizado del backend (ver backend/errores.py):
// mensaje para el usuario, código estable y detalle técnico opcional.
export class ErrorApi extends Error {
  constructor(mensaje, { codigo = "error", detalle = null, status = 0 } = {}) {
    super(mensaje);
    this.codigo = codigo;
    this.detalle = detalle;
    this.status = status;
  }
}

async function pedir(ruta, opciones) {
  let r;
  try {
    r = await fetch(ruta, opciones);
  } catch {
    throw new ErrorApi("No se pudo contactar con el servidor de la aplicación. Revisa que esté en ejecución.",
      { codigo: "sin_servidor" });
  }
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new ErrorApi(e.mensaje || `El servidor respondió con un error (${r.status}).`,
      { codigo: e.codigo, detalle: e.detalle, status: r.status });
  }
  return r.json();
}

const post = (ruta, body) => pedir(BASE + ruta, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const conectar = (cfg) => post("/conectar", cfg);

export const listarTablas = () => post("/tablas", { conexion: obtener() });
export const verTabla = (esquema, tabla, limit = 50) =>
  post("/tabla", { conexion: obtener(), esquema, tabla, limit });
export const ejecutarConsulta = (sql, limit = 200) =>
  post("/consulta", { conexion: obtener(), sql, limit });
export const analizar = (query) => post("/analizar", { conexion: obtener(), query });
export const estadisticas = () => post("/estadisticas", { conexion: obtener() });
export const listarIndices = () => post("/indices", { conexion: obtener() });
export const obtenerDiagrama = () => post("/diagrama", { conexion: obtener() });
export const predecirIndices = (query) => post("/prediccion-indices", { conexion: obtener(), query });

export const health = () => pedir("/health");
