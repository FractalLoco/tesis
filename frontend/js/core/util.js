export const $ = (id) => document.getElementById(id);

export const esc = (s) =>
  String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// Caja de error común: el mensaje para el usuario y, si existe, el detalle
// técnico plegado. Acepta un ErrorApi, cualquier Error o un texto.
export function cajaError(err) {
  const mensaje = typeof err === "string" ? err : err?.message || "Ocurrió un error.";
  const detalle = err?.detalle
    ? `<details class="err-mas"><summary>Ver detalle técnico</summary><pre>${esc(err.detalle)}</pre></details>`
    : "";
  return `<div class="err-box" role="alert"><div>${esc(mensaje)}</div>${detalle}</div>`;
}

export const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

export function formatoBytes(n) {
  const u = ["B", "kB", "MB", "GB", "TB"];
  let v = Number(n) || 0, i = 0;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return (i ? v.toLocaleString("es-CL", { maximumFractionDigits: 1 }) : v) + " " + u[i];
}

// Copia un texto al portapapeles. Sin HTTPS (servidor por IP) el navegador no
// deja usar navigator.clipboard: se copia con un textarea temporal.
export async function copiar(texto, boton) {
  try {
    await navigator.clipboard.writeText(texto);
  } catch {
    const t = document.createElement("textarea");
    t.value = texto;
    document.body.appendChild(t);
    t.select();
    document.execCommand("copy");
    t.remove();
  }
  if (boton) {
    const antes = boton.textContent;
    boton.textContent = "¡Copiado!";
    setTimeout(() => { boton.textContent = antes; }, 1500);
  }
}

// Caja con SQL y botón "Copiar". El texto se guarda en el <pre> y el botón lo lee
// de ahí, así la caja se puede actualizar sin volver a conectar el evento.
export function cajaSQL(id, sql, titulo = "") {
  return `<div class="sql-copiar">
    <div class="sql-copiar-cab"><span class="sql-copiar-titulo" id="${id}-titulo">${titulo}</span>
      <button type="button" class="copiar" data-copiar="${id}">Copiar</button></div>
    <pre class="idx-sql" id="${id}">${esc(sql)}</pre>
  </div>`;
}

export function activarCopiar(raiz) {
  raiz.querySelectorAll("[data-copiar]").forEach((b) => {
    b.onclick = () => copiar(document.getElementById(b.dataset.copiar).textContent, b);
  });
}
