"""Points d'entrée métier du LLM : les autres apps n'appellent que ces fonctions."""

from curriculum.choices import COLLEGE_LEVELS, Level, SubjectCode

from .clients import get_client
from .exceptions import LLMOutputInvalid
from .prompts import latest_prompt
from .schemas import ExtractionOutput, GeneratedExercise


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


def exam_for(level):
    return "BEPC" if level in COLLEGE_LEVELS else "BAC"


def generate_exercise(*, statement, subject, level, chapter=""):
    """Énoncé validé → parcours guidé. Renvoie un LLMResult[GeneratedExercise].

    Une réponse hors schéma (ex. bonne réponse absente des options) est relancée
    une fois en indiquant au modèle les erreurs à corriger.
    """
    context = {
        "subject": SubjectCode(subject).label,
        "level": Level(level).label,
        "exam": exam_for(level),
        "chapter": chapter or "non précisé",
        "statement": statement,
        "blank_example": "{{1}}, {{2}}",
    }
    prompt = latest_prompt("generation")
    try:
        return _generate(prompt.render(**context, correction=""))
    except LLMOutputInvalid as e:
        if not e.errors:
            raise
        correction = "\nTa réponse précédente était invalide. Corrige ces erreurs :\n" + "\n".join(
            f"- {line}" for line in e.errors
        )
        return _generate(prompt.render(**context, correction=correction))


def _generate(rendered):
    return get_client().generate(task="generation", prompt=rendered, output_schema=GeneratedExercise)
