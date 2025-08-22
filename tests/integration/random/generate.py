import random
import datetime

# Declare commodities
COMMODITIES = ['$']

# Declare accounts to open
ACCOUNTS = [
    'Assets:Cash',
    'Assets:Bank',
    'Expenses:Food',
    'Expenses:Travel',
    'Income:Salary',
    'Liabilities:CreditCard',
]

# Sample payees for transactions
PAYEES = ['Walmart', 'Amazon', 'Starbucks', 'Uber', 'Employer', 'Landlord']

def random_date(start, end):
    """Generate a random date between start and end dates."""
    delta = end - start
    random_days = random.randrange(delta.days + 1)
    return start + datetime.timedelta(days=random_days)

def write_commodities_and_accounts(f):
    """Write commodity and account declarations to file f."""
    for commodity in COMMODITIES:
        f.write(f"commodity {commodity}\n")
    f.write("\n")
    for acct in ACCOUNTS:
        f.write(f"account {acct}\n")
    f.write("\n")

def generate_transaction(date):
    """Generate a single random transaction string in Ledger format."""
    payee = random.choice(PAYEES)
    amount = round(random.uniform(5.0, 500.0), 2)

    # Debit usually Expenses or Assets
    debit_account = random.choice(['Expenses:Food', 'Expenses:Travel'])
    # Credit usually Assets or Liabilities
    credit_account = random.choice(['Assets:Cash', 'Assets:Bank', 'Liabilities:CreditCard'])

    txn = (
        f"{date.strftime('%Y/%m/%d')} {payee}\n"
        f"    {debit_account}     ${amount:.2f}\n"
        f"    {credit_account}\n"
    )
    return txn

def generate_ledger_file(filename, num_transactions=15):
    # Set random date range for transactions in last year
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=720)

    with open(filename, 'w') as f:
        f.write(";; Random generated Ledger journal file\n\n")
        write_commodities_and_accounts(f)

        for _ in range(num_transactions):
            date = random_date(start_date, end_date)
            txn = generate_transaction(date)
            f.write(txn)
            f.write("\n")

if __name__ == '__main__':
    output_file = 'random-ledger.dat'
    generate_ledger_file(output_file, num_transactions=1500)
    print(f"Generated {output_file} with 1500 random transactions and declarations.")
