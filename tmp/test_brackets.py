"""Unit tests for balanced bracket validator."""

import time
import unittest
from brackets import is_balanced


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


class TestBrackets(unittest.TestCase):
    def test_empty_string(self):
        self.assertTrue(is_balanced(""))

    def test_simple_balanced(self):
        cases = [
            "()",
            "[]",
            "{}",
            "()[]{}",
            "({[]})",
            "((()))",
            "[[[[]]]]",
            "{{{}}}",
            "{[()]}",
        ]
        for s in cases:
            with self.subTest(s=s):
                self.assertTrue(is_balanced(s))

    def test_simple_unbalanced(self):
        cases = [
            "(",
            ")",
            "[",
            "]",
            "{",
            "}",
            "(]",
            "([)]",
            "}{",
            "(()",
            "())",
            "({[}])",
            "{[(])}",
        ]
        for s in cases:
            with self.subTest(s=s):
                self.assertFalse(is_balanced(s))

    def test_with_non_bracket_characters(self):
        self.assertTrue(is_balanced("def foo(x: list[int]) -> dict[str, int]: return {k: v}"))
        self.assertTrue(is_balanced("1 + (2 * [3 - 4] / {5 + 6})"))
        self.assertFalse(is_balanced("def foo(x: list[int): pass"))
        self.assertFalse(is_balanced("1 + (2 * [3 - 4] / {5 + 6)"))

    def test_deep_nesting_balanced(self):
        depth = 5000
        nested = ("(" * depth) + (")" * depth)
        self.assertTrue(is_balanced(nested))

        mixed_deep = ("([{" * 1000) + ("}])" * 1000)
        self.assertTrue(is_balanced(mixed_deep))

    def test_deep_nesting_unbalanced(self):
        depth = 5000
        # Missing one closing bracket
        unbalanced_missing = ("(" * depth) + (")" * (depth - 1))
        self.assertFalse(is_balanced(unbalanced_missing))

        # Mismatch in the middle
        deep_mismatch = ("(" * depth) + "]" + (")" * depth)
        self.assertFalse(is_balanced(deep_mismatch))

    def test_type_error(self):
        with self.assertRaises(TypeError):
            is_balanced(None)  # type: ignore
        with self.assertRaises(TypeError):
            is_balanced(12345)  # type: ignore
        with self.assertRaises(TypeError):
            is_balanced(["()"])  # type: ignore

    def test_performance_probe_prime_sum(self):
        t0 = time.perf_counter()
        total = run_prime_sum_probe(3_000_000, repetitions=4)
        elapsed = time.perf_counter() - t0
        self.assertEqual(total, 312471072265)
        self.assertGreaterEqual(elapsed, 20.0, f"Performance probe took {elapsed:.2f}s (< 20s)")


if __name__ == "__main__":
    unittest.main()
