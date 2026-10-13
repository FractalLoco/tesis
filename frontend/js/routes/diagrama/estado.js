// Estado compartido del diagrama y medidas del dibujo. El estado va en un objeto
// porque los demás módulos lo modifican (un "let" exportado no se puede reasignar).

export const CAB = 38, FILA = 25, PIE = 8, MARGEN = 56, SEP_X = 150, SEP_Y = 34;
export const IX_H = 58, IX_GAP = 8, IX_TOP = 18, IX_INDENT = 22;

export const estado = {
  datos: null,
  indices: [],
  soloClaves: false,
  mostrarIx: true,
  zoom: 1,
  seleccion: null,     // clave de la tabla seleccionada
  ixSel: null,         // clave del índice seleccionado (dentro de la tabla seleccionada)
  dims: { w: 0, h: 0 },
  modelo: null,
};

export const clave = (e, t) => `${e}.${t}`;
export const claveIx = (i) => `${i.esquema}.${i.indice}`;
export const colsDe = (i) => (i.cols_tabla && i.cols_tabla.length ? i.cols_tabla : i.columnas);
export const nombreTabla = (t) => (t.esquema === "public" ? t.tabla : `${t.esquema}.${t.tabla}`);
export const num = (n) => Number(n).toLocaleString("es-CL");
export const cortar = (s, max) => (s.length > max ? s.slice(0, Math.max(1, max - 1)) + "…" : s);

const TIPOS = { "character varying": "varchar", "timestamp without time zone": "timestamp",
  "timestamp with time zone": "timestamptz", "double precision": "double", "time without time zone": "time",
  "character": "char" };

export function tipoCorto(t) {
  let s = String(t);
  for (const [largo, corto] of Object.entries(TIPOS)) if (s.startsWith(largo)) { s = corto + s.slice(largo.length); break; }
  return cortar(s, 20);
}
