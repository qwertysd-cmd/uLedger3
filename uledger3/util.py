import uledger3.parser as parser
import uledger3.ledger as ledger
from uledger3.parser import Amount, Lot, Transaction, \
    Posting, Position, Journal, Entity, PriceDecl
from uledger3.ledger import Account, Balance
from uledger3.exchange import Exchange
from typing import Callable

def read_journal(database: str, pedantic: bool = True) \
        -> tuple[Journal, list[str]]:
    p = parser.Parser(database, pedantic)
    lines = []
    with open(database, "r") as database:
        for line in database:
            line = line.rstrip()
            p.parse_line(line)
            lines.append(line)
    journal = p.journal
    return (journal, lines)

def apply_transaction(txn: Transaction, account: Account,
                      real: bool = False, lots: bool = False):
    ledger.unelide_transaction(txn)
    for p in txn.contents:
        if not isinstance(p, Posting):
            continue
        if real and parser.is_virtual_account(p.account):
            continue
        post_account = parser.strip_virtual_account(p.account)
        post_amount = p.amount
        if not lots and isinstance(post_amount.commodity, Lot):
            post_amount = Amount(post_amount.quantity,
                                 post_amount.commodity.commodity)
        account[post_account] += post_amount

def apply_journal(journal: Journal, account: Account,
                  real: bool = False, lots: bool = False):
    for txn in journal.contents:
        if not isinstance(txn, Transaction):
            continue
        apply_transaction(txn, account, real, lots)

def transform_account(old_account: Account, new_account: Account,
                      transformer: Callable[[Balance, str], Balance],
                      independent: bool = False):
    for child in old_account.children:
        transform_account(old_account[child], new_account[child],
                          transformer, independent)

    # If "independent", adjust each balance without considering the
    # contribution of children separately.
    if independent:
        b = old_account.balance
    else:
        b = old_account.balance_excluding_children()

    b_new = transformer(b, old_account.name)

    for cmdty in b_new:
        if independent:
            new_account.balance[cmdty] = b_new[cmdty]
        else:
            new_account += Amount(b_new[cmdty], cmdty)
