from typing import Union
from decimal import Decimal

from uledger3 import parser
from uledger3.parser import Amount, Lot, Transaction, \
    Posting, Position, Journal, Entity

class LedgerError(Exception):
    def __init__(self, message: str,
                 entity: Entity | None = None,
                 lines: list[str] | None = None):
        position = None
        context = None
        if entity:
            try:
                position = entity.span.start
            except AttributeError:
                position = None
        if lines and position:
            try:
                context = lines[position.line - 1]
            except (IndexError, AttributeError):
                context = None
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

class BalanceError(LedgerError):
    pass

def transaction_has_unit_rates(txn: Transaction) -> Amount | None:
    """Does the transaction contain an "@" posting?"""
    for i in range(len(txn.contents)):
        p = txn.contents[i]
        if isinstance(p, Posting) and p.amount and p.amount.unit_rate:
            return p.amount
    return None

def _check_transaction_elide(
        txn: Transaction, noelide: bool = False,
        lines: list[str] | None = None) \
        -> tuple[int, str]:
    """Check everything related to elided postings in a transaction."""
    elide_index = None
    elide_account = None
    for i in range(len(txn.contents)):
        p = txn.contents[i]
        if isinstance(p, Posting) and p.amount is None:
            if noelide:
                raise BalanceError(
                    "Elided posting not allowed.", p, lines)
            if parser.is_virtual_account(p.account):
                raise BalanceError(
                    "Virtual posting may not be elided.", p, lines)
            if elide_index is not None:
                raise BalanceError(
                    "More than one elided posting not allowed.", p, lines)
            elide_index = i
            elide_account = p.account
    return (elide_index, elide_account)

def check_transaction(txn: Transaction, lines: list[str] | None = None,
                      noelide: bool = False):
    a = transaction_has_unit_rates(txn)
    if a:
        raise BalanceError(
            "Cannot check balance with unit rates.", a, lines)
    elide_index, elide_account = _check_transaction_elide(txn, noelide, lines)
    if elide_index is not None:
        # There is no need to balance accounts because there is exactly one
        # elided posting.
        return None
    a = Account("root")
    for i in range(len(txn.contents)):
        p = txn.contents[i]
        if isinstance(p, Posting):
            if p.amount is None or parser.is_virtual_account(p.account):
                continue
            a.apply(p)
    if a.balance != 0:
        raise BalanceError(
            f"Transaction unbalanced by {a.balance}.", txn, lines)

def unelide_transaction(txn: Transaction, lines: list[str] | None = None) \
    -> None:
    """Replace elided postings with regular postings."""
    check_transaction(txn, lines)
    elide_index, elide_account = _check_transaction_elide(txn, lines=lines)
    if elide_index is not None:
        a = Account("root")
        for i in range(len(txn.contents)):
            p = txn.contents[i]
            if isinstance(p, Posting):
                if p.amount is None or parser.is_virtual_account(p.account):
                    continue
                a.apply(p)
        for i in a.balance:
            txn.contents.insert(
                elide_index + 1,
                parser.Posting(
                    elide_account,
                    parser.Amount(-a.balance[i], i)))
        txn.contents.pop(elide_index)
    check_transaction(txn, lines=lines, noelide=True)

class Balance(dict):
    def __init__(self, parent: "Balance" = None):
        super().__init__()
        self._parent = parent
    def _check_type(self, key, val = None):
        if not (isinstance(key, str) or
                isinstance(key, Lot)):
            raise TypeError(f"Incorrect type: {type(key)}.")
        if val and not isinstance(val, Decimal):
            raise TypeError(f"Incorrect type: {type(val)}.")
    def _remove_empty_balance(self, key):
        try:
            if self[key] == Decimal('0'):
                self.pop(key)
        except KeyError:
            pass
    def __missing__(self, key):
        self._check_type(key)
        return Decimal("0")
    def __setitem__(self, key, val):
        self._check_type(key, val)
        super().__setitem__(key, val)
        self._remove_empty_balance(key)
    def __iadd__(self, amount: Amount):
        if not isinstance(amount, Amount):
            raise TypeError(f"Unsupported type {type(amount)} for addition.")
        if amount.commodity not in self:
            self[amount.commodity] = amount.quantity
        else:
            self[amount.commodity] += amount.quantity
        if self._parent is not None:
            self._parent += amount
            self._remove_empty_balance(amount.commodity)
        return self
    def __isub__(self, amount: Amount):
        if not isinstance(amount, Amount):
            raise TypeError(f"Unsupported type {type(amount)} for subtraction.")
        if amount.commodity not in self:
            self[amount.commodity] = -amount.quantity
        else:
            self[amount.commodity] -= amount.quantity
        if self._parent is not None:
            self._parent -= amount
            self._remove_empty_balance(amount.commodity)
        return self
    def __eq__(self, other):
        if len(self) == 0 and other == len(self):
            return True
        if not isinstance(other, type(self)):
            return False
        return super().__eq__(other)
    def __ne__(self, other):
        return not (self == other)

class Account():
    def __init__(self, name: str, parent: Union["Account", None] = None):
        if not name or name.find(":") != -1:
            raise ValueError(f"Account name '{name}' is improperly formed.")
        self._name = name
        self._parent = parent
        self._children = {}
        if parent is not None:
            self._balance = Balance(parent.balance)
        else:
            self._balance = Balance()
    def __getitem__(self, name):
        hierarchy = [x.strip() for x in name.split(":")]
        account = self
        for i in hierarchy:
            if i not in account._children:
                account._children[i] = Account(i, account)
            account = account._children[i]
        return account
    def __setitem__(self, name, value):
        if not isinstance(value, Account):
            raise TypeError(f"Unsupported type: {type(value)}")
        x = self[name]
        x.parent.children[x.name] = value
    @property
    def name(self):
        return self._name
    @property
    def parent(self):
        return self._parent
    @property
    def children(self):
        return self._children
    @property
    def balance(self):
        return self._balance
    def apply(self, posting: Posting):
        account = parser.strip_virtual_account(posting.account)
        amount = posting.amount
        if amount.unit_rate:
            raise LedgerError("Unit rate cannot be applied.", amount)
        self[account]._balance += amount
    def __iadd__(self, amount: Amount):
        self._balance += amount
        return self
    def __isub__(self, amount: Amount):
        self._balance -= amount
        return self
    def __str__(self):
        return f"Account({self.name}, balance={self.balance})"
