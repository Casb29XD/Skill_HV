import os
import logging
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
    encaja_en: Literal["Puesto A", "Puesto B", "Ambos", "Ninguno"] = Field(
        ...,
        description="Determina si el candidato encaja en el 'Puesto A', 'Puesto B', 'Ambos' o 'Ninguno'."
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

        try:
            # Invocar Gemini usando google-genai
            # Usamos gemini-2.5-flash ya que soporta structured output y es rápido
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
            logger.error("Error durante la generación o validación estructurada del LLM: %s", e)
            raise RuntimeError(f"Error evaluando candidato con LLM: {e}")


def _tokenize(text: str) -> set:
    import re
    tokens = re.findall(r"\w+", (text or "").lower())
    return set(tokens)


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
    justificacion = f"[Simulación Heurística] Puntuaciones — A: {score_a:.1f}/10, B: {score_b:.1f}/10. Resultado: {encaja}."
    
    return EvaluacionCandidato(
        nombre_candidato="Candidato Simulado",
        encaja_en=encaja,
        puntuacion_prioridad=prioridad,
        justificacion=justificacion
    )


__all__ = ["EvaluacionCandidato", "AgenteEvaluador", "evaluate_candidate"]

