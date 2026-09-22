export const METODOS = {
  btree: { nombre: "B-tree", que: "El tipo más común: sirve para igualdades, rangos (<, >, BETWEEN), ordenamientos y uniones (JOIN)." },
  hash:  { nombre: "Hash",   que: "Solo sirve para comparaciones de igualdad (=). Es compacto, pero no ayuda con rangos ni orden." },
  gin:   { nombre: "GIN",    que: "Indexa el contenido de valores compuestos (JSONB, arrays, texto completo) para buscar dentro de ellos." },
  gist:  { nombre: "GiST",   que: "Índice general para datos geométricos, rangos y búsquedas por cercanía o solapamiento." },
  spgist: { nombre: "SP-GiST", que: "Para datos que se dividen en particiones no balanceadas (rangos de IP, textos con prefijos, puntos)." },
  brin:  { nombre: "BRIN",   que: "Muy liviano: resume rangos de bloques. Ideal para columnas que crecen en orden (fechas, IDs) en tablas enormes." },
};

export const sinUso = (i) => !i.es_primary && !i.es_unique && Number(i.usos) === 0;
export const nMetodo = (m) => (METODOS[m] || { nombre: m }).nombre;

export function explicar(i) {
  const cols = i.columnas.join(", ");
  const tabla = `«${i.tabla}»`;
  const partes = [];
  if (i.es_primary) partes.push(`Es la clave primaria de ${tabla}: identifica cada fila de forma única y permite encontrarla al instante por ${cols}.`);
  else if (i.es_unique) partes.push(`Garantiza que ${cols} no se repita en ${tabla} y además acelera las búsquedas por ese dato.`);
  else if (i.metodo === "btree") partes.push(`Acelera las búsquedas, ordenamientos y uniones (JOIN) que usan ${cols} en ${tabla}.`);
  else partes.push(`${(METODOS[i.metodo] || {}).que || "Índice especializado."} Aquí indexa ${cols} de ${tabla}.`);
  if (i.parcial) partes.push(`Es parcial: solo incluye las filas que cumplen ${i.predicado}, así que es más pequeño y rápido cuando la consulta usa esa misma condición.`);
  if (i.expresion) partes.push("Indexa el resultado de una expresión, no la columna directa: el motor solo lo usa si la consulta escribe la misma expresión.");
  if (i.incluye.length) partes.push(`Guarda además ${i.incluye.join(", ")} para poder responder sin leer la tabla (index-only scan).`);
  if (!i.valido) partes.push("Está marcado como inválido (su construcción no terminó): PostgreSQL no lo usa.");
  if (sinUso(i)) partes.push("Todavía no se ha usado desde que se reiniciaron las estadísticas: si tampoco se necesita, podría ser prescindible.");
  return partes.join(" ");
}
