#! /usr/bin/env python3

import argparse
from decimal import Decimal
from datetime import datetime

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
    argparser.add_argument("--account", type=str,
                           default="",
                           help="account name")
    argparser.add_argument("--src", type=str,
                           default="",
                           help="source commodity")
    argparser.add_argument("--dst", type=str,
                           default="",
                           help="destination commodity")
    argparser.add_argument("--factor", type=str,
                           default="",
                           help="conversion factor")
    return argparser.parse_args()

def main():
    args = parse_args()
    journal, lines = read_journal(args.database)

    root = Account("root")
    apply_journal(journal, root, real=True, lots=True)

    account = root[args.account]
    factor = Decimal(args.factor)
    transaction = Transaction(datetime.now(), None, None)
    misc = Account("misc")
    originalbalance = Decimal(0)
    originalcost = Decimal(0)
    finalbalance = Decimal(0)
    finalcost = Decimal(0)

    for i in account.sorted_commodities():
        if not isinstance(i, Lot):
            continue
        if i.commodity != args.src:
            continue

        balance = account.balance[i]
        amount = Amount(-balance, i)
        misc["originalbalance"] += Amount(balance, i.commodity)
        misc["originalcost"] += Amount(i.price.quantity * balance,
                                       i.price.commodity)
        transaction.contents.append(Posting(args.account, amount))
        amount = Amount(balance, i)
        transaction.contents.append(Posting(
            "Equity:Trading:Securities", amount))

        balance = balance * factor
        balance = balance.quantize(Decimal("0.001"))
        price = i.price.quantity / factor
        price = price.quantize(Decimal("0.0001"))
        lot = Lot(args.dst, i.date, Amount(price, i.price.commodity))
        misc["finalbalance"] += Amount(balance, i.commodity)
        misc["finalcost"] += Amount(price * balance, i.price.commodity)
        amount = Amount(-balance, lot)
        transaction.contents.append(Posting(
            "Equity:Trading:Securities", amount))
        amount = Amount(balance, lot)
        transaction.contents.append(Posting(args.account, amount))

    qty = misc["originalbalance"].balance[args.src]
    a, b = amount2str(Amount(qty, args.src), journal.get_commodity_format)
    balance = a + b
    worth = ""
    commodities = misc["originalcost"].sorted_commodities()
    for i in commodities:
        qty = misc["originalcost"].balance[i]
        c, d = amount2str(Amount(qty, i), journal.get_commodity_format)
        worth += " " + c + d
    worth = worth.strip()
    transaction.contents.append(f"; Original Balance -- {balance} at {worth}")

    qty = misc["finalbalance"].balance[args.src]
    a, b = amount2str(Amount(qty, args.src), journal.get_commodity_format)
    balance = a + b
    worth = ""
    commodities = misc["finalcost"].sorted_commodities()
    for i in commodities:
        qty = misc["finalcost"].balance[i]
        c, d = amount2str(Amount(qty, i), journal.get_commodity_format)
        worth += " " + c + d
    worth = worth.strip()
    transaction.contents.append(f"; New Balance -- {balance} at {worth}")

    print_transaction(transaction, journal.get_commodity_format)

if __name__ == "__main__":
    main()
