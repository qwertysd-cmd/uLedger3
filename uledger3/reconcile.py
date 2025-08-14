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
from uledger3.rewrite import print_transaction

def parse_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("database", type=str,
                           default="database.ledger",
                           help="database file")
    return argparser.parse_args()

def days_ago(input_date):
    if input_date is None:
        return float('inf')
    today = datetime.today()
    delta = today - input_date
    return delta.days

def main():
    args = parse_args()
    journal, lines = read_journal(args.database)

    assets = {}
    assertions = {}

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

            key = (p.amount.commodity, p.account)
            if isinstance(p.amount.commodity, Lot):
                key = (p.amount.commodity.commodity, p.account)
            quantity = p.amount.quantity

            if key not in assets:
                assets[key] = quantity
            else:
                assets[key] += quantity

            if p.assertion:
                key = (p.assertion.commodity, p.account)
                assertions[key] = txn.date
            elif key not in assertions:
                assertions[key] = None

    updates = []
    for i in assets:
        if assets[i] != 0:
            x = (days_ago(assertions[i]), i[1], i[0])
            updates.append(x)

    updates.sort(reverse=True)
    for i in updates:
        x = str(i[0]).ljust(5)
        a, b = amount2str(Amount(Decimal(0), i[2]),
                          journal.get_commodity_format)
        amount = a.rjust(10) + b
        print(f"{x} {i[1].ljust(50)} INR 0.00 = {amount}")

if __name__ == "__main__":
    main()
