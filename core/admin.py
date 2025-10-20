from django.contrib import admin
from .models import UserProfile, MicroLoan, LoanPayment, MobileMoneyAccount, SocialVouch, SavingsDeposit

# ============================================
# USER PROFILE ADMIN
# ============================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'national_id', 'current_credit_score', 'is_verified', 'account_created')
    list_filter = ('is_verified', 'employment_status', 'district')
    search_fields = ('user__username', 'phone_number', 'national_id')
    readonly_fields = ('current_credit_score', 'last_score_update', 'account_created')
    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'phone_number', 'national_id', 'date_of_birth')
        }),
        ('Location', {
            'fields': ('district', 'traditional_authority', 'village')
        }),
        ('Employment', {
            'fields': ('employment_status', 'monthly_income')
        }),
        ('Credit Information', {
            'fields': ('current_credit_score', 'last_score_update', 'account_created', 'is_verified')
        }),
    )
    ordering = ('-current_credit_score',)

# ============================================
# MICROLOAN ADMIN
# ============================================

@admin.register(MicroLoan)
class MicroLoanAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'due_date', 'is_overdue', 'days_overdue', 'score_at_application')
    list_filter = ('status', 'due_date')
    search_fields = ('user__username',)
    readonly_fields = ('applied_at', 'score_at_application', 'total_amount_due', 'amount_paid')
    fieldsets = (
        ('Loan Details', {
            'fields': ('user', 'amount', 'interest_rate', 'duration_days', 'total_amount_due')
        }),
        ('Status', {
            'fields': ('status', 'applied_at', 'approved_at', 'due_date', 'paid_at')
        }),
        ('Repayment', {
            'fields': ('amount_paid', 'score_at_application')
        }),
    )
    actions = ['mark_as_approved', 'mark_as_rejected']

    def mark_as_approved(self, request, queryset):
        queryset.update(status='approved', approved_at=timezone.now())
        self.message_user(request, "Selected loans have been approved.")
    mark_as_approved.short_description = "Mark selected loans as approved"

    def mark_as_rejected(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, "Selected loans have been rejected.")
    mark_as_rejected.short_description = "Mark selected loans as rejected"

# ============================================
# LOAN PAYMENT ADMIN
# ============================================

@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    list_display = ('loan', 'amount', 'payment_date', 'payment_method', 'was_on_time', 'days_from_due')
    list_filter = ('payment_method', 'was_on_time')
    search_fields = ('loan__user__username', 'transaction_reference')
    readonly_fields = ('payment_date',)
    fieldsets = (
        (None, {
            'fields': ('loan', 'amount', 'payment_method', 'transaction_reference')
        }),
        ('Payment Status', {
            'fields': ('was_on_time', 'days_from_due', 'payment_date')
        }),
    )

# ============================================
# MOBILE MONEY ACCOUNT ADMIN
# ============================================

@admin.register(MobileMoneyAccount)
class MobileMoneyAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'phone_number', 'is_verified', 'verified_at')
    list_filter = ('provider', 'is_verified')
    search_fields = ('user__username', 'phone_number')
    readonly_fields = ('created_at', 'verified_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'provider', 'phone_number')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_at')
        }),
        ('Transaction Data', {
            'fields': ('average_monthly_balance', 'transaction_count_30days', 'created_at')
        }),
    )

# ============================================
# SOCIAL VOUCH ADMIN
# ============================================

@admin.register(SocialVouch)
class SocialVouchAdmin(admin.ModelAdmin):
    list_display = ('voucher', 'vouchee', 'trust_level', 'relationship', 'willing_to_cosign', 'is_active')
    list_filter = ('trust_level', 'willing_to_cosign', 'is_active')
    search_fields = ('voucher__username', 'vouchee__username', 'relationship')
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': ('voucher', 'vouchee', 'trust_level', 'relationship')
        }),
        ('Co-signing', {
            'fields': ('willing_to_cosign', 'max_cosign_amount')
        }),
        ('Status', {
            'fields': ('is_active', 'vouchee_defaulted', 'created_at')
        }),
    )

# ============================================
# SAVINGS DEPOSIT ADMIN
# ============================================

@admin.register(SavingsDeposit)
class SavingsDepositAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'deposit_date', 'balance_after')
    list_filter = ('deposit_date',)
    search_fields = ('user__username',)
    readonly_fields = ('deposit_date',)
    fieldsets = (
        (None, {
            'fields': ('user', 'amount', 'balance_after')
        }),
        ('Details', {
            'fields': ('deposit_date',)
        }),
    )