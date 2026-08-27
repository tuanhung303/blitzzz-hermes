"""
Bracket balancing and validation module with comprehensive unit tests
and a live performance probe.
"""

import time
import unittest


def is_balanced(s: str) -> bool:
    """Check if all brackets in the string are properly balanced and nested."""
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    matching = {")": "(", "}": "{", "]": "["}
    stack = []
    for char in s:
        if char in "({[":
            stack.append(char)
        elif char in ")}]":
            if not stack or stack[-1] != matching[char]:
                return False
            stack.pop()
    return len(stack) == 0


def min_removals_to_balance(s: str) -> int:
    """Return the minimum number of bracket characters to remove to make the string valid."""
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    stack = []
    removals = 0
    for char in s:
        if char == "(":
            stack.append(char)
        elif char == ")":
            if stack:
                stack.pop()
            else:
                removals += 1
    return removals + len(stack)


def generate_parentheses(n: int) -> list[str]:
    """Generate all combinations of well-formed parentheses pairs."""
    if not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n cannot be negative")
    if n == 0:
        return [""]

    result = []

    def backtrack(current: str, open_count: int, close_count: int):
        if len(current) == 2 * n:
            result.append(current)
            return
        if open_count < n:
            backtrack(current + "(", open_count + 1, close_count)
        if close_count < open_count:
            backtrack(current + ")", open_count, close_count + 1)

    backtrack("", 0, 0)
    return result


def longest_valid_parentheses(s: str) -> int:
    """Calculate the length of the longest valid (well-formed) parentheses substring."""
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    stack = [-1]
    max_len = 0
    for i, char in enumerate(s):
        if char == "(":
            stack.append(i)
        elif char == ")":
            stack.pop()
            if not stack:
                stack.append(i)
            else:
                max_len = max(max_len, i - stack[-1])
    return max_len


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


class TestBrackets(unittest.TestCase):
    """Test suite for Bracket operations and performance probe."""

    def test_is_balanced_valid(self):
        self.assertTrue(is_balanced(""))
        self.assertTrue(is_balanced("()"))
        self.assertTrue(is_balanced("()[]{}"))
        self.assertTrue(is_balanced("{[()]}"))
        self.assertTrue(is_balanced("a(b[c]d){e}f"))

    def test_is_balanced_invalid(self):
        self.assertFalse(is_balanced("("))
        self.assertFalse(is_balanced(")"))
        self.assertFalse(is_balanced("(]"))
        self.assertFalse(is_balanced("([)]"))
        self.assertFalse(is_balanced("{[(])}"))

    def test_min_removals(self):
        self.assertEqual(min_removals_to_balance(""), 0)
        self.assertEqual(min_removals_to_balance("()"), 0)
        self.assertEqual(min_removals_to_balance("((("), 3)
        self.assertEqual(min_removals_to_balance("())"), 1)
        self.assertEqual(min_removals_to_balance(")(("), 3)

    def test_generate_parentheses(self):
        self.assertEqual(generate_parentheses(0), [""])
        self.assertEqual(generate_parentheses(1), ["()"])
        self.assertEqual(sorted(generate_parentheses(2)), ["(())", "()()"])
        self.assertEqual(
            sorted(generate_parentheses(3)),
            sorted(["((()))", "(()())", "(())()", "()(())", "()()()"])
        )

    def test_longest_valid_parentheses(self):
        self.assertEqual(longest_valid_parentheses(""), 0)
        self.assertEqual(longest_valid_parentheses("(()"), 2)
        self.assertEqual(longest_valid_parentheses(")()())"), 4)
        self.assertEqual(longest_valid_parentheses("((()))"), 6)

    def test_type_errors(self):
        with self.assertRaises(TypeError):
            is_balanced(123)  # type: ignore
        with self.assertRaises(TypeError):
            min_removals_to_balance(None)  # type: ignore
        with self.assertRaises(TypeError):
            generate_parentheses("two")  # type: ignore

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
            f"\n[brackets.py PROBE] Sum of primes up to {target_limit:,}: {prime_sum} "
            f"| Iterations: {iterations} | Time: {elapsed:.2f}s"
        )
        self.assertEqual(prime_sum, 312471072265)
        self.assertGreaterEqual(elapsed, min_seconds)


if __name__ == "__main__":
    unittest.main()
