"""Caesar cipher and ROT13 encoding/decoding utilities."""


def encode(text: str, shift: int = 13) -> str:
    """Encode text using a Caesar cipher with the given shift (default: ROT13).

    Args:
        text: Input string to encode.
        shift: Number of positions to rotate (default is 13).

    Returns:
        Encoded string with case preserved for alphabetic characters.

    Raises:
        TypeError: If text is not a string or shift is not an integer.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected text to be a string, got {type(text).__name__}")
    if not isinstance(shift, int):
        raise TypeError(f"Expected shift to be an integer, got {type(shift).__name__}")

    shift = shift % 26
    result = []

    for char in text:
        if "a" <= char <= "z":
            shifted = chr((ord(char) - ord("a") + shift) % 26 + ord("a"))
            result.append(shifted)
        elif "A" <= char <= "Z":
            shifted = chr((ord(char) - ord("A") + shift) % 26 + ord("A"))
            result.append(shifted)
        else:
            result.append(char)

    return "".join(result)


def decode(text: str, shift: int = 13) -> str:
    """Decode text previously encoded with Caesar cipher with the given shift.

    Args:
        text: Input string to decode.
        shift: Number of positions originally shifted (default is 13).

    Returns:
        Decoded string.

    Raises:
        TypeError: If text is not a string or shift is not an integer.
    """
    if not isinstance(shift, int):
        raise TypeError(f"Expected shift to be an integer, got {type(shift).__name__}")
    return encode(text, -shift)


def rot13(text: str) -> str:
    """Convenience function for ROT13 transform (involutive).

    Args:
        text: Input string.

    Returns:
        ROT13 encoded/decoded string.
    """
    return encode(text, 13)
