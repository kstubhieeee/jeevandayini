from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from datetime import datetime

# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    blood_group = models.CharField(max_length=3)
    
    def __str__(self):
        return f"{self.user.username}'s profile"

class Donor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    last_donation_date = models.DateField(null=True, blank=True)
    donation_type = models.CharField(max_length=20, choices=[
        ('whole_blood', 'Whole Blood'),
        ('platelets', 'Platelets'),
        ('plasma', 'Plasma'),
        ('red_cells', 'Red Cells'),
    ])
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.donation_type}"

class Receiver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    hospital_name = models.CharField(max_length=100)
    urgency_level = models.CharField(max_length=20, choices=[
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ])
    required_blood_type = models.CharField(max_length=3)
    units_needed = models.IntegerField()
    
    def __str__(self):
        return f"{self.user.username} - {self.required_blood_type}"

class State(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class District(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='districts')
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['state', 'name']
        unique_together = ['state', 'name']

    def __str__(self):
        return f"{self.name}, {self.state.name}"

class BloodBank(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='blood_banks')
    contact_number = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    email = models.EmailField(blank=True, null=True)
    license_number = models.CharField(
        max_length=50,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z]{2}\d{6}$',
                message="License number must be in format: 'XX999999' (2 uppercase letters followed by 6 digits)"
            )
        ]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['license_number']),
            models.Index(fields=['district', 'is_active']),
        ]

    def clean(self):
        # Custom validation
        if self.email and BloodBank.objects.exclude(pk=self.pk).filter(email=self.email).exists():
            raise ValidationError({'email': 'This email is already registered with another blood bank.'})
        
        if BloodBank.objects.exclude(pk=self.pk).filter(contact_number=self.contact_number).exists():
            raise ValidationError({'contact_number': 'This contact number is already registered with another blood bank.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_total_stock(self):
        return sum(stock.units_available for stock in self.blood_stocks.all())

    def get_available_blood_groups(self):
        return self.blood_stocks.filter(units_available__gt=0).values_list('blood_group', flat=True).distinct()

    def __str__(self):
        return self.name

class BloodStock(models.Model):
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A Positive'),
        ('A-', 'A Negative'),
        ('B+', 'B Positive'),
        ('B-', 'B Negative'),
        ('O+', 'O Positive'),
        ('O-', 'O Negative'),
        ('AB+', 'AB Positive'),
        ('AB-', 'AB Negative'),
    ]

    COMPONENT_CHOICES = [
        ('Whole Blood', 'Whole Blood'),
        ('Plasma', 'Plasma'),
        ('Platelets', 'Platelets'),
        ('Red Cells', 'Red Cells'),
    ]

    blood_bank = models.ForeignKey(BloodBank, on_delete=models.CASCADE, related_name='blood_stocks')
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES)
    component = models.CharField(max_length=20, choices=COMPONENT_CHOICES)
    units_available = models.PositiveIntegerField(
        default=0,
        validators=[
            MinValueValidator(0, message="Units cannot be negative"),
            MaxValueValidator(1000, message="Maximum 1000 units allowed")
        ]
    )
    last_updated = models.DateTimeField(auto_now=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ['blood_bank', 'blood_group', 'component']
        ordering = ['blood_bank', 'blood_group', 'component']
        indexes = [
            models.Index(fields=['blood_group', 'component']),
            models.Index(fields=['blood_bank', 'units_available']),
        ]

    def clean(self):
        if self.expiry_date and self.expiry_date < timezone.now().date():
            raise ValidationError({'expiry_date': 'Expiry date cannot be in the past.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_stock_level_percentage(self):
        MAX_CAPACITY = 100
        return min((self.units_available / MAX_CAPACITY) * 100, 100)

    def is_low_stock(self):
        return self.get_stock_level_percentage() <= 30

    def is_expired(self):
        return self.expiry_date and self.expiry_date < timezone.now().date()

    def __str__(self):
        return f"{self.blood_group} {self.component} at {self.blood_bank.name}"

class BloodCamp(models.Model):
    name = models.CharField(max_length=200)
    blood_bank = models.ForeignKey(BloodBank, on_delete=models.CASCADE, related_name='blood_camps')
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='blood_camps')
    location = models.TextField(help_text="Detailed address of the camp")
    camp_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    contact_person = models.CharField(max_length=100)
    contact_number = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    expected_donors = models.PositiveIntegerField(
        default=50,
        validators=[
            MinValueValidator(10, message="Expected donors should be at least 10"),
            MaxValueValidator(1000, message="Expected donors cannot exceed 1000")
        ]
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, help_text="Additional details about the camp")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['camp_date', 'start_time']
        indexes = [
            models.Index(fields=['camp_date']),
            models.Index(fields=['district', 'is_active']),
            models.Index(fields=['blood_bank', 'is_active']),
        ]

    def clean(self):
        # Validate that end time is after start time
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({'end_time': 'End time must be after start time.'})
        
        # Validate that camp date is not in the past
        if self.camp_date and self.camp_date < timezone.now().date():
            raise ValidationError({'camp_date': 'Camp date cannot be in the past.'})
        
        # Check if blood bank is active
        if not self.blood_bank.is_active:
            raise ValidationError({'blood_bank': 'Selected blood bank is not active.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def is_ongoing(self):
        now = timezone.now()
        camp_start = timezone.make_aware(datetime.combine(self.camp_date, self.start_time))
        camp_end = timezone.make_aware(datetime.combine(self.camp_date, self.end_time))
        return camp_start <= now <= camp_end

    def get_status(self):
        now = timezone.now()
        camp_date = self.camp_date
        camp_start = timezone.make_aware(datetime.combine(camp_date, self.start_time))
        camp_end = timezone.make_aware(datetime.combine(camp_date, self.end_time))

        if now < camp_start:
            return 'Upcoming'
        elif camp_start <= now <= camp_end:
            return 'Ongoing'
        else:
            return 'Completed'

    def __str__(self):
        return f"{self.name} on {self.camp_date}"

class Appointment(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other')
    ]

    ID_TYPE_CHOICES = [
        ('AADHAR', 'Aadhar Card'),
        ('PAN', 'PAN Card'),
        ('PASSPORT', 'Passport'),
        ('DRIVING_LICENSE', 'Driving License'),
        ('VOTER_ID', 'Voter ID')
    ]

    TIME_SLOTS = [
        ('09:00', '09:00 AM'),
        ('09:30', '09:30 AM'),
        ('10:00', '10:00 AM'),
        ('10:30', '10:30 AM'),
        ('11:00', '11:00 AM'),
        ('11:30', '11:30 AM'),
        ('12:00', '12:00 PM'),
        ('12:30', '12:30 PM'),
        ('14:00', '02:00 PM'),
        ('14:30', '02:30 PM'),
        ('15:00', '03:00 PM'),
        ('15:30', '03:30 PM'),
        ('16:00', '04:00 PM'),
        ('16:30', '04:30 PM'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled')
    ]

    DONATION_STATUS_CHOICES = [
        ('NOT_DONATED', 'Not Donated'),
        ('DONATED', 'Donated')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    blood_bank = models.ForeignKey(BloodBank, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField()
    appointment_time = models.CharField(max_length=5, choices=TIME_SLOTS)
    full_name = models.CharField(max_length=100)
    age = models.PositiveIntegerField(
        validators=[
            MinValueValidator(18, message="You must be at least 18 years old to donate blood"),
            MaxValueValidator(65, message="Maximum age for blood donation is 65 years")
        ]
    )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    blood_group = models.CharField(max_length=3, choices=BloodStock.BLOOD_GROUP_CHOICES)
    phone_number = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    email = models.EmailField()
    address = models.TextField()
    govt_id_type = models.CharField(max_length=15, choices=ID_TYPE_CHOICES)
    govt_id_number = models.CharField(max_length=20)
    previous_donation = models.DateField(null=True, blank=True, help_text="Date of last blood donation, if any")
    medical_conditions = models.TextField(blank=True, help_text="List any medical conditions or medications")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    donation_status = models.CharField(max_length=15, choices=DONATION_STATUS_CHOICES, default='NOT_DONATED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-appointment_date', '-appointment_time']
        indexes = [
            models.Index(fields=['appointment_date', 'appointment_time']),
            models.Index(fields=['blood_bank', 'status']),
            models.Index(fields=['user', 'status']),
        ]
        unique_together = ['blood_bank', 'appointment_date', 'appointment_time']

    def clean(self):
        # Validate previous donation date is not in the future
        if self.previous_donation and self.previous_donation > timezone.now().date():
            raise ValidationError({'previous_donation': 'Previous donation date cannot be in the future.'})
        
        # Check if the time slot is available
        if hasattr(self, 'blood_bank') and self.blood_bank and self.appointment_date and self.appointment_time:
            if Appointment.objects.filter(
                blood_bank=self.blood_bank,
                appointment_date=self.appointment_date,
                appointment_time=self.appointment_time
            ).exclude(pk=self.pk).exists():
                raise ValidationError({'appointment_time': 'This time slot is already booked.'})

    def save(self, *args, **kwargs):
        bypass_validation = kwargs.pop('bypass_validation', False)
        if not bypass_validation:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name}'s appointment at {self.blood_bank.name} on {self.appointment_date}"

class BloodDonationCamp(models.Model):
    blood_bank = models.ForeignKey(BloodBank, on_delete=models.CASCADE, related_name='donation_camps')
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=500)
    camp_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    contact_person = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    expected_donors = models.PositiveIntegerField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-camp_date', '-start_time']

    def __str__(self):
        return f"{self.name} by {self.blood_bank.name} on {self.camp_date}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)
