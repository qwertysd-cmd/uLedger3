from typing import Union
from collections import namedtuple
from datetime import datetime
import re
from decimal import Decimal

class Ledger():
    def __init__(self, name: str):
        self.name = name
        self.contents: list[str | AccountDecl | CommodityDecl | PriceDecl] = []

Position = namedtuple("Position", ["line", "column"])
Span = namedtuple("Span", ["start", "end"])

class Entity():
    def __init__(self):
        self.span: Span | None = None

class AccountDecl(Entity):
    pass

class CommodityDecl(Entity):
    pass

class PriceDecl(Entity):
    pass

class Transaction(Entity):
    def __init__(self, date: datetime, status: str, payee: str):
        super().__init__(self)
        self.date = date
        self.status = status
        self.payee = payee
        self.contents: list[str | Posting] = []

class Lot():
    def __init__(self, commodity: str, date: datetime, price: "Amount"):
        self.commodity = commodity
        self.date = date
        self.price = price
        assert isinstance(price.commodity, str)

class Amount(Entity):
    def __init__(self, quantity: Decimal, commodity: Lot | str,
                 at_rate: Union["Amount", None] = None):
        self.quantity = quantity
        self.commodity = commodity
        self.at_rate = at_rate
        if at_rate:
            assert isinstance(commodity, str)

class Posting(Entity):
    def __init__(self, account: str, amount: Amount):
        self.account = account
        self.amount = amount

def parse_date(line: str) -> tuple[datetime, int] | None:
    m = re.match("(\d{4})/(\d{1,2})/(\d{1,2})", line)
    if not m:
        m = re.match("(\d{4})-(\d{1,2})-(\d{1,2})", line)
    if not m:
        return None
    x = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return (x, m.end())

def parse_quantity(line: str) -> tuple[Decimal, int, bool, int] | None:
    m = re.match("-?[0-9,]+(\.[0-9]+)?", line)
    if not m:
        return None
    comma = "," in m.group(0)
    precision = 0
    if m.group(1):
        precision = len(m.group(1)) - 1
    return (Decimal(m.group(0).replace(',', '')), m.end(), comma, precision)

def parse_commodity(line: str) -> tuple[str, int] | None:
    quoted = '["\']([^"\']+)["\']'
    unquoted = '[^\s0-9-"\']+'
    m = re.match(quoted, line)
    if m:
        return (m.group(1), m.end())
    m = re.match(unquoted, line)
    if m:
        return (m.group(0), m.end())

def parse_hard_space(line: str) -> tuple[str, int] | None:
    m = re.match('[\s]{2,}|\t', line)
    if m:
        return (m.group(0), m.end())

def parse_space(line: str) -> tuple[str, int] | None:
    m = re.match('[\s]+', line)
    if m:
        return (m.group(0), m.end())
