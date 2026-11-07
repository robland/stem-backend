"""Conversion d'unités du programme (SI, préfixes, km/h, L, Wh…) pour revérifier `unit_conversion`.

Les températures (°C ↔ K, conversion affine) ne sont pas prises en charge.
"""

import re

PREFIXES = {
    "G": 1e9, "M": 1e6, "k": 1e3, "h": 1e2, "da": 1e1,
    "d": 1e-1, "c": 1e-2, "m": 1e-3, "µ": 1e-6, "μ": 1e-6, "u": 1e-6, "n": 1e-9,
}
# Unité → (facteur vers le SI, dimensions {grandeur de base: puissance}).
BASE_UNITS = {
    "m": (1.0, {"m": 1}),
    "g": (1e-3, {"kg": 1}),
    "s": (1.0, {"s": 1}),
    "mol": (1.0, {"mol": 1}),
    "A": (1.0, {"A": 1}),
    "L": (1e-3, {"m": 3}),
    "N": (1.0, {"kg": 1, "m": 1, "s": -2}),
    "J": (1.0, {"kg": 1, "m": 2, "s": -2}),
    "W": (1.0, {"kg": 1, "m": 2, "s": -3}),
    "Wh": (3600.0, {"kg": 1, "m": 2, "s": -2}),
    "Pa": (1.0, {"kg": 1, "m": -1, "s": -2}),
    "V": (1.0, {"kg": 1, "m": 2, "s": -3, "A": -1}),
    "Hz": (1.0, {"s": -1}),
    "C": (1.0, {"A": 1, "s": 1}),
}
# Sans préfixe.
SPECIAL_UNITS = {
    "min": (60.0, {"s": 1}),
    "h": (3600.0, {"s": 1}),
    "t": (1000.0, {"kg": 1}),
    "ha": (1e4, {"m": 2}),
}
POWERS = str.maketrans({"²": "2", "³": "3"})
FACTOR_RE = re.compile(r"^(.+?)\^?(-?\d)?$")


class UnitError(ValueError):
    pass


def _resolve(symbol):
    if symbol in SPECIAL_UNITS:
        return SPECIAL_UNITS[symbol]
    if symbol in BASE_UNITS:
        return BASE_UNITS[symbol]
    for prefix, factor in PREFIXES.items():
        if symbol.startswith(prefix) and symbol[len(prefix):] in BASE_UNITS:
            base_factor, dims = BASE_UNITS[symbol[len(prefix):]]
            return factor * base_factor, dims
    raise UnitError(f"Unité inconnue : {symbol}")


def _factor(text, sign):
    match = FACTOR_RE.match(text)
    if not match:
        raise UnitError(f"Unité illisible : {text}")
    symbol, power = match.group(1), int(match.group(2) or 1)
    factor, dims = _resolve(symbol)
    return factor ** (power * sign), {name: exponent * power * sign for name, exponent in dims.items()}


def parse_unit(text):
    """« km/h », « m/s² », « g/L », « cm3 », « kWh » → (facteur vers le SI, dimensions)."""
    text = re.sub(r"\s+", "", (text or "").translate(POWERS)).replace("·", ".").replace("*", ".")
    if not text:
        raise UnitError("Unité vide")
    numerator, _, denominator = text.partition("/")
    if "/" in denominator:
        raise UnitError(f"Unité illisible : {text}")

    total, dims = 1.0, {}
    for part, sign in [(numerator, 1)] + ([(denominator, -1)] if denominator else []):
        for piece in part.split("."):
            factor, piece_dims = _factor(piece, sign)
            total *= factor
            for name, exponent in piece_dims.items():
                dims[name] = dims.get(name, 0) + exponent
    return total, {name: exponent for name, exponent in dims.items() if exponent}


def convert(value, from_unit, to_unit):
    from_factor, from_dims = parse_unit(from_unit)
    to_factor, to_dims = parse_unit(to_unit)
    if from_dims != to_dims:
        raise UnitError(f"Unités incompatibles : {from_unit} → {to_unit}")
    return value * from_factor / to_factor
