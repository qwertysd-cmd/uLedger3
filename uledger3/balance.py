#! /usr/bin/env python3

import argparse
from typing import Callable
from decimal import Decimal

from uledger3.printing import print_account_balance
from uledger3.ledger import Account, Balance
from uledger3.util import read_journal, apply_journal
from uledger3.exchange import Exchange
from uledger3.parser import Amount, Lot, Transaction, \
    Posting, Position, Journal, Entity, PriceDecl
from uledger3.util import transform_account

def parse_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("database", type=str,
                           default="database.ledger",
                           help="database file")
    argparser.add_argument("--real", action="store_true",
                           default=False,
                           help="Show real transactions only")
    argparser.add_argument("--lots", action="store_true",
                           default=False,
                           help="Show lots")
    argparser.add_argument("--exchange", type=str,
                           default="",
                           help="Show lots")
    argparser.add_argument("--prices", type=str,
                           default="",
                           help="prices file")
    return argparser.parse_args()

def exchanger(exchange: Exchange, commodity: str, b: Balance) -> Balance:
    b_new = Balance()
    for i in b:
        if isinstance(i, Lot):
            x = exchange.get_price(i.date,
                                   i.price.commodity,
                                   commodity)
            if x:
                b_new += Amount(
                    b[i],
                    Lot(i.commodity, i.date,
                        Amount(i.price.quantity * x, commodity))
                )
        else:
            x = exchange.get_price(None, i, commodity)
            if x:
                b_new += Amount(b[i] * x, commodity)
    return b_new

def quantizer(format_function: Callable, b: Balance) -> Balance:
    b_new = Balance()
    for i in b:
        if isinstance(i, Lot):
            b_new[i] = b[i]
        else:
            fmt = format_function(i)
            if not fmt: continue
            precision = fmt.precision
            q = Decimal(10) ** -precision # 2 places --> '0.01'
            v = b[i].quantize(q)
            #print(f"Quantized {b[i]} to {v}.")
            b_new[i] = v
    return b_new

def main():
    args = parse_args()
    journal, lines = read_journal(args.database)

    root = Account("root")
    apply_journal(journal, root, args.real, args.lots)

    if args.exchange:
        prices = None
        if args.prices:
            prices, _ = read_journal(args.prices)
            prices = prices.contents
        exchange = Exchange()
        for i in (prices, journal.contents):
            for price in i:
                if not isinstance(price, PriceDecl):
                    continue
                exchange.add_price(
                    price.date, price.commodity,
                    price.price.commodity, price.price.quantity)
        exchanged = Account("root")
        commodity = args.exchange
        transform_account(root, exchanged,
                          lambda b, n : exchanger(exchange, commodity, b))
    else:
        exchanged = root

    quantized = Account("root")
    transform_account(exchanged, quantized,
                      lambda b, n : quantizer(journal.get_commodity_format, b),
                      independent = True)

    print_account_balance(quantized, format_function=journal.get_commodity_format)

if __name__ == "__main__":
    main()
