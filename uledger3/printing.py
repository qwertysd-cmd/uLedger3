from decimal import Decimal
from datetime import datetime
from typing import Callable

import uledger3.parser as parser
from uledger3.parser import Amount, Lot, Transaction, \
    Posting, Position, Journal, Entity
from uledger3.ledger import Account

# https://docs.python.org/3/library/decimal.html#decimal.getcontext
def moneyfmt(value, places=2, curr='', sep=',', dp='.',
             pos='', neg='-', trailneg=''):
    """Convert Decimal to a money formatted string.

    places:  required number of places after the decimal point
    curr:    optional currency symbol before the sign (may be blank)
    sep:     optional grouping separator (comma, period, space, or blank)
    dp:      decimal point indicator (comma or period)
             only specify as blank when places is zero
    pos:     optional sign for positive numbers: '+', space or blank
    neg:     optional sign for negative numbers: '-', '(', space or blank
    trailneg:optional trailing minus indicator:  '-', ')', space or blank

    >>> d = Decimal('-1234567.8901')
    >>> moneyfmt(d, curr='$')
    '-$1,234,567.89'
    >>> moneyfmt(d, places=0, sep='.', dp='', neg='', trailneg='-')
    '1.234.568-'
    >>> moneyfmt(d, curr='$', neg='(', trailneg=')')
    '($1,234,567.89)'
    >>> moneyfmt(Decimal(123456789), sep=' ')
    '123 456 789.00'
    >>> moneyfmt(Decimal('-0.02'), neg='<', trailneg='>')
    '<0.02>'

    """
    q = Decimal(10) ** -places      # 2 places --> '0.01'
    sign, digits, exp = value.quantize(q).as_tuple()
    result = []
    digits = list(map(str, digits))
    build, next = result.append, digits.pop
    if sign:
        build(trailneg)
    for i in range(places):
        build(next() if digits else '0')
    if places:
        build(dp)
    if not digits:
        build('0')
    i = 0
    while digits:
        build(next())
        i += 1
        if i == 3 and digits:
            i = 0
            build(sep)
    build(curr)
    build(neg if sign else pos)
    return ''.join(reversed(result))

def commodity2str(commodity: str) -> str:
    p, _ = parser.parse_commodity(commodity)
    if p == commodity:
        return commodity
    return f'"{commodity}"'

def date2str(date: datetime) -> str:
    return date.strftime('%Y/%m/%d')

def _is_representable_by_precision(amount: Amount, precision: int):
    x = amount.quantity.quantize(Decimal(10) ** -precision)
    if amount.quantity == x:
        return True

def amount2str(amount: Amount, format_function,
               force_prec: bool = False, noquote: bool = False) \
    -> tuple[str, str]:
    assert isinstance(amount.quantity, Decimal)
    if isinstance(amount.commodity, str):
        commodity = amount.commodity
    else:
        assert isinstance(amount.commodity, Lot)
        commodity = amount.commodity.commodity
    fmt = format_function(commodity)
    if force_prec or _is_representable_by_precision(amount, fmt.precision):
        precision = fmt.precision
    else:
        precision = -amount.quantity.as_tuple().exponent
    sep = "," if fmt.comma else ""

    left = ""
    right = ""
    commodity_str = commodity if noquote else commodity2str(commodity)
    if fmt.position == "left":
        left = commodity_str
        if fmt.space:
            left += " "
    else:
        if fmt.space:
            right += " "
        right += commodity_str
    left += moneyfmt(amount.quantity, places=precision, sep=sep)

    if isinstance(amount.commodity, Lot):
        x, y = amount2str(amount.commodity.price, format_function)
        right += " "
        right += ("{" + x + y + "}")
        right += " "
        right += f"[{date2str(amount.commodity.date)}]"

    return (left, right)

def _is_empty_parent(account: Account) -> bool:
    """All balance is contained in a single child account."""
    if len(account.children) == 0:
        return False
    child = None
    nonempty = 0
    for c in account.children:
        if not _account_is_deep_empty(account[c]):
            nonempty += 1
            child = account[c]
    if nonempty != 1:
        return False
    if child and account.balance == child.balance:
        return True

def print_account_balance(account: Account, format_function: Callable,
                          padding: int = 20, separator: str = "  ",
                          prefix: str = "", root=True):
    for child in account.sorted_children():
        if _is_empty_parent(account[child]):
            print_account_balance(account[child],
                                  format_function,
                                  padding=padding,
                                  separator=separator,
                                  prefix=prefix + child + ":",
                                  root=False)
        else:
            commodities = account[child].sorted_commodities()
            last_i = len(commodities) - 1
            for i in range(len(commodities)):
                commodity = commodities[i]
                qty = account[child].balance[commodity]
                a, b = amount2str(Amount(qty, commodity),
                                  format_function,
                                  force_prec=True,
                                  noquote=True)
                amount = (a + b).rjust(padding)
                if i == last_i:
                    amount += (separator + prefix + child)
                print(amount)
            print_account_balance(account[child],
                                  format_function,
                                  padding=padding,
                                  separator=separator + "  ",
                                  prefix="",
                                  root=False)
    if root:
        print(padding * "-")
        commodities = account.sorted_commodities()
        for i in range(len(commodities)):
            commodity = commodities[i]
            qty = account.balance[commodity]
            a, b = amount2str(Amount(qty, commodity),
                              format_function,
                              force_prec=True,
                              noquote=True)
            print((a + b).rjust(padding))
        if not commodities:
            print("0".rjust(padding))

def _account_is_deep_empty(account: Account) -> bool:
    if account.balance != 0:
        return False
    for c in account.children:
        if not _account_is_deep_empty(account[c]):
            return False
    return True
