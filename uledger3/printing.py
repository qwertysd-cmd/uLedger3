from decimal import Decimal

import uledger3.parser as parser
from uledger3.parser import Amount, Lot, Transaction, \
    Posting, Position, Journal, Entity

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

def amount2str(amount: Amount, format_function) -> tuple[str, str]:
    assert isinstance(amount.quantity, Decimal)
    if isinstance(amount.commodity, str):
        commodity = amount.commodity
    else:
        assert isinstance(amount.commodity, Lot)
        commodity = amount.commodity.commodity
    fmt = format_function(commodity)
    precision = max(-amount.quantity.as_tuple().exponent,
                    fmt.precision)
    sep = "," if fmt.comma else ""

    left = ""
    right = ""
    if fmt.position == "left":
        left = commodity2str(commodity)
        if fmt.space:
            left += " "
    else:
        if fmt.space:
            right += " "
        right += commodity2str(commodity)
    left += moneyfmt(amount.quantity, places=precision, sep=sep)

    if isinstance(amount.commodity, Lot):
        x, y = amount2str(amount.commodity.price, format_function)
        right += " "
        right += ("{" + x + y + "}")
        right += " "
        right += f"[{amount.commodity.date.strftime('%Y/%m/%d')}]"

    return (left, right)
