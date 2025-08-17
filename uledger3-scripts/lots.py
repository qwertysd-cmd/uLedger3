#! /usr/bin/env python3

import argparse
from decimal import Decimal
from datetime import datetime
import re

import uledger3.parser as parser
import uledger3.ledger as ledger
from uledger3.util import read_journal, apply_journal
from uledger3.parser import Amount, Lot, Transaction, \
    Posting, Position, Journal, Entity, PriceDecl, \
    AccountDecl, CommodityDecl, CommodityFormat, AccountAlias
from uledger3.printing import amount2str, date2str, \
    commodity2str
from uledger3.ledger import Account, BalanceError, \
    transaction_has_unit_rates

def parse_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("database", type=str,
                           default="database.ledger",
                           help="database file")
    return argparser.parse_args()

def main():
    args = parse_args()
    journal, lines = read_journal(args.database)

    root = Account("root")

    lots = {}

    for txn in journal.contents:
        if not isinstance(txn, Transaction):
            continue
        for p in txn.contents:
            if not isinstance(p, Posting):
                continue
            if parser.is_virtual_account(p.account):
                continue
            if not re.match("Assets", p.account):
                continue
            if not isinstance(p.amount.commodity, Lot):
                continue
            post_account = p.account
            post_amount = p.amount
            key = (p.amount.commodity, p.account)
            quantity = p.amount.quantity
            if key not in lots:
                lots[key] = quantity
            else:
                lots[key] += quantity

    sorted_lots = list(lots.keys())
    sorted_lots.sort(key=lambda x: (x[0].commodity, x[0].date))
    last_symbol = ""
    for i in sorted_lots:
        if lots[i] != 0:
            current_symbol = i[0].commodity
            if current_symbol != last_symbol:
                last_symbol = current_symbol
                print("")
            a, b = amount2str(Amount(lots[i], i[0]),
                              journal.get_commodity_format)
            print(f"{a + b} ; {i[1]}")

if __name__ == "__main__":
    main()
