# ============================================
# MALAWI CREDIT SCORING SYSTEM
# Build credit score from scratch based on behavior
# ============================================

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

# ============================================
# USER PROFILE - Starting Point
# ============================================

class UserProfile(models.Model):
    """
    Basic user information for credit scoring
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Personal Info
    phone_number = models.CharField(max_length=15, unique=True)
    national_id = models.CharField(max_length=50, unique=True)
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
    
    # Credit Score (calculated, not entered manually!)
    current_credit_score = models.IntegerField(default=300)
    last_score_update = models.DateTimeField(auto_now=True)
    
    # Account info
    account_created = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)  # Phone/ID verified
    
    def __str__(self):
        return f"{self.user.username} - Score: {self.current_credit_score}"


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
    Trust-based system - users vouch for each other
    Common in African lending (like VSLA groups)
    """
    voucher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vouches_given')
    vouchee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vouches_received')
    
    # Vouch details
    trust_level = models.IntegerField(choices=[
        (1, 'Know them slightly'),
        (2, 'Know them well'),
        (3, 'Trust completely'),
    ])
    relationship = models.CharField(max_length=100)  # friend, family, colleague, etc.
    
    # Is voucher willing to co-sign?
    willing_to_cosign = models.BooleanField(default=False)
    max_cosign_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # If vouchee defaults, voucher's score is affected
    vouchee_defaulted = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['voucher', 'vouchee']
    
    def __str__(self):
        return f"{self.voucher.username} vouches for {self.vouchee.username}"


# ============================================
# SAVINGS HISTORY
# ============================================

class SavingsDeposit(models.Model):
    """
    Track savings deposits - shows financial discipline
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_date = models.DateTimeField(auto_now_add=True)
    
    # Total savings balance
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.user.username} - MWK {self.amount} saved"


# ============================================
# CREDIT SCORE CALCULATOR
# ============================================

class CreditScoreCalculator:
    """
    Calculates credit score based on multiple factors
    Similar to FICO but adapted for Malawi context
    """
    
    @staticmethod
    def calculate_score(user):
        """
        Calculate comprehensive credit score
        Score range: 300 - 850
        """
        score = 300  # Everyone starts here
        profile = user.userprofile
        
        # =====================================
        # FACTOR 1: Payment History (35% weight)
        # =====================================
        loans = MicroLoan.objects.filter(user=user, status__in=['paid', 'active', 'defaulted'])
        if loans.exists():
            total_loans = loans.count()
            paid_loans = loans.filter(status='paid').count()
            defaulted_loans = loans.filter(status='defaulted').count()
            
            # On-time payment rate
            payments = LoanPayment.objects.filter(loan__user=user)
            if payments.exists():
                on_time_payments = payments.filter(was_on_time=True).count()
                on_time_rate = on_time_payments / payments.count()
                score += int(on_time_rate * 200)  # Up to +200 points
            
            # Penalty for defaults
            score -= (defaulted_loans * 100)  # -100 per default
            
            # Bonus for fully paid loans
            score += (paid_loans * 20)  # +20 per paid loan
        
        # =====================================
        # FACTOR 2: Credit Utilization (30% weight)
        # =====================================
        active_loans = MicroLoan.objects.filter(user=user, status='active')
        if active_loans.exists():
            total_borrowed = sum(loan.amount for loan in active_loans)
            max_borrowing_capacity = profile.monthly_income * 3 if profile.monthly_income else 50000
            
            utilization = float(total_borrowed) / float(max_borrowing_capacity)
            
            if utilization < 0.3:  # Using less than 30%
                score += 100
            elif utilization < 0.5:  # 30-50%
                score += 50
            elif utilization < 0.7:  # 50-70%
                score += 20
            # Over 70% = no bonus
        else:
            score += 50  # Bonus for no active debt
        
        # =====================================
        # FACTOR 3: Length of History (15% weight)
        # =====================================
        account_age = (timezone.now() - profile.account_created).days
        
        if account_age > 365:  # Over 1 year
            score += 80
        elif account_age > 180:  # 6-12 months
            score += 60
        elif account_age > 90:  # 3-6 months
            score += 40
        elif account_age > 30:  # 1-3 months
            score += 20
        
        # =====================================
        # FACTOR 4: Social Trust (10% weight)
        # =====================================
        vouches = SocialVouch.objects.filter(vouchee=user, is_active=True)
        vouch_count = vouches.count()
        
        if vouch_count >= 5:
            score += 60
        elif vouch_count >= 3:
            score += 40
        elif vouch_count >= 1:
            score += 20
        
        # Penalty if people you vouched for defaulted
        bad_vouches = SocialVouch.objects.filter(voucher=user, vouchee_defaulted=True).count()
        score -= (bad_vouches * 30)
        
        # =====================================
        # FACTOR 5: Savings Behavior (5% weight)
        # =====================================
        savings = SavingsDeposit.objects.filter(user=user)
        if savings.exists():
            total_saved = sum(s.amount for s in savings)
            
            if total_saved > 50000:
                score += 50
            elif total_saved > 20000:
                score += 30
            elif total_saved > 5000:
                score += 15
        
        # =====================================
        # FACTOR 6: Account Verification (5% weight)
        # =====================================
        if profile.is_verified:
            score += 30
        
        mobile_accounts = MobileMoneyAccount.objects.filter(user=user, is_verified=True)
        score += (mobile_accounts.count() * 10)  # +10 per verified account
        
        # =====================================
        # CAP SCORE BETWEEN 300-850
        # =====================================
        score = max(300, min(850, score))
        
        # Update user's profile
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
    """
    Decides whether to approve loan based on credit score
    """
    
    @staticmethod
    def evaluate_application(user, requested_amount):
        """
        Evaluate if user can get the loan
        """
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


# ================================