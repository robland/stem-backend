"""Normalisation des réponses saisies (règles à reproduire à l'identique côté client hors-ligne)."""

import re
import unicodedata

APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "`": "'"})
TRAILING_PUNCTUATION = " .;!?"
NUMBER_RE = re.compile(
    r"([+-]?\d+(?:\.\d+)?)"  # mantisse (virgule décimale déjà convertie)
    r"(?:(?:x|\*)10\^?\(?([+-]?\d+)\)?|e([+-]?\d+))?",  # ×10^n ou e±n
    re.IGNORECASE,
)


def normalize_text(value):
    """Casse, espaces, apostrophes typographiques et ponctuation finale ignorées.

    Les accents sont conservés : « a » et « à » sont des réponses différentes.
    """
    value = unicodedata.normalize("NFC", value).translate(APOSTROPHES).casefold()
    return " ".join(value.split()).strip(TRAILING_PUNCTUATION)


def parse_number(value):
    """Nombre saisi en français ou en anglais : « 2,5 », « 2 500 », « 2,5×10^3 », « 2.5e3 ». None si illisible."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    text = re.sub(r"[\s  ]", "", value).replace("×", "x").replace("·", "x").replace("−", "-")
    text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    match = NUMBER_RE.fullmatch(text)
    if not match:
        return None
    mantissa, power, exponent = match.groups()
    return float(mantissa) * 10 ** int(power or exponent or 0)


def close_enough(value, expected, tolerance):
    """Tolérance absolue (bornes comprises, avec une marge pour les arrondis binaires)."""
    return abs(value - expected) <= tolerance + 1e-9 * max(1.0, abs(expected))
