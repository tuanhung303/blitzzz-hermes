"""Memoized Fibonacci implementation."""

from functools import lru_cache


@lru_cache(maxsize=None)
def fib(n: int) -> int:
    """Calculate the nth Fibonacci number using memoization.

    Args:
        n: Non-negative integer index.

    Returns:
        The nth Fibonacci number.

    Raises:
        TypeError: If n is not an integer.
        ValueError: If n is negative.
    """
    if not isinstance(n, int):
        raise TypeError(f"Index must be an integer, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"Index must be non-negative, got {n}")
    if n == 0:
        return 0
    if n == 1:
        return 1
    return fib(n - 1) + fib(n - 2)
