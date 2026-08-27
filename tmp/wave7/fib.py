"""Fibonacci calculation module with unit tests and performance probe."""

import math
import time
import unittest


def fibonacci(n: int) -> int:
    """Return the nth Fibonacci number (0-indexed)."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def fibonacci_sequence(count: int) -> list[int]:
    """Return the first `count` Fibonacci numbers."""
    if count < 0:
        raise ValueError("count must be non-negative")
    if count == 0:
        return []
    seq = [0]
    if count == 1:
        return seq
    seq.append(1)
    a, b = 0, 1
    for _ in range(2, count):
        a, b = b, a + b
        seq.append(b)
    return seq


def is_perfect_square(x: int) -> bool:
    if x < 0:
        return False
    s = math.isqrt(x)
    return s * s == x


def is_fibonacci(n: int) -> bool:
    """Check if n is a Fibonacci number using 5n^2 +/- 4 property."""
    if n < 0:
        return False
    return is_perfect_square(5 * n * n + 4) or is_perfect_square(5 * n * n - 4)


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
        "module": "fib",
        "prime_sum": prime_sum,
        "limit": limit,
        "iterations": iterations,
        "elapsed_seconds": elapsed,
    }


class TestFibonacci(unittest.TestCase):
    def test_base_cases(self):
        self.assertEqual(fibonacci(0), 0)
        self.assertEqual(fibonacci(1), 1)
        self.assertEqual(fibonacci(2), 1)
        self.assertEqual(fibonacci(10), 55)
        self.assertEqual(fibonacci(20), 6765)

    def test_negative_input(self):
        with self.assertRaises(ValueError):
            fibonacci(-1)
        with self.assertRaises(ValueError):
            fibonacci_sequence(-5)

    def test_sequence_generation(self):
        self.assertEqual(fibonacci_sequence(0), [])
        self.assertEqual(fibonacci_sequence(1), [0])
        self.assertEqual(fibonacci_sequence(7), [0, 1, 1, 2, 3, 5, 8])

    def test_is_fibonacci(self):
        self.assertTrue(is_fibonacci(0))
        self.assertTrue(is_fibonacci(1))
        self.assertTrue(is_fibonacci(2))
        self.assertTrue(is_fibonacci(3))
        self.assertTrue(is_fibonacci(5))
        self.assertTrue(is_fibonacci(8))
        self.assertTrue(is_fibonacci(13))
        self.assertFalse(is_fibonacci(4))
        self.assertFalse(is_fibonacci(6))
        self.assertFalse(is_fibonacci(14))
        self.assertFalse(is_fibonacci(-3))

    def test_performance_probe(self):
        result = run_prime_performance_probe(limit=3_000_000, min_seconds=20.0)
        self.assertEqual(result["prime_sum"], 312471072265)
        self.assertGreaterEqual(result["elapsed_seconds"], 20.0)
        print(f"\n[PROBE fib.py] Elapsed: {result['elapsed_seconds']:.3f}s, Iterations: {result['iterations']}, Sum: {result['prime_sum']}")


if __name__ == "__main__":
    unittest.main()
