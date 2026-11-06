from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict

from curriculum.choices import Level, SubjectCode

from .rich_text import RichText, max_length

MAX_EXERCISES_PER_UPLOAD = 20

SubjectCodeLiteral = Literal[tuple(SubjectCode.values)]
LevelLiteral = Literal[tuple(Level.values)]


def _not_empty(value):
    if not value:
        raise ValueError("Énoncé vide.")
    return value


def _max_exercises(value):
    if len(value) > MAX_EXERCISES_PER_UPLOAD:
        raise ValueError(f"Plus de {MAX_EXERCISES_PER_UPLOAD} exercices dans un même document.")
    return value


# Pas de valeurs par défaut : le mode strict exige que tous les champs soient présents (null autorisé).
class ExtractedExerciseOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: Annotated[RichText, AfterValidator(_not_empty), max_length(5000)]
    subject: SubjectCodeLiteral | None
    level: LevelLiteral | None
    chapter_hint: Annotated[str, max_length(200)] | None


class ExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_exercise_document: bool
    exercises: Annotated[list[ExtractedExerciseOut], AfterValidator(_max_exercises)]
