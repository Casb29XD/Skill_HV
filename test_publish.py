import asyncio
from src.mcp_notion import MCPNotionClient

async def main():
    client = MCPNotionClient()
    fake = [{
        "nombre_candidato":"Prueba Local",
        "encaja_en":"Puesto A",
        "puntuacion_prioridad":8,
        "justificacion":"Prueba de publicación desde entorno local",
        "archivo":"prueba.pdf"
    }]
    await client.publicar_reporte(id_pagina_notion=client.page_id or "TU_PAGE_ID_AQUI", evaluaciones=fake)

if __name__ == "__main__":
    asyncio.run(main())