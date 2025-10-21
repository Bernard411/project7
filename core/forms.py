from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

class RegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput, required=True)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput, required=True)

    class Meta:
        model = UserProfile
        fields = [
            'phone_number', 'national_id', 'date_of_birth', 'district',
            'traditional_authority', 'village', 'employment_status', 'monthly_income'
        ]

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1']
        )
        profile = user.userprofile
        profile.phone_number = self.cleaned_data['phone_number']
        profile.national_id = self.cleaned_data['national_id']
        profile.date_of_birth = self.cleaned_data['date_of_birth']
        profile.district = self.cleaned_data['district']
        profile.traditional_authority = self.cleaned_data['traditional_authority']
        profile.village = self.cleaned_data['village']
        profile.employment_status = self.cleaned_data['employment_status']
        profile.monthly_income = self.cleaned_data['monthly_income']
        if commit:
            profile.save()
        return user, profile

class ProfileForm(forms.ModelForm):
    national_id_document = forms.FileField(required=False, help_text="Upload a valid National ID or Passport")
    proof_of_address = forms.FileField(required=False, help_text="Upload a utility bill or chief's letter")
    income_document = forms.FileField(required=False, help_text="Upload payslip, bank statement, or tax return")
    id_verified = forms.BooleanField(required=False, widget=forms.HiddenInput)
    address_verified = forms.BooleanField(required=False, widget=forms.HiddenInput)
    income_verified = forms.BooleanField(required=False, widget=forms.HiddenInput)
    authenticity_score = forms.FloatField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = UserProfile
        fields = ['national_id_document', 'proof_of_address', 'income_document', 'id_verified', 'address_verified', 'income_verified', 'authenticity_score']

    def clean(self):
        cleaned_data = super().clean()
        for field in ['national_id_document', 'proof_of_address', 'income_document']:
            file = cleaned_data.get(field)
            if file and not file.name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                self.add_error(field, "Only PDF, JPG, or PNG files are allowed.")
        
        # Enforce automated verification for uploaded documents
        if any(cleaned_data.get(field) for field in ['national_id_document', 'proof_of_address', 'income_document']):
            if not all([cleaned_data.get('id_verified'), cleaned_data.get('address_verified'), cleaned_data.get('income_verified')]):
                self.add_error(None, "All uploaded documents must be verified automatically.")
            if cleaned_data.get('authenticity_score', 0) < 0.5:
                self.add_error(None, "Document authenticity score is too low.")
        
        return cleaned_data

    def save(self, commit=True):
        profile = self.instance
        if self.cleaned_data.get('national_id_document'):
            profile.national_id_document = self.cleaned_data['national_id_document']
        if self.cleaned_data.get('proof_of_address'):
            profile.proof_of_address = self.cleaned_data['proof_of_address']
        if self.cleaned_data.get('income_document'):
            profile.income_document = self.cleaned_data['income_document']
        profile.id_verified = self.cleaned_data['id_verified']
        profile.address_verified = self.cleaned_data['address_verified']
        profile.income_verified = self.cleaned_data['income_verified']
        profile.is_verified = profile.all_documents_verified()
        if commit:
            profile.save()
            from .models import CreditScoreCalculator
            CreditScoreCalculator.calculate_score(profile.user)
        return profile
