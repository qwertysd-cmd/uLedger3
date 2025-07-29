#! /usr/bin/env python3

from decimal import Decimal
import argparse

import uledger3.parser as parser
import uledger3.ledger as ledger
from uledger3.printing import *
from uledger3.parser import Amount, Lot, Transaction, \
    Posting, Position, Journal, Entity

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--database", type=str,
                           default="database.ledger",
                           help="database file")
    args = argparser.parse_args()

    p = parser.Parser(args.database, pedantic=True)
    with open(args.database, "r") as database:
        for line in database:
            p.parse_line(line)

    for txn in p.journal.contents:
        if not isinstance(txn, Transaction):
            continue
        for posting in txn.contents:
            if not isinstance(posting, Posting):
                continue
            if posting.amount is None:
                continue
            a, b = amount2str(
                posting.amount, p.journal.get_commodity_format)
            print(f"{a}|{b}")

if __name__ == "__main__":
    main()
