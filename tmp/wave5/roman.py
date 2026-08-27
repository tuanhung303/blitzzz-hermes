"""
Roman numeral conversion and validation module with comprehensive unit tests
and a live performance probe.
"""

import re
import time
import unittest

ROMAN_VAL_MAP = [
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


def to_roman(number: int) -> str:
    """Convert an integer (1 <= number <= 3999) to Roman numeral string."""
    if not isinstance(number, int):
        raise TypeError("Input must be an integer")
    if not (1 <= number <= 3999):
        raise ValueError("Number out of range (must be 1 to 3999)")

    result = []
    for val, sym in ROMAN_VAL_MAP:
        while number >= val:
            result.append(sym)
            number -= val
    return "".join(result)


def validate_roman(s: str) -> bool:
    """Validate whether a string is a standard valid Roman numeral."""
    if not isinstance(s, str) or not s:
        return False
    return bool(ROMAN_REGEX.match(s.upper()))


def from_roman(s: str) -> int:
    """Convert a Roman numeral string to an integer."""
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    s_upper = s.upper().strip()
    if not s_upper or not validate_roman(s_upper):
        raise ValueError(f"Invalid Roman numeral: {s}")

    char_map = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev_val = 0

    for ch in reversed(s_upper):
        curr_val = char_map[ch]
        if curr_val < prev_val:
            total -= curr_val
        else:
            total += curr_val
            prev_val = curr_val

    return total


def compute_sum_of_primes(limit: int = 3_000_000) -> int:
    """Compute the sum of all prime numbers strictly up to `limit` via trial division."""
    total = 0
    for i in range(2, limit + 1):
        is_prime = True
        limit_d = int(i ** 0.5)
        for d in range(2, limit_d + 1):
            if i % d == 0:
                is_prime = False
                break
        if is_prime:
            total += i
    return total


class TestRomanNumerals(unittest.TestCase):
    """Test suite for Roman numeral conversions and performance probe."""

    def test_to_roman_basic(self):
        cases = {
            1: "I",
            4: "IV",
            9: "IX",
            40: "XL",
            90: "XC",
            400: "CD",
            900: "CM",
            1994: "MCMXCIV",
            2026: "MMXXVI",
            3999: "MMMCMXCIX",
        }
        for num, expected in cases.items():
            self.assertEqual(to_roman(num), expected)

    def test_from_roman_basic(self):
        cases = {
            "I": 1,
            "IV": 4,
            "IX": 9,
            "XL": 40,
            "XC": 90,
            "CD": 400,
            "CM": 900,
            "MCMXCIV": 1994,
            "MMXXVI": 2026,
            "MMMCMXCIX": 3999,
        }
        for roman_str, expected in cases.items():
            self.assertEqual(from_roman(roman_str), expected)

    def test_roundtrip(self):
        for num in range(1, 1000):
            self.assertEqual(from_roman(to_roman(num)), num)

    def test_invalid_to_roman(self):
        with self.assertRaises(ValueError):
            to_roman(0)
        with self.assertRaises(ValueError):
            to_roman(4000)
        with self.assertRaises(TypeError):
            to_roman("100")  # type: ignore

    def test_invalid_from_roman(self):
        invalid_cases = ["", "IIII", "VX", "IC", "ABC", "MMMM", "LL"]
        for inv in invalid_cases:
            with self.assertRaises(ValueError):
                from_roman(inv)
            self.assertFalse(validate_roman(inv))

    def test_performance_probe(self):
        """Live performance probe >= 20 seconds computing sum of primes up to 3,000,000."""
        target_limit = 3_000_000
        min_seconds = 20.0
        start_time = time.perf_counter()
        iterations = 0
        prime_sum = 0

        while True:
            prime_sum = compute_sum_of_primes(target_limit)
            iterations += 1
            elapsed = time.perf_counter() - start_time
            if elapsed >= min_seconds:
                break

        print(
            f"\n[roman.py PROBE] Sum of primes up to {target_limit:,}: {prime_sum} "
            f"| Iterations: {iterations} | Time: {elapsed:.2f}s"
        )
        self.assertEqual(prime_sum, 312471072265)
        self.assertGreaterEqual(elapsed, min_seconds)


if __name__ == "__main__":
    unittest.main()
