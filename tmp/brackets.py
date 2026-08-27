"""Balanced bracket validator."""


def is_balanced(text: str) -> bool:
    """Check if all brackets in the given string are properly balanced and nested.

    Supported bracket pairs: (), [], {}

    Args:
        text: Input string containing brackets and optional other characters.

    Returns:
        True if all brackets are properly paired and closed, False otherwise.

    Raises:
        TypeError: If text is not a string.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected string input, got {type(text).__name__}")

    matching = {")": "(", "]": "[", "}": "{"}
    opening = set(matching.values())
    stack = []

    for char in text:
        if char in opening:
            stack.append(char)
        elif char in matching:
            if not stack or stack[-1] != matching[char]:
                return False
            stack.pop()

    return len(stack) == 0
