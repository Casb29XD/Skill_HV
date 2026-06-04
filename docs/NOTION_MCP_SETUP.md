# Configurar MCP (Notion) para ejecutar el skill

Este documento detalla cómo preparar el entorno para que `src/mcp_notion.py` pueda invocar el servidor MCP de Notion vía `npx @notionhq/notion-mcp-server` y publicar bloques en una página.

Requisitos
- Node.js (v16+ recomendado) y `npx` en PATH.
- Python 3.10+ (para el skill en este repo).
- Un token de integración de Notion (Internal Integration token).

Pasos para obtener credenciales en Notion
1. Entra en Notion y crea una integración interna: https://www.notion.so/my-integrations
2. Crea una nueva integración y copia el "Internal Integration Token".
3. Abre la página de Notion donde quieres publicar el reporte. Haz clic en "Share" y comparte la página con la integración que creaste (la verás por nombre).
4. Copia el ID de la página: abre la página en el navegador y copia la parte final de la URL (o usa la opción "Copy Link" y extrae el ID). El ID puede necesitar formateo con guiones — el cliente `MCPNotionClient` hace esto automáticamente si el ID viene sin guiones.

Variables de entorno recomendadas (.env)

```
NOTION_API_KEY=ntn_xxx...   # token de integración
NOTION_PAGE_ID=375237bd-e5eb-801e-a0a5-f74cfed22a9c
NOTION_VERSION=2022-06-28
NOTION_DRY_RUN=false
NOTION_VERBOSE=true
GEMINI_API_KEY=tu_clave_gemini_aqui
```

Instalación de Node / npx (Windows)
1. Descarga e instala Node.js LTS desde https://nodejs.org/
2. Verifica `node -v` y `npx -v` en la terminal.

Ejecutar el servidor MCP manualmente (opcional)
Si prefieres levantar el servidor MCP manualmente para depurar, puedes ejecutar:

```bash
npx -y @notionhq/notion-mcp-server
```

Nota: el código `MCPNotionClient` ya invoca `npx` automáticamente cuando se conecta (usa `StdioServerParameters` con `npx`). Sólo necesitas `npx` disponible en PATH.

Ejecución del skill con MCP
1. Configura `.env` con las variables anteriores.
2. Desde la raíz del repo, instala dependencias Python:

```bash
pip install -r requirements.txt
```

3. Ejecuta el skill (ejemplo):

```bash
python main.py --candidates-dir data/candidates --job-a data/jobs/job-a.pdf --job-b data/jobs/job-b.pdf
```

Depuración y logs
- Activa `NOTION_VERBOSE=true` para más mensajes de debug (si el servidor los soporta).
- Si el proceso falla en la fase de `npx`, asegúrate que Node y npx funcionan y que tu token no está bloqueado.
- Errores típicos:
  - `EACCES` o `permission denied`: problemas de permisos al ejecutar `npx`.
  - `401`/`403` de Notion API: token inválido o la integración no tiene acceso a la página.

Ejecución en entornos gestionados (Cowork / Codex / OpenCode)
- Asegúrate de que el runner permita ejecutar `npx` y procesos hijos. Si el entorno bloquea `npx`, levanta el servidor MCP en una máquina externa (o contenedor) y actualiza `src/mcp_notion.py` para conectarse por HTTP en lugar de stdio.

Conexión alternativa (si no puede usarse stdio)
- Si tu entorno NO permite ejecutar `npx` desde el proceso Python, puedes ejecutar `notion-mcp-server` de forma persistente en otra máquina/VM y exponer una interfaz compatible; luego deberías adaptar el cliente para usar transporte HTTP o socket según la implementación del servidor MCP. Esto requiere cambios en `src/mcp_notion.py`.

Checklist rápido
- [ ] Node.js y `npx` en PATH
- [ ] Token de integración creado y copiado en `NOTION_API_KEY`
- [ ] Página de Notion compartida con la integración
- [ ] `NOTION_PAGE_ID` colocado en `.env` o pasado por CLI
