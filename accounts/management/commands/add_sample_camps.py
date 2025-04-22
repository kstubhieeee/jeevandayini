from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import BloodBank, District, BloodCamp
from datetime import datetime, time

class Command(BaseCommand):
    help = 'Add sample blood camp data'

    def handle(self, *args, **kwargs):
        try:
            # Get Mumbai City district
            district = District.objects.get(name='Mumbai City')
            
            # Get some existing blood banks
            blood_banks = BloodBank.objects.filter(district=district)[:2]
            if len(blood_banks) < 2:
                self.stdout.write(self.style.ERROR('Please ensure there are at least 2 blood banks in Mumbai City district'))
                return
            
            blood_bank1, blood_bank2 = blood_banks

            # Create sample camps
            camps_data = [
                {
                    'name': 'Community Health Drive',
                    'blood_bank': blood_bank1,
                    'district': district,
                    'location': 'Andheri Sports Complex, Western Express Highway',
                    'camp_date': '2025-03-16',
                    'start_time': time(9, 0),  # 9:00 AM
                    'end_time': time(17, 0),   # 5:00 PM
                    'contact_person': 'Dr. Rajesh Kumar',
                    'contact_number': '+919876543210',
                    'expected_donors': 100,
                    'description': 'Annual community blood donation camp with free health checkup'
                },
                {
                    'name': 'College Blood Drive',
                    'blood_bank': blood_bank2,
                    'district': district,
                    'location': 'Mumbai University Campus, Kalina',
                    'camp_date': '2025-03-16',
                    'start_time': time(10, 0),  # 10:00 AM
                    'end_time': time(16, 0),    # 4:00 PM
                    'contact_person': 'Prof. Meera Sharma',
                    'contact_number': '+919876543211',
                    'expected_donors': 150,
                    'description': 'Blood donation camp organized by university students'
                },
                {
                    'name': 'Corporate Wellness Camp',
                    'blood_bank': blood_bank1,
                    'district': district,
                    'location': 'Bandra Kurla Complex, G Block',
                    'camp_date': '2025-03-16',
                    'start_time': time(8, 30),  # 8:30 AM
                    'end_time': time(18, 30),   # 6:30 PM
                    'contact_person': 'Mr. Suresh Patel',
                    'contact_number': '+919876543212',
                    'expected_donors': 200,
                    'description': 'Blood donation drive for corporate professionals with health awareness session'
                }
            ]

            # Create the camps
            for camp_data in camps_data:
                BloodCamp.objects.create(**camp_data)
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created camp: {camp_data["name"]}')
                )

        except District.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Mumbai City district not found in the database')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating sample camps: {str(e)}')
            ) 