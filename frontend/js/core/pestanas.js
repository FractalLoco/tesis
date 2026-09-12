export function pestanasDatos(activa) {
  const p = (ruta, texto) =>
    `<a class="pestana${activa === ruta ? " activa" : ""}" href="#${ruta}">${texto}</a>`;
  return `<div class="pestanas">${p("/tablas", "Tablas")}${p("/indices", "Índices")}</div>`;
}
