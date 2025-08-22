#! /usr/bin/env bash

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

source ../utils.sh

rm -rf *.out

mkdir -p random-ledger.out
try $ULEDGER3_SCRIPTS/balance.py random-ledger.dat > random-ledger.out/balance.txt
try diff random-ledger.out/balance.txt random-ledger.golden/balance.txt
try ledger -f random-ledger.dat bal > random-ledger.out/balance.txt
try diff random-ledger.out/balance.txt random-ledger.golden/balance.txt
