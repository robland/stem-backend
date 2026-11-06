"""Points d'entrée métier du LLM : les autres apps n'appellent que ces fonctions."""

from curriculum.choices import Level, SubjectCode

from .clients import get_client
from .prompts import latest_prompt
from .schemas import ExtractionOutput


def extract_exercises(images, *, declared_level=""):
    """Transcrit les exercices d'un document (pages en images). Renvoie un LLMResult[ExtractionOutput]."""
    if not images:
        raise ValueError("Au moins une image est requise.")

    prompt = latest_prompt("extraction").render(
        subjects=", ".join(f"{code} ({label})" for code, label in SubjectCode.choices),
        levels=", ".join(Level.values),
        declared_level=Level(declared_level).label if declared_level else "non précisé",
    )
    return get_client().generate(
        task="extraction",
        prompt=prompt,
        output_schema=ExtractionOutput,
        images=images,
    )
