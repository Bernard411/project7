import random
import pandas as pd
from faker import Faker

fake = Faker()

# Feature columns
FEATURES = [
    'age', 'monthly_income', 'employment_status', 'num_loans', 'num_defaults',
    'num_paid_loans', 'on_time_payment_rate', 'num_vouches', 'num_savings', 'total_saved',
    'is_verified', 'num_mobile_accounts', 'loan_amount', 'loan_duration_days'
]

# Target: 1 = good (paid), 0 = bad (defaulted)
def generate_synthetic_data(n=1000):
    data = []
    for _ in range(n):
        age = random.randint(18, 65)
        monthly_income = random.randint(20000, 500000)
        employment_status = random.choice([0, 1, 2, 3])  # encode as int
        num_loans = random.randint(0, 10)
        num_defaults = random.randint(0, min(num_loans, 3))
        num_paid_loans = num_loans - num_defaults
        on_time_payment_rate = round(random.uniform(0.5, 1.0), 2)
        num_vouches = random.randint(0, 7)
        num_savings = random.randint(0, 20)
        total_saved = random.randint(0, 200000)
        is_verified = random.choice([0, 1])
        num_mobile_accounts = random.randint(0, 2)
        loan_amount = random.randint(5000, 500000)
        loan_duration_days = random.choice([30, 60, 90, 180])
        # Target: more likely to default if low income, high loan, many defaults, low savings, not verified
        risk = (
            (monthly_income < 50000 and loan_amount > 20000) or
            num_defaults > 0 or
            on_time_payment_rate < 0.7 or
            total_saved < 10000 or
            not is_verified
        )
        target = 0 if risk and random.random() < 0.8 else 1
        data.append([
            age, monthly_income, employment_status, num_loans, num_defaults,
            num_paid_loans, on_time_payment_rate, num_vouches, num_savings, total_saved,
            is_verified, num_mobile_accounts, loan_amount, loan_duration_days, target
        ])
    df = pd.DataFrame(data, columns=FEATURES + ['target'])
    return df

if __name__ == "__main__":
    df = generate_synthetic_data(2000)
    df.to_csv("synthetic_loan_data.csv", index=False)
    print(df.head())
