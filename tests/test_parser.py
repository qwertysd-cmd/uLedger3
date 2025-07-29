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
        self.assertEqual(x, (Decimal("2004"), 4, False, 0))
        x = parser.parse_quantity("200,400.39/01/02brownjarsprevented")
        self.assertEqual(x, (Decimal("200400.39"), 10, True, 2))
        x = parser.parse_quantity("-2004.96/01/02brownjarsprevented")
        self.assertEqual(x, (Decimal("-2004.96"), 8, False, 2))
        x = parser.parse_quantity("-2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, (Decimal("-2004.9658"), 10, False, 4))
        x = parser.parse_quantity("--2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, None)

    def test_parse_commodity(self):
        x = parser.parse_commodity("-2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, None)
        x = parser.parse_commodity("2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, None)
        x = parser.parse_commodity(" aux 2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, None)
        x = parser.parse_commodity("usd-2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, ("usd", 3))
        x = parser.parse_commodity("'usd'-2004.9658/01")
        self.assertEqual(x, ("usd", 5))
        x = parser.parse_commodity("'usd-'2004.9658/01")
        self.assertEqual(x, ("usd-", 6))
        x = parser.parse_commodity("'$'2004.9658/01")
        self.assertEqual(x, ("$", 3))
        x = parser.parse_commodity("$2004.9658/01")
        self.assertEqual(x, ("$", 1))
        x = parser.parse_commodity("\"$20 04.9658/01\" brown jars prevented")
        self.assertEqual(x, ("$20 04.9658/01", 16))

    def test_parse_hard_space(self):
        x = parser.parse_hard_space(" -2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, None)
        x = parser.parse_hard_space("-2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, None)
        x = parser.parse_hard_space("\t  -2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, ("\t  ", 3))
        x = parser.parse_hard_space("  -2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, ("  ", 2))

    def test_parse_space(self):
        x = parser.parse_space(" -2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, (" ", 1))
        x = parser.parse_space("-2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, None)
        x = parser.parse_space("\t  -2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, ("\t  ", 3))
        x = parser.parse_space("  -2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, ("  ", 2))
