# Benchmark Worker Modules

A lightweight collection of four standalone algorithmic utility modules.

## Modules & Usage

### 1. Fibonacci (`fib.py`)
Computes the n-th Fibonacci number using LRU-cache memoization.

```python
from fib import fib

# Compute Fibonacci values
print([fib(n) for n in range(11)])
# Output: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
```

### 2. Roman Numerals (`roman.py`)
Bidirectional Roman numeral conversion supporting integers 1..3999.

```python
from roman import to_roman, from_roman

# Encode and decode Roman numerals
roman_str = to_roman(2026)
print(roman_str)             # 'MMXXVI'
print(from_roman(roman_str)) # 2026
```

### 3. Balanced Brackets (`brackets.py`)
Validates balanced parenthesis, bracket, and brace pairs (`()`, `[]`, `{}`) across arbitrary depth.

```python
from brackets import is_balanced

# Validate bracket nesting
print(is_balanced("def process(items: list[dict[str, int]]) -> None: pass")) # True
print(is_balanced("([)]"))                                                  # False
```

### 4. Caesar Cipher & ROT13 (`caesar.py`)
Encodes and decodes text using Caesar rotation with case and non-ASCII character preservation.

```python
from caesar import rot13, encode, decode

# ROT13 transform
cipher = rot13("Hello, World!")
print(cipher)        # 'Uryyb, Jbeyq!'
print(rot13(cipher)) # 'Hello, World!'
```

## Running Tests

Run the full unit test suite across all modules:

```bash
python3 -m unittest test_fib.py test_roman.py test_brackets.py test_caesar.py -v
```
