Skill para con automata o con IA para la identificacion de los mejores cadidatos para cada propuesta

## Agent: Skill_HV

Este repositorio contiene un "skill" para evaluar candidatos frente a descripciones de puestos y publicar un reporte priorizado en Notion usando MCP.

### Propósito
- Evaluar todos los perfiles de candidatos presentes en `data/candidates/` frente a todas las descripciones de puesto en `data/jobs/` (sin límite por defecto).
- Para cada candidato determinar para qué puesto(es) encaja mejor, y asignar una `puntuacion_prioridad` por puesto.
- Generar un reporte priorizado "a quién contactar" (ordenado por `puntuacion_prioridad`) y separar candidatos por puesto.
- Publicar el reporte en Notion conectándose vía MCP (Notion MCP Server por stdio).

### Requisitos previos
- Python 3.10+
- Node.js (v16+ / LTS) y `npx` disponible en PATH
- Tener las dependencias de Python instaladas. Desde la raíz del proyecto:

```bash
pip install -r requirements.txt
```

- El archivo `.env` debe estar en la raíz del proyecto para que `load_dotenv()` lo detecte correctamente.
- Las vacantes `Jobs` y los postulantes `candidates` deben ir en su correspondiente carpeta en `data/`.

### Variables de entorno necesarias
- `NOTION_API_KEY` o `NOTION_TOKEN`: token interno de integración de Notion (MCP usa `NOTION_API_KEY`).
- `NOTION_PAGE_ID`: ID de la página de Notion donde publicar el reporte (se puede pasar por CLI también).
- `GEMINI_API_KEY` (opcional): clave para usar el LLM de Gemini; si no existe, el skill usa la heurística local.

### Ejecutores disponibles
- `main.py`: ejecutador principal. Intenta usar Gemini para evaluar candidatos cuando `GEMINI_API_KEY` está disponible y `--no-llm` no fue indicado. Si falta la clave o Gemini falla, cae a la heurística local. Publica en Notion si `NOTION_PAGE_ID` y `NOTION_API_KEY` están configurados.
- `run_no_gemini.py`: ejecutador de prueba sin Gemini; fuerza `use_llm=False` para validar extracción, agrupamiento y publicación sin depender de APIs externas.

### Ejecución (básica)
Desde la raíz del repositorio:

```bash
python main.py --candidates-dir data/candidates --job-a data/jobs/job-a-integration-developer-oracle-ebs.pdf \
	--job-b data/jobs/job-b-business-systems-analyst-oracle-ebs.pdf
```

Forzar modo heurístico (sin LLM):

```bash
python main.py --no-llm
```

Ejecutar el flujo sin Gemini:

```bash
python run_no_gemini.py
```

Pasar `NOTION_PAGE_ID` por CLI (sobrescribe `.env`):

```bash
python main.py --notion-page-id 375237bde5eb801ea0a5f74cfed22a9c
```

### Salida
- Si `NOTION_PAGE_ID` y `NOTION_API_KEY` están configurados, el skill intentará publicar un reporte en la página de Notion vía MCP.
- Si falta `NOTION_PAGE_ID`, mostrará un resumen local del reporte en consola.

### Buenas prácticas
- Preparar una carpeta `data/candidates` con los PDFs que desees procesar (el skill procesará todos por defecto).
- Preparar una o más descripciones de puesto en `data/jobs/` (el skill identificará todos los PDFs/archivos soportados en esa carpeta) o pasarlos por CLI.
- Testear primero con `NOTION_DRY_RUN=true` (si tu env/servidor MCP lo soporta) o usando `test_publish.py`.

### Errores comunes y diagnóstico
- `npx` no encontrado: instala Node.js y asegúrate que `npx` esté en PATH.
- Error de credenciales Notion: verificar que la integración está compartida con la página y que el token es válido.
- Fallos LLM: si `GEMINI_API_KEY` no es válida, el skill cambia a modo heurístico.

### Notas de seguridad
- No subas tokens a repositorios públicos. Usa variables de entorno o secret managers.

### Soporte
- Guía para configurar el MCP de Notion: [docs/NOTION_MCP_SETUP.md](docs/NOTION_MCP_SETUP.md#L1-L1)

---
_El archivo `agent.md` contiene la metadata del agente (frontmatter YAML). Usa ese metadata para integrar o ejecutar el skill desde herramientas de orquestación._

### Scripts de ejecución
Se incluyen dos scripts útiles para ejecutar el agente desde entornos Unix y Windows:

- `run_agent.sh`: instala dependencias y ejecuta `main.py`. Uso:

```bash
./run_agent.sh        # pasa cualquier argumento extra a main.py
```

- `run_agent.bat`: equivalente para Windows. Puede recibir opcionalmente un `NOTION_PAGE_ID` como primer argumento:

```bat
run_agent.bat [NOTION_PAGE_ID]
```

Estos scripts son auxiliares para simplificar pruebas locales.