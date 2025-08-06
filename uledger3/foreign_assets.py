#! /usr/bin/env python3

import argparse
from typing import Callable
from decimal import Decimal
import decimal
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
from uledger3.parser import parse_commodity, parse_date

logger = logging.getLogger(__name__)

def last_day_of_last_month(today):
    first = today.replace(day=1)
    last_month = first - datetime.timedelta(days=1)
    return last_month

class Valuation():

    def __init__(self, startDate, endDate):
        self.startDate = startDate
        self.endDate = endDate
        # {(Account, Lot): (Peak Date, Amount, Latest Date)}
        self.peakValues: dict[tuple(str, str), tuple(datetime, Amount, datetime)] = {}
        # {("AAPL", "USD"): [(t1, t2, 195, date), (t2, t3, 192, date)]}
        self.peakPrices: dict[tuple(str, str),
                              list(tuple(datetime, datetime, Decimal))] = {}
        # {(Account, Lot): (Initial Date, Amount)}
        self.initialValues: dict[tuple(str, str), tuple(datetime, Amount)] = {}
        # {("AAPL", "USD"): (192, date)}
        self.closingPrices: dict[tuple(str, str), tuple(Decimal, datetime)] = {}
        self.root = Account("Root")

    def getBalance(self, account, lot):
        b = self.root[account].balance
        return b[lot]

    def getClosingValue(self, account, lot):
        b = self.getBalance(account, lot)
        if not isinstance(lot, Lot):
            return (self.endDate, Amount(b, lot))
        commodity = lot.commodity
        currency = lot.price.commodity
        quantity = b
        price, date = self.getClosingPrice(commodity, currency)
        return (date, Amount(quantity * price, currency))

    def applyPosting(self, p, date):
        key = (p.account, p.amount.commodity)
        if date >= self.startDate and date <= self.endDate :
            self.updatePeakValues(key, date)
        self.root[p.account] += p.amount
        if key not in self.initialValues:
            if isinstance(p.amount.commodity, Lot):
                lot = p.amount.commodity
                price = lot.price.quantity
                currency = lot.price.commodity
                quantity = p.amount.quantity
            else:
                price = Decimal(1)
                currency = p.amount.commodity
                quantity = p.amount.quantity
            amount = Amount(price * quantity, currency)
            self.initialValues[key] = (date, amount)

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
        peakPrice = None
        while peakPrice is None:
            try:
                peakPrice = Decimal(input(f"Enter the peak price of {commodity} "
                                          f"between {s} and {e} in {currency}: "))
            except decimal.InvalidOperation:
                pass
        peakDate = None
        while peakDate is None:
            try:
                y = input(f"Enter the date of this price: ")
                peakDate = datetime.datetime.strptime(y, '%Y/%m/%d')
            except ValueError:
                pass
        z = (startDate, endDate, peakPrice, peakDate)
        try:
            self.peakPrices[(commodity, currency)].append(z)
        except KeyError:
            self.peakPrices[(commodity, currency)] = [z]
        self.peakPrices[(commodity, currency)].sort(key=lambda a: a[0])
        return z

    def readPeakPrices(self, fileHandle):
        for line in fileHandle:
            line = line.strip()
            if not line: continue
            tokens = [x.strip() for x in line.split(',')]
            if tokens[0] != "peak": continue
            assert len(tokens) == 7
            commodity, _ = parse_commodity(tokens[1])
            currency, _ = parse_commodity(tokens[2])
            startDate, _ = parse_date(tokens[3])
            endDate, _ = parse_date(tokens[4])
            peakPrice = Decimal(tokens[5])
            peakDate, _ = parse_date(tokens[6])
            entry = (startDate, endDate, peakPrice, peakDate)
            key = (commodity, currency)
            try:
                self.peakPrices[key].append(entry)
            except KeyError:
                self.peakPrices[key] = [entry]

    def printPeakPrices(self, fileHandle):
        line = "# peak, commodity, currency, startDate," \
            "endDate, price, peakDate"
        print(line, file=fileHandle)
        for key in self.peakPrices:
            commodity, currency = key
            for i in self.peakPrices[key]:
                startDate, endDate, peakPrice, peakDate = i
                line = "peak, "
                line += (commodity2str(commodity) + ", ")
                line += (commodity2str(currency) + ", ")
                line += (date2str(startDate) + ", ")
                line += (date2str(endDate) + ", ")
                line += (str(peakPrice) + ", ")
                line += date2str(peakDate)
                print(line, file=fileHandle)

    def getClosingPrice(self, commodity, currency):
        try:
            return self.closingPrices[(commodity, currency)]
        except KeyError:
            return self.newClosingPrice(commodity, currency)

    def newClosingPrice(self, commodity, currency):
        closingPrice = None
        while closingPrice is None:
            try:
                closingPrice = Decimal(
                    input(f"Enter the closing price of {commodity} "
                          f"in {currency}: "))
            except decimal.InvalidOperation:
                pass
        closingDate = None
        while closingDate is None:
            try:
                y = input(f"Enter the date of this price: ")
                closingDate = datetime.datetime.strptime(y, '%Y/%m/%d')
            except ValueError:
                pass
        z = (closingPrice, closingDate)
        self.closingPrices[(commodity, currency)] = z
        return z

    def readClosingPrices(self, fileHandle):
        for line in fileHandle:
            line = line.strip()
            if not line: continue
            tokens = [x.strip() for x in line.split(',')]
            if tokens[0] != "closing": continue
            assert len(tokens) == 5
            commodity, _ = parse_commodity(tokens[1])
            currency, _ = parse_commodity(tokens[2])
            closingPrice = Decimal(tokens[3])
            closingDate, _ = parse_date(tokens[4])
            key = (commodity, currency)
            self.closingPrices[key] = (closingPrice, closingDate)

    def printClosingPrices(self, fileHandle):
        line = "# closing, commodity, currency, price, date"
        print(line, file=fileHandle)
        for key in self.closingPrices:
            commodity, currency = key
            closingPrice, closingDate = self.closingPrices[key]
            line = "closing, "
            line += (commodity2str(commodity) + ", ")
            line += (commodity2str(currency) + ", ")
            line += (str(closingPrice) + ", ")
            line += date2str(closingDate)
            print(line, file=fileHandle)

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
    argparser.add_argument("--config-file", type=str,
                           required=True,
                           help="Config File")
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

def create_exchange(journal):
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

def main():
    args = parseArgs()
    if args.log_file:
        logging.basicConfig(filename=args.log_file,
                            filemode="w",
                            format='[%(name)s:%(levelname)s] %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p',
                            level=logging.INFO)

    journal, lines = read_journal(args.prices, pedantic=False)
    exchange = create_exchange(journal)

    journal, lines = read_journal(args.database, pedantic=False)

    start_date = args.start_date
    end_date = args.end_date
    s = start_date.strftime('%Y-%m-%d')
    e = end_date.strftime('%Y-%m-%d')
    print(f"Generating foreign asset report from {s} to {e}.")

    valuation = Valuation(start_date, end_date)
    with open(args.config_file, "r") as config_file:
        valuation.readPeakPrices(config_file)
    with open(args.config_file, "r") as config_file:
        valuation.readClosingPrices(config_file)

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
            valuation.applyPosting(p, txn.date)

    valuation.extendToEnd()
    for i in valuation.peakValues:
        account, lot = i
        a, b = amount2str(
            Amount(Decimal(1), lot), journal.get_commodity_format)
        tmp = b if isinstance(lot, Lot) else a
        print(f"{account} {tmp}")

        peakDate, amount, latestDate = valuation.peakValues[i]
        dateStr = peakDate.strftime('%Y-%m-%d')
        a, b = amount2str(amount, journal.get_commodity_format)
        amountStr = a + b
        print(f"> Peak value was {amountStr} on {dateStr}.")
        amount = convertForTax(
            exchange, peakDate, amount, args.base_currency)
        a, b = amount2str(amount, journal.get_commodity_format)
        amountStr = a + b
        print(f"> Peak value was {amountStr} on {dateStr}.")

        initialDate, amount = valuation.initialValues[i]
        dateStr = initialDate.strftime('%Y-%m-%d')
        c, d = amount2str(amount, journal.get_commodity_format)
        amountStr = c + d
        print(f"> Initial value was {amountStr} on {dateStr}.")
        amount = convertForTax(
            exchange, peakDate, amount, args.base_currency)
        a, b = amount2str(amount, journal.get_commodity_format)
        amountStr = a + b
        print(f"> Initial value was {amountStr} on {dateStr}.")

        closingDate, amount = valuation.getClosingValue(account, lot)
        dateStr = closingDate.strftime('%Y-%m-%d')
        c, d = amount2str(amount, journal.get_commodity_format)
        amountStr = c + d
        print(f"> Closing value was {amountStr} on {dateStr}.")
        amount = convertForTax(
            exchange, peakDate, amount, args.base_currency)
        a, b = amount2str(amount, journal.get_commodity_format)
        amountStr = a + b
        print(f"> Closing value was {amountStr} on {dateStr}.")

    with open(args.config_file, "w") as config_file:
        valuation.printPeakPrices(config_file)
        valuation.printClosingPrices(config_file)

def convertForTax(exchange, date, amount, currency):
    lastDay = last_day_of_last_month(date)
    x = exchange.get_price(lastDay, amount.commodity, currency)
    if x:
        logger.info(f"Found price: {x}")
        return Amount(amount.quantity * x, currency)
    else:
        logger.info(f"Unable to convert {amount.commodity} to {currency}.")
        return amount

if __name__ == "__main__":
    main()
