import pandas as pd

from django.core.management.base import BaseCommand
from core.models import UserProfile, MicroLoan, LoanPayment, SocialVouch, SavingsDeposit, MobileMoneyAccount
from django.contrib.auth.models import User
from django.db.models import Sum

FEATURES = [
    'age', 'monthly_income', 'employment_status', 'num_loans', 'num_defaults',
    'num_paid_loans', 'on_time_payment_rate', 'num_vouches', 'num_savings', 'total_saved',
    'is_verified', 'num_mobile_accounts', 'loan_amount', 'loan_duration_days'
]

EMPLOYMENT_MAP = {
    'employed': 0,
    'self_employed': 1,
    'student': 2,
    'unemployed': 3
}

def extract_user_features(user_profile):
    user = user_profile.user
    age = (pd.Timestamp.now().date() - user_profile.date_of_birth).days // 365
    monthly_income = user_profile.monthly_income or 0
    employment_status = EMPLOYMENT_MAP.get(user_profile.employment_status, 3)
    loans = MicroLoan.objects.filter(user=user)
    num_loans = loans.count()
    num_defaults = loans.filter(status='defaulted').count()
    num_paid_loans = loans.filter(status='paid').count()
    payments = LoanPayment.objects.filter(loan__user=user)
    on_time_payment_rate = 1.0
    if payments.exists():
        on_time_payment_rate = payments.filter(was_on_time=True).count() / payments.count()
    num_vouches = SocialVouch.objects.filter(vouchee=user).count()
    num_savings = SavingsDeposit.objects.filter(user=user).count()
    total_saved = SavingsDeposit.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or 0
    is_verified = 1 if user_profile.is_verified else 0
    num_mobile_accounts = MobileMoneyAccount.objects.filter(user=user, is_verified=True).count()
    # For ML, use most recent loan or zeros
    last_loan = loans.order_by('-applied_at').first()
    loan_amount = last_loan.amount if last_loan else 0
    loan_duration_days = last_loan.duration_days if last_loan else 0
    return [
        age, monthly_income, employment_status, num_loans, num_defaults,
        num_paid_loans, on_time_payment_rate, num_vouches, num_savings, total_saved,
        is_verified, num_mobile_accounts, loan_amount, loan_duration_days
    ]

class Command(BaseCommand):
    help = 'Extracts user and loan features for ML model training.'

    def handle(self, *args, **kwargs):
        rows = []
        for profile in UserProfile.objects.all():
            features = extract_user_features(profile)
            # Use defaulted (0) or paid (1) as target if user has loans
            loans = MicroLoan.objects.filter(user=profile.user)
            if loans.exists():
                # Use worst outcome as target
                if loans.filter(status='defaulted').exists():
                    target = 0
                else:
                    target = 1
                rows.append(features + [target])
        df = pd.DataFrame(rows, columns=FEATURES + ['target'])
        df.to_csv('real_user_loan_data.csv', index=False)
        self.stdout.write(self.style.SUCCESS(f'Extracted {len(rows)} user records to real_user_loan_data.csv'))
