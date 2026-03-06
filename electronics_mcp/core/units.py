"""EE unit parsing and formatting.

Handles SI prefix shorthand (10k, 47u, 100n) and explicit units (10kohm, 100nF).
"""

import re

SI_PREFIXES = {
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "\u00b5": 1e-6,
    "m": 1e-3,
    "k": 1e3,
    "K": 1e3,
    "M": 1e6,
    "G": 1e9,
}

# Units to strip before prefix parsing
UNIT_SUFFIXES = [
    "ohm",
    "ohms",
    "Ohm",
    "Ohms",
    "F",
    "H",
    "V",
    "A",
    "W",
    "Hz",
    "hz",
    "s",
    "S",
]

# For formatting: ordered by magnitude
FORMAT_PREFIXES = [
    (1e-12, "p"),
    (1e-9, "n"),
    (1e-6, "u"),
    (1e-3, "m"),
    (1, ""),
    (1e3, "k"),
    (1e6, "M"),
    (1e9, "G"),
]

_PARSE_PATTERN = re.compile(
    r"^([+-]?\d+\.?\d*)\s*([pnu\u00b5mkKMG])?\s*("
    + "|".join(re.escape(s) for s in UNIT_SUFFIXES)
    + r")?$"
)


def parse_value(s: str) -> float:
    """Parse an EE value string to a float.

    Examples: '10k' -> 10000.0, '47u' -> 47e-6, '100nF' -> 100e-9
    """
    s = s.strip()
    if not s:
        raise ValueError("Empty value string")

    match = _PARSE_PATTERN.match(s)
    if match:
        number = float(match.group(1))
        prefix = match.group(2)
        multiplier = SI_PREFIXES.get(prefix, 1.0) if prefix else 1.0
        return number * multiplier

    # Fallback: try plain float
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"Cannot parse EE value: {s!r}")


def format_value(value: float) -> str:
    """Format a float as an EE value string.

    Examples: 10000.0 -> '10k', 47e-6 -> '47u'
    """
    if value == 0:
        return "0"

    abs_val = abs(value)
    for magnitude, prefix in reversed(FORMAT_PREFIXES):
        if abs_val >= magnitude * 0.999:
            scaled = value / magnitude
            # Format without trailing zeros
            if scaled == int(scaled):
                return f"{int(scaled)}{prefix}"
            else:
                return f"{scaled:g}{prefix}"

    # Very small values
    scaled = value / 1e-12
    if scaled == int(scaled):
        return f"{int(scaled)}p"
    return f"{scaled:g}p"
