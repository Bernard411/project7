from .forms import RegistrationForm
# ============================================
# REGISTRATION VIEW
# ============================================
def registration_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            from django.contrib.auth.models import User
            if User.objects.filter(username=username).exists():
                form.add_error('username', 'Username already exists.')
            elif User.objects.filter(email=email).exists():
                form.add_error('email', 'Email already exists.')
            else:
                user, profile = form.save()
                messages.success(request, 'Registration successful! You can now log in.')
                return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegistrationForm()

    return render(request, 'registration.html', {'form': form})
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import (
    UserProfile, MicroLoan, LoanPayment, MobileMoneyAccount,
    SocialVouch, SavingsDeposit, CreditScoreCalculator, LoanApprovalEngine
)

# ============================================
# LOGIN VIEW
# ============================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'login.html')

# ============================================
# LOGOUT VIEW
# ============================================

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

# ============================================
# DASHBOARD
# ============================================

@login_required
def dashboard(request):
    """
    Main dashboard showing credit score and activity
    """
    profile = request.user.userprofile
    
    # Recalculate current score
    current_score = CreditScoreCalculator.calculate_score(request.user)
    
    # Get max loan amount for their score
    max_loan = CreditScoreCalculator.get_max_loan_amount(current_score)
    interest_rate = CreditScoreCalculator.get_interest_rate(current_score)
    
    # Get loan history
    loans = MicroLoan.objects.filter(user=request.user).order_by('-applied_at')[:5]
    active_loan = MicroLoan.objects.filter(user=request.user, status='active').first()
    
    # Get vouches
    vouches_received = SocialVouch.objects.filter(vouchee=request.user, is_active=True).count()
    
    # Get savings
    total_savings = sum(
        s.amount for s in SavingsDeposit.objects.filter(user=request.user)
    )
    
    # Score rating
    if current_score >= 740:
        rating = "Excellent"
        rating_color = "success"
    elif current_score >= 670:
        rating = "Good"
        rating_color = "info"
    elif current_score >= 580:
        rating = "Fair"
        rating_color = "warning"
    else:
        rating = "Building"
        rating_color = "secondary"
    
    context = {
        'profile': profile,
        'current_score': current_score,
        'rating': rating,
        'rating_color': rating_color,
        'max_loan': max_loan,
        'interest_rate': interest_rate,
        'loans': loans,
        'active_loan': active_loan,
        'vouches_received': vouches_received,
        'total_savings': total_savings,
    }
    
    return render(request, 'dashboard.html', context)


# ============================================
# LOAN APPLICATION
# ============================================

@login_required
def apply_for_loan(request):
    """
    Apply for a micro-loan
    """
    profile = request.user.userprofile
    current_score = CreditScoreCalculator.calculate_score(request.user)
    max_loan = CreditScoreCalculator.get_max_loan_amount(current_score)
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        duration = int(request.POST.get('duration'))  # days
        
        # Evaluate application
        result = LoanApprovalEngine.evaluate_application(request.user, amount)
        
        if result['approved']:
            # Create loan
            loan = MicroLoan.objects.create(
                user=request.user,
                amount=amount,
                interest_rate=result['interest_rate'],
                duration_days=duration,
                status='approved',
                score_at_application=result['score'],
                approved_at=timezone.now(),
                due_date=timezone.now().date() + timedelta(days=duration)
            )
            loan.status = 'active'
            loan.save()
            
            messages.success(request, f"Loan approved! MWK {amount:,.0f} at {result['interest_rate']}% interest.")
            return redirect('dashboard')
        else:
            messages.error(request, result['reason'])
    
    accounts = MobileMoneyAccount.objects.filter(user=request.user)
    
    context = {
        'accounts': accounts,
        'max_loan': max_loan,
        'current_score': current_score,
    }
    
    return render(request, 'apply_loan.html', context)


# ============================================
# CREDIT SCORE BREAKDOWN
# ============================================

@login_required
def score_breakdown(request):
    """
    Show detailed breakdown of how credit score is calculated
    """
    profile = request.user.userprofile
    current_score = CreditScoreCalculator.calculate_score(request.user)
    
    # Calculate each factor's contribution
    breakdown = {
        'base_score': 300,
        'payment_history': 0,
        'credit_utilization': 0,
        'account_age': 0,
        'social_trust': 0,
        'savings': 0,
        'verification': 0,
    }
    
    # Payment History (35%)
    loans = MicroLoan.objects.filter(user=request.user, status__in=['paid', 'active', 'defaulted'])
    if loans.exists():
        paid_loans = loans.filter(status='paid').count()
        defaulted_loans = loans.filter(status='defaulted').count()
        payments = LoanPayment.objects.filter(loan__user=request.user)
        
        if payments.exists():
            on_time_payments = payments.filter(was_on_time=True).count()
            on_time_rate = on_time_payments / payments.count()
            breakdown['payment_history'] += int(on_time_rate * 200)
        
        breakdown['payment_history'] -= (defaulted_loans * 100)
        breakdown['payment_history'] += (paid_loans * 20)
    
    # Credit Utilization (30%)
    active_loans = MicroLoan.objects.filter(user=request.user, status='active')
    if active_loans.exists():
        total_borrowed = sum(loan.amount for loan in active_loans)
        max_capacity = profile.monthly_income * 3 if profile.monthly_income else 50000
        utilization = float(total_borrowed) / float(max_capacity)
        
        if utilization < 0.3:
            breakdown['credit_utilization'] = 100
        elif utilization < 0.5:
            breakdown['credit_utilization'] = 50
        elif utilization < 0.7:
            breakdown['credit_utilization'] = 20
    else:
        breakdown['credit_utilization'] = 50
    
    # Account Age (15%)
    account_age = (timezone.now() - profile.account_created).days
    if account_age > 365:
        breakdown['account_age'] = 80
    elif account_age > 180:
        breakdown['account_age'] = 60
    elif account_age > 90:
        breakdown['account_age'] = 40
    elif account_age > 30:
        breakdown['account_age'] = 20
    
    # Social Trust (10%)
    vouches = SocialVouch.objects.filter(vouchee=request.user, is_active=True)
    vouch_count = vouches.count()
    
    if vouch_count >= 5:
        breakdown['social_trust'] = 60
    elif vouch_count >= 3:
        breakdown['social_trust'] = 40
    elif vouch_count >= 1:
        breakdown['social_trust'] = 20
    
    bad_vouches = SocialVouch.objects.filter(voucher=request.user, vouchee_defaulted=True).count()
    breakdown['social_trust'] -= (bad_vouches * 30)
    
    # Savings (5%)
    savings = SavingsDeposit.objects.filter(user=request.user)
    if savings.exists():
        total_saved = sum(s.amount for s in savings)
        
        if total_saved > 50000:
            breakdown['savings'] = 50
        elif total_saved > 20000:
            breakdown['savings'] = 30
        elif total_saved > 5000:
            breakdown['savings'] = 15
    
    # Verification (5%)
    if profile.is_verified:
        breakdown['verification'] = 30
    
    mobile_accounts = MobileMoneyAccount.objects.filter(user=request.user, is_verified=True)
    breakdown['verification'] += (mobile_accounts.count() * 10)
    
    # Tips to improve
    tips = []
    
    if breakdown['payment_history'] < 100:
        tips.append("Pay your loans on time to boost your score (+200 points possible)")
    
    if breakdown['social_trust'] < 40:
        tips.append("Get vouches from friends and family (+60 points possible)")
    
    if breakdown['savings'] < 30:
        tips.append("Save regularly to show financial discipline (+50 points possible)")
    
    if not profile.is_verified:
        tips.append("Verify your phone number and ID (+30 points)")
    
    if mobile_accounts.count() < 2:
        tips.append("Link your mobile money accounts (+10 points each)")
    
    context = {
        'current_score': current_score,
        'breakdown': breakdown,
        'tips': tips,
        'account_age_days': account_age,
        'vouch_count': vouch_count,
        'loan_count': loans.count() if loans.exists() else 0,
    }
    
    return render(request, 'score_breakdown.html', context)


# ============================================
# ALL LOANS HISTORY
# ============================================

@login_required
def loan_history(request):
    """
    View all loan history
    """
    loans = MicroLoan.objects.filter(user=request.user).order_by('-applied_at')
    
    stats = {
        'total_loans': loans.count(),
        'active_loans': loans.filter(status='active').count(),
        'paid_loans': loans.filter(status='paid').count(),
        'defaulted_loans': loans.filter(status='defaulted').count(),
        'total_borrowed': sum(l.amount for l in loans),
        'total_paid': sum(l.amount_paid for l in loans),
    }
    
    context = {
        'loans': loans,
        'stats': stats,
    }
    
    return render(request, 'loan_history.html', context)


# ============================================
# LOAN DETAIL
# ============================================

@login_required
def loan_detail(request, loan_id):
    """
    View details of a specific loan
    """
    loan = get_object_or_404(MicroLoan, id=loan_id, user=request.user)
    payments = loan.payments.all().order_by('-payment_date')
    
    remaining = loan.total_amount_due - loan.amount_paid
    
    context = {
        'loan': loan,
        'payments': payments,
        'remaining': remaining,
        'is_overdue': loan.is_overdue(),
        'days_overdue': loan.days_overdue(),
    }
    
    return render(request, 'loan_detail.html', context)


# ============================================
# MAKE PAYMENT
# ============================================

@login_required
def make_payment(request, loan_id):
    """
    Make a payment towards a loan
    """
    loan = get_object_or_404(MicroLoan, id=loan_id, user=request.user)
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        payment_method = request.POST.get('payment_method')
        transaction_ref = request.POST.get('transaction_reference')
        
        # Calculate if payment is on time
        days_from_due = (timezone.now().date() - loan.due_date).days
        was_on_time = days_from_due <= 0
        
        # Create payment
        payment = LoanPayment.objects.create(
            loan=loan,
            amount=amount,
            payment_method=payment_method,
            transaction_reference=transaction_ref,
            was_on_time=was_on_time,
            days_from_due=days_from_due
        )
        
        # Update loan
        loan.amount_paid += amount
        
        if loan.amount_paid >= loan.total_amount_due:
            loan.status = 'paid'
            loan.paid_at = timezone.now()
            messages.success(request, "Congratulations! Loan fully paid. Your credit score will increase!")
        else:
            messages.success(request, f"Payment of MWK {amount:,.0f} received.")
        
        loan.save()
        
        # Recalculate credit score
        CreditScoreCalculator.calculate_score(request.user)
        
        return redirect('loan_detail', loan_id=loan.id)
    
    remaining = loan.total_amount_due - loan.amount_paid
    
    context = {
        'loan': loan,
        'remaining': remaining,
    }
    
    return render(request, 'make_payment.html', context)


# ============================================
# VOUCH FOR SOMEONE
# ============================================

@login_required
def vouch_for_user(request):
    """
    Vouch for another user to boost their credit
    """
    if request.method == 'POST':
        vouchee_username = request.POST.get('username')
        trust_level = int(request.POST.get('trust_level'))
        relationship = request.POST.get('relationship')
        
        try:
            from django.contrib.auth.models import User
            vouchee = User.objects.get(username=vouchee_username)
            
            # Can't vouch for yourself
            if vouchee == request.user:
                messages.error(request, "You cannot vouch for yourself!")
                return redirect('vouch_for_user')
            
            # Create vouch
            vouch, created = SocialVouch.objects.get_or_create(
                voucher=request.user,
                vouchee=vouchee,
                defaults={
                    'trust_level': trust_level,
                    'relationship': relationship,
                }
            )
            
            if created:
                messages.success(request, f"You vouched for {vouchee.username}! Their credit score will increase.")
                # Recalculate their score
                CreditScoreCalculator.calculate_score(vouchee)
            else:
                messages.info(request, "You already vouched for this user.")
            
        except User.DoesNotExist:
            messages.error(request, "User not found.")
    
    # Show who vouched for current user
    vouches_for_me = SocialVouch.objects.filter(vouchee=request.user, is_active=True)
    my_vouches = SocialVouch.objects.filter(voucher=request.user, is_active=True)
    
    context = {
        'vouches_for_me': vouches_for_me,
        'my_vouches': my_vouches,
    }
    
    return render(request, 'vouch.html', context)


# ============================================
# ADD SAVINGS
# ============================================

@login_required
def add_savings(request):
    """
    Record a savings deposit
    """
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        
        # Get current balance
        last_deposit = SavingsDeposit.objects.filter(user=request.user).order_by('-deposit_date').first()
        current_balance = last_deposit.balance_after if last_deposit else Decimal('0')
        
        # Create deposit
        deposit = SavingsDeposit.objects.create(
            user=request.user,
            amount=amount,
            balance_after=current_balance + amount
        )
        
        messages.success(request, f"MWK {amount:,.0f} saved! Your credit score will improve.")
        
        # Recalculate score
        CreditScoreCalculator.calculate_score(request.user)
        
        return redirect('savings_history')
    
    return render(request, 'add_savings.html')


# ============================================
# SAVINGS HISTORY
# ============================================

@login_required
def savings_history(request):
    """
    View savings history
    """
    deposits = SavingsDeposit.objects.filter(user=request.user).order_by('-deposit_date')
    
    total = sum(d.amount for d in deposits)
    current_balance = deposits.first().balance_after if deposits.exists() else 0
    
    context = {
        'deposits': deposits,
        'total_deposits': total,
        'current_balance': current_balance,
    }
    
    return render(request, 'savings_history.html', context)


# ============================================
# VERIFY MOBILE MONEY
# ============================================

@login_required
def verify_mobile_money(request):
    """
    Link and verify mobile money account
    """
    if request.method == 'POST':
        provider = request.POST.get('provider')
        phone = request.POST.get('phone_number')
        
        # Create account (in real app, you'd send verification code)
        account, created = MobileMoneyAccount.objects.get_or_create(
            user=request.user,
            provider=provider,
            phone_number=phone,
            defaults={'is_verified': True, 'verified_at': timezone.now()}
        )
        
        if created:
            messages.success(request, "Mobile money account added! +10 credit score points.")
            CreditScoreCalculator.calculate_score(request.user)
        else:
            messages.info(request, "This account is already linked.")
        
        return redirect('dashboard')
    
    return render(request, 'verify_mobile_money.html')