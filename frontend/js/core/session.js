let credenciales = null;
let modoDemo = false;

export function guardar(cfg) { credenciales = cfg; }
export function obtener() { return credenciales; }
export function limpiar() { credenciales = null; modoDemo = false; }
export function estaConectado() { return credenciales !== null; }
export function setDemo(v) { modoDemo = v; }
export function esDemo() { return modoDemo; }
