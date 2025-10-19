from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile, MicroLoan, LoanPayment, SavingsDeposit, SocialVouch
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random
from core.signals import thread_local  # Import thread_local

class Command(BaseCommand):
    help = 'Seed database with sample data for ML training'

    def handle(self, *args, **options):
        # DISABLE SIGNALS during seeding
        thread_local.disable_signals = True
        
        try:
            # Create users
            for i in range(1001):
                username = f"user_{i}"
                if not User.objects.filter(username=username).exists():
                    try:
                        user = User.objects.create_user(
                            username=username,
                            password='password123',
                            email=f"user_{i}@example.com"
                        )
                        # Explicitly create UserProfile (signal is disabled)
                        profile, created = UserProfile.objects.get_or_create(
                            user=user,
                            defaults={
                                'current_credit_score': 300,
                                'phone_number': f"0888000{i:03d}",
                                'national_id': f"MW{i:04d}",
                                'date_of_birth': timezone.now().date() - timedelta(days=365*30),
                                'district': random.choice(['Lilongwe', 'Blantyre', 'Mzuzu']),
                                'traditional_authority': 'TA Unknown',
                                'village': 'Village Unknown',
                                'employment_status': random.choice(['employed', 'self_employed', 'unemployed']),
                                'monthly_income': Decimal(str(random.uniform(10000, 100000))),
                            }
                        )
                        if created:
                            self.stdout.write(self.style.SUCCESS(f"Created UserProfile for {username}"))
                        else:
                            self.stdout.write(self.style.WARNING(f"UserProfile already exists for {username}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Failed to create user {username}: {e}"))
                        continue

            # Create loans
            users = User.objects.all()
            for user in users:
                try:
                    profile = user.userprofile
                except UserProfile.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"No UserProfile for {user.username}, skipping"))
                    continue

                num_loans = random.randint(1, 5)
                for _ in range(num_loans):
                    amount = Decimal(str(random.uniform(5000, 50000)))
                    duration = random.choice([30, 60, 90])
                    status = random.choice(['paid', 'defaulted', 'active'])
                    try:
                        loan = MicroLoan.objects.create(
                            user=user,
                            amount=amount,
                            interest_rate=Decimal(str(random.uniform(5, 25))),
                            duration_days=duration,
                            status=status,
                            score_at_application=profile.current_credit_score,
                            applied_at=timezone.now() - timedelta(days=random.randint(10, 365)),
                            approved_at=timezone.now() - timedelta(days=random.randint(5, 360)) if status != 'pending' else None,
                            due_date=timezone.now().date() - timedelta(days=random.randint(-30, 90)),
                            total_amount_due=amount * (1 + Decimal(str(random.uniform(0.05, 0.25)))),
                            amount_paid=amount if status == 'paid' else Decimal('0') if status == 'defaulted' else Decimal(str(random.uniform(0, float(amount))))
                        )
                        self.stdout.write(self.style.SUCCESS(f"Created loan for {user.username}: {status}, MWK {amount}"))
                        # Add payments
                        if status in ['paid', 'active']:
                            LoanPayment.objects.create(
                                loan=loan,
                                amount=loan.amount_paid,
                                payment_method=random.choice(['airtel_money', 'tnm_mpamba', 'bank_transfer', 'cash']),
                                transaction_reference=f"TXN{random.randint(1000, 9999)}",
                                was_on_time=random.choice([True, False]),
                                days_from_due=random.randint(-10, 10)
                            )
                        # Add savings
                        SavingsDeposit.objects.create(
                            user=user,
                            amount=Decimal(str(random.uniform(1000, 20000))),
                            balance_after=Decimal(str(random.uniform(1000, 50000))),
                            deposit_date=timezone.now() - timedelta(days=random.randint(1, 365))
                        )
                        # Add vouches
                        if random.random() > 0.5:
                            other_users = list(users.exclude(id=user.id))
                            if other_users:
                                other_user = random.choice(other_users)
                                SocialVouch.objects.get_or_create(
                                    voucher=other_user,
                                    vouchee=user,
                                    defaults={
                                        'trust_level': random.randint(1, 3),
                                        'relationship': random.choice(['friend', 'family', 'colleague']),
                                    }
                                )
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Failed to create loan for {user.username}: {e}"))
                        continue

            self.stdout.write(self.style.SUCCESS(f"Seeded {len(users)} users with loans, payments, savings, and vouches"))
        
        finally:
            # RE-ENABLE SIGNALS after seeding
            thread_local.disable_signals = False
            self.stdout.write(self.style.SUCCESS("Signals re-enabled"))