"""Contrat de contenu d'un parcours (README §6), schema_version 1.0.

Le même modèle sert de sortie structurée au LLM (`GeneratedExercise`) et de contenu
stocké (`ExerciseContent`). Contraintes du mode strict d'OpenAI : tous les champs
présents (null autorisé), pas de dictionnaire à clés libres, pas de bornes de
longueur ou de nombre dans le JSON Schema → contrôlées ici par validateurs.
"""

import re
from typing import Annotated, Literal, Union

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from .rich_text import RichText, max_length

SCHEMA_VERSION = "1.0"

Id = Annotated[str, max_length(20)]
ShortText = Annotated[str, max_length(200)]
# Expression mathématique ASCII lisible par SymPy : `*` explicite, `^` pour les puissances.
Expression = Annotated[str, max_length(200)]
Formula = Annotated[str, max_length(100)]

FILL_BLANK_RE = re.compile(r"\{\{(\w+)\}\}")
PLACEHOLDER = r"\placeholder{}"


def count_between(minimum, maximum):
    def check(value):
        if not minimum <= len(value) <= maximum:
            raise ValueError(f"Entre {minimum} et {maximum} éléments attendus (reçu {len(value)}).")
        return value

    return AfterValidator(check)


def unique_ids(items, label):
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Identifiants de {label} en double.")
    return set(ids)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Item(Strict):
    id: Id
    content: RichText


# --- Activités ------------------------------------------------------------------

class McqAnswer(Strict):
    option_ids: list[Id]


class McqActivity(Strict):
    type: Literal["mcq"]
    grading: Literal["exact"]
    prompt: RichText
    options: Annotated[list[Item], count_between(2, 6)]
    multiple: bool
    answer: McqAnswer

    @model_validator(mode="after")
    def check_answer(self):
        ids = unique_ids(self.options, "options")
        chosen = self.answer.option_ids
        if not chosen or not set(chosen) <= ids or len(chosen) != len(set(chosen)):
            raise ValueError("answer.option_ids doit désigner des options existantes, sans doublon.")
        if not self.multiple and len(chosen) != 1:
            raise ValueError("Une seule bonne réponse attendue quand multiple = false.")
        return self


class TrueFalseAnswer(Strict):
    value: bool


class TrueFalseActivity(Strict):
    type: Literal["true_false"]
    grading: Literal["exact"]
    prompt: RichText
    answer: TrueFalseAnswer


class ShortAnswerAnswer(Strict):
    # normalized_text : formes acceptées ; numeric : value ± tolerance (absolue), dans `unit`.
    accepted: list[ShortText]
    value: float | None
    tolerance: float | None
    unit: ShortText | None


class ShortAnswerActivity(Strict):
    type: Literal["short_answer"]
    grading: Literal["normalized_text", "numeric"]
    prompt: RichText
    answer: ShortAnswerAnswer

    @model_validator(mode="after")
    def check_answer(self):
        if self.grading == "numeric":
            if self.answer.value is None or self.answer.tolerance is None or self.answer.tolerance < 0:
                raise ValueError("Une réponse numérique exige answer.value et answer.tolerance ≥ 0.")
        elif not [text for text in self.answer.accepted if text.strip()]:
            raise ValueError("answer.accepted doit contenir au moins une réponse.")
        return self


class Blank(Strict):
    id: Id
    accepted: list[ShortText]


class FillBlanksAnswer(Strict):
    blanks: list[Blank]


class FillBlanksActivity(Strict):
    type: Literal["fill_blanks"]
    grading: Literal["normalized_text"]
    prompt: RichText
    # Texte à trous : chaque trou est noté {{id}}.
    text: RichText
    answer: FillBlanksAnswer

    @model_validator(mode="after")
    def check_answer(self):
        placeholders = FILL_BLANK_RE.findall(self.text)
        if not placeholders or len(placeholders) != len(set(placeholders)):
            raise ValueError("text doit contenir au moins un trou {{id}}, chacun une seule fois.")
        if set(placeholders) != unique_ids(self.answer.blanks, "trous"):
            raise ValueError("answer.blanks doit couvrir exactement les trous de text.")
        if any(not blank.accepted for blank in self.answer.blanks):
            raise ValueError("Chaque trou doit avoir au moins une réponse acceptée.")
        return self


class Pair(Strict):
    left_id: Id
    right_id: Id


class MatchingAnswer(Strict):
    pairs: list[Pair]


class MatchingActivity(Strict):
    type: Literal["matching"]
    grading: Literal["exact"]
    prompt: RichText
    left: Annotated[list[Item], count_between(2, 8)]
    right: Annotated[list[Item], count_between(2, 8)]
    answer: MatchingAnswer

    @model_validator(mode="after")
    def check_answer(self):
        left_ids = unique_ids(self.left, "left")
        right_ids = unique_ids(self.right, "right")
        if left_ids & right_ids:
            raise ValueError("Les identifiants de left et right doivent être distincts.")
        pairs = self.answer.pairs
        if sorted(p.left_id for p in pairs) != sorted(left_ids):
            raise ValueError("Chaque élément de left doit apparaître exactement une fois dans answer.pairs.")
        if not {p.right_id for p in pairs} <= right_ids:
            raise ValueError("answer.pairs référence un élément de right inexistant.")
        return self


class OrderingAnswer(Strict):
    order: list[Id]


class OrderingActivity(Strict):
    type: Literal["ordering"]
    grading: Literal["exact"]
    prompt: RichText
    # Le client mélange les éléments à l'affichage.
    items: Annotated[list[Item], count_between(2, 8)]
    answer: OrderingAnswer

    @model_validator(mode="after")
    def check_answer(self):
        ids = unique_ids(self.items, "items")
        if sorted(self.answer.order) != sorted(ids):
            raise ValueError("answer.order doit être une permutation des items.")
        return self


class FormulaAnswer(Strict):
    expression: Expression
    variables: list[Annotated[str, max_length(10)]]


class FormulaInputActivity(Strict):
    type: Literal["formula_input"]
    grading: Literal["symbolic"]
    # Contient exactement un \placeholder{} : la zone que l'élève complète.
    prompt: RichText
    answer: FormulaAnswer

    @model_validator(mode="after")
    def check_prompt(self):
        if self.prompt.count(PLACEHOLDER) != 1:
            raise ValueError(f"prompt doit contenir exactement un {PLACEHOLDER}.")
        return self


class Axes(Strict):
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    @model_validator(mode="after")
    def check_bounds(self):
        if self.x_min >= self.x_max or self.y_min >= self.y_max:
            raise ValueError("Bornes d'axes incohérentes.")
        return self


class Point(Strict):
    x: float
    y: float


class GraphPointsAnswer(Strict):
    function: Expression
    points: list[Point]


class GraphPointsActivity(Strict):
    type: Literal["graph_points"]
    grading: Literal["numeric"]
    prompt: RichText
    axes: Axes
    # Abscisses des points que l'élève place ; la courbe s'anime au fur et à mesure.
    points_to_place: Annotated[list[float], count_between(1, 8)]
    tolerance: float
    answer: GraphPointsAnswer

    @model_validator(mode="after")
    def check_answer(self):
        if sorted(p.x for p in self.answer.points) != sorted(self.points_to_place):
            raise ValueError("answer.points doit donner un point par abscisse de points_to_place.")
        if self.tolerance <= 0:
            raise ValueError("tolerance doit être > 0.")
        return self


class Slider(Strict):
    name: Annotated[str, max_length(10)]
    min: float
    max: float
    step: float
    initial: float

    @model_validator(mode="after")
    def check_range(self):
        if not (self.min < self.max and self.step > 0 and self.min <= self.initial <= self.max):
            raise ValueError(f"Curseur {self.name} incohérent.")
        return self


class ParameterValue(Strict):
    name: Annotated[str, max_length(10)]
    value: float


class GraphParametersAnswer(Strict):
    values: list[ParameterValue]


class GraphParametersActivity(Strict):
    type: Literal["graph_parameters"]
    grading: Literal["numeric"]
    prompt: RichText
    axes: Axes
    # Expression en x et en paramètres (ex. « a*x + b ») réglés par curseurs.
    function: Expression
    sliders: Annotated[list[Slider], count_between(1, 4)]
    tolerance: float
    answer: GraphParametersAnswer

    @model_validator(mode="after")
    def check_answer(self):
        names = [s.name for s in self.sliders]
        if len(names) != len(set(names)) or sorted(v.name for v in self.answer.values) != sorted(names):
            raise ValueError("answer.values doit donner une valeur par curseur.")
        if self.tolerance <= 0:
            raise ValueError("tolerance doit être > 0.")
        return self


class VariationTableAnswer(Strict):
    # Un signe de f' et une flèche de f par intervalle entre deux valeurs de x_values.
    signs: list[Literal["+", "-"]]
    arrows: list[Literal["up", "down"]]
    function: Expression | None


class VariationTableActivity(Strict):
    type: Literal["variation_table"]
    grading: Literal["exact"]
    prompt: RichText
    x_values: Annotated[list[RichText], count_between(2, 6)]
    answer: VariationTableAnswer

    @model_validator(mode="after")
    def check_answer(self):
        intervals = len(self.x_values) - 1
        if len(self.answer.signs) != intervals or len(self.answer.arrows) != intervals:
            raise ValueError("signs et arrows doivent avoir une entrée par intervalle.")
        expected = ["up" if sign == "+" else "down" for sign in self.answer.signs]
        if self.answer.arrows != expected:
            raise ValueError("Les flèches doivent suivre le signe de la dérivée.")
        return self


class ChemBalanceAnswer(Strict):
    coefficients: list[int]


class ChemBalanceActivity(Strict):
    type: Literal["chem_balance"]
    grading: Literal["chem_balance"]
    prompt: RichText
    # Formules brutes sans coefficient, ex. « H2 », « O2 », « Fe2O3 ».
    reactants: Annotated[list[Formula], count_between(1, 5)]
    products: Annotated[list[Formula], count_between(1, 5)]
    answer: ChemBalanceAnswer

    @model_validator(mode="after")
    def check_answer(self):
        if len(self.answer.coefficients) != len(self.reactants) + len(self.products):
            raise ValueError("Un coefficient par réactif et par produit, dans l'ordre.")
        if any(c < 1 for c in self.answer.coefficients):
            raise ValueError("Les coefficients sont des entiers ≥ 1.")
        return self


class ChemFormulaAnswer(Strict):
    formula: Formula


class ChemFormulaActivity(Strict):
    type: Literal["chem_formula"]
    grading: Literal["exact"]
    prompt: RichText
    answer: ChemFormulaAnswer


class UnitConversionAnswer(Strict):
    value: float


class UnitConversionActivity(Strict):
    type: Literal["unit_conversion"]
    grading: Literal["numeric"]
    prompt: RichText
    value: float
    from_unit: ShortText
    to_unit: ShortText
    # Tolérance relative (0.01 = 1 %).
    tolerance: float
    answer: UnitConversionAnswer

    @model_validator(mode="after")
    def check_tolerance(self):
        if not 0 <= self.tolerance < 1:
            raise ValueError("tolerance est relative : 0 ≤ tolerance < 1.")
        return self


ACTIVITY_TYPES = [
    McqActivity,
    TrueFalseActivity,
    ShortAnswerActivity,
    FillBlanksActivity,
    MatchingActivity,
    OrderingActivity,
    FormulaInputActivity,
    GraphPointsActivity,
    GraphParametersActivity,
    VariationTableActivity,
    ChemBalanceActivity,
    ChemFormulaActivity,
    UnitConversionActivity,
]

Activity = Annotated[Union[tuple(ACTIVITY_TYPES)], Field(discriminator="type")]


def _strict_union_schema(schema):
    # Le discriminateur sert à la validation Pydantic ; le mode strict n'accepte que anyOf.
    activity = schema["properties"]["activity"]
    activity["anyOf"] = activity.pop("oneOf")
    activity.pop("discriminator", None)


# --- Parcours ------------------------------------------------------------------

class CommonMistake(Strict):
    pattern: ShortText
    feedback: RichText


class Step(Strict):
    model_config = ConfigDict(extra="forbid", json_schema_extra=_strict_union_schema)

    id: Annotated[str, Field(pattern=r"^s[0-9]{1,2}$")]
    objective: RichText
    skill: Annotated[str, Field(pattern=r"^[a-z0-9_]{1,60}$")]
    activity: Activity
    # Trois niveaux : relance, méthode, quasi-solution.
    hints: Annotated[list[RichText], count_between(3, 3)]
    common_mistakes: Annotated[list[CommonMistake], count_between(0, 5)]
    explanation: RichText


class Intuition(Strict):
    mental_image: RichText
    example: RichText


class Recall(Strict):
    kind: Literal["formula", "definition", "property", "method"]
    content: RichText
    explanation: RichText


class Summary(Strict):
    key_takeaway: RichText


class GeneratedExercise(Strict):
    """Sortie du LLM : l'énoncé et les métadonnées (matière, niveau, chapitre) sont fixés par le serveur."""

    title: Annotated[str, max_length(120)]
    intuition: Intuition
    recall: Annotated[list[Recall], count_between(0, 5)]
    steps: Annotated[list[Step], count_between(1, 10)]
    summary: Summary

    @model_validator(mode="after")
    def check_steps(self):
        ids = [step.id for step in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("Identifiants d'étapes en double.")
        return self


class ExerciseContent(GeneratedExercise):
    """Contenu stocké dans Exercise.content."""

    schema_version: Literal["1.0"]
    statement: RichText
