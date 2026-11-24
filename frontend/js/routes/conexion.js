import * as api from "../core/api.js";
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
      <form id="form-conexion" autocomplete="off">
        <div class="row">
          <div class="field grow"><label for="host">IP / Host</label><input id="host" type="text" value="localhost" maxlength="255" spellcheck="false" required /></div>
          <div class="field port"><label for="port">Puerto</label><input id="port" type="text" value="5432" inputmode="numeric" maxlength="5" required /></div>
        </div>
        <div class="field"><label for="dbname">Base de datos</label><input id="dbname" type="text" placeholder="mi_base" maxlength="63" spellcheck="false" required /></div>
        <div class="field"><label for="user">Usuario</label><input id="user" type="text" placeholder="analizador_ro" maxlength="63" spellcheck="false" required /></div>
        <div class="field"><label for="password">Contraseña de base de datos</label><input id="password" type="password" placeholder="••••••••" maxlength="1024" /></div>
        <button type="submit">Ingresar</button>
        <p class="hint">Son las credenciales de tu base de datos. Solo lectura; no se modifican datos.</p>
      </form>
    </div>`;

  $("form-conexion").addEventListener("submit", (e) => {
    e.preventDefault();
    const host = $("host");
    // El servidor también lo valida; aquí solo se avisa antes de enviar.
    if (/[\s,/]/.test(host.value.trim())) {
      host.setCustomValidity("Un solo servidor (IP o nombre), sin espacios, comas ni rutas.");
      host.reportValidity();
      return;
    }
    session.guardar({
      host: host.value.trim(),
      port: $("port").value.trim(),
      dbname: $("dbname").value.trim(),
      user: $("user").value.trim(),
      password: $("password").value,
    });
    $("password").value = "";
    session.setDemo(false);
    irA("/validando");
  });

  // Lo que la persona escribe no se pisa con los datos precargados.
  $("form-conexion").addEventListener("input", (e) => {
    e.target.dataset.editado = "1";
    e.target.setCustomValidity("");
  });
  precargar();
}

// Con PRECARGAR_CONEXION activo llena el formulario con la base del .env. La
// contraseña nunca llega al navegador: el servidor la usa si el campo queda vacío.
async function precargar() {
  let datos;
  try { datos = await api.conexionPorDefecto(); } catch { return; }
  if (!datos.precargar || !$("form-conexion")) return;
  for (const campo of ["host", "port", "dbname", "user"]) {
    if (datos[campo] && !$(campo).dataset.editado) $(campo).value = datos[campo];
  }
  if (datos.clave_guardada) {
    $("password").placeholder = "Guardada en el servidor (puedes dejarla en blanco)";
  }
}
