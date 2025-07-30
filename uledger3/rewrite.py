#! /usr/bin/env python3

import argparse
from decimal import Decimal

import uledger3.parser as parser
import uledger3.ledger as ledger
from uledger3.util import read_journal, apply_transaction
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

def print_account_decl(d):
    indent = "  "
    print("account " + d.account)
    for i in d.contents:
        if isinstance(i, AccountAlias):
            print(indent + "alias " + i.alias)
        else:
            print(indent + i)

def print_commodity_decl(d, format_function):
    indent = "  "
    print("commodity " + commodity2str(d.commodity))
    for i in d.contents:
        if isinstance(i, CommodityFormat):
            left, right = amount2str(Amount(Decimal('1000'),
                                            d.commodity),
                                     format_function)
            print(indent + "format " + left + right)
        else:
            print(indent + i)

def print_price_decl(d, format_function):
    line = "P " + date2str(d.date)
    line += " " + commodity2str(d.commodity)
    a, b = amount2str(d.price, format_function)
    line += " " + a + b
    print(line)

def print_transaction(txn, format_function):
    alignment_column = 80
    indent = "  "
    hard_space = "  "
    line = date2str(txn.date)
    if txn.status:
        line += " " + txn.status
    elif txn.payee:
        line += "  "
    if txn.payee:
        line += " " + txn.payee
    print(line)
    for p in txn.contents:
        if not isinstance(p, Posting):
            assert isinstance(p, str)
            print(indent + p)
            continue
        account = p.account
        amount = p.amount
        line = indent + account
        if not amount:
            print(line)
            continue

        left, right = amount2str(amount, format_function)
        left = hard_space + left
        line += left.rjust(alignment_column - len(line))
        line += right
        if amount.unit_rate:
            line += " @ "
            a, b = amount2str(amount.unit_rate, format_function)
            line += a + b
        print(line)

def main():
    args = parse_args()
    journal, lines = read_journal(args.database)
    root = Account("root")
    for item in journal.contents:
        if isinstance(item, str):
            print(item)
        elif isinstance(item, AccountDecl):
            print_account_decl(item)
        elif isinstance(item, CommodityDecl):
            print_commodity_decl(item, journal.get_commodity_format)
        elif isinstance(item, PriceDecl):
            print_price_decl(item, journal.get_commodity_format)
        elif isinstance(item, Transaction):
            if transaction_has_unit_rates(item):
                p = expand_and_apply_unit_rate (
                    item, root, journal.get_commodity_format)
                print_transaction(item, journal.get_commodity_format)
                if p:
                    print("")
                for i in p:
                    print_price_decl(i, journal.get_commodity_format)
            else:
                apply_transaction(item, root, real=True, lots=True)
                print_transaction(item, journal.get_commodity_format)

def expand_and_apply_unit_rate(txn, account, format_function):
    # Return list of price statements
    prices = []
    contents = []
    equity_n = "Equity:Trading:Securities"
    equity = account[equity_n]
    gains_n = "Income:Capital Gains"
    gains = account[gains_n]
    for p in txn.contents:
        contents.append(p)
        if not isinstance(p, Posting):
            continue
        if parser.is_virtual_account(p.account):
            continue
        if not p.amount.unit_rate:
            account[p.account] += p.amount
            continue
        contents.pop()
        assets = account[p.account]
        price = PriceDecl(p.amount.commodity, txn.date, p.amount.unit_rate)
        prices.append(price)
        ### Buying ###
        if p.amount.quantity >= 0:
            amount = Amount(
                p.amount.quantity,
                Lot(p.amount.commodity, txn.date, p.amount.unit_rate))
            contents.append(Posting(p.account, amount))
            assets += amount
            amount = Amount(
                -p.amount.quantity,
                Lot(p.amount.commodity, txn.date, p.amount.unit_rate))
            contents.append(Posting(equity_n, post_amount))
            equity += amount
            amount = Amount(
                p.amount.quantity * p.amount.unit_rate.quantity,
                p.amount.unit_rate.commodity)
            contents.append(Posting(equity_n, post_amount))
            equity += amount
            continue
        ### Selling ###
        commodity = p.amount.commodity
        remaining_balance = -p.amount.quantity
        assert remaining_balance > 0
        equity_balance = 0
        contents.append(f"; Before this sale:")
        x = _get_sorted_positive_lots(
            commodity, p.amount.unit_rate.commodity, assets)
        for lot in x:
            a, b = amount2str(Amount(account[p.account].balance[lot], lot),
                              format_function)
            contents.append(f";   {a}{b} ; {p.account}")
        a, b = amount2str(Amount(remaining_balance, commodity),
                          format_function)
        c, d = amount2str(p.amount.unit_rate, format_function)
        contents.append(f"; Selling {a}{b} @ {c}{d} each.")
        while remaining_balance > 0:
            x = _get_sorted_positive_lots(
                commodity, p.amount.unit_rate.commodity, account[p.account])
            if not x:
                break
            selected = x[0]
            min_bal = min(remaining_balance,
                          account[p.account].balance[selected])
            remaining_balance -= min_bal
            amount = Amount(-min_bal, selected)
            contents.append(Posting(p.account, amount))
            assets += amount
            amount = Amount(min_bal, selected)
            contents.append(Posting(equity_n, amount))
            equity += amount
            equity_balance -= min_bal * selected.price.quantity
        if remaining_balance != 0:
            sold = -p.amount.quantity - remaining_balance
            a, b = amount2str(Amount(sold, commodity),
                              format_function)
            contents.append(f"; WARNING: Sold only {a}{b}.")
            a, b = amount2str(Amount(remaining_balance, commodity),
                              format_function)
            contents.append(f"; WARNING: Unsold balance is {a}{b}.")
        amount = Amount(equity_balance, p.amount.unit_rate.commodity)
        contents.append(Posting(equity_n, amount))
        equity += amount
        # `quantity` is negative and `remaining_balance` is positive.
        # sold, proceeds, cost, profit are normally negative.
        sold = p.amount.quantity + remaining_balance
        proceeds = sold * p.amount.unit_rate.quantity
        cost = equity_balance
        profit = proceeds - equity_balance
        post_amount = Amount(profit, p.amount.unit_rate.commodity)
        contents.append(Posting(gains_n, post_amount))
        gains += post_amount
    txn.contents = contents
    return prices

def _get_sorted_positive_lots(commodity, price_commodity, account):
    selected = []
    for i in account.sorted_commodities():
        if not isinstance(i, Lot):
            continue
        if i.commodity != commodity:
            continue
        if i.price.commodity != price_commodity:
            continue
        if account.balance[i] > 0:
            selected.append(i)
    return selected

if __name__ == "__main__":
    main()
