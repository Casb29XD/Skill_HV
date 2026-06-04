from pathlib import Path
from typing import Dict
import logging

try:
    from pypdf import PdfReader
except Exception:
    # pypdf should be in requirements; raise a clear error if missing at runtime
    PdfReader = None

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """Extrae y devuelve todo el texto de un PDF.

    Args:
        file_path: Ruta al archivo PDF.

    Returns:
        Texto concatenado de todas las páginas (cadena vacía si no hay texto).

    Raises:
        RuntimeError: Si `pypdf` no está disponible o la lectura falla.
    """
    if PdfReader is None:
        raise RuntimeError("Dependencia 'pypdf' no está disponible. Instala desde requirements.txt")

    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    try:
        reader = PdfReader(str(p))
        texts = []
        for page in reader.pages:
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            texts.append(page_text)
        return "\n".join(texts).strip()
    except Exception as e:
        logger.exception("Error leyendo PDF %s", file_path)
        raise RuntimeError(f"No se pudo extraer texto de {file_path}: {e}")


def extract_texts_from_folder(folder_path: str, pattern: str = "*.pdf") -> Dict[str, str]:
    """Extrae texto de todos los PDFs en una carpeta.

    Args:
        folder_path: Ruta a la carpeta que contiene PDFs.
        pattern: Glob pattern para localizar archivos (por defecto "*.pdf").

    Returns:
        Diccionario mapping `nombre_archivo` -> `texto`.
    """
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Carpeta no encontrada: {folder_path}")

    results: Dict[str, str] = {}
    files = list(folder.glob(pattern))
    for f in sorted(files):
        try:
            text = extract_text_from_pdf(str(f))
            results[f.name] = text
        except Exception as e:
            logger.warning("Fallo extrayendo %s: %s", f.name, e)
            # No elevamos para permitir que el flujo continúe; el llamador decide qué hacer.
    return results


def extraer_texto_pdf(file_path: str) -> str:
    """Wrapper para extract_text_from_pdf."""
    return extract_text_from_pdf(file_path)


def cargar_candidatos_desde_carpeta(folder_path: str) -> list:
    """Carga los PDFs de la carpeta y los devuelve en el formato de lista esperado por main.py."""
    texts = extract_texts_from_folder(folder_path)
    return [{"archivo": name, "perfil_texto": text} for name, text in texts.items()]


__all__ = [
    "extract_text_from_pdf",
    "extract_texts_from_folder",
    "extraer_texto_pdf",
    "cargar_candidatos_desde_carpeta"
]
