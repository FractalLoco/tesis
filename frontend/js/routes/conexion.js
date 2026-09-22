import * as session from "../core/session.js";
import { irA } from "../core/router.js";
import { $ } from "../core/util.js";

export function render(app) {
  app.innerHTML = `
    <div class="login-card">
      <div class="brand">
        <div class="logo">ML·SQL</div>
        <h1>Optimizador SQL con Machine Learning</h1>
        <p>Ingresa los datos de tu base de datos PostgreSQL para comenzar.</p>
      </div>
      <form id="form-conexion">
        <div class="row">
          <div class="field grow"><label>IP / Host</label><input id="host" type="text" value="localhost" required /></div>
          <div class="field port"><label>Puerto</label><input id="port" type="text" value="5432" required /></div>
        </div>
        <div class="field"><label>Base de datos</label><input id="dbname" type="text" placeholder="mi_base" required /></div>
        <div class="field"><label>Usuario</label><input id="user" type="text" placeholder="analizador_ro" required /></div>
        <div class="field"><label>Contraseña de base de datos</label><input id="password" type="password" placeholder="••••••••" /></div>
        <button type="submit">Ingresar</button>
        <p class="hint">Son las credenciales de tu base de datos. Solo lectura; no se modifican datos.</p>
      </form>
    </div>`;

  $("form-conexion").addEventListener("submit", (e) => {
    e.preventDefault();
    session.guardar({
      host: $("host").value.trim(),
      port: $("port").value.trim(),
      dbname: $("dbname").value.trim(),
      user: $("user").value.trim(),
      password: $("password").value,
    });
    session.setDemo(false);
    irA("/validando");   // paso a la validación paso a paso
  });
}
