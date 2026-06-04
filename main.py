import os
import asyncio
import logging
from dotenv import load_dotenv
from google import genai
from src.pdf_utils import cargar_candidatos_desde_carpeta, extraer_texto_pdf
from src.agent import AgenteEvaluador
from src.mcp_notion import MCPNotionClient

# Cargar credenciales desde el archivo .env
load_dotenv()

async def main():
    print("=== INICIANDO SKILL AGÉNTICO DE RECLUTAMIENTO ===")
    
    # 1. Validación de Entorno
    notion_page_id = os.getenv("NOTION_PAGE_ID")
    if not notion_page_id:
        print("[ERROR] Falta NOTION_PAGE_ID en el archivo .env")
        return

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("[ERROR] Falta GEMINI_API_KEY en el archivo .env")
        return

    # 2. Inicializar el Cliente del LLM y el Agente
    try:
        # El cliente genai de google-genai lee automáticamente GEMINI_API_KEY de las variables de entorno
        client_llm = genai.Client()
        agente = AgenteEvaluador(cliente_llm=client_llm)
    except Exception as e:
        print(f"[ERROR] No se pudo inicializar el cliente de Gemini: {e}")
        return

    # 3. Extraer perfiles de las Vacantes (Puestos estáticos de la ejecución)
    print("\n[INFO] Cargando descripciones de puesto...")
    try:
        texto_puesto_a = extraer_texto_pdf("data/jobs/job-a-integration-developer-oracle-ebs.pdf")
        texto_puesto_b = extraer_texto_pdf("data/jobs/job-b-business-systems-analyst-oracle-ebs.pdf")
    except Exception as e:
        print(f"[ERROR] No se pudieron cargar las descripciones de las vacantes: {e}")
        return

    if not texto_puesto_a or not texto_puesto_b:
        print("[ERROR] Una o ambas descripciones de puesto están vacías o no pudieron ser leídas.")
        return
    
    print("[SUCCESS] Descripciones de puesto cargadas correctamente.")

    # 4. Cargar todos los candidatos
    print("\n[INFO] Escaneando y extrayendo perfiles de candidatos...")
    try:
        candidatos = cargar_candidatos_desde_carpeta("data/candidates")
    except Exception as e:
        print(f"[ERROR] Error al escanear la carpeta de candidatos: {e}")
        return

    print(f"[INFO] Se encontraron {len(candidatos)} candidatos para procesar.")

    # 5. Ejecutar análisis uno por uno (Garantizando consistencia y manejo de excepciones por candidato)
    evaluaciones_finales = []
    print("\n[INFO] Iniciando evaluación agéntica con el LLM...")
    
    for idx, cand in enumerate(candidatos, 1):
        print(f"\n[{idx}/{len(candidatos)}] Evaluando candidato desde archivo: {cand['archivo']}...")
        
        try:
            # Validar que el texto extraído del CV no esté vacío
            if not cand["perfil_texto"] or not cand["perfil_texto"].strip():
                raise ValueError("El texto extraído del currículum está vacío o corrupto.")

            # Inferencia lógica del Agente
            evaluacion = agente.evaluar_candidato(
                texto_candidato=cand["perfil_texto"],
                texto_puesto_a=texto_puesto_a,
                texto_puesto_b=texto_puesto_b
            )
            
            # Asociar el nombre de archivo a la evaluación para el reporte final
            evaluacion.archivo = cand["archivo"]
            evaluaciones_finales.append(evaluacion)
            
            print(f"[SUCCESS] Candidato '{evaluacion.nombre_candidato}' evaluado correctamente.")
            print(f"         - Fit: {evaluacion.encaja_en}")
            print(f"         - Prioridad: {evaluacion.puntuacion_prioridad}/10")
            
        except Exception as e:
            # Manejo de excepciones robusto para que un error en un candidato no rompa el lote completo
            print(f"[ERROR] Falló la evaluación para el archivo '{cand['archivo']}': {e}")
        
        # Pequeña pausa de cortesía para mitigar Rate Limits de la API
        await asyncio.sleep(1.0)

    # Validar si logramos evaluar a algún candidato
    if not evaluaciones_finales:
        print("\n[ERROR] No se pudo realizar la evaluación de ningún candidato. Abortando publicación.")
        return

    # 6. Priorizar el reporte: Ordenar de Mayor a Menor según 'puntuacion_prioridad'
    print("\n[INFO] Ordenando reporte por prioridad de contratación...")
    evaluaciones_finales.sort(key=lambda x: x.puntuacion_prioridad, reverse=True)
    print("[SUCCESS] Reporte ordenado de mayor a menor prioridad.")

    # 7. Publicación en Notion vía MCP
    print("\n[INFO] Enviando reporte ordenado a Notion mediante MCP...")
    try:
        mcp_notion = MCPNotionClient()
        await mcp_notion.publicar_reporte(id_pagina_notion=notion_page_id, evaluaciones=evaluaciones_finales)
        print("\n=== PROCESO COMPLETADO EXITOSAMENTE ===")
    except Exception as e:
        print(f"\n[ERROR] Falló la publicación del reporte final en Notion: {e}")
        print("=== PROCESO FINALIZADO CON ERRORES DE PUBLICACIÓN ===")

if __name__ == "__main__":
    asyncio.run(main())