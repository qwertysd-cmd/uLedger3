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

class Amount(Entity):
    def __init__(self, quantity: Decimal, commodity: Lot | str):
        self.quantity = quantity
        self.commodity = commodity

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

def parse_quantity(line: str) -> tuple[Decimal, int] | None:
    m = re.match("-?[0-9,.]+", line)
    if not m:
        return None
    return (Decimal(m.group(0).replace(',', '')), m.end())

