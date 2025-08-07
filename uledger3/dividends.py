#! /usr/bin/env python3

import argparse
from typing import Callable
from decimal import Decimal
import datetime
import logging
import re

import uledger3.parser as parser

from uledger3.ledger import Account, Balance
from uledger3.util import read_journal, apply_journal
from uledger3.exchange import Exchange
from uledger3.parser import Amount, Lot, Transaction, \
    Posting, Position, Journal, Entity, PriceDecl
from uledger3.util import transform_account
from uledger3.printing import print_account_balance, \
    print_account_tree

logger = None

def parse_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("database", type=str,
                           default="database.ledger",
                           help="database file")
    argparser.add_argument("--prices", type=str,
                           default="prices.ledger",
                           help="prices file")
    argparser.add_argument("--account", type=str,
                           default="Income:Stock Dividend",
                           help="Account Name")
    argparser.add_argument('--start-date',
                           type=lambda s: datetime.datetime.strptime(s, '%Y/%m/%d'),
                           help="Start Date - YYYY/MM/DD")
    argparser.add_argument('--end-date',
                           type=lambda s: datetime.datetime.strptime(s, '%Y/%m/%d'),
                           help="End Date - YYYY/MM/DD")
    argparser.add_argument("--log-file", type=str,
                           help="Log File")
    argparser.add_argument("--base-currency", type=str,
                           default="INR",
                           help="Base Currency")
    argparser.add_argument("--tree", action="store_true",
                           default=False,
                           help="Display a tree")
    argparser.add_argument("--convert", action="store_true",
                           default=False,
                           help="Convert to base currency")
    return argparser.parse_args()

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

def create_exchange(journal, logger):
    prices = journal.contents
    exchange = Exchange()
    for price in prices:
        if not isinstance(price, PriceDecl):
            continue
        exchange.add_price(
            price.date,
            price.commodity,
            price.price.commodity,
            price.price.quantity
        )
        logger.info(f"Adding: P {price.date} {price.commodity} "
                    f"{price.price.commodity} {price.price.quantity}")
    return exchange

def last_day_of_last_month(today):
    first = today.replace(day=1)
    last_month = first - datetime.timedelta(days=1)
    return last_month

def main():
    args = parse_args()

    if args.log_file:
        logging.basicConfig(filename=args.log_file,
                            filemode="w",
                            format='[%(name)s:%(levelname)s] %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p',
                            level=logging.INFO)
    logger = logging.getLogger(__name__)

    journal, lines = read_journal(args.prices, pedantic=False)
    exchange = create_exchange(journal, logger)

    journal, lines = read_journal(args.database, pedantic=False)

    start_date = args.start_date
    end_date = args.end_date
    if not end_date: end_date = datetime.datetime.now()
    s = None
    if start_date:
        s = start_date.strftime('%Y-%m-%d')
    e = end_date.strftime('%Y-%m-%d')
    print(f"Generating Payee-Account report from {s} to {e}.")
    print(f"Account: {args.account}\n")

    root = Account("Root")

    for txn in journal.contents:
        if not isinstance(txn, Transaction):
            continue
        if start_date and txn.date < start_date:
            continue
        if txn.date > end_date:
            continue
        for p in txn.contents:
            if not isinstance(p, Posting): continue
            if parser.is_virtual_account(p.account): continue
            if not re.match(args.account, p.account): continue
            logger.info(f"Processing posting by {txn.payee} on {txn.date}.")
            if (not args.convert or p.amount.commodity == args.base_currency):
                root[txn.payee] -= p.amount
            else:
                d = last_day_of_last_month(txn.date)
                logger.info(f"Converting {p.amount.commodity} to "
                            f"{args.base_currency} as on {d}.")
                x = exchange.get_price(d, p.amount.commodity,
                                       args.base_currency)
                if x:
                    logger.info(f"Got price: {x}")
                    root[txn.payee] -= Amount(p.amount.quantity * x,
                                              args.base_currency)
                else:
                    logger.info(f"Unable to convert {p.amount.commodity} to "
                                f"{args.base_currency}.")
                    root[txn.payee] -= p.amount

    if args.tree:
        print_account_tree(
            root, format_function=journal.get_commodity_format,
                           commodity=args.base_currency)
    else:
        print_account_balance(
            root, format_function=journal.get_commodity_format)


if __name__ == "__main__":
    main()
