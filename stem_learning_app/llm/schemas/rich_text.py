import re
from typing import Annotated

from pydantic import AfterValidator

# Balises HTML courantes uniquement : « $a<b$ » ou « x < 3 » restent valides.
HTML_TAG_RE = re.compile(
    r"<\s*/?\s*(a|b|br|div|em|h[1-6]|i|iframe|img|li|ol|p|script|span|strong|style|sub|sup|table|td|th|tr|u|ul)\b[^>]*>",
    re.IGNORECASE,
)


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


# Texte riche (README §6) : texte + LaTeX $...$ / $$...$$ + \ce{...}, sans HTML.
RichText = Annotated[str, AfterValidator(_strip), AfterValidator(_no_html)]
