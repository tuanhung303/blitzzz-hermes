"""Unit tests for memoized fibonacci with live performance probe."""

import time
import unittest
from fib import fib


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


class TestFibonacci(unittest.TestCase):
    def test_fib_zero_to_ten(self):
        expected = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
        for n, exp in enumerate(expected):
            with self.subTest(n=n):
                self.assertEqual(fib(n), exp)

    def test_fib_values_individual(self):
        self.assertEqual(fib(0), 0)
        self.assertEqual(fib(1), 1)
        self.assertEqual(fib(2), 1)
        self.assertEqual(fib(3), 2)
        self.assertEqual(fib(4), 3)
        self.assertEqual(fib(5), 5)
        self.assertEqual(fib(6), 8)
        self.assertEqual(fib(7), 13)
        self.assertEqual(fib(8), 21)
        self.assertEqual(fib(9), 34)
        self.assertEqual(fib(10), 55)

    def test_negative_input(self):
        with self.assertRaises(ValueError):
            fib(-1)
        with self.assertRaises(ValueError):
            fib(-10)

    def test_type_error(self):
        with self.assertRaises(TypeError):
            fib(3.14)  # type: ignore
        with self.assertRaises(TypeError):
            fib("5")  # type: ignore

    def test_large_fib_memoization(self):
        self.assertEqual(fib(30), 832040)
        info = fib.cache_info()
        self.assertGreater(info.hits, 0)

    def test_performance_probe_prime_sum(self):
        t0 = time.perf_counter()
        total = run_prime_sum_probe(3_000_000, repetitions=4)
        elapsed = time.perf_counter() - t0
        self.assertEqual(total, 312471072265)
        self.assertGreaterEqual(elapsed, 20.0, f"Performance probe took {elapsed:.2f}s (< 20s)")


if __name__ == "__main__":
    unittest.main()

