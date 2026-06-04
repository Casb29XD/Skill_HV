# Skill Agéntico — Evaluación de Candidatos y Publicación en Notion

- Propósito
- Evaluar todos los perfiles de candidatos presentes en `data/candidates/` frente a todas las descripciones de puesto en `data/jobs/` (sin límite por defecto).
- Para cada candidato determinar para qué puesto(es) encaja mejor, y asignar una `puntuacion_prioridad` por puesto.
- Generar un reporte priorizado "a quién contactar" (ordenado por `puntuacion_prioridad`) y separar candidatos por puesto.
- Publicar el reporte en Notion conectándose vía MCP (Notion MCP Server por stdio).


Requisitos previos
- Python 3.10+
- Node.js (v16+ / LTS) y `npx` disponible en PATH
- Tener las dependencias de Python instaladas:
- El archivo `.env` debe estar en la raíz del proyecto para que `load_dotenv()` lo detecte correctamente.
-Las vacantes `Jobs` y los postulantes `candidates` deben ir en su correspondiente carpeta en data

```bash
pip install -r requirements.txt
```

Variables de entorno necesarias
- `NOTION_API_KEY` o `NOTION_TOKEN`: token interno de integración de Notion (MCP usa `NOTION_API_KEY`).
- `NOTION_PAGE_ID`: ID de la página de Notion donde publicar el reporte (se puede pasar por CLI también).
- `GEMINI_API_KEY` (opcional): clave para usar el LLM de Gemini; si no existe, el skill usa la heurística local.

Ejecutores disponibles
- `main.py`: es el ejecutador principal. Intenta usar Gemini para evaluar candidatos cuando `GEMINI_API_KEY` está disponible y `--no-llm` no fue indicado. Si falta la clave, o Gemini falla por cuota o error, cae a la heurística local para no detener el proceso. También publica el reporte en Notion si `NOTION_PAGE_ID` y `NOTION_API_KEY` están configurados.
- `run_no_gemini.py`: es el ejecutador de prueba sin Gemini. Fuerza `use_llm=False`, así que todo el flujo se resuelve con la heurística local. Sirve para validar extracción, agrupamiento y publicación sin depender de cuotas ni de la API de Gemini.

Ejecución (básica)

Desde la raíz del repositorio:

```bash
python main.py --candidates-dir data/candidates --job-a data/jobs/job-a-integration-developer-oracle-ebs.pdf \
  --job-b data/jobs/job-b-business-systems-analyst-oracle-ebs.pdf
```

Si quieres forzar modo heurístico (sin LLM):

```bash
python main.py --no-llm
```

Si quieres ejecutar directamente el flujo sin Gemini:

```bash
python run_no_gemini.py
```

Pasar `NOTION_PAGE_ID` desde la línea de comandos (sobrescribe .env):

```bash
python main.py --notion-page-id 375237bde5eb801ea0a5f74cfed22a9c
```

Salida
- Si `NOTION_PAGE_ID` y `NOTION_API_KEY` están configurados, el skill intentará publicar un reporte en la página de Notion vía MCP.
- Si falta `NOTION_PAGE_ID`, mostrará un resumen local del reporte en consola.

- Buenas prácticas
- Preparar una carpeta `data/candidates` con los PDFs que desees procesar (el skill procesará todos por defecto).
- Preparar una o más descripciones de puesto en `data/jobs/` (el skill identificará todos los PDFs/archivos soportados en esa carpeta) o pasarlos por CLI.
- Testear primero con `NOTION_DRY_RUN=true` (si tu env/servidor MCP lo soporta) o usando `test_publish.py`.

Errores comunes y diagnóstico
- `npx` no encontrado: instala Node.js y asegúrate que `npx` esté en PATH.
- Error de credenciales Notion: verificar que la integración está compartida con la página y que el token es válido.
- Fallos LLM: si `GEMINI_API_KEY` no es válida, el skill cambia a modo heurístico.

Notas de seguridad
- No subas tokens a repositorios públicos. Usa variables de entorno o secret managers.

Soporte
- Guía para configurar el MCP de Notion: [docs/NOTION_MCP_SETUP.md](docs/NOTION_MCP_SETUP.md#L1-L1)
