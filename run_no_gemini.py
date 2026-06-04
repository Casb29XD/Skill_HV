import asyncio
from main import run_skill


if __name__ == "__main__":
    # Ejecuta el skill en modo heurístico (no usa Gemini). Ajusta paths/límite si hace falta.
    asyncio.run(run_skill(
        candidates_dir="data/candidates",
        job_a_path="data/jobs/job-a-integration-developer-oracle-ebs.pdf",
        job_b_path="data/jobs/job-b-business-systems-analyst-oracle-ebs.pdf",
        notion_page_id=None,
        limit=None,
        use_llm=False
    ))
