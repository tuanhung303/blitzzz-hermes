import unittest
from catalan import catalan_dp, catalan_binomial

KNOWN_CATALAN_12 = [
    1,       # C_0
    1,       # C_1
    2,       # C_2
    5,       # C_3
    14,      # C_4
    42,      # C_5
    132,     # C_6
    429,     # C_7
    1430,    # C_8
    4862,    # C_9
    16796,   # C_10
    58786,   # C_11
]


class TestCatalan(unittest.TestCase):
    def test_first_12_values_agreement(self):
        for n in range(12):
            dp_val = catalan_dp(n)
            bin_val = catalan_binomial(n)
            expected = KNOWN_CATALAN_12[n]
            self.assertEqual(dp_val, bin_val, f"Mismatch between DP and Binomial at n={n}")
            self.assertEqual(dp_val, expected, f"DP does not match known value at n={n}")
            self.assertEqual(bin_val, expected, f"Binomial does not match known value at n={n}")

    def test_input_validation(self):
        for fn in (catalan_dp, catalan_binomial):
            with self.assertRaises(TypeError):
                fn(3.5)  # type: ignore
            with self.assertRaises(TypeError):
                fn("5")  # type: ignore
            with self.assertRaises(TypeError):
                fn(False)  # type: ignore
            with self.assertRaises(ValueError):
                fn(-1)
            with self.assertRaises(ValueError):
                fn(-10)


if __name__ == "__main__":
    unittest.main()
