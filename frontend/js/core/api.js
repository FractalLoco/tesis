import { obtener } from "./session.js";

// Vacío: el frontend se sirve desde el mismo proceso y puerto que la API
// (ver backend/main.py), así que las rutas son relativas al origen actual.
const BASE = "";

async function post(ruta, body) {
  const r = await fetch(BASE + ruta, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(e.detail || "Error del servidor");
  }
  return r.json();
}

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

export async function health() {
  const r = await fetch(BASE + "/health");
  if (!r.ok) throw new Error("El backend respondió con error " + r.status);
  return r.json();
}
