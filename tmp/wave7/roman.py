"""Roman numeral conversion module with unit tests and performance probe."""

import math
import time
import unittest

ROMAN_NUMERAL_MAP = (
    ("M", 1000),
    ("CM", 900),
    ("D", 500),
    ("CD", 400),
    ("C", 100),
    ("XC", 90),
    ("L", 50),
    ("XL", 40),
    ("X", 10),
    ("IX", 9),
    ("V", 5),
    ("IV", 4),
    ("I", 1),
)

ROMAN_VALUE_MAP = {
    "I": 1,
    "V": 5,
    "X": 10,
    "L": 50,
    "C": 100,
    "D": 500,
    "M": 1000,
}


def to_roman(n: int) -> str:
    """Convert an integer to a Roman numeral string (1..3999)."""
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")
    if not (1 <= n <= 3999):
        raise ValueError("Number out of range (must be 1..3999)")

    result = []
    for roman, val in ROMAN_NUMERAL_MAP:
        while n >= val:
            result.append(roman)
            n -= val
    return "".join(result)


def from_roman(s: str) -> int:
    """Convert a Roman numeral string to an integer."""
    if not isinstance(s, str) or not s:
        raise ValueError("Input must be a non-empty string")
    s = s.upper().strip()
    total = 0
    prev_value = 0
    for char in reversed(s):
        if char not in ROMAN_VALUE_MAP:
            raise ValueError(f"Invalid Roman numeral character: {char}")
        value = ROMAN_VALUE_MAP[char]
        if value < prev_value:
            total -= value
        else:
            total += value
            prev_value = value

    if to_roman(total) != s:
        raise ValueError(f"Invalid Roman numeral formatting: {s}")
    return total


def compute_sum_primes(limit: int = 3_000_000) -> int:
    """Calculate sum of primes below limit using trial division."""
    total = 0
    for n in range(2, limit):
        is_p = True
        root = math.isqrt(n)
        for d in range(2, root + 1):
            if n % d == 0:
                is_p = False
                break
        if is_p:
            total += n
    return total


def run_prime_performance_probe(limit: int = 3_000_000, min_seconds: float = 20.0) -> dict:
    """Run performance probe summing primes up to limit until at least min_seconds elapsed."""
    start = time.perf_counter()
    iterations = 0
    prime_sum = 0
    while True:
        prime_sum = compute_sum_primes(limit)
        iterations += 1
        elapsed = time.perf_counter() - start
        if elapsed >= min_seconds:
            break
    return {
        "module": "roman",
        "prime_sum": prime_sum,
        "limit": limit,
        "iterations": iterations,
        "elapsed_seconds": elapsed,
    }


class TestRoman(unittest.TestCase):
    def test_to_roman_standard(self):
        self.assertEqual(to_roman(1), "I")
        self.assertEqual(to_roman(4), "IV")
        self.assertEqual(to_roman(9), "IX")
        self.assertEqual(to_roman(58), "LVIII")
        self.assertEqual(to_roman(1994), "MCMXCIV")
        self.assertEqual(to_roman(3999), "MMMCMXCIX")

    def test_from_roman_standard(self):
        self.assertEqual(from_roman("I"), 1)
        self.assertEqual(from_roman("IV"), 4)
        self.assertEqual(from_roman("IX"), 9)
        self.assertEqual(from_roman("LVIII"), 58)
        self.assertEqual(from_roman("MCMXCIV"), 1994)
        self.assertEqual(from_roman("MMMCMXCIX"), 3999)

    def test_roundtrip(self):
        for num in [1, 2, 3, 4, 9, 14, 49, 99, 444, 999, 1492, 2026]:
            self.assertEqual(from_roman(to_roman(num)), num)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            to_roman(0)
        with self.assertRaises(ValueError):
            to_roman(4000)
        with self.assertRaises(ValueError):
            from_roman("IIII")
        with self.assertRaises(ValueError):
            from_roman("ABC")

    def test_performance_probe(self):
        result = run_prime_performance_probe(limit=3_000_000, min_seconds=20.0)
        self.assertEqual(result["prime_sum"], 312471072265)
        self.assertGreaterEqual(result["elapsed_seconds"], 20.0)
        print(f"\n[PROBE roman.py] Elapsed: {result['elapsed_seconds']:.3f}s, Iterations: {result['iterations']}, Sum: {result['prime_sum']}")


if __name__ == "__main__":
    unittest.main()
