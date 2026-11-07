"""Points d'entrée métier du LLM : les autres apps n'appellent que ces fonctions."""

from curriculum.choices import COLLEGE_LEVELS, Level, SubjectCode

from .clients import get_client
from .exceptions import LLMOutputInvalid
from .prompts import latest_prompt
from .statement import count_questions
from .schemas import ExtractionOutput, GeneratedExercise, ModerationOutput


def extract_exercises(images, *, declared_level=""):
    """Transcrit les exercices d'un document (pages en images). Renvoie un LLMResult[ExtractionOutput]."""
    if not images:
        raise ValueError("Au moins une image est requise.")

    context = {
        "subjects": ", ".join(f"{code} ({label})" for code, label in SubjectCode.choices),
        "levels": ", ".join(Level.values),
        "declared_level": Level(declared_level).label if declared_level else "non précisé",
    }
    prompt = latest_prompt("extraction")

    def extract(correction):
        return get_client().generate(
            task="extraction",
            prompt=prompt.render(**context, correction=correction),
            output_schema=ExtractionOutput,
            images=images,
        )

    # Comme pour la génération : une réponse hors schéma est relancée une fois avec ses erreurs.
    try:
        return extract("")
    except LLMOutputInvalid as e:
        if not e.errors:
            raise
        return extract(_correction_text(e.errors))


def moderate_statement(statement):
    """Énoncé → verdict avant publication au catalogue public. Renvoie un LLMResult[ModerationOutput]."""
    return get_client().generate(
        task="moderation",
        prompt=latest_prompt("moderation").render(statement=statement),
        output_schema=ModerationOutput,
    )


def exam_for(level):
    return "BEPC" if level in COLLEGE_LEVELS else "BAC"


def generate_exercise(*, statement, subject, level, chapter="", corrections=()):
    """Énoncé validé → parcours guidé. Renvoie un LLMResult[GeneratedExercise].

    Une réponse hors schéma (ex. bonne réponse absente des options) est relancée
    une fois en indiquant au modèle les erreurs à corriger. `corrections` transmet
    les erreurs détectées sur une génération précédente (revérification).
    """
    context = {
        "subject": SubjectCode(subject).label,
        "level": Level(level).label,
        "exam": exam_for(level),
        "chapter": chapter or "non précisé",
        "statement": statement,
        # Valeurs littérales : « {{1}} » dans le gabarit serait pris pour une variable.
        "blank_example": "{{1}}, {{2}}",
        "blank_one": "{{1}}",
        "blank_two": "{{2}}",
        "structure": _structure_text(statement),
    }
    prompt = latest_prompt("generation")
    try:
        return _generate(prompt.render(**context, correction=_correction_text(corrections)))
    except LLMOutputInvalid as e:
        if not e.errors:
            raise
        return _generate(prompt.render(**context, correction=_correction_text(e.errors)))


def _structure_text(statement):
    questions = count_questions(statement)
    if not questions:
        return ""
    return (
        f"\nCet énoncé comporte {questions} questions numérotées : le parcours doit avoir au moins "
        f"{questions} étapes, au moins une par question, dans l'ordre.\n"
    )


def _correction_text(errors):
    if not errors:
        return ""
    return "\nTa réponse précédente était invalide. Corrige ces erreurs :\n" + "\n".join(f"- {line}" for line in errors)


def _generate(rendered):
    return get_client().generate(task="generation", prompt=rendered, output_schema=GeneratedExercise)
