#! /usr/bin/env python3

import argparse

from uledger3.printing import print_account_balance
from uledger3.ledger import Account
from uledger3.util import read_journal, apply_journal

def parse_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("database", type=str,
                           default="database.ledger",
                           help="database file")
    argparser.add_argument("--real", action="store_true",
                           default=False,
                           help="Show real transactions only")
    argparser.add_argument("--lots", action="store_true",
                           default=False,
                           help="Show lots")
    return argparser.parse_args()

def main():
    args = parse_args()
    journal, lines = read_journal(args.database)
    root = Account("root")
    apply_journal(journal, root, args.real, args.lots)
    print_account_balance(root, format_function=journal.get_commodity_format)

if __name__ == "__main__":
    main()
