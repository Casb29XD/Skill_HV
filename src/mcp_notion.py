import os
import asyncio
import logging
from typing import List, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def format_uuid(uuid_str: str) -> str:
    """Asegura que el ID de la página de Notion tenga guiones en formato UUID estándar."""
    clean = uuid_str.replace("-", "")
    if len(clean) == 32:
        return f"{clean[:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:]}"
    return uuid_str


class MCPNotionClient:
    """Cliente MCP para publicar reportes en Notion usando transporte stdio."""

    def __init__(self):
        load_dotenv()
        self.notion_key = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
        self.page_id = os.getenv("NOTION_PAGE_ID")

    async def publicar_reporte(self, id_pagina_notion: str, evaluaciones: Any):
        """Publica el reporte de evaluaciones en Notion usando el servidor MCP oficial vía stdio.

        `evaluaciones` puede ser:
        - una lista de evaluaciones (comportamiento legacy), o
        - un diccionario mapeando `job_name` -> lista de evaluaciones para ese puesto.
        """
        if not self.notion_key:
            raise ValueError("[ERROR] No se configuró NOTION_API_KEY ni NOTION_TOKEN en el archivo .env")

        if not id_pagina_notion:
            raise ValueError("[ERROR] No se especificó el ID de la página de Notion.")

        formatted_page_id = format_uuid(id_pagina_notion)
        print(f"[INFO] Conectando al servidor MCP Notion por stdio...")

        # Parámetros para levantar el servidor oficial de Notion mediante npx
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@notionhq/notion-mcp-server"],
            env={**os.environ, "NOTION_API_KEY": self.notion_key}
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                print("[INFO] Inicializando sesión MCP con Notion...")
                await session.initialize()

                # Construir los bloques a insertar en Notion
                children = []

                # Título del Reporte
                children.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "📊 REPORTE AUTOMATIZADO DE RECLUTAMIENTO"}
                            }
                        ]
                    }
                })

                # Separador
                children.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "=================================================="}
                            }
                        ]
                    }
                })

                # Insertar evaluaciones. Soportamos agrupamiento por puesto.
                if isinstance(evaluaciones, dict):
                    # Para cada puesto, crear encabezado y listar candidatos ordenados por prioridad
                    for job_name, evs in evaluaciones.items():
                        # Encabezado del puesto
                        children.append({
                            "type": "heading_2",
                            "heading_2": {"rich_text": [{"type": "text", "text": {"content": f"📌 {job_name} - Candidatos recomendados"}}]}
                        })

                        # Ordenar por prioridad desc
                        try:
                            evs_sorted = sorted(evs, key=lambda x: (getattr(x, 'puntuacion_prioridad', 0) if not isinstance(x, dict) else x.get('puntuacion_prioridad', 0)), reverse=True)
                        except Exception:
                            evs_sorted = evs

                        for idx, ev in enumerate(evs_sorted, 1):
                            if hasattr(ev, "model_dump"):
                                data = ev.model_dump()
                            elif isinstance(ev, dict):
                                data = ev
                            else:
                                data = {}

                            nombre = data.get("nombre_candidato", getattr(ev, "nombre_candidato", "Desconocido"))
                            prioridad = data.get("puntuacion_prioridad", getattr(ev, "puntuacion_prioridad", 0))
                            justificacion = data.get("justificacion", getattr(ev, "justificacion", ""))
                            archivo = getattr(ev, "archivo", data.get("archivo", "Desconocido"))

                            texto_evaluacion = (
                                f"Rank #{idx} | {nombre} ({archivo})\n"
                                f"• Prioridad: {prioridad}/10\n"
                                f"• Análisis: {justificacion}"
                            )

                            children.append({
                                "type": "paragraph",
                                "paragraph": {"rich_text": [{"type": "text", "text": {"content": texto_evaluacion}}]}
                            })
                else:
                    # Comportamiento legacy: lista plana de evaluaciones
                    for idx, ev in enumerate(evaluaciones, 1):
                        # Extraer campos de datos (soporta diccionario o Pydantic)
                        if hasattr(ev, "model_dump"):
                            data = ev.model_dump()
                        elif isinstance(ev, dict):
                            data = ev
                        else:
                            data = {}

                        nombre = data.get("nombre_candidato", getattr(ev, "nombre_candidato", "Desconocido"))
                        encaja = data.get("encaja_en", getattr(ev, "encaja_en", "Ninguno"))
                        prioridad = data.get("puntuacion_prioridad", getattr(ev, "puntuacion_prioridad", 0))
                        justificacion = data.get("justificacion", getattr(ev, "justificacion", ""))
                        archivo = getattr(ev, "archivo", data.get("archivo", "Desconocido"))

                        texto_evaluacion = (
                            f"Rank #{idx} | {nombre} ({archivo})\n"
                            f"• Ajuste: {encaja}\n"
                            f"• Prioridad de Ajuste: {prioridad}/10\n"
                            f"• Análisis Técnico: {justificacion}"
                        )

                        children.append({
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {"content": texto_evaluacion}
                                    }
                                ]
                            }
                        })

                print(f"[INFO] Enviando reporte ordenado de {len(evaluaciones)} candidatos a la página Notion {formatted_page_id}...")
                
                try:
                    # Invocar la herramienta oficial del servidor
                    res = await session.call_tool(
                        name="API-patch-block-children",
                        arguments={
                            "block_id": formatted_page_id,
                            "children": children
                        }
                    )
                    print("[SUCCESS] ¡El reporte ha sido publicado exitosamente en Notion vía MCP!")
                    return res
                except Exception as e:
                    print(f"[ERROR] Ocurrió un error al invocar la herramienta del servidor MCP Notion: {e}")
                    raise e
