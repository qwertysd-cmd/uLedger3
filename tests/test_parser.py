import unittest
from datetime import datetime
from decimal import Decimal

import uledger3.parser as parser

class TestParser(unittest.TestCase):

    def test_journal(self):
        p = parser.Journal("test")

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
        self.assertEqual(l.journal.get_commodity_format("c1"), a)
        self.assertEqual(l.journal.get_commodity_format("c2"), b)

    def test_parser_parse_amount(self):
        l = parser.Parser("test")
        x = l._parse_amount("eur 256.239")
        self.assertEqual(x, (parser.Amount(Decimal('256.239'), "eur"), 11))
        x = l._parse_amount("$256.239")
        self.assertEqual(x, (parser.Amount(Decimal('256.239'), "$"), 8))
        with self.assertRaises(parser.ParseError):
            x = l._parse_amount("$256.239 @ abc")
        x = l._parse_amount("$256.239 @ EUR 23")
        self.assertEqual(x,
                         (parser.Amount(Decimal('256.239'), "$",
                                        parser.Amount(Decimal('23'), "EUR")),
                          17))
        x = l._parse_amount("$256.239 [2022/01/17] {EUR 36.00} ; abc")
        self.assertEqual(x,
                         (parser.Amount(Decimal('256.239'),
                                        parser.Lot("$",
                                                   datetime(2022, 1, 17),
                                                   parser.Amount(Decimal('36'),
                                                                 "EUR"))),
                          33))

    def test_parse_account_name(self):
        x = parser.parse_account_name("abc:def:g h i:jk l  abc")
        self.assertEqual(x, ("abc:def:g h i:jk l", 18))
        x = parser.parse_account_name("-2004.9658/01/02brownjarsprevented")
        self.assertEqual(x, ("-2004.9658/01/02brownjarsprevented", 34))
        x = parser.parse_account_name("-2004.9658/01/02brownjarsprevented  abc")
        self.assertEqual(x, ("-2004.9658/01/02brownjarsprevented", 34))

    def test_parse_keyword(self):
        x = parser.parse_keyword("tag", "  tag abc", 2)
        self.assertEqual(x, ("tag", 5))
        x = parser.parse_keyword("tag", "tag abc", 2)
        self.assertEqual(x, (None, 2))
        x = parser.parse_keyword("tag", "tag abc")
        self.assertEqual(x, ("tag", 3))

    def test_parser_finish_parse_commodity_decl(self):
        l = parser.Parser("test")
        with self.assertRaises(parser.ParseError):
            x = l._finish_parse_commodity_decl("commodity test1")
        x = l._finish_parse_commodity_decl("commodity 'test1'")
        self.assertEqual(x.commodity, "test1")

    def test_parser_finish_parse_account_decl(self):
        l = parser.Parser("test")
        x = l._finish_parse_account_decl("account test1")
        self.assertEqual(x.account, "test1")
        with self.assertRaises(parser.ParseError):
            x = l._finish_parse_account_decl("account test1:test 2  test3")
        x = l._finish_parse_account_decl("account test1:test 2 test3")
        self.assertEqual(x.account, "test1:test 2 test3")

    def test_parser_finish_parse_price_decl(self):
        l = parser.Parser("test")
        x = l._finish_parse_price_decl("P 2022/01/02 abc $6")
        self.assertEqual(x.commodity, "abc")
        self.assertEqual(x.date, datetime(2022, 1, 2))
        self.assertEqual(x.price, parser.Amount(Decimal("6"), "$"))
        x = l._finish_parse_price_decl("P 2022/01/02 abc $$6")
        self.assertEqual(x.price, parser.Amount(Decimal("6"), "$$"))
        with self.assertRaises(parser.ParseError):
            x = l._finish_parse_price_decl("P 2022/01/02 abc $ $6")

    def test_parser_finish_parse_transaction_start(self):
        l = parser.Parser("test")
        x = l._finish_parse_transaction_start("2022/01/02 * abc123 ghi ")
        self.assertEqual(x.date, datetime(2022, 1, 2))
        self.assertEqual(x.status, "*")
        self.assertEqual(x.payee, "abc123 ghi")
        x = l._finish_parse_transaction_start("2022/01/02  abc123 ghi ")
        self.assertEqual(x.date, datetime(2022, 1, 2))
        self.assertEqual(x.status, None)
        self.assertEqual(x.payee, "abc123 ghi")
        x = l._finish_parse_transaction_start("2022/01/02   ")
        self.assertEqual(x.date, datetime(2022, 1, 2))
        self.assertEqual(x.status, None)
        self.assertEqual(x.payee, None)
        x = l._finish_parse_transaction_start("2022/01/02  ! ")
        self.assertEqual(x.date, datetime(2022, 1, 2))
        self.assertEqual(x.status, "!")
        self.assertEqual(x.payee, None)

    def test_parser_finish_parse_commodity_decl_contents(self):
        l = parser.Parser("test")
        x = l._finish_parse_commodity_decl_contents("  format $123.45")
        # ["comma", "precision", "position", "space"])
        b = parser.CommodityFormat(False, 2, "left", False)
        self.assertEqual(x, b)
        x = l._finish_parse_commodity_decl_contents("  abc def  ghi ")
        self.assertEqual(x, "abc def  ghi")
        with self.assertRaises(parser.ParseError):
            x = l._finish_parse_commodity_decl_contents("  format$123.45")
        with self.assertRaises(parser.ParseError):
            x = l._finish_parse_commodity_decl_contents("  format 123.45")

    def test_parser_finish_parse_transaction_contents(self):
        l = parser.Parser("test")
        x = l._finish_parse_transaction_contents("  format $123.45")
        self.assertEqual(x.account, "format $123.45")
        self.assertEqual(x.amount, None)
        with self.assertRaises(parser.ParseError):
            x = l._finish_parse_transaction_contents("  format  $123.45 l")
        x = l._finish_parse_transaction_contents("  format  $123.45")
        self.assertEqual(x.account, "format")
        self.assertEqual(x.amount, parser.Amount(Decimal("123.45"), "$"))
        with self.assertRaises(parser.ParseError):
            x = l._finish_parse_transaction_contents("  format  123.45 EUR k")
        x = l._finish_parse_transaction_contents("  format  123.45 EUR ; k")
        self.assertEqual(x.account, "format")
        self.assertEqual(x.amount, parser.Amount(Decimal("123.45"), "EUR"))

    def test_parser_parse_line(self):
        l = parser.Parser("test", pedantic=True)
        with self.assertRaises(parser.ParseError):
            l.parse_line(" hello")
        l.parse_line("2021/11/03 payee")
        with self.assertRaises(parser.ParseError):
            l.parse_line("  2021/11/03 acc1")
        with self.assertRaises(parser.ParseError):
            l.parse_line("  2021/11/03 acc2  EUR 15")
        l.parse_line("commodity EUR")
        l.parse_line("2021/11/03 payee")
        with self.assertRaises(parser.ParseError):
            l.parse_line("  2021/11/03 acc1")
        with self.assertRaises(parser.ParseError):
            l.parse_line("  2021/11/03 acc2  EUR 15")
        l.parse_line("account 2021/11/03 acc1")
        l.parse_line("2021/11/03 payee")
        l.parse_line("  2021/11/03 acc1")
        with self.assertRaises(parser.ParseError):
            l.parse_line("  2021/11/03 acc2  EUR 15")
        l.parse_line("account 2021/11/03 acc2")
        l.parse_line("2021/11/03 payee")
        l.parse_line("  (2021/11/03 acc1)  EUR 17")
        l.parse_line("  2021/11/03 acc1")
        l.parse_line("  2021/11/03 acc2  EUR 15")
