#! /usr/bin/env bash

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

source ../utils.sh

rm -rf *.out

mkdir -p good-1.out
try $ULEDGER3_SCRIPTS/balance.py good-1.ledger > good-1.out/balance.txt
try diff good-1.golden/balance.txt good-1.out/balance.txt
try silent $ULEDGER3_SCRIPTS/verify.py good-1.ledger
try $ULEDGER3_SCRIPTS/rewrite.py good-1.ledger > good-1.out/rewrite.txt
try diff good-1.golden/rewrite.txt good-1.out/rewrite.txt

mkdir -p good-2.out
try $ULEDGER3_SCRIPTS/balance.py good-2.ledger > good-2.out/balance.txt
try diff good-2.golden/balance.txt good-2.out/balance.txt
try silent $ULEDGER3_SCRIPTS/verify.py good-2.ledger
try $ULEDGER3_SCRIPTS/rewrite.py good-2.ledger > good-2.out/rewrite.txt
try diff good-2.golden/rewrite.txt good-2.out/rewrite.txt

try run_and_expect_error "$ULEDGER3_SCRIPTS/balance.py bad-1.ledger" \
    "BalanceError: More than one elided posting not allowed"

try run_and_expect_error "$ULEDGER3_SCRIPTS/verify.py bad-2.ledger" \
    "BalanceError: Balance assertion failed"

try run_and_expect_error "$ULEDGER3_SCRIPTS/verify.py bad-3.ledger" \
    "BalanceError: root:Equity:Trading:Currency unbalanced"

try run_and_expect_error "$ULEDGER3_SCRIPTS/verify.py bad-4.ledger" \
    "ParseError: Account 'foodx' not declared"
