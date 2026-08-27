"""
Fibonacci module providing multiple implementations for generating Fibonacci numbers,
along with a comprehensive unittest suite and a live performance probe.
"""

import time
import unittest


def fib_iterative(n: int) -> int:
    """Compute the n-th Fibonacci number iteratively (0-indexed: fib(0)=0, fib(1)=1)."""
    if not isinstance(n, int):
        raise TypeError("Index n must be an integer")
    if n < 0:
        raise ValueError("Index n cannot be negative")
    if n in (0, 1):
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def fib_matrix(n: int) -> int:
    """Compute the n-th Fibonacci number using fast matrix exponentiation in O(log n)."""
    if not isinstance(n, int):
        raise TypeError("Index n must be an integer")
    if n < 0:
        raise ValueError("Index n cannot be negative")
    if n in (0, 1):
        return n

    def multiply_2x2(A, B):
        return [
            [A[0][0] * B[0][0] + A[0][1] * B[1][0], A[0][0] * B[0][1] + A[0][1] * B[1][1]],
            [A[1][0] * B[0][0] + A[1][1] * B[1][0], A[1][0] * B[0][1] + A[1][1] * B[1][1]]
        ]

    def power_2x2(M, p):
        result = [[1, 0], [0, 1]]
        base = M
        while p > 0:
            if p % 2 == 1:
                result = multiply_2x2(result, base)
            base = multiply_2x2(base, base)
            p //= 2
        return result

    T = [[1, 1], [1, 0]]
    result_matrix = power_2x2(T, n - 1)
    return result_matrix[0][0]


def fib_sequence(count: int) -> list[int]:
    """Generate the first `count` Fibonacci numbers."""
    if count < 0:
        raise ValueError("Count cannot be negative")
    if count == 0:
        return []
    if count == 1:
        return [0]
    seq = [0, 1]
    while len(seq) < count:
        seq.append(seq[-1] + seq[-2])
    return seq


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


class TestFibonacci(unittest.TestCase):
    """Test suite for Fibonacci functions and performance verification."""

    def test_fib_base_cases(self):
        self.assertEqual(fib_iterative(0), 0)
        self.assertEqual(fib_iterative(1), 1)
        self.assertEqual(fib_matrix(0), 0)
        self.assertEqual(fib_matrix(1), 1)

    def test_fib_values(self):
        expected = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]
        for i, val in enumerate(expected):
            self.assertEqual(fib_iterative(i), val)
            self.assertEqual(fib_matrix(i), val)

    def test_fib_sequence(self):
        self.assertEqual(fib_sequence(0), [])
        self.assertEqual(fib_sequence(1), [0])
        self.assertEqual(fib_sequence(7), [0, 1, 1, 2, 3, 5, 8])

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            fib_iterative(-1)
        with self.assertRaises(ValueError):
            fib_matrix(-5)
        with self.assertRaises(TypeError):
            fib_iterative("5")  # type: ignore

    def test_large_fib(self):
        self.assertEqual(fib_iterative(50), fib_matrix(50))
        self.assertEqual(fib_matrix(50), 12586269025)

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
            f"\n[fib.py PROBE] Sum of primes up to {target_limit:,}: {prime_sum} "
            f"| Iterations: {iterations} | Time: {elapsed:.2f}s"
        )
        self.assertEqual(prime_sum, 312471072265)
        self.assertGreaterEqual(elapsed, min_seconds)


if __name__ == "__main__":
    unittest.main()
