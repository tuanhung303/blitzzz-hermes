"""Fibonacci numbers computation module with unittest suite and performance probe."""

import time
import unittest


def fib_iterative(n: int) -> int:
    """Compute the n-th Fibonacci number iteratively."""
    if not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def fib_memo(n: int, memo: dict = None) -> int:
    """Compute the n-th Fibonacci number with recursion and memoization."""
    if not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    if memo is None:
        memo = {0: 0, 1: 1}
    if n in memo:
        return memo[n]
    memo[n] = fib_memo(n - 1, memo) + fib_memo(n - 2, memo)
    return memo[n]


def fib_matrix(n: int) -> int:
    """Compute the n-th Fibonacci number in O(log n) using matrix exponentiation."""
    if not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n

    def multiply_2x2(A, B):
        return (
            A[0] * B[0] + A[1] * B[2],
            A[0] * B[1] + A[1] * B[3],
            A[2] * B[0] + A[3] * B[2],
            A[2] * B[1] + A[3] * B[3],
        )

    def power_2x2(M, p):
        res = (1, 0, 0, 1)  # Identity matrix
        base = M
        while p > 0:
            if p % 2 == 1:
                res = multiply_2x2(res, base)
            base = multiply_2x2(base, base)
            p //= 2
        return res

    T = (1, 1, 1, 0)
    res = power_2x2(T, n - 1)
    return res[0]


def fib_sequence(limit: int) -> list[int]:
    """Generate Fibonacci sequence up to count `limit`."""
    if limit <= 0:
        return []
    seq = []
    a, b = 0, 1
    for _ in range(limit):
        seq.append(a)
        a, b = b, a + b
    return seq


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


class TestFibModule(unittest.TestCase):
    """Unit test suite for fib module including performance probe."""

    def test_fib_base_cases(self):
        self.assertEqual(fib_iterative(0), 0)
        self.assertEqual(fib_iterative(1), 1)
        self.assertEqual(fib_memo(0), 0)
        self.assertEqual(fib_memo(1), 1)
        self.assertEqual(fib_matrix(0), 0)
        self.assertEqual(fib_matrix(1), 1)

    def test_fib_consistency(self):
        expected = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]
        for i, val in enumerate(expected):
            self.assertEqual(fib_iterative(i), val)
            self.assertEqual(fib_memo(i), val)
            self.assertEqual(fib_matrix(i), val)

    def test_fib_sequence(self):
        self.assertEqual(fib_sequence(0), [])
        self.assertEqual(fib_sequence(5), [0, 1, 1, 2, 3])
        self.assertEqual(fib_sequence(10), [0, 1, 1, 2, 3, 5, 8, 13, 21, 34])

    def test_fib_large_number(self):
        self.assertEqual(fib_iterative(50), 12586269025)
        self.assertEqual(fib_matrix(50), 12586269025)
        self.assertEqual(fib_memo(50), 12586269025)

    def test_fib_invalid_input(self):
        with self.assertRaises(TypeError):
            fib_iterative("10")
        with self.assertRaises(ValueError):
            fib_iterative(-5)
        with self.assertRaises(TypeError):
            fib_memo(3.14)
        with self.assertRaises(ValueError):
            fib_memo(-1)
        with self.assertRaises(TypeError):
            fib_matrix(None)
        with self.assertRaises(ValueError):
            fib_matrix(-10)

    def test_performance_probe(self):
        """Live performance probe: sum of primes up to 3,000,000, duration >= 20.0s."""
        print("\n[fib.py] Starting live performance probe (sum primes to 3,000,000)...")
        prime_sum, duration, passes = run_prime_performance_probe(limit=3_000_000, min_duration=20.0)
        print(f"[fib.py] Probe finished: sum={prime_sum}, elapsed={duration:.3f}s, passes={passes}")
        self.assertEqual(prime_sum, 312471072265)
        self.assertGreaterEqual(duration, 20.0)


if __name__ == "__main__":
    unittest.main()
