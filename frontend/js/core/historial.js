// Historial de consultas analizadas, guardado en localStorage del navegador.
// Separado por base de datos (dbname) y por tipo de pantalla (optimizacion / prediccion).
// Nunca se guarda la contraseña de conexión, solo la consulta y su resultado.
const PREFIJO = "mlsql-historial";
const MAX_ENTRADAS = 60;

function clave(tipo, dbname) {
  return `${PREFIJO}:${tipo}:${dbname || "sin-base"}`;
}

function leer(tipo, dbname) {
  try {
    const raw = localStorage.getItem(clave(tipo, dbname));
    const lista = raw ? JSON.parse(raw) : [];
    return Array.isArray(lista) ? lista : [];
  } catch {
    return []; // localStorage no disponible (privado/bloqueado): se sigue viendo la app, sin historial
  }
}

function escribir(tipo, dbname, lista) {
  try { localStorage.setItem(clave(tipo, dbname), JSON.stringify(lista)); } catch { /* idem */ }
}

export function listar(tipo, dbname) {
  return leer(tipo, dbname);
}

export function agregar(tipo, dbname, entrada) {
  const lista = leer(tipo, dbname);
  lista.unshift({ id: Date.now().toString(36) + Math.random().toString(36).slice(2, 7), ts: Date.now(), ...entrada });
  if (lista.length > MAX_ENTRADAS) lista.length = MAX_ENTRADAS;
  escribir(tipo, dbname, lista);
  return lista;
}

export function eliminar(tipo, dbname, id) {
  const lista = leer(tipo, dbname).filter((e) => e.id !== id);
  escribir(tipo, dbname, lista);
  return lista;
}

export function limpiar(tipo, dbname) {
  escribir(tipo, dbname, []);
  return [];
}
