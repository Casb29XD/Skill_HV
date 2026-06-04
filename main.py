import os
import asyncio
import logging
import argparse
from dotenv import load_dotenv
from google import genai
from src.pdf_utils import cargar_candidatos_desde_carpeta, extraer_texto_pdf
from src.agent import AgenteEvaluador
from src.mcp_notion import MCPNotionClient

# Cargar credenciales desde el archivo .env si existe
load_dotenv()


async def run_skill(candidates_dir: str, job_a_path: str, job_b_path: str, notion_page_id: str | None, limit: int | None = None, use_llm: bool = True):
    print("=== INICIANDO SKILL AGÉNTICO DE RECLUTAMIENTO ===")

    # Validaciones mínimas
    if notion_page_id is None:
        notion_page_id = os.getenv("NOTION_PAGE_ID")

    if use_llm and not os.getenv("GEMINI_API_KEY"):
        print("[WARNING] GEMINI_API_KEY no encontrada en entorno; continuando en modo heurístico (use_llm=False)")
        use_llm = False

    # Inicializar agente (si corresponde)
    agente = None
    if use_llm:
        try:
            client_llm = genai.Client()
            agente = AgenteEvaluador(cliente_llm=client_llm)
        except Exception as e:
            print(f"[ERROR] No se pudo inicializar el cliente de Gemini: {e}")
            use_llm = False

    # Cargar descripciones de puesto: soporta múltiples archivos en la carpeta de jobs
    print("\n[INFO] Cargando descripciones de puesto desde la carpeta de jobs...")
    job_dir = os.path.dirname(job_a_path) or "data/jobs"
    job_files = sorted([f for f in os.listdir(job_dir) if f.lower().endswith('.pdf') or f.lower().endswith('.txt')])
    if not job_files:
        print(f"[ERROR] No se encontraron archivos de vacantes en {job_dir}")
        return

    jobs = []  # lista de tuples (job_name, texto_puesto)
    for jf in job_files:
        path = os.path.join(job_dir, jf)
        try:
            texto = extraer_texto_pdf(path)
            jobs.append((jf, texto))
        except Exception as e:
            print(f"[WARNING] No se pudo leer {path}: {e}")

    if not jobs:
        print("[ERROR] Ninguna descripción de puesto fue legible.")
        return

    print(f"[SUCCESS] Cargadas {len(jobs)} descripciones de puesto: {', '.join([j for j,_ in jobs])}")

    # Cargar candidatos
    print("\n[INFO] Escaneando y extrayendo perfiles de candidatos...")
    try:
        candidatos = cargar_candidatos_desde_carpeta(candidates_dir)
    except Exception as e:
        print(f"[ERROR] Error al escanear la carpeta de candidatos: {e}")
        return

    if not candidatos:
        print("[ERROR] No se encontraron candidatos en la carpeta indicada.")
        return

    if limit and limit > 0:
        candidatos = candidatos[:limit]
        print(f"[INFO] Procesando {len(candidatos)} candidatos (límite: {limit}).")
    else:
        print(f"[INFO] Procesando {len(candidatos)} candidatos (sin límite).")

    # Evaluar candidatos
    evaluaciones_finales = []
    grouped_evaluaciones = {job_name: [] for job_name, _ in jobs}
    print("\n[INFO] Iniciando evaluación agéntica...")

    for idx, cand in enumerate(candidatos, 1):
        print(f"\n[{idx}/{len(candidatos)}] Evaluando candidato desde archivo: {cand.get('archivo')}")
        try:
            if not cand.get("perfil_texto") or not cand.get("perfil_texto").strip():
                raise ValueError("El texto extraído del currículum está vacío o corrupto.")

            mejores = []  # acumulador de (job_name, EvaluacionCandidato)
            for job_name, job_text in jobs:
                if use_llm and agente and hasattr(agente, 'evaluar_un_puesto'):
                    ev = agente.evaluar_un_puesto(texto_candidato=cand["perfil_texto"], texto_puesto=job_text, nombre_puesto=job_name)
                else:
                    from src.agent import evaluate_candidate
                    # Heurística: evaluar candidato vs job_text (vacante A) y vacante B vacío
                    ev = evaluate_candidate(candidate_text=cand["perfil_texto"], vacante_a_text=job_text, vacante_b_text="", use_llm=False)
                    ev.encaja_en = f"{job_name}: {ev.encaja_en}"

                ev.archivo = cand.get("archivo")
                mejores.append((job_name, ev))

            # Seleccionar el job con mayor puntuacion_prioridad
            mejores.sort(key=lambda x: x[1].puntuacion_prioridad, reverse=True)
            mejor_job, mejor_ev = mejores[0]
            evaluaciones_finales.append(mejor_ev)
            grouped_evaluaciones[mejor_job].append(mejor_ev)

            print(f"[SUCCESS] Candidato '{mejor_ev.nombre_candidato}' => {mejor_job} ({mejor_ev.puntuacion_prioridad}/10)")
        except Exception as e:
            print(f"[ERROR] Falló la evaluación para '{cand.get('archivo')}': {e}")

        await asyncio.sleep(0.25)

    if not evaluaciones_finales:
        print("[ERROR] No se pudo realizar la evaluación de ningún candidato. Abortando publicación.")
        return

    # Ordenar por prioridad
    evaluaciones_finales.sort(key=lambda x: x.puntuacion_prioridad, reverse=True)

    # Publicar en Notion vía MCP (agrupado por puesto)
    if notion_page_id:
        print("\n[INFO] Enviando reporte ordenado a Notion mediante MCP...")
        try:
            mcp_notion = MCPNotionClient()
            # pasar el diccionario agrupado para que el cliente inserte secciones por puesto
            await mcp_notion.publicar_reporte(id_pagina_notion=notion_page_id, evaluaciones=grouped_evaluaciones)
            print("\n=== PROCESO COMPLETADO EXITOSAMENTE ===")
        except Exception as e:
            print(f"\n[ERROR] Falló la publicación del reporte final en Notion: {e}")
            print("=== PROCESO FINALIZADO CON ERRORES DE PUBLICACIÓN ===")
    else:
        print("[WARNING] NOTION_PAGE_ID no especificado. Mostrando resumen local del reporte por puesto:\n")
        for job_name, evs in grouped_evaluaciones.items():
            print(f"--- {job_name} ({len(evs)}) ---")
            for idx, ev in enumerate(sorted(evs, key=lambda x: x.puntuacion_prioridad, reverse=True), 1):
                print(f"{idx}. {ev.nombre_candidato} — {ev.puntuacion_prioridad}/10 — {getattr(ev,'archivo', '')}")


def parse_args():
    parser = argparse.ArgumentParser(description="Skill agéntico: evaluar candidatos y publicar reporte en Notion via MCP")
    parser.add_argument("--candidates-dir", default="data/candidates", help="Carpeta con PDFs/archivos de candidatos")
    parser.add_argument("--job-a", default="data/jobs/job-a-integration-developer-oracle-ebs.pdf", help="PDF de la Vacante A")
    parser.add_argument("--job-b", default="data/jobs/job-b-business-systems-analyst-oracle-ebs.pdf", help="PDF de la Vacante B")
    parser.add_argument("--notion-page-id", default=None, help="ID de la página de Notion (puede venir de .env NOTION_PAGE_ID)")
    parser.add_argument("--limit", type=int, default=None, help="Máximo número de candidatos a procesar (por defecto sin límite)")
    parser.add_argument("--no-llm", action="store_true", help="Forzar modo heurístico sin llamar al LLM")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_skill(
        candidates_dir=args.candidates_dir,
        job_a_path=args.job_a,
        job_b_path=args.job_b,
        notion_page_id=args.notion_page_id,
        limit=args.limit,
        use_llm=not args.no_llm
    ))