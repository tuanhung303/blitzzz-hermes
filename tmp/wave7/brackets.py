"""Bracket validation and analyzer module with unit tests and performance probe."""

import math
import time
import unittest

OPEN_TO_CLOSE = {"(": ")", "[": "]", "{": "}"}
CLOSE_TO_OPEN = {")": "(", "]": "[", "}": "{"}


def is_balanced(s: str) -> bool:
    """Check if all brackets in string s are properly closed and nested."""
    stack = []
    for ch in s:
        if ch in OPEN_TO_CLOSE:
            stack.append(ch)
        elif ch in CLOSE_TO_OPEN:
            if not stack or stack[-1] != CLOSE_TO_OPEN[ch]:
                return False
            stack.pop()
    return len(stack) == 0


def clean_brackets(s: str) -> str:
    """Filter string to only include bracket characters."""
    valid = set("()[]{}")
    return "".join(ch for ch in s if ch in valid)


def max_nesting_depth(s: str) -> int:
    """Return the maximum bracket nesting depth, or raise ValueError if unbalanced."""
    stack = []
    max_depth = 0
    for ch in s:
        if ch in OPEN_TO_CLOSE:
            stack.append(ch)
            if len(stack) > max_depth:
                max_depth = len(stack)
        elif ch in CLOSE_TO_OPEN:
            if not stack or stack[-1] != CLOSE_TO_OPEN[ch]:
                raise ValueError("String has unbalanced brackets")
            stack.pop()
    if stack:
        raise ValueError("String has unbalanced brackets")
    return max_depth


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
        "module": "brackets",
        "prime_sum": prime_sum,
        "limit": limit,
        "iterations": iterations,
        "elapsed_seconds": elapsed,
    }


class TestBrackets(unittest.TestCase):
    def test_balanced_strings(self):
        self.assertTrue(is_balanced(""))
        self.assertTrue(is_balanced("()"))
        self.assertTrue(is_balanced("()[]{}"))
        self.assertTrue(is_balanced("{[()]}"))
        self.assertTrue(is_balanced("def fn(x): return [x * 2 for x in {1, 2}]"))

    def test_unbalanced_strings(self):
        self.assertFalse(is_balanced("("))
        self.assertFalse(is_balanced(")"))
        self.assertFalse(is_balanced("(]"))
        self.assertFalse(is_balanced("([)]"))
        self.assertFalse(is_balanced("{{{{}"))

    def test_clean_brackets(self):
        self.assertEqual(clean_brackets("a(b)c[d]{e}"), "()[]{}")
        self.assertEqual(clean_brackets("hello world"), "")

    def test_max_nesting_depth(self):
        self.assertEqual(max_nesting_depth(""), 0)
        self.assertEqual(max_nesting_depth("()"), 1)
        self.assertEqual(max_nesting_depth("((()))"), 3)
        self.assertEqual(max_nesting_depth("{[()]}"), 3)
        self.assertEqual(max_nesting_depth("()[{}]"), 2)
        with self.assertRaises(ValueError):
            max_nesting_depth("(()")

    def test_performance_probe(self):
        result = run_prime_performance_probe(limit=3_000_000, min_seconds=20.0)
        self.assertEqual(result["prime_sum"], 312471072265)
        self.assertGreaterEqual(result["elapsed_seconds"], 20.0)
        print(f"\n[PROBE brackets.py] Elapsed: {result['elapsed_seconds']:.3f}s, Iterations: {result['iterations']}, Sum: {result['prime_sum']}")


if __name__ == "__main__":
    unittest.main()
