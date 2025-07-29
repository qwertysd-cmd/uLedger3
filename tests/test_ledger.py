import unittest
from datetime import datetime
from decimal import Decimal

import uledger3.parser as parser
from uledger3.parser import Amount, Lot, Transaction, \
    Posting, Position, Journal, Entity
import uledger3.ledger as ledger

class TestParser(unittest.TestCase):

    def test_balance(self):
        b = ledger.Balance()
        b1 = ledger.Balance(b)
        b2 = ledger.Balance(b)
        b21 = ledger.Balance(b2)
        with self.assertRaises(TypeError):
            b2 += parser.Amount(2, "CHF")
        b2 += parser.Amount(Decimal('2'), "CHF")
        self.assertEqual(len(b2), 1)
        b2 += parser.Amount(Decimal('1.12'), "EUR")
        self.assertEqual(len(b2), 2)
        self.assertEqual(len(b), 2)
        b2 -= parser.Amount(Decimal('1.10'), "EUR")
        self.assertEqual(len(b2), 2)
        self.assertEqual(len(b), 2)
        b += parser.Amount(Decimal('-0.02'), "EUR")
        self.assertEqual(len(b), 1)
        self.assertEqual(len(b2), 2)
        b21 += parser.Amount(Decimal('-0.02'), "XAU")
        self.assertEqual(len(b), 2)
        self.assertEqual(len(b21), 1)
        self.assertEqual(len(b2), 3)
        b2 -= parser.Amount(Decimal('-0.02'), "XAU")
        self.assertEqual(len(b), 1)
        self.assertEqual(len(b21), 1)
        self.assertEqual(len(b2), 2)
        self.assertEqual(b2["abc"], Decimal(0))
        b1 -= parser.Amount(Decimal('2'), "CHF")
        self.assertEqual(len(b2), 2)
        self.assertEqual(len(b1), 1)
        self.assertEqual(len(b), 0)
        self.assertEqual(b, 0)
        self.assertNotEqual(b1, 1)

    def test_transaction_has_unit_rates(self):
        p = parser.Parser("test")
        p.parse_lines([
            "2021/11/03 payee",
            "  acc1  AUD 15 @ EUR 10",
            "  acc2  EUR 15",
            "2021/11/03 payee",
            "  acc1  AUD 150",
            "  acc2  EUR 15",
        ])
        self.assertTrue(ledger.transaction_has_unit_rates(
            p.journal.contents[0]))
        self.assertFalse(ledger.transaction_has_unit_rates(
            p.journal.contents[1]))

    def test_check_transaction(self):
        p = parser.Parser("test")
        lines = [
            "2021/11/03 payee",
            "  acc1  AUD 15 @ EUR 10",
            "  acc2  EUR 15",
            "2021/11/03 payee",
            "  (acc1)  ",
            "  acc2  EUR 15",
            "2021/11/03 payee",
            "  acc1  ",
            "  acc2",
            "2021/11/03 payee",
            "  acc1  ",
            "  acc2  EUR 15",
            "  acc3  AUD 12",
            "  acc3  CHF 100 [2022/01/03] {USD 65}",
            "2021/11/03 payee",
            "  acc1  EUR 15",
            "  acc2  EUR 15",
            "2021/11/03 payee",
            "  acc1  EUR -15",
            "  acc2  EUR 15",
            "  acc2  USD 10.2134",
            "  acc3  USD -10",
            "2021/11/03 payee",
            "  acc1  EUR -15",
            "  acc1  USD -0.1134",
            "  acc2  EUR 15",
            "  acc2  USD 10.2134",
            "  acc3  USD -10",
            "  acc1  USD -0.1",
        ]
        p.parse_lines(lines)

        with self.assertRaises(ledger.BalanceError):
            ledger.check_transaction(p.journal.contents[0], lines=lines)

        with self.assertRaises(ledger.BalanceError):
            ledger.check_transaction(p.journal.contents[1], lines=lines)

        with self.assertRaises(ledger.BalanceError):
            ledger.check_transaction(p.journal.contents[2], lines=lines)

        ledger.check_transaction(p.journal.contents[3], lines=lines)
        with self.assertRaises(ledger.BalanceError):
            ledger.check_transaction(p.journal.contents[3], lines=lines, noelide=True)
        self.assertEqual(len(p.journal.contents[3].contents), 4)
        ledger.unelide_transaction(p.journal.contents[3], lines=lines)
        self.assertEqual(len(p.journal.contents[3].contents), 6)
        ledger.check_transaction(p.journal.contents[3], lines=lines, noelide=True)

        with self.assertRaises(ledger.BalanceError):
            ledger.check_transaction(p.journal.contents[4], lines=lines)

        with self.assertRaises(ledger.BalanceError):
            ledger.check_transaction(p.journal.contents[5], lines=lines)

        ledger.check_transaction(p.journal.contents[6], lines=lines)

    def test_account(self):
        a = ledger.Account("root")
        p = Posting("Assets:Checking",
                    Amount(Decimal("3"), "JPY"))
        a.apply(p)
        p = Posting("Assets:Savings",
                    Amount(Decimal("6"), "JPY"))
        a.apply(p)
        p = Posting("Assets:Hello",
                    Amount(Decimal("6"), "JPY"))
        a.apply(p)
        p = Posting("ABC:1 2 3",
                    Amount(Decimal("6"), "JPY"))
        a.apply(p)
        self.assertEqual(a.balance["JPY"], Decimal(21))
        self.assertEqual(a["Assets"].balance["JPY"], Decimal(15))
        self.assertEqual(a["Assets"]["Savings"].balance["JPY"], Decimal(6))
        self.assertEqual(a.balance["JPY"], Decimal(21))
        a["Liabilities:Credit Card"] += Amount(Decimal(55), "AED")
        self.assertEqual(a["Liabilities"].balance["AED"], Decimal(55))
        a["Liabilities: Credit Card : test"] += Amount(Decimal(25), "GBP")
        self.assertEqual(a["Liabilities"].balance["GBP"], Decimal(25))
        self.assertEqual(a["Liabilities"]["Credit Card"].balance["GBP"],
                         Decimal(25))
        self.assertEqual(a["Liabilities"]["Credit Card"].balance["AED"],
                         Decimal(55))
        self.assertEqual(a["Liabilities"]["Credit Card"]["test"].balance["GBP"],
                         Decimal(25))
        a["Liabilities: Credit Card : test"] -= Amount(Decimal(25), "GBP")
        self.assertEqual(a["Liabilities"]["Credit Card"]["test"].balance, 0)
        self.assertEqual(a["Liabilities"].balance["GBP"], 0)
        a["Liabilities:Credit Card:abc"] -= Amount(Decimal(55), "AED")
        self.assertEqual(a["Liabilities"].balance, 0)
        self.assertEqual(a["Liabilities"].balance, 0)
        with self.assertRaises(ValueError):
            x = a[":abc"]
        with self.assertRaises(ValueError):
            x = a["abc:   \t  :123"]
        with self.assertRaises(ValueError):
            x = a["abc: : 123"]
        x = a["abc: 123"]
        y = a["abc:  123"]
        z = a["abc:123"]
        a = a["abc:1234"]
        self.assertEqual(x, y)
        self.assertEqual(y, z)
        self.assertNotEqual(y, a)
        print(a.children)
