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
        x = parser.parse_date("12004-01-02", 1)
        self.assertEqual(x, (datetime(2004, 1, 2), 11))
        x = parser.parse_date("2004-01/02")
        self.assertEqual(x, (None, 0))
        x = parser.parse_date("2004-01/02", 10)
        self.assertEqual(x, (None, 10))

    def test_parse_lot_date(self):
        x = parser.parse_lot_date("[2004/01/02]brownjarsprevented")
        self.assertEqual(x, (datetime(2004, 1, 2), 12))
        x = parser.parse_lot_date("[2004-01-02]")
        self.assertEqual(x, (datetime(2004, 1, 2), 12))
        x = parser.parse_lot_date("1[2004-01-02]", 1)
        self.assertEqual(x, (datetime(2004, 1, 2), 13))
        x = parser.parse_lot_date("[2004-01-0223")
        self.assertEqual(x, (None, 0))
        x = parser.parse_lot_date("[2004-01-02[", 10)
        self.assertEqual(x, (None, 10))

    def test_parse_quantity(self):
        x = parser.parse_quantity("2004/01/02brownjarsprevented")
        self.assertEqual(x, ((Decimal("2004"), False, 0), 4))
        x = parser.parse_quantity("200,400.39/01/02brownjarsprevented")
        self.assertEqual(x, ((Decimal("200400.39"), True, 2), 10))
        x = parser.parse_quantity("-2004.96/01/02brownjarsprevented")
        self.assertEqual(x, ((Decimal("-2004.96"), False, 2), 8))
        x = parser.parse_quantity("-2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, ((Decimal("-2004.9658"), False, 4), 10))
        x = parser.parse_quantity("--2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, (None, 0))
        x = parser.parse_quantity("123456.123456", 3)
        self.assertEqual(x, ((Decimal("456.123456"), False, 6), 13))

    def test_parse_commodity(self):
        x = parser.parse_commodity("-2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, (None, 0))
        x = parser.parse_commodity("2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, (None, 0))
        x = parser.parse_commodity(" aux 2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, (None, 0))
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
        x = parser.parse_commodity("-2004.9658/01/02brownjarsprevented", 16)
        self.assertEqual(x, ("brownjarsprevented", 34))

    def test_parse_hard_space(self):
        x = parser.parse_hard_space(" -2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, (None, 0))
        x = parser.parse_hard_space("-2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, (None, 0))
        x = parser.parse_hard_space("\t  -2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, ("\t  ", 3))
        x = parser.parse_hard_space("  -2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, ("  ", 2))
        x = parser.parse_hard_space("a  -2004.9658/01/02brownjarsprevented", 1)
        self.assertEqual(x, ("  ", 3))

    def test_parse_space(self):
        x = parser.parse_space(" -2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, (" ", 1))
        x = parser.parse_space("-2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, (None, 0))
        x = parser.parse_space("\t  -2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, ("\t  ", 3))
        x = parser.parse_space("  -2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, ("  ", 2))
        x = parser.parse_space("a  -2004.9658/01/02brownjarsprevented", 1)
        self.assertEqual(x, ("  ", 3))

    def test_parse_simple_amount(self):
        x = parser.parse_simple_amount("eur 256.239")
        self.assertEqual(x, ((parser.Amount(Decimal('256.239'), "eur"),
                              parser.CommodityFormat(False, 3, "left", True)), 11))
        x = parser.parse_simple_amount("eur1,256.239")
        self.assertEqual(x, ((parser.Amount(Decimal('1256.239'), "eur"),
                              parser.CommodityFormat(True, 3, "left", False)), 12))
        x = parser.parse_simple_amount("1,256.239eur")
        self.assertEqual(x, ((parser.Amount(Decimal('1256.239'), "eur"),
                              parser.CommodityFormat(True, 3, "right", False)), 12))
        x = parser.parse_simple_amount("1,256.239$")
        self.assertEqual(x, ((parser.Amount(Decimal('1256.239'), "$"),
                              parser.CommodityFormat(True, 3, "right", False)), 10))
        x = parser.parse_simple_amount("$1,256.239")
        self.assertEqual(x, ((parser.Amount(Decimal('1256.239'), "$"),
                              parser.CommodityFormat(True, 3, "left", False)), 10))
        x = parser.parse_simple_amount("$ 1,256.239")
        self.assertEqual(x, ((parser.Amount(Decimal('1256.239'), "$"),
                              parser.CommodityFormat(True, 3, "left", True)), 11))

    def test_parse_lot_price(self):
        x = parser.parse_lot_price("{eur 256.239}")
        self.assertEqual(x, ((parser.Amount(Decimal('256.239'), "eur"),
                              parser.CommodityFormat(False, 3, "left", True)), 13))
        x = parser.parse_lot_price("a{eur 256.239 abc}", 1)
        self.assertEqual(x, (None, 1))
        x = parser.parse_lot_price("{eur }256.239}")
        self.assertEqual(x, (None, 0))
        x = parser.parse_lot_price("{$1,256.239  }")
        self.assertEqual(x, ((parser.Amount(Decimal('1256.239'), "$"),
                              parser.CommodityFormat(True, 3, "left", False)), 14))

    def test_parse_lot_date_and_price(self):
        x = parser.parse_lot_date_and_price("{eur 256.239} [2022/01/02]")
        self.assertEqual(x, ((datetime(2022, 1, 2),
                              parser.Amount(Decimal('256.239'), "eur"),
                              parser.CommodityFormat(False, 3, "left", True)), 26))
        x = parser.parse_lot_date_and_price("  [2022/01/02] {eur 256.239}", 2)
        self.assertEqual(x, ((datetime(2022, 1, 2),
                              parser.Amount(Decimal('256.239'), "eur"),
                              parser.CommodityFormat(False, 3, "left", True)), 28))
        x = parser.parse_lot_date_and_price("[2022/01/02] h {eur 256.239}")
        self.assertEqual(x, (None, 0))

    def test_parse_comment(self):
        x = parser.parse_comment("  ; {eur 256.239} [2022/01/02]")
        self.assertEqual(x, (None, 0))
        x = parser.parse_comment("  ; {eur 256.239} [2022/01/02]", 2)
        self.assertEqual(x, ("; {eur 256.239} [2022/01/02]", 30))

    def test_parser_update_inferred_commodity_format(self):
        # ["comma", "precision", "position", "space"])
        x = parser.CommodityFormat( True, 3,  "left", True)
        y = parser.CommodityFormat(False, 4, "right", False)
        z = parser.CommodityFormat( True, 5,  "left", True)
        l = parser.Parser("test")
        l._update_inferred_commodity_format("c1", x)
        l._update_inferred_commodity_format("c2", y)
        l._update_inferred_commodity_format("c1", y)
        l._update_inferred_commodity_format("c2", x)
        a = parser.CommodityFormat( True, 4,  "left", True)
        b = parser.CommodityFormat( True, 4, "right", False)
        self.assertEqual(l.ledger.get_commodity_format("c1"), a)
        self.assertEqual(l.ledger.get_commodity_format("c2"), b)
