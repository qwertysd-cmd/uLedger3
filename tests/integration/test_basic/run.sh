#! /usr/bin/env bash

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

source ../utils.sh

mkdir -p good-1.out

try $ULEDGER3_SCRIPTS/balance.py good-1.ledger > good-1.out/balance.txt
try diff good-1.golden/balance.txt good-1.out/balance.txt
try silent $ULEDGER3_SCRIPTS/verify.py good-1.ledger

try run_and_expect_error "$ULEDGER3_SCRIPTS/balance.py bad-1.ledger" \
    "BalanceError: More than one elided posting not allowed"
