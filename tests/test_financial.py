import unittest

import financial


class TestFinancial(unittest.TestCase):
    def test_pv(self):
        result = financial.pv(0.159, 9, -380)
        self.assertEqual(result, 1756.5991035086788)

        result = financial.pv(0.05 / 12, 10 * 12, -100, 15692.93)
        self.assertEqual(result, -100.00067131625819)

    def test_pv_zero_rate(self):
        result = financial.pv(0, 9, 380)
        self.assertEqual(result, -3420)

    def test_rl(self):
        result = financial.rl(10)
        self.assertEqual(result, 10)

        result = financial.rl(10, 50)
        self.assertEqual(result, 50)

        result = financial.rl(10.2, 50)
        self.assertEqual(result, 50)

        result = financial.rl(1230, 50)
        self.assertEqual(result, 1250)

    def test_rl_one(self):
        result = financial.rl(10)
        self.assertEqual(result, 10)

        result = financial.rl(10, 1)
        self.assertEqual(result, 10)
