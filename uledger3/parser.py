from typing import Union
from collections import namedtuple
from datetime import datetime
import re
from decimal import Decimal

CommodityFormat = namedtuple("CommodityFormat",
                             ["comma", "precision", "position", "space"])
class Ledger():
    def __init__(self, name: str):
        self.name = name
        self.contents: list[str |
                            AccountDecl |
                            CommodityDecl |
                            PriceDecl |
                            Transaction] = []
        self.declared_commodities: set[str] = set()
        self.declared_accounts: set[str] = set()
        self.declared_commodity_formats: dict[str, CommodityFormat] = {}
        self.inferred_commodity_formats: dict[str, CommodityFormat] = {}
    def get_commodity_format(self, commodity: str) -> CommodityFormat | None:
        if commodity in self.declared_commodity_formats:
            return self.declared_commodity_formats[commodity]
        if commodity in self.inferred_commodity_formats:
            return self.inferred_commodity_formats[commodity]
        return None

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
                 unit_rate: Union["Amount", None] = None):
        self.quantity = quantity
        self.commodity = commodity
        # Unit rate is specified with the "@" syntax.
        self.unit_rate = unit_rate
        if unit_rate:
            assert isinstance(commodity, str)
    def __eq__(self, other):
        if not isinstance(other, Amount):
            return None
        return (self.quantity == other.quantity and
                self.commodity == other.commodity and
                self.unit_rate == other.unit_rate)
    def __repr__(self):
        return f"Amount({self.quantity}, {self.commodity}, {self.unit_rate})"

class Posting(Entity):
    def __init__(self, account: str, amount: Amount):
        self.account = account
        self.amount = amount

def parse_date(line: str, begin: int = 0) -> tuple[datetime | None, int]:
    if len(line) <= begin:
        return (None, len(line))
    line = line[begin:]
    m = re.match("(\d{4})/(\d{1,2})/(\d{1,2})", line)
    if not m:
        m = re.match("(\d{4})-(\d{1,2})-(\d{1,2})", line)
    if not m:
        return (None, begin)
    x = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return (x, begin + m.end())

def parse_quantity(line: str, begin: int = 0) \
    -> tuple[tuple[Decimal, int, bool] | None, int]:
    if len(line) <= begin:
        return (None, len(line))
    line = line[begin:]
    m = re.match("-?[0-9,]+(\.[0-9]+)?", line)
    if not m:
        return (None, begin)
    comma = "," in m.group(0)
    precision = 0
    if m.group(1):
        precision = len(m.group(1)) - 1
    return ((Decimal(m.group(0).replace(',', '')), comma, precision),
            begin + m.end())

def parse_commodity(line: str, begin: int = 0) \
    -> tuple[str | None, int]:
    if len(line) <= begin:
        return (None, len(line))
    line = line[begin:]
    quoted = '["\']([^"\']+)["\']'
    unquoted = '[^\s0-9-"\']+'
    m = re.match(quoted, line)
    if m:
        return (m.group(1), begin + m.end())
    m = re.match(unquoted, line)
    if m:
        return (m.group(0), begin + m.end())
    return (None, begin)

def parse_hard_space(line: str, begin: int = 0) \
    -> tuple[str | None, int]:
    if len(line) <= begin:
        return (None, len(line))
    line = line[begin:]
    m = re.match('[\s]{2,}|\t', line)
    if m:
        return (m.group(0), begin + m.end())
    return (None, begin)

def parse_space(line: str, begin: int = 0) \
    -> tuple[str | None, int]:
    if len(line) <= begin:
        return (None, len(line))
    line = line[begin:]
    m = re.match('[\s]+', line)
    if m:
        return (m.group(0), begin + m.end())
    return (None, begin)

def parse_simple_amount(line: str, begin: int = 0) \
    -> tuple[tuple[Amount, CommodityFormat] | None, int]:
    if len(line) <= begin:
        return (None, len(line))

    commodity, consumed = parse_commodity(line, begin)
    if commodity:
        # [commodity] [quantity]
        space, consumed = parse_space(line, consumed)
        quantity, consumed = parse_quantity(line, consumed)
        if not quantity:
            return (None, begin)
        quantity, comma, precision = quantity
        amount = Amount(quantity, commodity)
        return ((amount,
                 CommodityFormat(comma, precision, "left", bool(space))),
                consumed)
    else:
        # [quantity] [commodity]
        quantity, consumed = parse_quantity(line, begin)
        if not quantity:
            return (None, begin)
        quantity, comma, precision = quantity
        space, consumed = parse_space(line, consumed)
        commodity, consumed = parse_commodity(line, consumed)
        if not commodity:
            return (None, begin)
        amount = Amount(quantity, commodity)
        return ((amount,
                 CommodityFormat(comma, precision, "right", bool(space))),
                consumed)

def parse_lot_date(line: str, begin: int = 0) -> tuple[datetime | None, int]:
    if len(line) <= begin:
        return (None, len(line))
    if line[begin] != "[":
        return (None, begin)
    consumed = begin + 1
    space, consumed = parse_space(line, consumed)
    date, consumed = parse_date(line, consumed)
    if (date is None) or (len(line) <= consumed):
        return (None, begin)
    space, consumed = parse_space(line, consumed)
    if line[consumed] != "]":
        return (None, begin)
    consumed += 1
    return (date, consumed)

def parse_lot_price(line: str, begin: int = 0) \
    -> tuple[tuple[Amount, CommodityFormat] | None, int]:
    if len(line) <= begin:
        return (None, len(line))
    if line[begin] != "{":
        return (None, begin)
    consumed = begin + 1
    space, consumed = parse_space(line, consumed)
    amount, consumed = parse_simple_amount(line, consumed)
    if (amount is None) or (len(line) <= consumed):
        return (None, begin)
    space, consumed = parse_space(line, consumed)
    if line[consumed] != "}":
        return (None, begin)
    consumed += 1
    return (amount, consumed)

def parse_lot_date_and_price(line: str, begin: int = 0) \
    -> tuple[tuple[datetime, Amount, CommodityFormat] | None, int]:
    if len(line) <= begin:
        return (None, len(line))
    lot_price, consumed = parse_lot_price(line, begin)
    if lot_price:
        # [lot_price] [lot_date]
        space, consumed = parse_space(line, consumed)
        lot_date, consumed = parse_lot_date(line, consumed)
        if not lot_date:
            return (None, begin)
        lot_price, commodity_format = lot_price
        return ((lot_date, lot_price, commodity_format), consumed)
    else:
        # [lot_date] [lot_price]
        lot_date, consumed = parse_lot_date(line, begin)
        if not lot_date:
            return (None, begin)
        space, consumed = parse_space(line, consumed)
        lot_price, consumed = parse_lot_price(line, consumed)
        if not lot_price:
            return (None, begin)
        lot_price, commodity_format = lot_price
        return ((lot_date, lot_price, commodity_format), consumed)

def parse_comment(line: str, begin: int = 0) \
    -> tuple[str | None, int]:
    if len(line) <= begin:
        return (None, len(line))
    if line[begin] == ";":
        return (line[begin:], len(line))
    else:
        return (None, begin)

class Parser():
    def __init__(self, name: str):
        self.ledger = Ledger(name)

    def _parse_amount(self, line: str, begin: int = 0):
        pass

    def _update_inferred_commodity_format(
            self, commodity: str, new_format: CommodityFormat) -> None:
        if commodity in self.ledger.inferred_commodity_formats:
            old_format = self.ledger.inferred_commodity_formats[commodity]
            comma = old_format.comma or new_format.comma
            precision = max(old_format.precision, new_format.precision)
            position = old_format.position
            space = old_format.space
            self.ledger.inferred_commodity_formats[commodity] = \
                CommodityFormat(comma, precision, position, space)
        else:
            self.ledger.inferred_commodity_formats[commodity] = new_format
