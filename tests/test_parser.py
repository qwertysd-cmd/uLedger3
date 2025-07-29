import unittest
from datetime import datetime
from decimal import Decimal

import uledger3.parser as parser

class TestParser(unittest.TestCase):

    def test_ledger(self):
        p = parser.Ledger("test")

    def test_parse_date(self):
        x = parser.parse_date("2004/01/02brownjarsprevented")
        self.assertEqual(x, (datetime(2004, 1, 2), 10))
        x = parser.parse_date("2004-01-02")
        self.assertEqual(x, (datetime(2004, 1, 2), 10))
        x = parser.parse_date("2004-01/02")
        self.assertEqual(x, None)

    def test_parse_quantity(self):
        x = parser.parse_quantity("2004/01/02brownjarsprevented")
        self.assertEqual(x, (Decimal("2004"), False, 0, 4))
        x = parser.parse_quantity("200,400.39/01/02brownjarsprevented")
        self.assertEqual(x, (Decimal("200400.39"), True, 2, 10))
        x = parser.parse_quantity("-2004.96/01/02brownjarsprevented")
        self.assertEqual(x, (Decimal("-2004.96"), False, 2, 8))
        x = parser.parse_quantity("-2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, (Decimal("-2004.9658"), False, 4, 10))
