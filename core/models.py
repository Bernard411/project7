from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import os
import logging
from django.db.models import Sum  # Add this import

logger = logging.getLogger(__name__)

# Helper function to define upload path
def user_document_path(instance, filename):
    return f'documents/{instance.user.username}/{filename}'

# ============================================
# USER PROFILE - Starting Point
# ============================================

class UserProfile(models.Model):
    """
    Basic user information for credit scoring with document uploads
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Personal Info
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    national_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    date_of_birth = models.DateField()
    
    # Location
    district = models.CharField(max_length=100)
    traditional_authority = models.CharField(max_length=100)
    village = models.CharField(max_length=100)
    
    # Employment
    employment_status = models.CharField(max_length=50, choices=[
        ('employed', 'Employed'),
        ('self_employed', 'Self Employed'),
        ('student', 'Student'),
        ('unemployed', 'Unemployed'),
    ])
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Document Uploads
    national_id_document = models.FileField(upload_to=user_document_path, null=True, blank=True)
    proof_of_address = models.FileField(upload_to=user_document_path, null=True, blank=True)
    income_document = models.FileField(upload_to=user_document_path, null=True, blank=True)
    
    # Document Verification Status
    id_verified = models.BooleanField(default=False)
    address_verified = models.BooleanField(default=False)
    income_verified = models.BooleanField(default=False)
    
    # Credit Score
    current_credit_score = models.IntegerField(default=300)
    last_score_update = models.DateTimeField(auto_now=True)
    
    # Account Info
    account_created = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)  # Overall verification (phone/ID)
    
    def __str__(self):
        return f"{self.user.username} - Score: {self.current_credit_score}"

    def all_documents_verified(self):
        """Check if all required documents are verified"""
        return self.id_verified and self.address_verified and self.income_verified

# ============================================
# MICROLOANS - The Core of the System
# ============================================

class MicroLoan(models.Model):
    """
    Small loans that help users build credit history
    Start small (MWK 5,000) and grow with good behavior
    """
    LOAN_STATUS = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('paid', 'Fully Paid'),
        ('defaulted', 'Defaulted'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Loan details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    duration_days = models.IntegerField()  # e.g., 30, 60, 90 days
    
    # Status
    status = models.CharField(max_length=20, choices=LOAN_STATUS, default='pending')
    
    # Dates
    applied_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True)
    due_date = models.DateField(null=True)
    paid_at = models.DateTimeField(null=True)
    
    # Repayment tracking
    total_amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Credit score at time of application
    score_at_application = models.IntegerField()
    
    def save(self, *args, **kwargs):
        if not self.total_amount_due:
            # Calculate total with interest
            interest = self.amount * (self.interest_rate / 100)
            self.total_amount_due = self.amount + interest
        super().save(*args, **kwargs)
    
    def is_overdue(self):
        if self.due_date and self.status == 'active':
            return timezone.now().date() > self.due_date
        return False
    
    def days_overdue(self):
        if self.is_overdue():
            return (timezone.now().date() - self.due_date).days
        return 0
    
    def __str__(self):
        return f"{self.user.username} - MWK {self.amount} ({self.status})"

# ============================================
# LOAN PAYMENTS - Track Every Payment
# ============================================

class LoanPayment(models.Model):
    """
    Every payment made towards a loan
    """
    loan = models.ForeignKey(MicroLoan, on_delete=models.CASCADE, related_name='payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, choices=[
        ('airtel_money', 'Airtel Money'),
        ('tnm_mpamba', 'TNM Mpamba'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
    ])
    
    # Was it on time?
    was_on_time = models.BooleanField()
    days_from_due = models.IntegerField()  # Negative = early, Positive = late
    
    # Receipt
    transaction_reference = models.CharField(max_length=100)
    
    def __str__(self):
        return f"Payment MWK {self.amount} - {self.payment_date.date()}"

# ============================================
# MOBILE MONEY VERIFICATION
# ============================================

class MobileMoneyAccount(models.Model):
    """
    Link and verify mobile money accounts
    In Malawi: Airtel Money, TNM Mpamba
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    provider = models.CharField(max_length=50, choices=[
        ('airtel_money', 'Airtel Money'),
        ('tnm_mpamba', 'TNM Mpamba'),
    ])
    phone_number = models.CharField(max_length=15)
    
    # Verification (send small amount, user confirms)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True)
    
    # Transaction history (if we can pull it)
    average_monthly_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    transaction_count_30days = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.provider} - {self.phone_number}"

# ============================================
# SOCIAL VOUCHING SYSTEM
# ============================================

class SocialVouch(models.Model):
    """
    Social vouching to boost creditworthiness
    """
    voucher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vouches_given')
    vouchee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vouches_received')
    trust_level = models.IntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    relationship = models.CharField(max_length=100)
    willing_to_cosign = models.BooleanField(default=False)
    max_cosign_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    vouchee_defaulted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.voucher.username} vouches for {self.vouchee.username}"

# ============================================
# SAVINGS DEPOSITS
# ============================================

class SavingsDeposit(models.Model):
    """
    Track savings to improve credit score, including loan deposits and repayment deductions
    """
    TRANSACTION_TYPES = (
        ('DEPOSIT', 'Regular Deposit'),
        ('LOAN_DEPOSIT', 'Loan Deposit'),
        ('REPAYMENT_DEDUCTION', 'Repayment Deduction'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_date = models.DateTimeField(auto_now_add=True)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='DEPOSIT')
    
    def save(self, *args, **kwargs):
        """
        Update balance_after based on previous transactions
        """
        if not self.pk:  # Only for new transactions
            last_transaction = SavingsDeposit.objects.filter(user=self.user).order_by('-deposit_date').first()
            current_balance = last_transaction.balance_after if last_transaction else 0
            self.balance_after = current_balance + self.amount
            # Log transaction for fraud detection
            logger.info(f"Savings transaction: {self.user.username}, {self.transaction_type}, MWK {self.amount}")
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.username} - MWK {self.amount} ({self.transaction_type})"

    @classmethod
    def get_current_balance(cls, user):
        """
        Calculate the current savings balance for a user
        """
        return cls.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or 0

# ============================================
# CREDIT SCORE CALCULATOR
# ============================================

class CreditScoreCalculator:
    @staticmethod
    def calculate_score(user):
        """
        Calculate score with additional document verification factor
        """
        profile = user.userprofile
        score = 300  # Base score
        
        # FACTOR 1: Payment History (50% weight, max 200 points)
        loans = MicroLoan.objects.filter(user=user).exclude(status__in=['pending', 'rejected'])
        payment_score = 0
        for loan in loans:
            payments = loan.payments.all()
            if payments.exists():
                on_time_payments = payments.filter(was_on_time=True).count()
                total_payments = payments.count()
                points_per_payment = 200 / total_payments if total_payments > 0 else 0
                payment_score += on_time_payments * points_per_payment
            
            late_payments = payments.filter(was_on_time=False).count()
            payment_score -= (late_payments * 50)
            
            if loan.status == 'defaulted':
                payment_score -= 100
        
        payment_score = max(0, min(200, payment_score))
        score += payment_score
        
        # FACTOR 2: Credit Utilization (30% weight)
        active_loans = loans.filter(status='active')
        if active_loans.exists():
            total_borrowed = sum(loan.amount for loan in active_loans)
            max_borrowing_capacity = profile.monthly_income * 3 if profile.monthly_income else 50000
            utilization = float(total_borrowed) / float(max_borrowing_capacity)
            
            if utilization < 0.3:
                score += 100
            elif utilization < 0.5:
                score += 50
            elif utilization < 0.7:
                score += 20
        else:
            score += 50
        
        # FACTOR 3: Length of History (15% weight)
        account_age = (timezone.now() - profile.account_created).days
        if account_age > 365:
            score += 80
        elif account_age > 180:
            score += 60
        elif account_age > 90:
            score += 40
        elif account_age > 30:
            score += 20
        
        # FACTOR 4: Social Trust (10% weight)
        vouches = SocialVouch.objects.filter(vouchee=user, is_active=True)
        vouch_count = vouches.count()
        if vouch_count >= 5:
            score += 60
        elif vouch_count >= 3:
            score += 40
        elif vouch_count >= 1:
            score += 20
        bad_vouches = SocialVouch.objects.filter(voucher=user, vouchee_defaulted=True).count()
        score -= (bad_vouches * 30)
        
        # FACTOR 5: Savings Behavior (5% weight)
        savings = SavingsDeposit.objects.filter(user=user)
        if savings.exists():
            total_saved = sum(s.amount for s in savings)
            if total_saved > 50000:
                score += 50
            elif total_saved > 20000:
                score += 30
            elif total_saved > 5000:
                score += 15
        
        # FACTOR 6: Account Verification (5% weight)
        if profile.is_verified:
            score += 30
        mobile_accounts = MobileMoneyAccount.objects.filter(user=user, is_verified=True)
        score += (mobile_accounts.count() * 10)
        
        # FACTOR 7: Document Verification (5% weight, max 30 points)
        document_score = 0
        if profile.id_verified:
            document_score += 10
        if profile.address_verified:
            document_score += 10
        if profile.income_verified:
            document_score += 10
        score += document_score
        
        # CAP SCORE BETWEEN 300-850
        score = max(300, min(850, score))
        
        profile.current_credit_score = score
        profile.save()
        
        return score
    
    @staticmethod
    def get_max_loan_amount(score):
        """
        Determine maximum loan amount based on score
        """
        if score >= 750:
            return 500000  # MWK 500,000
        elif score >= 700:
            return 250000  # MWK 250,000
        elif score >= 650:
            return 100000  # MWK 100,000
        elif score >= 600:
            return 50000   # MWK 50,000
        elif score >= 550:
            return 25000   # MWK 25,000
        elif score >= 500:
            return 10000   # MWK 10,000
        else:
            return 5000    # MWK 5,000 (starter loan)
    
    @staticmethod
    def get_interest_rate(score):
        """
        Interest rate based on credit score
        """
        if score >= 750:
            return Decimal('5.0')   # 5% interest
        elif score >= 700:
            return Decimal('8.0')   # 8%
        elif score >= 650:
            return Decimal('12.0')  # 12%
        elif score >= 600:
            return Decimal('15.0')  # 15%
        elif score >= 550:
            return Decimal('18.0')  # 18%
        elif score >= 500:
            return Decimal('22.0')  # 22%
        else:
            return Decimal('25.0')  # 25% (high risk)

# ============================================
# LOAN APPLICATION APPROVAL
# ============================================

class LoanApprovalEngine:
    @staticmethod
    def evaluate_application(user, requested_amount):
        """
        Evaluate if user can get the loan
        """
        profile = user.userprofile
        # Check document verification
        if not profile.all_documents_verified():
            return {
                'approved': False,
                'reason': 'Please verify all required documents (ID, address, income) before applying.',
                'score': profile.current_credit_score
            }
        
        # Recalculate current score
        score = CreditScoreCalculator.calculate_score(user)
        
        # Get max allowed
        max_amount = CreditScoreCalculator.get_max_loan_amount(score)
        interest_rate = CreditScoreCalculator.get_interest_rate(score)
        
        # Check if they have active loans
        active_loans = MicroLoan.objects.filter(user=user, status='active')
        if active_loans.exists():
            return {
                'approved': False,
                'reason': 'You have an active loan. Pay it off first.',
                'score': score
            }
        
        # Check if they defaulted recently
        recent_defaults = MicroLoan.objects.filter(
            user=user, 
            status='defaulted',
            approved_at__gte=timezone.now() - timedelta(days=90)
        )
        if recent_defaults.exists():
            return {
                'approved': False,
                'reason': 'Recent default detected. Build your credit first.',
                'score': score
            }
        
        # Check amount requested
        if requested_amount > max_amount:
            return {
                'approved': False,
                'reason': f'Maximum loan for your score: MWK {max_amount:,.0f}',
                'max_amount': max_amount,
                'score': score
            }
        
        # APPROVED!
        return {
            'approved': True,
            'amount': requested_amount,
            'interest_rate': interest_rate,
            'score': score,
            'message': f'Congratulations! Approved at {interest_rate}% interest.'
        }
