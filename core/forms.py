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
        # Retrieve the profile created by the signal
        profile = user.userprofile  # Access via the reverse relation
        # Update with form data (overwrites placeholders)
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