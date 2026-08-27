"""Roman numeral conversion utilities."""

import re

ROMAN_MAP = [
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
]

ROMAN_REGEX = re.compile(
    r"^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$"
)


def to_roman(n: int) -> str:
    """Convert an integer in range 1..3999 to a Roman numeral.

    Args:
        n: Integer between 1 and 3999 inclusive.

    Returns:
        Roman numeral string.

    Raises:
        TypeError: If n is not an integer.
        ValueError: If n is not in 1..3999.
    """
    if not isinstance(n, int):
        raise TypeError(f"Input must be an integer, got {type(n).__name__}")
    if not (1 <= n <= 3999):
        raise ValueError(f"Input out of range (1..3999): {n}")

    result = []
    for val, numeral in ROMAN_MAP:
        while n >= val:
            result.append(numeral)
            n -= val
    return "".join(result)


def from_roman(s: str) -> int:
    """Convert a Roman numeral string to an integer.

    Args:
        s: Roman numeral string.

    Returns:
        Integer representation (1..3999).

    Raises:
        TypeError: If s is not a string.
        ValueError: If s is empty or not a valid Roman numeral.
    """
    if not isinstance(s, str):
        raise TypeError(f"Input must be a string, got {type(s).__name__}")
    s = s.strip().upper()
    if not s or not ROMAN_REGEX.match(s):
        raise ValueError(f"Invalid Roman numeral: '{s}'")

    char_values = {
        "I": 1,
        "V": 5,
        "X": 10,
        "L": 50,
        "C": 100,
        "D": 500,
        "M": 1000,
    }

    total = 0
    prev_val = 0
    for ch in reversed(s):
        val = char_values[ch]
        if val < prev_val:
            total -= val
        else:
            total += val
            prev_val = val
    return total
