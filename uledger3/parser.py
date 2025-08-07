from typing import Union
from typing import NamedTuple
from typing import Iterable
from datetime import datetime
import re
from decimal import Decimal

class CommodityFormat(NamedTuple):
    comma: bool
    precision: int
    position: str
    space: bool

class AccountAlias(NamedTuple):
    alias: str

class ParseError(Exception):
    def __init__(self, message: str,
                 position: Union["Position", None] = None,
                 context: str = ""):
        if not position:
            super().__init__(message)
        elif context:
            super().__init__(
                f"{message}\n"
                f"line: {position.line}, column: {position.column}\n"
                f"{context}\n" + (position.column * " ") + "^"
            )
        else:
            super().__init__(
                f"{message}\n"
                f"line: {position.line}, column: {position.column}\n"
            )

class Journal():
    def __init__(self, name: str):
        self.name = name
        self.contents: list[str |
                            AccountDecl |
                            CommodityDecl |
                            PriceDecl |
                            Transaction] = []
        self.default_commodity: str = None
        self.account_aliases: dict[str, str] = {}
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

class Position(NamedTuple):
    line: int
    column: int

class Span(NamedTuple):
    start: Position
    end: Position

class Entity():
    def __init__(self, span: Span | None = None):
        self.span: Span | None = span

class AccountDecl(Entity):
    def __init__(self, account: str):
        super().__init__()
        self.account = account
        self.contents: list[AccountAlias | str] = []

class CommodityDecl(Entity):
    def __init__(self, commodity: str):
        super().__init__()
        self.commodity = commodity
        self.contents: list[CommodityFormat | str] = []

class PriceDecl(Entity):
    def __init__(self, commodity: str, date: datetime, price: "Amount"):
        super().__init__()
        self.commodity = commodity
        self.date = date
        self.price = price

class Transaction(Entity):
    def __init__(self, date: datetime, status: str, payee: str):
        super().__init__()
        self.date = date
        self.status = status
        self.payee = payee
        self.contents: list[str | Posting] = []

class Lot(NamedTuple):
    commodity: str
    date: datetime
    price: "Amount"

class Amount(Entity):
    def __init__(self, quantity: Decimal, commodity: Lot | str,
                 unit_rate: Union["Amount", None] = None):
        super().__init__()
        self._quantity = quantity
        self._commodity = commodity
        # Unit rate is specified with the "@" syntax.
        self._unit_rate = unit_rate
        if unit_rate:
            assert isinstance(commodity, str)
    @property
    def quantity(self):
        return self._quantity
    @property
    def commodity(self):
        return self._commodity
    @property
    def unit_rate(self):
        return self._unit_rate
    def __hash__(self):
        return hash((self._quantity, self._commodity, self._unit_rate))
    def __eq__(self, other):
        if not isinstance(other, Amount):
            return None
        return (self.quantity == other.quantity and
                self.commodity == other.commodity and
                self.unit_rate == other.unit_rate)
    def __repr__(self):
        return f"Amount({self.quantity}, {self.commodity}, {self.unit_rate})"

class Posting(Entity):
    def __init__(self, account: str, amount: Amount, assertion: Amount = None):
        super().__init__()
        self.account = account
        self.amount = amount
        self.assertion = assertion

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

def parse_commodity(line: str, begin: int = 0, relaxed=False) \
    -> tuple[str | None, int]:
    if len(line) <= begin:
        return (None, len(line))
    line = line[begin:]
    quoted = '["\']([^"\']+)["\']'
    unquoted = '[^\s@0-9-"\'&]+'
    if relaxed:
        unquoted = '[^\s@"\']+'
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

def parse_account_name(line: str, begin: int = 0) \
    -> tuple[str | None, int]:
    if len(line) <= begin:
        return (None, len(line))
    line = line[begin:]
    m = re.match('[^\s]([^\s]| ?[^\s])*', line)
    if m:
        x = m.group(0)
        if x[0] == "(" and x[-1] != ")":
            return (None, begin)
        return (m.group(0), begin + m.end())
    return (None, begin)

def parse_keyword(keyword: str, line: str, begin: int = 0) \
    -> tuple[str | None, int]:
    if len(line) <= begin:
        return (None, len(line))
    line = line[begin:]
    m = re.match(keyword, line)
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

def strip_virtual_account(account: str) -> str:
    if is_virtual_account(account):
        return account[1:-1]
    else:
        return account

def is_virtual_account(account: str) -> bool:
    if len(account) > 1 and account[0] == "(" and account[-1] == ")":
        return True
    else:
        return False

class Parser():
    def __init__(self, name: str, pedantic: bool = False):
        self.journal = Journal(name)
        self._current_line_number = 0
        self._current_block = None
        self._pedantic = pedantic

    def _create_span(self, begin: int, end: int) -> Span:
        return Span(
            Position(self._current_line_number, begin),
            Position(self._current_line_number, end)
        )

    def _pedantic_check_commodity(self,
                                  commodity: str,
                                  line: str,
                                  begin: int) -> None:
        if self._pedantic:
            if commodity not in self.journal.declared_commodities:
                raise ParseError(
                    "Commodity '{}' not declared".format(commodity),
                    Position(self._current_line_number, begin), line)

    def _pedantic_check_account(self,
                                account: str,
                                line: str,
                                begin: int) -> None:
        if self._pedantic:
            account = strip_virtual_account(account)
            if account not in self.journal.declared_accounts:
                raise ParseError(
                    "Account '{}' not declared".format(account),
                    Position(self._current_line_number, begin), line)

    def _parse_balance_assertion(self, line: str, begin: int) \
        -> tuple[Amount | None, int]:
        if len(line) <= begin:
            return (None, len(line))
        space, consumed = parse_space(line, begin)
        if line[consumed] != "=":
            return (None, begin)
        consumed += 1
        space, consumed = self._parse_space_or_error(
            "Balance assertion ill formed.", line, consumed)
        amount, consumed = self._parse_amount(line, consumed)
        if not amount:
            raise ParseError(
                "Balance assertion ill formed.",
                Position(self._current_line_number, consumed), line)
        return (amount, consumed)

    def _parse_amount(self, line: str, begin: int = 0) \
        -> tuple[Amount | None, int]:
        if len(line) <= begin:
            return (None, len(line))
        amount_1, consumed = parse_simple_amount(line, begin)
        if not amount_1:
            return (None, begin)
        amount_1, cmdty_fmt = amount_1
        if not amount_1.commodity and self.journal.default_commodity:
            amount_1 = Amount(amount_1.quantity, self.journal.default_commodity)
        self._pedantic_check_commodity(amount_1.commodity, line, begin)
        amount_1.span = self._create_span(begin, consumed - 1)
        self._update_inferred_commodity_format(amount_1.commodity, cmdty_fmt)
        space, consumed = parse_space(line, consumed)
        if len(line) <= consumed:
            assert len(line) == consumed
            return (amount_1, consumed)
        elif line[consumed] == "@":
            consumed += 1
            space, consumed_x = parse_space(line, consumed)
            amount_2, consumed = parse_simple_amount(line, consumed_x)
            if not amount_2:
                raise ParseError("Expected unit rate",
                                 Position(self._current_line_number, consumed),
                                 line)
            amount_2, cmdty_fmt = amount_2
            if not amount_2.commodity and self.journal.default_commodity:
                amount_2 = Amount(amount_2.quantity, self.journal.default_commodity)
            amount_2.span = self._create_span(consumed_x, consumed - 1)
            self._pedantic_check_commodity(amount_2.commodity, line, consumed_x)
            self._update_inferred_commodity_format(amount_2.commodity, cmdty_fmt)
            x = Amount(amount_1.quantity, amount_1.commodity, amount_2)
            x.span = self._create_span(begin, consumed - 1)
            return (x, consumed)
        else:
            consumed_x = consumed
            lot, consumed = parse_lot_date_and_price(line, consumed)
            if not lot:
                return (amount_1, consumed)
            date, price, cmdty_fmt = lot
            self._pedantic_check_commodity(price.commodity, line, consumed_x)
            self._update_inferred_commodity_format(price.commodity, cmdty_fmt)
            lot = Lot(amount_1.commodity, date, price)
            amount = Amount(amount_1.quantity, lot)
            amount.span = self._create_span(begin, consumed - 1)
            return (amount, consumed)

    def _update_inferred_commodity_format(
            self, commodity: str, new_format: CommodityFormat) -> None:
        if commodity in self.journal.inferred_commodity_formats:
            old_format = self.journal.inferred_commodity_formats[commodity]
            comma = old_format.comma or new_format.comma
            precision = max(old_format.precision, new_format.precision)
            position = old_format.position
            space = old_format.space
            self.journal.inferred_commodity_formats[commodity] = \
                CommodityFormat(comma, precision, position, space)
        else:
            self.journal.inferred_commodity_formats[commodity] = new_format

    def _parse_space_or_error(self,
                              message: str,
                              line: str, begin: int) -> tuple[str, int]:
        space, consumed = parse_space(line, begin)
        if not space:
            raise ParseError(
                message,
                Position(self._current_line_number, consumed),
                line)
        return (space, consumed)

    def _finish_parse_commodity_decl(self, line: str, begin: int = 0) \
        -> CommodityDecl:
        commodity, consumed = parse_keyword("commodity", line, begin)
        assert commodity
        space, consumed = self._parse_space_or_error(
            "Commodity declaration not well formed.", line, consumed)
        commodity, consumed = parse_commodity(line, consumed)
        space, consumed = parse_space(line, consumed)
        comment, consumed = parse_comment(line, consumed)
        if (not commodity) or (consumed < len(line)):
            raise ParseError(
                "Commodity declaration not well formed",
                Position(self._current_line_number, consumed), line)
        return CommodityDecl(commodity)

    def _finish_parse_account_decl(self, line: str, begin: int = 0) \
        -> AccountDecl:
        account, consumed = parse_keyword("account", line, begin)
        assert account
        space, consumed = self._parse_space_or_error(
            "Price declaration not well formed.", line, consumed)
        account, consumed = parse_account_name(line, consumed)
        space, consumed = parse_space(line, consumed)
        comment, consumed = parse_comment(line, consumed)
        if (not account) or (consumed < len(line)):
            raise ParseError(
                "Account declaration not well formed",
                Position(self._current_line_number, consumed), line)
        return AccountDecl(account)

    def _finish_parse_price_decl(self, line: str, begin: int = 0) \
        -> PriceDecl:
        P, consumed = parse_keyword("P", line, begin)
        assert P
        space, consumed = self._parse_space_or_error(
            "Price declaration not well formed.", line, consumed)
        date, consumed = parse_date(line, consumed)
        space, consumed = self._parse_space_or_error(
            "Price declaration not well formed.", line, consumed)
        commodity, consumed = parse_commodity(line, consumed, relaxed=True)
        price = None
        if commodity:
            space, consumed = parse_space(line, consumed)
            price, consumed = parse_simple_amount(line, consumed)
        if (not price) or (not commodity) or (consumed < len(line)):
            raise ParseError(
                "Price declaration not well formed",
                Position(self._current_line_number, consumed), line)
        price, fmt = price
        self._update_inferred_commodity_format(price.commodity, fmt)
        return PriceDecl(commodity, date, price)

    def _finish_parse_transaction_start(self, line: str, begin: int = 0) \
        -> Transaction:
        line = line.rstrip()
        date, consumed = parse_date(line, begin)
        assert date
        if len(line) == consumed:
            return Transaction(date, None, None)
        space, consumed = self._parse_space_or_error(
            "Transaction header not well formed.", line, consumed)
        status, consumed = parse_keyword("\*|\!", line, consumed)
        if len(line) == consumed:
            return Transaction(date, status, None)
        if status:
            space, consumed = self._parse_space_or_error(
                "Transaction header not well formed.", line, consumed)
        return Transaction(date, status, line[consumed:])

    def _finish_parse_commodity_decl_contents(self, line: str, begin: int = 0) \
        -> str | CommodityFormat:
        line = line.rstrip()
        space, consumed = self._parse_space_or_error(
            "Expected indentation.", line, begin)
        fmt, consumed = parse_keyword("format", line, consumed)
        default, consumed = parse_keyword("default", line, consumed)
        if fmt:
            space, consumed = self._parse_space_or_error(
                "Format statement not well formed.", line, consumed)
            fmt, consumed =  parse_simple_amount(line, consumed)
            space, consumed = parse_space(line, consumed)
            comment, consumed = parse_comment(line, consumed)
            if (not fmt) or (consumed < len(line)):
                raise ParseError(
                    "Format statement not well formed",
                    Position(self._current_line_number, consumed), line)
            return fmt[1]
        elif default:
            return "default"
        else:
            # rstripped line definitely has some more content.
            assert len(line) > consumed
            return line[consumed:]

    def _finish_parse_account_decl_contents(self, line: str, begin: int = 0) \
        -> str:
        line = line.rstrip()
        space, consumed = self._parse_space_or_error(
            "Expected indentation.", line, begin)
        alias, consumed = parse_keyword("alias", line, consumed)
        if alias:
            space, consumed = self._parse_space_or_error(
                "Format statement not well formed.", line, consumed)
            account, consumed = parse_account_name(line, consumed)
            return AccountAlias(account)
        else:
            # rstripped line definitely has some more content.
            assert len(line) > consumed
            return line[consumed:]

    def _finish_parse_transaction_contents(self, line: str, begin: int = 0) \
        -> str | Posting:
        line = line.rstrip()
        space, consumed = self._parse_space_or_error(
            "Expected indentation.", line, begin)
        # rstripped line definitely has some more content.
        comment, consumed = parse_comment(line, consumed)
        if comment:
            return comment
        consumed_x = consumed
        account, consumed = parse_account_name(line, consumed)
        if not account:
            raise ParseError(
                "Posting (account) not well formed",
                Position(self._current_line_number, consumed), line)
        if is_virtual_account(account):
            x = strip_virtual_account(account)
            if x in self.journal.account_aliases:
                y = self.journal.account_aliases[x]
                account = account[0] + y + account[-1]
        elif account in self.journal.account_aliases:
            account = self.journal.account_aliases[account]
        self._pedantic_check_account(account, line, consumed_x)
        consumed_x = consumed
        space, consumed = parse_space(line, consumed)
        comment, consumed = parse_comment(line, consumed)
        if len(line) == consumed:
            return Posting(account, None)
        space, consumed = parse_hard_space(line, consumed_x)
        if not space:
            raise ParseError(
                "Posting not well formed",
                Position(self._current_line_number, consumed), line)
        amount, consumed = self._parse_amount(line, consumed)
        assertion, consumed = self._parse_balance_assertion(line, consumed)
        space, consumed = parse_space(line, consumed)
        comment, consumed = parse_comment(line, consumed)
        if (not amount) or (consumed < len(line)):
            raise ParseError("Posting not well formed",
                Position(self._current_line_number, consumed), line)
        return Posting(account, amount, assertion)

    def parse_line(self, line: str) -> None:
        self._current_line_number += 1

        line = line.rstrip()
        if not line:
            self.journal.contents.append(line)
            return None

        commodity, _ = parse_keyword("commodity", line)
        account,   _ = parse_keyword("account", line)
        P,         _ = parse_keyword("P", line)
        tag,       _ = parse_keyword("tag", line)
        date,      _ = parse_date(line)
        indent,    _ = parse_space(line)
        comment,   _ = parse_comment(line)

        line_span = self._create_span(0, len(line) - 1)
        line_end = Position(self._current_line_number, len(line) - 1)

        if commodity:
            c = self._finish_parse_commodity_decl(line)
            c.span = line_span
            self.journal.contents.append(c)
            self.journal.declared_commodities.add(c.commodity)
        elif account:
            a = self._finish_parse_account_decl(line)
            a.span = line_span
            self.journal.contents.append(a)
            self.journal.declared_accounts.add(a.account)
        elif P:
            p = self._finish_parse_price_decl(line)
            p.span = line_span
            self.journal.contents.append(p)
        elif date:
            t = self._finish_parse_transaction_start(line)
            t.span = line_span
            self.journal.contents.append(t)
        elif indent:
            if len(self.journal.contents) == 0:
                raise ParseError(
                    "Unexpected indent",
                    Position(self._current_line_number, 0), line)
            x = self.journal.contents[-1]
            if isinstance(x, CommodityDecl):
                y = self._finish_parse_commodity_decl_contents(line)
                if isinstance(y, CommodityFormat):
                    self.journal.declared_commodity_formats[x.commodity] = y
                elif y == "default":
                    self.journal.default_commodity = x.commodity
                x.contents.append(y)
                x.span = Span(x.span.start, line_end)
            elif isinstance(x, AccountDecl):
                y = self._finish_parse_account_decl_contents(line)
                if isinstance(y, AccountAlias):
                    self.journal.account_aliases[y.alias] = x.account
                x.contents.append(y)
                x.span = Span(x.span.start, line_end)
            elif isinstance(x, Transaction):
                y = self._finish_parse_transaction_contents(line)
                if isinstance(y, Posting):
                    y.span = line_span
                x.contents.append(y)
                x.span = Span(x.span.start, line_end)
            else:
                raise ParseError(
                    "Unexpected indent",
                    Position(self._current_line_number, 0), line)
        elif comment:
            self.journal.contents.append(comment)
        elif tag:
            self.journal.contents.append(line)
        else:
            raise ParseError(
                "Unable to parse line",
                Position(self._current_line_number, 0), line)

    def parse_lines(self, lines: Iterable[str]) -> None:
        for i in lines:
            self.parse_line(i)
