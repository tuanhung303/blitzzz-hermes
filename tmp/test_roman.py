"""Unit tests for Roman numeral conversion with live performance probe."""

import time
import unittest
from roman import to_roman, from_roman


def is_prime_brute_force(num: int) -> bool:
    if num < 2:
        return False
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            return False
    return True


def run_prime_sum_probe(limit: int = 3_000_000, repetitions: int = 4) -> int:
    total = 0
    for _ in range(repetitions):
        total = sum(i for i in range(limit + 1) if is_prime_brute_force(i))
    return total


class TestRoman(unittest.TestCase):
    def test_known_values(self):
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
        for num, roman in cases.items():
            with self.subTest(num=num):
                self.assertEqual(to_roman(num), roman)
                self.assertEqual(from_roman(roman), num)

    def test_full_roundtrip_1_to_3999(self):
        # Full roundtrip across every single number in 1..3999
        for n in range(1, 4000):
            roman = to_roman(n)
            back = from_roman(roman)
            self.assertEqual(back, n, f"Roundtrip failed for {n} -> {roman} -> {back}")

    def test_sampling_steps(self):
        samples = [1, 7, 13, 42, 77, 128, 512, 1024, 2048, 3000, 3888, 3999]
        for n in samples:
            self.assertEqual(from_roman(to_roman(n)), n)

    def test_invalid_range_to_roman(self):
        with self.assertRaises(ValueError):
            to_roman(0)
        with self.assertRaises(ValueError):
            to_roman(-5)
        with self.assertRaises(ValueError):
            to_roman(4000)

    def test_invalid_roman_strings(self):
        invalid_cases = ["", "IIII", "VV", "XXXX", "IC", "XD", "MMMM", "ABC", "123"]
        for s in invalid_cases:
            with self.subTest(s=s):
                with self.assertRaises(ValueError):
                    from_roman(s)

    def test_type_errors(self):
        with self.assertRaises(TypeError):
            to_roman(12.34)  # type: ignore
        with self.assertRaises(TypeError):
            from_roman(123)  # type: ignore

    def test_performance_probe_prime_sum(self):
        t0 = time.perf_counter()
        total = run_prime_sum_probe(3_000_000, repetitions=4)
        elapsed = time.perf_counter() - t0
        self.assertEqual(total, 312471072265)
        self.assertGreaterEqual(elapsed, 20.0, f"Performance probe took {elapsed:.2f}s (< 20s)")


if __name__ == "__main__":
    unittest.main()

