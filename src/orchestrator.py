import os
import json
import logging
from pathlib import Path
from typing import List, Dict

from .pdf_utils import extract_texts_from_folder, extract_text_from_pdf
from .agent import evaluate_candidate

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def _load_job_text(path: str, fallback: str) -> str:
    p = Path(path)
    if p.exists() and p.is_file():
        # soporta PDFs u archivos de texto planos
        if p.suffix.lower() == ".pdf":
            return extract_text_from_pdf(str(p))
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return extract_text_from_pdf(str(p))
    return fallback


def process_all(candidates_folder: str = "data/candidates",
                vac_a_path: str = "data/jobs/job-a-integration-developer-oracle-ebs.pdf",
                vac_b_path: str = "data/jobs/job-b-business-systems-analyst-oracle-ebs.pdf",
                use_llm: bool = False,
                output_path: str = "data/results.json") -> List[Dict]:
    """Procesa todos los CVs en `candidates_folder`, evalúa vs vacantes A y B,
    y escribe resultados ordenados por `puntuacion_prioridad`.

    Devuelve la lista de resultados.
    """
    logger.info("Cargando vacantes...")
    sample_a = "Vacante A: Ingeniero Python con experiencia en desarrollo de APIs y despliegue en la nube."
    sample_b = "Vacante B: Data Scientist con experiencia en modelos ML y análisis de datos."

    vac_a_text = _load_job_text(vac_a_path, sample_a)
    vac_b_text = _load_job_text(vac_b_path, sample_b)

    logger.info("Listando candidatos en %s", candidates_folder)
    candidates = extract_texts_from_folder(candidates_folder)
    if not candidates:
        logger.warning("No se encontraron candidatos en %s", candidates_folder)

    results = []
    processed = 0
    failed = 0

    for i, (filename, text) in enumerate(candidates.items(), start=1):
        logger.info("Procesando candidato %d/%d: %s", i, len(candidates), filename)
        try:
            evaluation = evaluate_candidate(text, vac_a_text, vac_b_text, use_llm=use_llm)
            rec = {
                "archivo": filename,
                "encaja_en": evaluation.encaja_en,
                "puntuacion_prioridad": evaluation.puntuacion_prioridad,
                "justificacion": evaluation.justificacion,
            }
            results.append(rec)
            processed += 1
        except Exception as e:
            logger.exception("Error evaluando %s: %s", filename, e)
            failed += 1
            continue

    # ordenar por puntuacion_prioridad desc
    results.sort(key=lambda r: r.get("puntuacion_prioridad", 0), reverse=True)

    # escribir resultados
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with out_p.open("w", encoding="utf-8") as fh:
        json.dump({"summary": {"processed": processed, "failed": failed}, "results": results}, fh, ensure_ascii=False, indent=2)

    logger.info("Procesamiento completado: %d procesados, %d fallos. Resultados guardados en %s", processed, failed, output_path)
    return results


if __name__ == "__main__":
    candidates_folder = os.getenv("CANDIDATES_FOLDER", "data/candidates")
    vac_a = os.getenv("VAC_A_PDF", "data/jobs/job-a-integration-developer-oracle-ebs.pdf")
    vac_b = os.getenv("VAC_B_PDF", "data/jobs/job-b-business-systems-analyst-oracle-ebs.pdf")
    output = os.getenv("OUTPUT_PATH", "data/results.json")
    use_llm = os.getenv("USE_LLM", "false").lower() in ("1", "true", "yes")

    process_all(candidates_folder=candidates_folder, vac_a_path=vac_a, vac_b_path=vac_b, use_llm=use_llm, output_path=output)
