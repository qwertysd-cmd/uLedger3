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
        # {(Account, Lot)}
        self.keys = set()
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
        self.consolidatedRoot = Account("Consolidated Root")

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
        self.keys.add(key)
        if date >= self.startDate and date <= self.endDate :
            self.updatePeakValues(key, date)
        self.root[p.account] += p.amount
        if isinstance(p.amount.commodity, Lot):
            self.consolidatedRoot["Assets"] += Amount(
                p.amount.quantity, p.amount.commodity.commodity)
        else:
            self.consolidatedRoot["Assets"] += p.amount
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
        logger.info(f"Updating peak date from {oldPeakDate} to {newPeakDate}.")
        if (newPeakAmount.quantity > oldPeakAmount.quantity):
            self.peakValues[key] = (newPeakDate, newPeakAmount, currentDate)
        else:
            self.peakValues[key] = (oldPeakDate, oldPeakAmount, currentDate)

    def extendToEnd(self):
        for i in self.keys:
            self.updatePeakValues(i, self.endDate)

    def getPeakPrice(self, commodity, currency, startDate, endDate):
        if commodity == currency: return (Decimal(1), endDate)
        if commodity == "": return (Decimal(1), endDate)
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
    argparser.add_argument("--commodity", type=str,
                           help="Commodity")
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

    foreignAccounts = []]
    dividendAccounts = []
    payee2cmdty = {}
    # {(Account, Lot): Amount}
    dividendValues: dict[tuple(str, str), Amount] = {}

    for txn in journal.contents:
        if not isinstance(txn, Transaction):
            continue
        if txn.date > end_date:
            continue
        for p in txn.contents:
            if not isinstance(p, Posting): continue
            if parser.is_virtual_account(p.account): continue
            if isinstance(p.amount.commodity, Lot):
                commodity = p.amount.commodity.commodity
                if args.commodity and commodity != args.commodity: continue
            d = txn.date.strftime('%Y-%m-%d')
            if p.account in foreignAccounts:
                logger.info(f"Processing posting by {txn.payee} on {d}.")
                valuation.applyPosting(p, txn.date)
            if (p.account in dividendAccounts and txn.payee in payee2cmdty):
                a = p.amount
                assert isinstance(a.commodity, str)
                b = valuation.consolidatedRoot["Assets"].balance
                cmdty = payee2cmdty[txn.payee]
                qty_tot = b[cmdty]
                logger.info(f"Dividend by {txn.payee} on {d}.")
                logger.info(f"Current total quantity of {cmdty} is {qty_tot}.")
                a2, x = convertForTax(exchange, txn.date, a, args.base_currency)
                a_str = _amount2str(a, journal.get_commodity_format)
                a2_str = _amount2str(a2, journal.get_commodity_format)
                logger.info(f"Total dividend is {a_str} or {a2_str} "
                            f"(Conversion Rate: {x})")
                for i in foreignAccounts:
                    b = valuation.root[i].balance
                    for lot in b:
                        if not isinstance(lot, Lot): continue
                        if lot.commodity != cmdty: continue
                        qty = b[lot]
                        div = qty * a2.quantity / qty_tot
                        amt = Amount(div, args.base_currency)
                        amt_str = _amount2str(amt, journal.get_commodity_format)
                        logger.info(f"Dividend of {amt_str} on {lot} in {i}"
                                    f"(Conversion Rate: {x})")
                        try:
                            x = dividendValues[(i, lot)]
                            dividendValues[(i, lot)] = Amount(
                                -div + x.quantity, args.base_currency)
                        except KeyError:
                            dividendValues[(i, lot)] = Amount(
                                -div, args.base_currency)

    valuation.extendToEnd()
    for i in valuation.peakValues:
        account, lot = i
        a, b = amount2str(
            Amount(Decimal(1), lot), journal.get_commodity_format)
        tmp = b if isinstance(lot, Lot) else a
        print(f"\n{account} {tmp}")

        peakDate, amount, latestDate = valuation.peakValues[i]
        printValues(peakDate, amount, journal.get_commodity_format,
                    args.base_currency, "Peak Value", exchange)

        initialDate, amount = valuation.initialValues[i]
        printValues(initialDate, amount, journal.get_commodity_format,
                    args.base_currency, "Initial Value", exchange)

        closingDate, amount = valuation.getClosingValue(account, lot)
        printValues(closingDate, amount, journal.get_commodity_format,
                    args.base_currency, "Closing Value", exchange)

        try:
            amount = dividendValues[(account, lot)]
            amountStr = _amount2str(amount, journal.get_commodity_format)
            print(f"  > Dividend Paid: {amountStr}")
        except KeyError:
            print(f"  > Dividend Paid: 0")

    with open(args.config_file, "w") as config_file:
        valuation.printPeakPrices(config_file)
        valuation.printClosingPrices(config_file)

def printValues(date, amount, formatFunction, currency,
                description, exchange):
    dateStr = date.strftime('%Y-%m-%d')
    amountStr = _amount2str(amount, formatFunction)
    amount, x = convertForTax(exchange, date, amount, currency)
    amountStr2 = _amount2str(amount, formatFunction)
    print(f"  > {description} was {amountStr} on {dateStr}"
          f" or {amountStr2} (Conversion Rate: {x}).")

def _amount2str(amount, formatFunction):
    if isinstance(amount.commodity, str):
        fmt = formatFunction(amount.commodity)
        if fmt:
            q = Decimal(10) ** -fmt.precision # 2 places --> '0.01'
            v = amount.quantity.quantize(q)
            amount = Amount(v, amount.commodity)
    a, b = amount2str(amount, formatFunction)
    return a + b

def convertForTax(exchange, date, amount, currency):
    lastDay = last_day_of_last_month(date)
    x = exchange.get_price(lastDay, amount.commodity, currency)
    if x:
        return (Amount(amount.quantity * x, currency), x)
    else:
        logger.info(f"Unable to convert {amount.commodity} to {currency}.")
        return (amount, 1)

if __name__ == "__main__":
    main()
