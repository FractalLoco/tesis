export function render(app, ctx) {
  app.innerHTML = `
    <div class="pagina-404">
      <div class="cod">404</div>
      <div class="msg">Página no encontrada</div>
      <div class="sub">${(ctx && ctx.titulo) || "Esta sección"} todavía no está disponible.</div>
    </div>`;
}
