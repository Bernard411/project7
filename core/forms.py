from django import forms
from .models import CreditScore, PaymentHistory, CreditAccount

class CreditScoreForm(forms.ModelForm):
    class Meta:
        model = CreditScore
        fields = ['score', 'bureau', 'notes']
        widgets = {
            'score': forms.NumberInput(attrs={'class': 'form-control', 'min': 300, 'max': 850}),
            'bureau': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class PaymentHistoryForm(forms.ModelForm):
    class Meta:
        model = PaymentHistory
        fields = ['creditor_name', 'payment_date', 'amount', 'status', 'days_late']
        widgets = {
            'creditor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'days_late': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class CreditAccountForm(forms.ModelForm):
    class Meta:
        model = CreditAccount
        fields = ['account_name', 'account_type', 'credit_limit', 'current_balance', 
                  'interest_rate', 'opened_date', 'is_active']
        widgets = {
            'account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-control'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'current_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'opened_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }