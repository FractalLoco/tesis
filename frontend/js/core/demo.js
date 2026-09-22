export const tablasDemo = () => [
  { esquema: "public", tabla: "clientes", filas_est: 1200, n_indices: 2 },
  { esquema: "public", tabla: "pedidos", filas_est: 8400, n_indices: 2 },
  { esquema: "public", tabla: "detalle", filas_est: 25300, n_indices: 1 },
  { esquema: "public", tabla: "productos", filas_est: 640, n_indices: 1 },
];

export const datosTablaDemo = (tabla) => {
  const demo = {
    clientes: { columnas: [{ nombre: "id", tipo: "integer" }, { nombre: "nombre", tipo: "text" }, { nombre: "ciudad", tipo: "text" }, { nombre: "email", tipo: "text" }],
      filas: [["1", "Ana Pérez", "Concepción", "ana@mail.cl"], ["2", "Luis Soto", "Chillán", "luis@mail.cl"], ["3", "María Díaz", "Los Ángeles", "maria@mail.cl"], ["4", "Jorge Rivas", "Concepción", "jorge@mail.cl"]] },
    pedidos: { columnas: [{ nombre: "id", tipo: "integer" }, { nombre: "cliente_id", tipo: "integer" }, { nombre: "fecha", tipo: "date" }, { nombre: "total", tipo: "numeric" }],
      filas: [["101", "1", "2026-08-02", "45990"], ["102", "2", "2026-08-03", "12990"], ["103", "1", "2026-08-05", "78990"], ["104", "3", "2026-08-06", "9990"]] },
    detalle: { columnas: [{ nombre: "id", tipo: "integer" }, { nombre: "pedido_id", tipo: "integer" }, { nombre: "producto", tipo: "text" }, { nombre: "cantidad", tipo: "integer" }],
      filas: [["1", "101", "Teclado", "2"], ["2", "101", "Mouse", "1"], ["3", "102", "Monitor", "1"], ["4", "103", "Notebook", "1"]] },
    productos: { columnas: [{ nombre: "id", tipo: "integer" }, { nombre: "nombre", tipo: "text" }, { nombre: "precio", tipo: "numeric" }],
      filas: [["1", "Teclado", "15990"], ["2", "Mouse", "8990"], ["3", "Monitor", "89990"], ["4", "Notebook", "499990"]] },
  };
  const d = demo[tabla] || { columnas: [{ nombre: "columna", tipo: "text" }], filas: [["(datos de ejemplo)"]] };
  return { ...d, n_filas: d.filas.length };
};

let base = 30000;
export const estadisticasDemo = () => {
  base += Math.floor(Math.random() * 40); // simula actividad creciente
  return {
    tiempo_respuesta_ms: +(1 + Math.random() * 4).toFixed(2),
    conexiones: 3 + Math.floor(Math.random() * 3),
    cache_hit_ratio: +(96 + Math.random() * 3).toFixed(1),
    blks_read: 1800 + Math.floor(Math.random() * 50),
    blks_hit: base,
    tup_returned: base * 4,
    tup_fetched: base * 2,
    commits: 5200 + Math.floor(Math.random() * 20),
  };
};

const col = (nombre, tipo, pk = false, fk = false) => ({ nombre, tipo, pk, fk, not_null: pk });

export const diagramaDemo = () => ({
  tablas: [
    { esquema: "public", tabla: "clientes", filas_est: 1200,
      columnas: [col("id", "integer", true), col("nombre", "text"), col("ciudad", "text"), col("email", "text")] },
    { esquema: "public", tabla: "pedidos", filas_est: 8400,
      columnas: [col("id", "integer", true), col("cliente_id", "integer", false, true), col("fecha", "date"), col("total", "numeric")] },
    { esquema: "public", tabla: "detalle", filas_est: 25300,
      columnas: [col("id", "integer", true), col("pedido_id", "integer", false, true), col("producto_id", "integer", false, true), col("cantidad", "integer")] },
    { esquema: "public", tabla: "productos", filas_est: 640,
      columnas: [col("id", "integer", true), col("nombre", "text"), col("precio", "numeric")] },
  ],
  relaciones: [
    { nombre: "pedidos_cliente_fk", desde: { esquema: "public", tabla: "pedidos", columnas: ["cliente_id"] }, hacia: { esquema: "public", tabla: "clientes", columnas: ["id"] } },
    { nombre: "detalle_pedido_fk", desde: { esquema: "public", tabla: "detalle", columnas: ["pedido_id"] }, hacia: { esquema: "public", tabla: "pedidos", columnas: ["id"] } },
    { nombre: "detalle_producto_fk", desde: { esquema: "public", tabla: "detalle", columnas: ["producto_id"] }, hacia: { esquema: "public", tabla: "productos", columnas: ["id"] } },
  ],
});

const ix = (tabla, indice, columnas, extra = {}) => ({
  esquema: "public", tabla, indice, metodo: "btree", es_primary: false, es_unique: false, valido: true,
  parcial: false, expresion: false, predicado: null, columnas, incluye: [], cols_tabla: columnas, bytes: 16384, usos: 0, lecturas: 0,
  definicion: `CREATE INDEX ${indice} ON public.${tabla} USING btree (${columnas.join(", ")})`, ...extra,
});

export const indicesDemo = () => [
  ix("clientes", "clientes_pkey", ["id"], { es_primary: true, es_unique: true, bytes: 40960, usos: 5200 }),
  ix("clientes", "idx_clientes_ciudad", ["ciudad"], { bytes: 32768, usos: 340 }),
  ix("detalle", "detalle_pkey", ["id"], { es_primary: true, es_unique: true, bytes: 589824, usos: 900 }),
  ix("pedidos", "pedidos_pkey", ["id"], { es_primary: true, es_unique: true, bytes: 180224, usos: 7100 }),
  ix("pedidos", "idx_pedidos_cliente", ["cliente_id"], { bytes: 122880, usos: 2100 }),
  ix("productos", "productos_pkey", ["id"], { es_primary: true, es_unique: true, bytes: 16384, usos: 1300 }),
];

const nodo = (n) => ({ relacion: null, alias: null, indice: null, costo_inicial: 0, costo_total: 0,
  filas_estimadas: 0, ancho_fila: 0, tiempo_inicial_ms: 0, tiempo_total_ms: 0, filas_reales: 0, loops: 1,
  filtro: null, cond_join: null, filas_eliminadas_filtro: null, orden: null, hijos: [], ...n });

export const analizarDemo = (query) => ({
  consulta: query || "SELECT p.id, c.nombre, p.total FROM pedidos p JOIN clientes c ON c.id = p.cliente_id WHERE p.cliente_id = 1",
  analisis: {
    operadores: ["Hash Join", "Seq Scan", "Seq Scan"],
    n_operadores: 3,
    costo_total_estimado: 148.5,
    filas_estimadas: 42,
    tiempo_real_ms: 3.8,
    arbol: nodo({
      tipo: "Hash Join", costo_total: 148.5, filas_estimadas: 42, tiempo_total_ms: 3.8, filas_reales: 40,
      cond_join: "pedidos.cliente_id = clientes.id",
      hijos: [
        nodo({ tipo: "Seq Scan", relacion: "pedidos", alias: "pedidos", costo_total: 108, filas_estimadas: 40,
          tiempo_total_ms: 1.9, filas_reales: 40, filtro: "(cliente_id = 1)", filas_eliminadas_filtro: 5960 }),
        nodo({ tipo: "Seq Scan", relacion: "clientes", alias: "clientes", costo_total: 32.5, filas_estimadas: 1500,
          tiempo_total_ms: 0.6, filas_reales: 1500 }),
      ],
    }),
  },
  recomendaciones: {
    orden_join: "pendiente (modelo ML)",
    indices: "pendiente (HypoPG)",
    diagnostico: "pendiente (módulo de diagnóstico)",
  },
});

export const prediccionDemo = (query) => ({
  consulta: query || "SELECT * FROM pedidos WHERE cliente_id = 1",
  n_recomendaciones: 1,
  recomendaciones: [
    { tabla: "pedidos", columna: "cliente_id",
      motivos: ["Filtro sobre pedidos.cliente_id revisa ~6.000 filas sin índice (Seq Scan)."],
      sql_sugerido: "CREATE INDEX idx_pedidos_cliente_id ON pedidos (cliente_id);" },
  ],
  nota: "Sugerencias heurísticas a partir del plan estimado (EXPLAIN). La recomendación por Machine Learning llegará más adelante.",
});
