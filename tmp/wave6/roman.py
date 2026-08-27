"""Roman numeral conversion and validation module with unittest suite and performance probe."""

import re
import time
import unittest

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

ROMAN_VALUE = {
    "I": 1,
    "V": 5,
    "X": 10,
    "L": 50,
    "C": 100,
    "D": 500,
    "M": 1000,
}

ROMAN_REGEX = re.compile(
    r"^(?=.)M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$"
)


def to_roman(n: int) -> str:
    """Convert an integer (1 to 3999) to a Roman numeral."""
    if not isinstance(n, int):
        raise TypeError("n must be an integer")
    if not (1 <= n <= 3999):
        raise ValueError("n must be between 1 and 3999")

    result = []
    for value, symbol in ROMAN_MAP:
        while n >= value:
            result.append(symbol)
            n -= value
    return "".join(result)


def from_roman(s: str) -> int:
    """Convert a Roman numeral string to an integer."""
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    s = s.strip().upper()
    if not s or not ROMAN_REGEX.match(s):
        raise ValueError(f"Invalid Roman numeral: {s}")

    total = 0
    prev_val = 0
    for char in reversed(s):
        curr_val = ROMAN_VALUE[char]
        if curr_val < prev_val:
            total -= curr_val
        else:
            total += curr_val
        prev_val = curr_val
    return total


def validate_roman(s: str) -> bool:
    """Check if a string is a valid Roman numeral."""
    if not isinstance(s, str):
        return False
    s = s.strip().upper()
    if not s:
        return False
    return bool(ROMAN_REGEX.match(s))


def run_prime_performance_probe(limit: int = 3_000_000, min_duration: float = 20.0) -> tuple[int, float, int]:
    """
    Live performance probe summing primes up to `limit`.
    Runs full passes until total elapsed time >= `min_duration` (>= 20 seconds).
    Returns (sum_of_primes, elapsed_seconds, iterations_completed).
    """
    start_time = time.perf_counter()
    iterations = 0
    prime_sum = 0

    while True:
        current_sum = 0
        for n in range(2, limit):
            is_prime = True
            for k in range(2, int(n**0.5) + 1):
                if n % k == 0:
                    is_prime = False
                    break
            if is_prime:
                current_sum += n
        prime_sum = current_sum
        iterations += 1
        elapsed = time.perf_counter() - start_time
        if elapsed >= min_duration:
            break

    return prime_sum, elapsed, iterations


class TestRomanModule(unittest.TestCase):
    """Unit test suite for roman module including performance probe."""

    def test_to_roman_standard(self):
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

    def test_from_roman_standard(self):
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
        for num in range(1, 4000):
            r = to_roman(num)
            self.assertEqual(from_roman(r), num)
            self.assertTrue(validate_roman(r))

    def test_invalid_to_roman(self):
        with self.assertRaises(ValueError):
            to_roman(0)
        with self.assertRaises(ValueError):
            to_roman(4000)
        with self.assertRaises(TypeError):
            to_roman("100")

    def test_invalid_from_roman(self):
        invalid_cases = ["", "IIII", "VV", "IC", "MMMM", "ABC", "123", "ix_v"]
        for case in invalid_cases:
            with self.assertRaises(ValueError):
                from_roman(case)
            self.assertFalse(validate_roman(case))

    def test_performance_probe(self):
        """Live performance probe: sum of primes up to 3,000,000, duration >= 20.0s."""
        print("\n[roman.py] Starting live performance probe (sum primes to 3,000,000)...")
        prime_sum, duration, passes = run_prime_performance_probe(limit=3_000_000, min_duration=20.0)
        print(f"[roman.py] Probe finished: sum={prime_sum}, elapsed={duration:.3f}s, passes={passes}")
        self.assertEqual(prime_sum, 312471072265)
        self.assertGreaterEqual(duration, 20.0)


if __name__ == "__main__":
    unittest.main()
