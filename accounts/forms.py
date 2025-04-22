from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Donor, Receiver, District, State, BloodBank, Appointment
import re
from django.core.exceptions import ValidationError
from django.utils import timezone

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    blood_group = forms.ChoiceField(choices=[
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
    ], widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'blood_group', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

class DonorRegistrationForm(forms.ModelForm):
    class Meta:
        model = Donor
        fields = ['phone_number', 'donation_type']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'donation_type': forms.Select(attrs={'class': 'form-control'}),
        }

class ReceiverRegistrationForm(forms.ModelForm):
    class Meta:
        model = Receiver
        fields = ['phone_number', 'hospital_name', 'urgency_level', 'required_blood_type', 'units_needed']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'hospital_name': forms.TextInput(attrs={'class': 'form-control'}),
            'urgency_level': forms.Select(attrs={'class': 'form-control'}),
            'required_blood_type': forms.Select(attrs={'class': 'form-control'}),
            'units_needed': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class BloodBankSignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    name = forms.CharField(max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    state = forms.ModelChoiceField(
        queryset=State.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'state-select'}),
        empty_label="Select State",
        required=True
    )
    district = forms.ModelChoiceField(
        queryset=District.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'district-select'}),
        empty_label="Select District",
        required=True
    )
    contact_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Format: +999999999 (up to 15 digits)"
    )
    license_number = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Format: XX999999 (2 uppercase letters followed by 6 digits)"
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'name', 'address', 'state', 'district', 'contact_number', 'license_number', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize state field with all states
        self.fields['state'].queryset = State.objects.all().order_by('name')
        
        # Initialize district field based on state if provided
        if 'state' in self.data:
            try:
                state_id = int(self.data.get('state'))
                self.fields['district'].queryset = District.objects.filter(state_id=state_id).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['district'].queryset = self.instance.district.state.districts.all().order_by('name')

    def clean_contact_number(self):
        contact_number = self.cleaned_data.get('contact_number')
        if not contact_number:
            return contact_number
        if not re.match(r'^\+?1?\d{9,15}$', contact_number):
            raise forms.ValidationError("Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
        return contact_number

    def clean_license_number(self):
        license_number = self.cleaned_data.get('license_number')
        if not license_number:
            return license_number
        if not re.match(r'^[A-Z]{2}\d{6}$', license_number):
            raise forms.ValidationError("License number must be in format: 'XX999999' (2 uppercase letters followed by 6 digits)")
        return license_number

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            'appointment_date', 'appointment_time', 'full_name', 'age',
            'gender', 'blood_group', 'phone_number', 'email', 'address',
            'govt_id_type', 'govt_id_number', 'previous_donation',
            'medical_conditions'
        ]
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date', 'min': timezone.now().date().isoformat()}),
            'previous_donation': forms.DateInput(attrs={'type': 'date'}),
            'medical_conditions': forms.Textarea(attrs={'rows': 3, 'placeholder': 'List any medical conditions or medications you are currently taking'}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_appointment_date(self):
        date = self.cleaned_data['appointment_date']
        if date < timezone.now().date():
            raise ValidationError("Appointment date cannot be in the past")
        return date

    def clean_previous_donation(self):
        date = self.cleaned_data.get('previous_donation')
        if date and date > timezone.now().date():
            raise ValidationError("Previous donation date cannot be in the future")
        return date

    def clean_govt_id_number(self):
        id_type = self.cleaned_data.get('govt_id_type')
        id_number = self.cleaned_data.get('govt_id_number')

        if id_type == 'AADHAR':
            if not (id_number.isdigit() and len(id_number) == 12):
                raise ValidationError("Aadhar number must be 12 digits")
        elif id_type == 'PAN':
            if not (len(id_number) == 10 and id_number.isalnum()):
                raise ValidationError("PAN number must be 10 alphanumeric characters")
        elif id_type == 'PASSPORT':
            if not (len(id_number) == 8 and id_number[0].isalpha() and id_number[1:].isdigit()):
                raise ValidationError("Passport number must be 1 letter followed by 7 digits")
        
        return id_number 