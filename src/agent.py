import os
import logging
import re
import time
from typing import Literal
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class EvaluacionCandidato(BaseModel):
    nombre_candidato: str = Field(
        ...,
        description="Nombre completo del candidato extraído del currículum (CV). Si no está disponible o no se encuentra, usar 'Desconocido'."
    )
    encaja_en: str = Field(
        ...,
        description="Indica en qué puesto(s) o categoría encaja el candidato (por ejemplo: 'Puesto A', 'Backend Engineer', 'Ninguno')."
    )
    puntuacion_prioridad: int = Field(
        ...,
        description="Una puntuación de prioridad entera del 1 al 10 que representa el nivel de ajuste técnico del candidato frente a las vacantes, donde 10 es un ajuste perfecto y 1 es el menor ajuste.",
        ge=1,
        le=10
    )
    justificacion: str = Field(
        ...,
        description="Un análisis técnico conciso que justifica la decisión de ajuste y la puntuación de prioridad asignada."
    )
    archivo: str | None = Field(
        None,
        description="Nombre de archivo fuente del candidato (opcional, añadido por el pipeline)."
    )


class AgenteEvaluador:
    """Agente que evalúa CVs de candidatos frente a perfiles de vacantes usando Gemini."""

    def __init__(self, cliente_llm: genai.Client = None):
        """Inicializa el agente evaluador con el cliente de GenAI.
        Si cliente_llm es None, intenta inicializarlo usando la API KEY del entorno.
        """
        self.client = cliente_llm or genai.Client()

    def evaluar_candidato(self, texto_candidato: str, texto_puesto_a: str, texto_puesto_b: str) -> EvaluacionCandidato:
        """Evalúa un candidato frente a dos descripciones de puesto de forma semántica con un LLM.

        Args:
            texto_candidato: El texto extraído de la hoja de vida (CV).
            texto_puesto_a: La descripción técnica de la Vacante A / Puesto A.
            texto_puesto_b: La descripción técnica de la Vacante B / Puesto B.

        Returns:
            Instancia de EvaluacionCandidato validada por Pydantic.
        """
        system_instruction = (
            "Eres un reclutador técnico senior y experto en evaluación de talento de TI. "
            "Tu tarea es analizar detalladamente el currículum (CV) del candidato en relación con "
            "los requisitos descritos para el Puesto A y el Puesto B.\n\n"
            "Reglas críticas de evaluación:\n"
            "1. Extrae el nombre completo del candidato directamente de su CV. Si no se puede determinar, usa 'Desconocido'.\n"
            "2. Determina objetivamente si el perfil técnico e historial laboral encaja en: 'Puesto A', 'Puesto B', 'Ambos' o 'Ninguno'.\n"
            "3. Asigna una puntuación entera de prioridad de 1 a 10 (donde 10 es el ajuste perfecto y 1 es nulo/mínimo ajuste) evaluando tecnologías clave, experiencia y responsabilidades.\n"
            "4. Escribe una justificación técnica clara, concisa y detallada sobre la asignación del ajuste."
        )

        prompt = (
            f"Por favor, evalúa al siguiente candidato frente a las descripciones de los dos puestos provistos abajo.\n\n"
            f"=== DESCRIPCIÓN DEL PUESTO A ===\n{texto_puesto_a}\n\n"
            f"=== DESCRIPCIÓN DEL PUESTO B ===\n{texto_puesto_b}\n\n"
            f"=== CURRÍCULUM (CV) DEL CANDIDATO ===\n{texto_candidato}\n"
        )

        # Intentar llamada al LLM con reintentos en caso de quota, y fallback a heurística si falla
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=EvaluacionCandidato,
                        system_instruction=system_instruction,
                        temperature=0.1,
                    )
                )

                # Intentar usar el atributo parsed si el SDK lo generó directamente
                if hasattr(response, 'parsed') and response.parsed is not None:
                    return response.parsed

                # Alternativamente parsear manualmente el JSON
                if response.text:
                    return EvaluacionCandidato.model_validate_json(response.text)

                raise ValueError("El modelo devolvió una respuesta vacía.")

            except Exception as e:
                msg = str(e)
                logger.warning("Intento %d/%d: error LLM: %s", attempt, max_retries, msg)
                # Detectar errores por cuota / rate-limit y respetar sugerencia de retry si existe
                if 'RESOURCE_EXHAUSTED' in msg or 'quota' in msg or '429' in msg or 'rate limit' in msg.lower():
                    m = re.search(r"Please retry in ([0-9]+(?:\.[0-9]+)?)s", msg)
                    wait = float(m.group(1)) if m else min(60.0, 2 ** attempt)
                    logger.info("Quota hit: esperando %.1fs antes de reintentar...", wait)
                    time.sleep(wait)
                    continue
                # Para otros errores no reintentables, salir y usar fallback
                break

        # Si llegamos aquí, LLM falló tras reintentos; usar heurística de fallback
        logger.info("Fallo LLM permanente, usando heurística local para candidato.")
        return evaluate_candidate(candidate_text=texto_candidato, vacante_a_text=texto_puesto_a, vacante_b_text=texto_puesto_b, use_llm=False)

    def evaluar_un_puesto(self, texto_candidato: str, texto_puesto: str, nombre_puesto: str = "Puesto") -> EvaluacionCandidato:
        """Evalúa un candidato para un único puesto y devuelve una EvaluacionCandidato.

        Este método adapta la misma lógica de `evaluar_candidato` pero formatea
        el prompt para comparar el candidato contra una sola descripción de puesto.
        """
        system_instruction = (
            "Eres un reclutador técnico senior. Analiza si el candidato encaja en el puesto dado. "
            "Devuelve: nombre_candidato, encaja_en ('Encaja' o 'No encaja' o texto libre), puntuacion_prioridad (1-10), justificacion."
        )

        prompt = (
            f"Por favor, evalúa al siguiente candidato frente a la descripción del puesto provista abajo.\n\n"
            f"=== DESCRIPCIÓN DEL PUESTO ===\n{texto_puesto}\n\n"
            f"=== CURRÍCULUM (CV) DEL CANDIDATO ===\n{texto_candidato}\n"
        )

        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=EvaluacionCandidato,
                    system_instruction=system_instruction,
                    temperature=0.1,
                )
            )

            if hasattr(response, 'parsed') and response.parsed is not None:
                ev = response.parsed
                # Normalizar encaja_en para incluir el nombre del puesto
                ev.encaja_en = f"{nombre_puesto}: {ev.encaja_en}"
                return ev

            if response.text:
                ev = EvaluacionCandidato.model_validate_json(response.text)
                ev.encaja_en = f"{nombre_puesto}: {ev.encaja_en}"
                return ev

            raise ValueError("El modelo devolvió una respuesta vacía.")

        except Exception as e:
            logger.error("Error en evaluar_un_puesto: %s", e)
            raise RuntimeError(f"Error evaluando candidato para puesto '{nombre_puesto}': {e}")


def _tokenize(text: str) -> set:
    import re
    tokens = re.findall(r"\w+", (text or "").lower())
    return set(tokens)


def _extract_name(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return "Desconocido"

    label_patterns = [
        r"^nombre\s*[:\-]\s*(.+)$",
        r"^name\s*[:\-]\s*(.+)$",
        r"^candidato\s*[:\-]\s*(.+)$",
    ]
    for line in lines[:15]:
        for pattern in label_patterns:
            match = re.match(pattern, line, flags=re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value:
                    return value

    for line in lines[:10]:
        if 2 <= len(line.split()) <= 4 and re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'\-. ]+", line):
            return line

    return "Desconocido"


def _extract_keyword_hits(candidate: str, vacante: str) -> tuple[list[str], list[str]]:
    candidate_tokens = _tokenize(candidate)
    vacante_tokens = _tokenize(vacante)

    technical_groups = {
        "backend": {"python", "java", "c#", "dotnet", "node", "api", "rest", "microservices", "backend"},
        "frontend": {"react", "angular", "vue", "javascript", "typescript", "html", "css", "frontend"},
        "datos": {"sql", "mysql", "postgresql", "oracle", "power bi", "tableau", "etl", "data"},
        "cloud": {"aws", "azure", "gcp", "devops", "docker", "kubernetes", "terraform"},
        "erp": {"sap", "oracle", "ebs", "netsuite", "crm", "erp"},
        "metodologias": {"agile", "scrum", "kanban", "jira", "ci/cd", "testing", "tdd"},
    }

    matched_groups: list[str] = []
    missing_groups: list[str] = []
    for group_name, keywords in technical_groups.items():
        hits = []
        for keyword in keywords:
            normalized = keyword.lower().replace(" ", "")
            if keyword.lower() in candidate.lower() and keyword.lower() in vacante.lower():
                hits.append(keyword)
                continue
            if normalized in candidate_tokens and normalized in vacante_tokens:
                hits.append(keyword)
        if hits:
            matched_groups.append(f"{group_name}: {', '.join(sorted(set(hits))[:4])}")
        else:
            if any(keyword.lower() in vacante.lower() for keyword in keywords):
                missing_groups.append(group_name)

    return matched_groups, missing_groups


def _simple_score(candidate: str, vacante: str) -> float:
    c = _tokenize(candidate)
    v = _tokenize(vacante)
    if not c or not v:
        return 0.0
    inter = c & v
    score = (len(inter) / max(1, len(v))) * 10.0
    return min(10.0, max(1.0, score))


def evaluate_candidate(candidate_text: str, vacante_a_text: str, vacante_b_text: str, use_llm: bool = True) -> EvaluacionCandidato:
    """Función de compatibilidad que evalúa un candidato con LLM (si use_llm=True) o heurística simple (si False)."""
    if use_llm and os.getenv("GEMINI_API_KEY"):
        agent = AgenteEvaluador()
        return agent.evaluar_candidato(candidate_text, vacante_a_text, vacante_b_text)
    
    score_a = _simple_score(candidate_text, vacante_a_text)
    score_b = _simple_score(candidate_text, vacante_b_text)
    name = _extract_name(candidate_text)
    hits_a, missing_a = _extract_keyword_hits(candidate_text, vacante_a_text)
    hits_b, missing_b = _extract_keyword_hits(candidate_text, vacante_b_text)
    
    if score_a > score_b:
        encaja = "Puesto A"
        prioridad = int(round(score_a))
    elif score_b > score_a:
        encaja = "Puesto B"
        prioridad = int(round(score_b))
    elif score_a == score_b and score_a > 0:
        encaja = "Ambos"
        prioridad = int(round(score_a))
    else:
        encaja = "Ninguno"
        prioridad = 1
        
    prioridad = max(1, min(10, prioridad))
    justificacion_partes = [
        "[Simulación Heurística] Análisis local sin Gemini.",
        f"Puntuaciones comparativas — A: {score_a:.1f}/10, B: {score_b:.1f}/10.",
        f"Coincidencias relevantes en A: {', '.join(hits_a[:3]) if hits_a else 'sin coincidencias claras'}.",
        f"Coincidencias relevantes en B: {', '.join(hits_b[:3]) if hits_b else 'sin coincidencias claras'}.",
    ]

    if missing_a or missing_b:
        gaps = []
        if missing_a:
            gaps.append(f"A carece de señales fuertes en {', '.join(missing_a[:3])}")
        if missing_b:
            gaps.append(f"B carece de señales fuertes en {', '.join(missing_b[:3])}")
        justificacion_partes.append("Brechas detectadas: " + "; ".join(gaps) + ".")

    if encaja == "Ambos":
        justificacion_partes.append("El perfil comparte señales útiles para ambas vacantes, por lo que se considera versátil.")
    elif encaja == "Ninguno":
        justificacion_partes.append("No se observan coincidencias técnicas suficientes para priorizar alguna vacante.")
    else:
        justificacion_partes.append(f"La vacante prioritaria es {encaja} por mejor densidad de coincidencias textuales.")

    justificacion = " ".join(justificacion_partes)
    
    return EvaluacionCandidato(
        nombre_candidato=name,
        encaja_en=encaja,
        puntuacion_prioridad=prioridad,
        justificacion=justificacion
    )


__all__ = ["EvaluacionCandidato", "AgenteEvaluador", "evaluate_candidate"]

