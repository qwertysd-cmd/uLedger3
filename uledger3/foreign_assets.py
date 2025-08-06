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
from uledger3.printing import amount2str, date2str, \
    commodity2str

logger = logging.getLogger(__name__)

class PeakValuation():

    def __init__(self, startDate, endDate):
        self.startDate = startDate
        self.endDate = endDate
        # {(Account, Lot): (Peak Date, Amount, Latest Date)}
        self.peakValues: dict[tuple(str, str), tuple(datetime, Amount)] = {}
        # {("AAPL", "USD"): [(t1, t2, 195, date), (t2, t3, 192, date)]}
        self.peakPrices: dict[tuple(str, str),
                              list(tuple(datetime, datetime, Decimal))] = {}
        self.root = Account("Root")

    def applyPosting(self, p, date):
        if date < self.startDate:
            self.root[p.account] += p.amount
            return
        x = (p.account, p.amount.commodity)
        self.updatePeakValues(x, date)
        self.root[p.account] += p.amount

    def updatePeakValues(self, key: tuple[str, str|Lot],
                         currentDate: datetime):
        account, lot = key
        commodity, currency = lot, lot
        if isinstance(lot, Lot):
            commodity, currency = lot.commodity, lot.price.commodity
        balance = self.root[account].balance[lot]
        try:
            tmp = self.peakValues[key]
            oldPeakDate, oldPeakAmount, oldLatestDate = tmp
            tmp = self.getPeakPrice(
                commodity, currency, oldLatestDate, currentDate)
            newPeakAmount = Amount(balance * tmp[0], currency)
            newPeakDate = tmp[1]
        except KeyError:
            oldPeakAmount = Amount(Decimal(0), currency)
            oldPeakDate = currentDate
            newPeakAmount = Amount(Decimal(0), currency)
            newPeakDate = currentDate
            if balance:
                tmp = self.getPeakPrice(
                    commodity, currency, self.startDate, currentDate)
                newPeakAmount = Amount(balance * tmp[0], currency)
                newPeakDate = tmp[1]
        logging.info(f"Updating peak date from {oldPeakDate} to {newPeakDate}.")
        if (newPeakAmount.quantity > oldPeakAmount.quantity):
            self.peakValues[key] = (newPeakDate, newPeakAmount, currentDate)
        else:
            self.peakValues[key] = (oldPeakDate, oldPeakAmount, currentDate)

    def extendToEnd(self):
        for i in self.peakValues:
            self.updatePeakValues(i, self.endDate)

    def getPeakPrice(self, commodity, currency, startDate, endDate):
        if commodity == currency: return (Decimal(1), endDate)
        if commodity == "US3160671075": return (Decimal(1), endDate)
        x = (commodity, currency)
        peakPrice = None
        peakDate = None
        try:
            y = self.peakPrices[x]
            found = False
            for i in y:
                if i[0] == startDate and i[1] <= endDate:
                    peakPrice, peakDate = updatePeakPrice(
                        peakPrice, peakDate, i)
                else: continue
                if i[1] == endDate: found = True; break
                startDate = i[1]
            if not found:
                i = self.newPeakPrice(commodity, currency, startDate, endDate)
                peakPrice, peakDate = updatePeakPrice(
                    peakPrice, peakDate, i)
        except KeyError:
            i = self.newPeakPrice(commodity, currency, startDate, endDate)
            peakPrice, peakDate = updatePeakPrice(peakPrice, peakDate, i)
        return (peakPrice, peakDate)

    def newPeakPrice(self, commodity, currency, startDate, endDate):
        s = startDate.strftime('%Y-%m-%d')
        e = endDate.strftime('%Y-%m-%d')
        x = Decimal(input(f"Enter the peak price of {commodity} "
                          f"between {s} and {e} in {currency}: "))
        y = input(f"Enter the date of this price: ")
        y = datetime.datetime.strptime(y, '%Y/%m/%d')
        z = (startDate, endDate, x, y)
        try:
            self.peakPrices[(commodity, currency)].append(z)
        except KeyError:
            self.peakPrices[(commodity, currency)] = [z]
        self.peakPrices[(commodity, currency)].sort(key=lambda a: a[0])
        return z

def updatePeakPrice(peakPrice, peakDate, peakPriceTuple):
    if not peakPrice:
        peakPrice = peakPriceTuple[2]
        peakDate = peakPriceTuple[3]
    elif peakPriceTuple[2] > peakPrice:
        peakPrice = peakPriceTuple[2]
        peakDate = peakPriceTuple[3]
    return (peakPrice, peakDate)

def parseArgs():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("database", type=str,
                           default="database.ledger",
                           help="database file")
    argparser.add_argument("--prices", type=str,
                           default="prices.ledger",
                           help="prices file")
    argparser.add_argument('--start-date',
                           type=lambda s: datetime.datetime.strptime(s, '%Y/%m/%d'),
                           required=True,
                           help="Start Date - YYYY/MM/DD")
    argparser.add_argument('--end-date',
                           type=lambda s: datetime.datetime.strptime(s, '%Y/%m/%d'),
                           required=True,
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

def main():
    args = parseArgs()
    if args.log_file:
        logging.basicConfig(filename=args.log_file,
                            filemode="w",
                            format='[%(name)s:%(levelname)s] %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p',
                            level=logging.INFO)

    journal, lines = read_journal(args.database, pedantic=False)

    start_date = args.start_date
    end_date = args.end_date
    s = start_date.strftime('%Y-%m-%d')
    e = end_date.strftime('%Y-%m-%d')
    print(f"Generating foreign asset report from {s} to {e}.")

    peakValuation = PeakValuation(start_date, end_date)
    foreign_accounts = []

    for txn in journal.contents:
        if not isinstance(txn, Transaction):
            continue
        if txn.date > end_date:
            continue
        for p in txn.contents:
            if not isinstance(p, Posting): continue
            if parser.is_virtual_account(p.account): continue
            if not p.account in foreign_accounts: continue
            logging.info(f"Processing posting by {txn.payee} on "
                         f"{txn.date.strftime('%Y-%m-%d')}.")
            peakValuation.applyPosting(p, txn.date)

    peakValuation.extendToEnd()
    for i in peakValuation.peakValues:
        peakDate, amount, latestDate = peakValuation.peakValues[i]
        account, lot = i
        a, b = amount2str(
            Amount(Decimal(1), lot), journal.get_commodity_format)
        c, d = amount2str(amount, journal.get_commodity_format)
        e = peakDate.strftime('%Y-%m-%d')
        print(f"{account} | {a + b} | Peak value was {c + d} on {e}.")

if __name__ == "__main__":
    main()
