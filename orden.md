Para asegurar que el proyecto no se desvíe y que construyas exactamente lo que los evaluadores técnicos buscan (un sistema robusto, reutilizable y desacoplado), vamos a establecer un **Plan de Hitos** estricto y a definir los **Diagramas de Flujo y Módulos (DM)** que gobernarán el código.

---

## 🗺️ El Plan de Ejecución (En 4 Hitos)

Seguiremos una estrategia de desarrollo incremental. No pasaremos al siguiente hito hasta que el anterior esté 100% probado.

```
[ Hito 1: Ingesta ] ──► [ Hito 2: Cerebro ] ──► [ Hito 3: Orquestación ] ──► [ Hito 4: MCP Notion ]
  (Extracción PDF)       (Prompt + Pydantic)       (Bucle + Priorización)     (Publicación Final)

```

1. **Hito 1: Ingesta de Datos Estables (PDFs)**
* *Objetivo:* Leer de forma genérica cualquier PDF en las carpetas de entrada y devolver texto limpio.


2. **Hito 2: El Cerebro Agéntico (Clasificación Estricta)**
* *Objetivo:* Probar con **un solo candidato** que el LLM procese el perfil contra los dos puestos y devuelva de forma consistente el JSON estructurado por Pydantic.


3. **Hito 3: Orquestación Secuencial y Controlada**
* *Objetivo:* Procesar los 30 candidatos uno por uno, manejando excepciones (si un PDF falla, el proceso continúa con el siguiente) y ordenando los resultados finales por puntuación.


4. **Hito 4: Integración MCP y Publicación**
* *Objetivo:* Conectar el cliente MCP al servidor de Notion para volcar los resultados ordenados.



---

## 📐 Diagrama de Módulos (DM) y Responsabilidades

Para asegurar que sea **genérico y reutilizable**, el código debe estar desacoplado. Ningún módulo debe saber cómo hace su trabajo el otro; solo se comunican mediante datos estructurados.

```
                     ┌───────────────────────┐
                     │        main.py        │  ◄── Punto de entrada único
                     └───────────┬───────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  pdf_utils.py   │     │    agent.py     │     │ mcp_notion.py   │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ Extrae texto de │     │ Evalúa texto de │     │ Toma el reporte │
│ PDFs en rutas   │     │ candidato vs    │     │ final y lo      │
│ dinámicas.      │     │ vacantes usando │     │ escribe en      │
│                 │     │ Pydantic.       │     │ Notion vía MCP. │
└─────────────────┘     └─────────────────┘     └─────────────────┘

```

### Contratos de Datos (Qué entra y qué sale de cada módulo)

* **`pdf_utils.py`**
* *Entrada:* Ruta de una carpeta o archivo PDF.
* *Salida:* Un string con el texto limpio (o un diccionario `{"nombre_archivo": "texto"}`).


* **`agent.py`**
* *Entrada:* El texto del perfil de un candidato + el texto de la Vacante A + el texto de la Vacante B.
* *Salida:* Una instancia del objeto Pydantic `EvaluacionCandidato` (con campos fijos: `encaja_en`, `puntuacion_prioridad`, `justificacion`).


* **`mcp_notion.py`**
* *Entrada:* Lista ordenada de evaluaciones (List of `EvaluacionCandidato`).
* *Salida:* Confirmación de éxito de escritura en Notion.



---

## 🔄 Diagrama de Flujo del Proceso Completo

Este es el camino exacto que seguirá el algoritmo de `main.py` al ejecutarse:

```text
[Inicio: Ejecución de main.py]
   │
   ▼
1. Cargar Variables de Entorno (.env)
   │
   ▼
2. Leer y almacenar PDFs de Vacante A y Vacante B (pdf_utils)
   │
   ▼
3. Listar todos los PDFs en la carpeta /candidatos
   │
   ▼
4. [Bucle para cada candidato (1 al 30)]
   ├── Extraer texto del PDF actual
   ├── Enviar al Agente (texto_candidato + textos_vacantes)
   ├── Capturar respuesta estructurada en JSON (Pydantic)
   └── Capturar y loggear errores (si el PDF está corrupto o el LLM falla, no rompe el flujo)
   │
   ▼
5. Coleccionar todas las evaluaciones exitosas
   │
   ▼
6. Ordenar la lista descendentemente por 'puntuacion_prioridad'
   │
   ▼
7. Inicializar Cliente MCP y conectar con Servidor Notion
   │
   ▼
8. Enviar el reporte ordenado a la página de Notion
   │
   ▼
[Fin: Proceso Completado con Éxito]

```

---

## 🚨 Reglas de Oro para mantener el proyecto en el camino correcto

* **No uses Expresiones Regulares complejas para "parsear" los PDFs:** Deja que el extractor de PDF saque el texto plano de forma limpia y transparente, y que el LLM se encargue de interpretar la información semántica. Esto evita que el código falle ante variaciones de diseño en las hojas de vida.
* **Aislamiento de Prompts:** Los prompts del Agente deben vivir exclusivamente dentro de `agent.py`. `main.py` no debe saber qué modelo estás usando ni cómo le hablas a la IA.
* **Loggear el progreso:** Como procesar 30 PDFs con un LLM tomará un par de minutos, pon `print()` informativos (ej. `[INFO] Procesando candidato 12/30: Juan_Perez.pdf...`). Esto demuestra madurez de software en una prueba técnica.

Si estás de acuerdo con esta arquitectura y orden, empecemos a escribir el código del **Hito 1: `pdf_utils.py**` y a dejar lista la extracción limpia de los textos.