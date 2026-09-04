# Guía de contribución

## Estrategia de ramificación (GitHub Flow)
- `main` siempre estable y desplegable.
- Una rama corta por funcionalidad, salida desde `main`:
  - `feat/consola-sql`, `feat/explorador`, `fix/conexion-timeout`, `docs/readme`…
- Se abre **Pull Request** hacia `main`, pasa el CI y luego se fusiona.

## Buenas prácticas de commits (Conventional Commits)
Formato: `tipo: descripción breve en imperativo`
- `feat:` nueva funcionalidad — `feat: agregar consola SQL de solo lectura`
- `fix:` corrección — `fix: manejar error de credenciales inválidas`
- `docs:` documentación — `docs: actualizar README con instrucciones`
- `refactor:` cambios internos sin cambiar comportamiento
- `style:` formato/estilos (no lógica)
- `test:` pruebas
- `chore:` tareas varias (config, dependencias)

Commits chicos y frecuentes, cada uno con un solo propósito.
