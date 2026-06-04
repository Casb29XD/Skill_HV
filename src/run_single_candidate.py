from pathlib import Path
import json
import os

from .agent import evaluate_candidate
from .pdf_utils import extract_text_from_pdf


def load_text_or_sample(path: str, sample: str) -> str:
    p = Path(path)
    if p.exists():
        return extract_text_from_pdf(str(p))
    return sample


def main():
    # Rutas por defecto (si existen archivos en el workspace, los usará)
    candidate_pdf = os.getenv("CANDIDATE_PDF", "data/candidates/candidate-01.pdf")
    vac_a_pdf = os.getenv("VAC_A_PDF", "data/jobs/job-a-integration-developer-oracle-ebs.pdf")
    vac_b_pdf = os.getenv("VAC_B_PDF", "data/jobs/job-b-business-systems-analyst-oracle-ebs.pdf")

    sample_cand = "Ingeniero de software senior con 5 años en Python, APIs y cloud."
    sample_a = "Vacante A: Ingeniero Python con experiencia en desarrollo de APIs y despliegue en AWS."
    sample_b = "Vacante B: Data Scientist con experiencia en ML, modelos supervisados y Python."

    cand_text = load_text_or_sample(candidate_pdf, sample_cand)
    a_text = load_text_or_sample(vac_a_pdf, sample_a)
    b_text = load_text_or_sample(vac_b_pdf, sample_b)

    # Usamos la heurística local para la prueba de Hito 2
    result = evaluate_candidate(cand_text, a_text, b_text, use_llm=False)

    print(result.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
