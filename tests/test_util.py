import unittest
from datetime import datetime
from decimal import Decimal

import uledger3.parser as parser
from uledger3.parser import Amount, Lot, Transaction, \
    Posting, Position, Journal, Entity
import uledger3.ledger as ledger
from uledger3.ledger import Account, Balance
from uledger3.util import transform_account

class TestParser(unittest.TestCase):

    def test_divide_balance(self):
        a = ledger.Account("root")
        a.apply(Posting("A:B:C", Amount(Decimal("6"),   "JPY")))
        a.apply(Posting("A:B:D", Amount(Decimal("7"),   "JPY")))
        a.apply(Posting("A:B",   Amount(Decimal("14"),  "JPY")))
        a.apply(Posting("A:B",   Amount(Decimal("12"),  "ABC")))
        a.apply(Posting("A:B:X", Amount(Decimal("-12"), "ABC")))

        self.assertEqual(a["A"].balance["ABC"], 0)
        self.assertEqual(a["A:B"].balance["JPY"], 27)
        self.assertEqual(a["A:B"].balance["ABC"], 0)
        self.assertEqual(a["A:B:X"].balance["ABC"], -12)

        def div2(b: Balance, n: str) -> Balance:
            b_new = Balance()
            for i in b:
                b_new[i] += b[i] / 2
            return b_new

        b = ledger.Account("root")
        transform_account(a, b, div2)

        self.assertEqual(b["A"].balance["ABC"], 0)
        self.assertEqual(b["A:B"].balance["JPY"], Decimal("13.5"))
        self.assertEqual(b["A:B"].balance["ABC"], 0)
        self.assertEqual(b["A:B:X"].balance["ABC"], -6)
