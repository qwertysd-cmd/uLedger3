#! /usr/bin/env python3

import argparse
from decimal import Decimal

import uledger3.parser as parser
import uledger3.ledger as ledger
from uledger3.parser import Amount, Lot, Transaction, \
    Posting, Position, Journal, Entity, PriceDecl
from uledger3.ledger import Account
from uledger3.util import read_journal
from uledger3.util import apply_transaction

def check_journal(journal: Journal, lines: list[str]):
    last_date = None
    root = Account("root")
    for i in journal.contents:
        if not (isinstance(i, Transaction) or
                isinstance(i, PriceDecl)):
            continue
        if last_date and last_date > i.date:
                raise ledger.LedgerError(
                    "Dates out of order.", i, lines)
        last_date = i.date
        if not isinstance(i, Transaction):
            continue
        ledger.check_transaction(i, lines)
        check_trading_equity(i, lines)
        apply_transaction(i, root, real=True, lots=True,
                          assertions=True, lines=lines)

def _read_exchange_rate_comment(comment: str) -> tuple[str, Amount] | None:
    x = ledger.read_uledger_comment(comment)
    if not x:
        return None
    if x[0] != "Exchange Rate":
        return None
    x = x[1]
    amount, consumed = parser.parse_simple_amount(x, 0)
    if not amount:
        return None
    amount = amount[0]
    assert amount.quantity == Decimal(1)
    commodity = amount.commodity
    _, consumed = parser.parse_space(x, consumed)
    equal, consumed = parser.parse_keyword("=", x, consumed)
    if not equal:
        return None
    _, consumed = parser.parse_space(x, consumed)
    amount, consumed = parser.parse_simple_amount(x, consumed)
    if not amount:
        return None
    amount = amount[0]
    return (commodity, amount)

def check_trading_equity(txn: Transaction, lines: list[str] | None = None):
    ledger.unelide_transaction(txn, lines)
    a = Account("root")
    exchange_rates: dict[str, Amount] = {}
    for i in range(len(txn.contents)):
        p = txn.contents[i]
        if isinstance(p, str):
            x = _read_exchange_rate_comment(p)
            if not x:
                continue
            exchange_rates[x[0]] = x[1]
        elif isinstance(p, Posting):
            if parser.is_virtual_account(p.account):
                continue
            if isinstance(p.amount.commodity, Lot):
                x = Amount(
                    p.amount.quantity * p.amount.commodity.price.quantity,
                    p.amount.commodity.price.commodity)
            elif (p.account == "Equity:Trading:Currency" and
                  p.amount.commodity in exchange_rates):
                y = exchange_rates[p.amount.commodity]
                x = Amount(p.amount.quantity * y.quantity, y.commodity)
            else:
                x = p.amount
            a[p.account] += x
    trading = a["Equity:Trading:Securities"]
    _verify_balance_within_tolerance(trading, txn, lines)
    trading = a["Equity:Trading:Currency"]
    _verify_balance_within_tolerance(trading, txn, lines)

def _verify_balance_within_tolerance(account, txn, lines):
    if account.balance == 0:
        return None
    x = account.sorted_commodities()
    if len(x) == 1 and abs(account.balance[x[0]]) < Decimal('0.01'):
        return None
    raise ledger.BalanceError(
        f"{account.full_name()} unbalanced by {account.balance}.", txn, lines)

def parse_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("database", type=str,
                           default="database.ledger",
                           help="database file")
    return argparser.parse_args()

def main():
    args = parse_args()
    journal, lines = read_journal(args.database)
    check_journal(journal, lines)

if __name__ == "__main__":
    main()
