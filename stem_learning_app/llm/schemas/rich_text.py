import re
from typing import Annotated

from pydantic import AfterValidator

# Balises HTML courantes uniquement : « $a<b$ » ou « x < 3 » restent valides.
HTML_TAG_RE = re.compile(
    r"<\s*/?\s*(a|b|br|div|em|h[1-6]|i|iframe|img|li|ol|p|script|span|strong|style|sub|sup|table|td|th|tr|u|ul)\b[^>]*>",
    re.IGNORECASE,
)
# Segments où le LaTeX est attendu : $$…$$, $…$ et \ce{…} (accolades imbriquées sur un niveau).
MATH_SEGMENT_RE = re.compile(r"\$\$.+?\$\$|\$.+?\$", re.DOTALL)
CHEMISTRY_RE = re.compile(r"\\ce\{(?:[^{}]|\{[^{}]*\})*\}")
# Commandes (\frac, \mathbb) et espacements (\, \; \!) n'ont de sens qu'en mode mathématique.
LATEX_COMMAND_RE = re.compile(r"\\(?:[A-Za-z]+|[,;:!])")
RAW_SCRIPT_RE = re.compile(r"[A-Za-z0-9)\]]\s*\^|[A-Za-z]_\{?[A-Za-z0-9]")
# x², (2x + 3)², CH₄ ; mais m², cm³ (unités) restent permis.
UNICODE_SCRIPT_RE = re.compile(r"(?<!m)[²³]|[⁰¹⁴-⁹₀-₉]")


def max_length(limit):
    # Contrôlé côté Pydantic : maxLength n'est pas accepté par les structured outputs stricts.
    def check(value):
        if len(value) > limit:
            raise ValueError(f"Texte trop long ({len(value)} > {limit} caractères).")
        return value

    return AfterValidator(check)


def _no_html(value):
    if HTML_TAG_RE.search(value):
        raise ValueError("Le HTML est interdit dans le texte riche (utiliser $...$ et \\ce{...}).")
    return value


def _strip(value):
    return value.strip()


def _math_delimited(value):
    outside = CHEMISTRY_RE.sub("", MATH_SEGMENT_RE.sub("", value))
    if LATEX_COMMAND_RE.search(outside):
        raise ValueError(
            "Commande LaTeX hors de $...$ : écrire les mathématiques entre $...$ (ex. $\\mathbb{R}$, "
            "$\\frac{1}{2}$) et la chimie avec \\ce{...}."
        )
    if RAW_SCRIPT_RE.search(outside) or UNICODE_SCRIPT_RE.search(outside):
        raise ValueError(
            "Exposant ou indice hors de $...$ : écrire $x^2 - 4x$, $(2x + 3)^2$ ou \\ce{CH4}, "
            "pas x^2, x², CH_4 ni CH₄."
        )
    return value


math_delimited = AfterValidator(_math_delimited)

# Texte riche (README §6) : texte + LaTeX $...$ / $$...$$ + \ce{...}, sans HTML.
RichText = Annotated[str, AfterValidator(_strip), AfterValidator(_no_html)]
# Texte riche produit par le LLM : en plus, aucune notation mathématique hors de $...$ / \ce{...}.
# (Plus souple pour la saisie des élèves, qui passe par RichText.)
LLMRichText = Annotated[RichText, math_delimited]
