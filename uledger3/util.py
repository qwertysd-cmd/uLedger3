import uledger3.parser as parser
import uledger3.ledger as ledger
from uledger3.parser import Amount, Lot, Transaction, \
    Posting, Position, Journal, Entity, PriceDecl
from uledger3.ledger import Account

def read_journal(database: str) -> tuple[Journal, list[str]] :
    p = parser.Parser(database, pedantic=True)
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
        if not lots and isinstance(p.amount.commodity, Lot):
            post_amount = Amount(p.amount.quantity,
                                 p.amount.commodity.commodity)
        account[post_account] += post_amount

def apply_journal(journal: Journal, account: Account,
                  real: bool = False, lots: bool = False):
    for txn in journal.contents:
        if not isinstance(txn, Transaction):
            continue
        apply_transaction(txn, account, real, lots)
