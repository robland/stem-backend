"""Réponses LLM valides pour les tests (jamais d'appel réel)."""

import copy

ACTIVITIES = {
    "mcq": {
        "type": "mcq", "grading": "exact", "prompt": "Quel est le degré de $f$ ?",
        "options": [{"id": "a", "content": "1"}, {"id": "b", "content": "2"}],
        "multiple": False, "answer": {"option_ids": ["b"]},
    },
    "true_false": {
        "type": "true_false", "grading": "exact", "prompt": "$f(1) = 0$ ?", "answer": {"value": True},
    },
    "short_answer": {
        "type": "short_answer", "grading": "numeric", "prompt": "Calcule $f(0)$.",
        "answer": {"accepted": [], "value": 3, "tolerance": 0, "unit": None},
    },
    "fill_blanks": {
        "type": "fill_blanks", "grading": "normalized_text", "prompt": "Complète.",
        "text": "Le sommet a pour abscisse {{1}} et pour ordonnée {{2}}.",
        "answer": {"blanks": [{"id": "1", "accepted": ["2"]}, {"id": "2", "accepted": ["-1"]}]},
    },
    "matching": {
        "type": "matching", "grading": "exact", "prompt": "Associe.",
        "left": [{"id": "l1", "content": "$x^2$"}, {"id": "l2", "content": "$x$"}],
        "right": [{"id": "r1", "content": "$2x$"}, {"id": "r2", "content": "$1$"}],
        "answer": {"pairs": [{"left_id": "l1", "right_id": "r1"}, {"left_id": "l2", "right_id": "r2"}]},
    },
    "ordering": {
        "type": "ordering", "grading": "exact", "prompt": "Range les étapes.",
        "items": [{"id": "i1", "content": "Dériver"}, {"id": "i2", "content": "Étudier le signe"}],
        "answer": {"order": ["i1", "i2"]},
    },
    "formula_input": {
        "type": "formula_input", "grading": "symbolic", "prompt": "Complète : $f'(x) = \\placeholder{}$",
        "answer": {"expression": "2*x - 4", "variables": ["x"], "form": "any", "source": None},
    },
    "graph_points": {
        "type": "graph_points", "grading": "numeric", "prompt": "Place les points de la courbe.",
        "axes": {"x_min": -1, "x_max": 5, "y_min": -2, "y_max": 8},
        "points_to_place": [0, 2], "tolerance": 0.2,
        "answer": {"function": "x^2 - 4*x + 3", "points": [{"x": 0, "y": 3}, {"x": 2, "y": -1}]},
    },
    "graph_parameters": {
        "type": "graph_parameters", "grading": "numeric", "prompt": "Règle $a$ et $b$.",
        "axes": {"x_min": -5, "x_max": 5, "y_min": -5, "y_max": 5}, "function": "a*x + b",
        "sliders": [
            {"name": "a", "min": -3, "max": 3, "step": 0.5, "initial": 0},
            {"name": "b", "min": -3, "max": 3, "step": 0.5, "initial": 0},
        ],
        "tolerance": 0.25, "answer": {"values": [{"name": "a", "value": 2}, {"name": "b", "value": -1}]},
    },
    "variation_table": {
        "type": "variation_table", "grading": "exact", "prompt": "Complète le tableau.",
        "x_values": ["$-\\infty$", "2", "$+\\infty$"],
        "answer": {"signs": ["-", "+"], "arrows": ["down", "up"], "function": "x^2 - 4*x + 3"},
    },
    "chem_balance": {
        "type": "chem_balance", "grading": "chem_balance", "prompt": "Équilibre \\ce{H2 + O2 -> H2O}.",
        "reactants": ["H2", "O2"], "products": ["H2O"], "answer": {"coefficients": [2, 1, 2]},
    },
    "chem_formula": {
        "type": "chem_formula", "grading": "exact", "prompt": "Formule de l'eau ?", "answer": {"formula": "H2O"},
    },
    "unit_conversion": {
        "type": "unit_conversion", "grading": "numeric", "prompt": "Convertis.",
        "value": 2.5, "from_unit": "km", "to_unit": "m", "tolerance": 0.01, "answer": {"value": 2500},
    },
}


def step(step_id="s1", activity="formula_input", **overrides):
    data = {
        "id": step_id,
        "objective": "Calculer la dérivée",
        "skill": "derivee_polynome",
        "activity": copy.deepcopy(ACTIVITIES[activity]),
        "hints": ["Quelle règle s'applique à $x^2$ ?", "$(x^n)' = n x^{n-1}$", "$f'(x) = 2x - \\dots$"],
        "common_mistakes": [{"pattern": "2x + 4", "feedback": "Attention au signe de $-4x$."}],
        "explanation": "$f'(x) = 2x - 4$.",
    }
    return data | overrides


def generated_exercise(*steps, **overrides):
    data = {
        "title": "Variations d'une fonction du second degré",
        "intuition": {"mental_image": "Une colline à l'envers.", "example": "Le trajet d'un ballon."},
        "recall": [{"kind": "formula", "content": "$(x^n)' = n x^{n-1}$", "explanation": "Dérivée d'une puissance."}],
        "steps": list(steps) or [step("s1"), step("s2", "variation_table")],
        "summary": {"key_takeaway": "Le signe de $f'$ donne les variations de $f$."},
    }
    return data | overrides
