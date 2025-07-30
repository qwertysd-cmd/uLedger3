import unittest
from datetime import datetime
from decimal import Decimal

import uledger3.exchange as exchange

class TestExchange(unittest.TestCase):

    def test_search_date(self):
        x = [
            (datetime(2001, 2, 3), 0.1),

            (datetime(2002, 2, 3), 0.1),
            (datetime(2002, 2, 3), 0.4),
            (datetime(2002, 2, 3), 0.5),

            (datetime(2003, 2, 3), 0.5),

            (datetime(2009, 2, 3), 0.7),
            (datetime(2009, 2, 3), 9.5),

            (datetime(2009, 2, 4), 8.5),

            (datetime(2019, 2, 4), 9.6),
        ]
        self.assertEqual(exchange._search_date(x, datetime(2001, 2, 3)),
                         (datetime(2001, 2, 3), 0.1))
        self.assertEqual(exchange._search_date(x, datetime(2001, 3, 3)),
                         (datetime(2001, 2, 3), 0.1))
        self.assertEqual(exchange._search_date(x, datetime(2002, 3, 3)),
                         (datetime(2002, 2, 3), 0.5))
        self.assertEqual(exchange._search_date(x, datetime(2004, 3, 3)),
                         (datetime(2003, 2, 3), 0.5))
        self.assertEqual(exchange._search_date(x, datetime(2009, 2, 3)),
                         (datetime(2009, 2, 3), 9.5))
        self.assertEqual(exchange._search_date(x, datetime(2029, 2, 3)),
                         (datetime(2019, 2, 4), 9.6))
        self.assertEqual(exchange._search_date(x, datetime(2000, 2, 3)),
                         None)

    def test_get_price(self):
        x = exchange.Exchange()
        x.add_price(datetime(2001, 2,  1), "EUR", "JPY", Decimal("3.9"))
        x.add_price(datetime(2001, 2,  1), "JPY", "XAU", Decimal("4.9"))
        x.add_price(datetime(2001, 2,  3), "USD", "EUR", Decimal("1.5"))
        x.add_price(datetime(2001, 2,  4), "USD", "CHF", Decimal("1.7"))
        x.add_price(datetime(2001, 2,  5), "CHF", "EUR", Decimal("1.3"))
        x.add_price(datetime(2001, 2,  6), "CHF", "XAU", Decimal("0.1"))
        x.add_price(datetime(2001, 2,  7), "XAU", "ABC", Decimal("0.9"))
        x.add_price(datetime(2001, 2,  8), "ABC", "DEF", Decimal("0.8"))
        x.add_price(datetime(2001, 2,  9), "DEF", "USD", Decimal("0.5"))
        x.add_price(datetime(2001, 2, 10), "DEF", "CHF", Decimal("0.5"))
        p = x.get_price(datetime(2001, 2, 6), "CHF", "XAU")
        self.assertEqual(p, Decimal("0.1"))
        p = x.get_price(datetime(2001, 2, 7), "CHF", "EUR")
        self.assertEqual(p, Decimal("1.3"))
        p = x.get_price(datetime(2001, 2, 4), "CHF", "EUR")
        self.assertEqual(p, 1/Decimal("1.7") * Decimal("1.5"))
        p = x.get_price(datetime(2001, 2, 4), "CHF", "DEF")
        self.assertEqual(p, None)
        p = x.get_price(datetime(2001, 2, 7), "CHF", "DEF")
        self.assertEqual(p, None)
        p = x.get_price(datetime(2001, 2, 8), "CHF", "DEF")
        t = Decimal("0.1") * Decimal("0.9") * Decimal("0.8")
        self.assertEqual(p, t)
        p = x.get_price(datetime(2001, 2, 8), "DEF", "CHF")
        self.assertEqual(p, 1/t)
        p = x.get_price(datetime(2001, 2, 10), "DEF", "CHF")
        self.assertEqual(p, Decimal("0.5"))
        p = x.get_price(datetime(2001, 2, 10), "USD", "XAU")
        self.assertEqual(p, Decimal("1.7") * Decimal("0.1"))
        p = x.get_price(datetime(2001, 2, 3), "USD", "XAU")
        self.assertEqual(p, Decimal("1.5") * Decimal("3.9") * Decimal("4.9"))
