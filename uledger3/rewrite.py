#! /usr/bin/env python3

import argparse
from decimal import Decimal

import uledger3.parser as parser
import uledger3.ledger as ledger
from uledger3.util import read_journal, apply_transaction
from uledger3.parser import Amount, Lot, Transaction, \
    Posting, Position, Journal, Entity, PriceDecl, \
    AccountDecl, CommodityDecl, CommodityFormat
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

        # Convert to preferred precision if possible.
        if isinstance(amount.commodity, str):
            preferred = format_function(amount.commodity)
            preferred = preferred.precision
        else:
            preferred = format_function(amount.commodity.commodity)
            preferred = preferred.precision
        x = amount.quantity.quantize(Decimal(10) ** -preferred)
        if amount.quantity == x:
            amount = Amount(x, p.amount.commodity, p.amount.unit_rate)

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
                print_transaction(item, journal.get_commodity_format)
                apply_transaction(item, root, real=True, lots=True)

def expand_and_apply_unit_rate(txn, account, format_function):
    # Return list of price statements
    prices = []
    new_postings = []
    delete_postings = []
    equity = "Equity:Trading:Securities"
    gains = "Income:Capital Gains"
    index = 0
    dindex = 0
    for p in txn.contents:
        index += 1
        dindex += 1
        if not isinstance(p, Posting):
            continue
        if parser.is_virtual_account(p.account):
            continue
        if not p.amount.unit_rate:
            account[p.account] += p.amount
            continue
        dindex -= 1
        delete_postings.append(dindex)
        ### Buying ###
        if p.amount.quantity >= 0:
            post_amount = Amount(
                p.amount.quantity,
                Lot(p.amount.commodity, txn.date, p.amount.unit_rate))
            x = parser.Posting(p.account, post_amount)
            new_postings.append((index, x))
            index += 1; dindex += 1
            account[p.account] += post_amount
            post_amount = Amount(
                -p.amount.quantity,
                Lot(p.amount.commodity, txn.date, p.amount.unit_rate))
            x = parser.Posting(equity, post_amount)
            new_postings.append((index, x))
            index += 1; dindex += 1
            prices.append(PriceDecl(
                p.amount.commodity, txn.date, p.amount.unit_rate))
            account[equity] += post_amount
            post_amount = Amount(
                p.amount.quantity * p.amount.unit_rate.quantity,
                p.amount.unit_rate.commodity)
            x = parser.Posting(equity, post_amount)
            new_postings.append((index, x))
            index += 1; dindex += 1
            account[equity] += post_amount
            continue
        ### Selling ###
        commodity = p.amount.commodity
        remaining_balance = -p.amount.quantity
        equity_balance = 0
        assert remaining_balance > 0
        new_postings.append((index, f"; Before this sale:"))
        index += 1; dindex += 1
        x = _get_sorted_positive_lots(
            commodity, p.amount.unit_rate.commodity, account[p.account])
        for lot in x:
            a, b = amount2str(Amount(account[p.account].balance[lot], lot),
                              format_function)
            new_postings.append((index, f";   {a}{b} ; {p.account}"))
            index += 1; dindex += 1
        a, b = amount2str(Amount(remaining_balance, commodity),
                          format_function)
        c, d = amount2str(p.amount.unit_rate, format_function)
        new_postings.append((index, f"; Selling {a}{b} @ {c}{d}."))
        index += 1; dindex += 1
        prices.append(
            PriceDecl(p.amount.commodity, txn.date, p.amount.unit_rate))
        while remaining_balance > 0:
            x = _get_sorted_positive_lots(
                commodity, p.amount.unit_rate.commodity, account[p.account])
            if not x: break
            selected = x[0]
            min_bal = min(remaining_balance,
                          account[p.account].balance[selected])
            remaining_balance -= min_bal
            post_amount = Amount(-min_bal, selected)
            x = parser.Posting(p.account, post_amount)
            new_postings.append((index, x))
            index += 1; dindex += 1
            account[p.account] += post_amount
            post_amount = Amount(min_bal, selected)
            x = parser.Posting(equity, post_amount)
            new_postings.append((index, x))
            index += 1; dindex += 1
            account[equity] += post_amount
            equity_balance -= min_bal * selected.price.quantity
        if remaining_balance != 0:
            sold = -p.amount.quantity - remaining_balance
            a, b = amount2str(Amount(sold, commodity),
                              format_function)
            new_postings.append(
                (index, f"; WARNING: Sold only {a}{b}."))
            index += 1; dindex += 1
            a, b = amount2str(Amount(remaining_balance, commodity),
                              format_function)
            new_postings.append(
                (index, f"; WARNING: Unsold balance is {a}{b}."))
            index += 1; dindex += 1
        post_amount = Amount(equity_balance, p.amount.unit_rate.commodity)
        x = parser.Posting(equity, post_amount)
        new_postings.append((index, x))
        index += 1; dindex += 1
        account[equity] += post_amount
        # `quantity` is negative and `remaining_balance` is positive.
        # sold, proceeds, cost, profit are normally negative.
        sold = p.amount.quantity + remaining_balance
        proceeds = sold * p.amount.unit_rate.quantity
        cost = equity_balance
        profit = proceeds - equity_balance
        post_amount = Amount(profit, p.amount.unit_rate.commodity)
        x = parser.Posting(gains, post_amount)
        new_postings.append((index, x))
        index += 1; dindex += 1
        account[gains] += post_amount

    for p in new_postings:
        txn.contents.insert(p[0], p[1])
    for i in delete_postings:
        txn.contents.pop(i)
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
