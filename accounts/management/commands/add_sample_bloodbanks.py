from django.core.management.base import BaseCommand
from accounts.models import BloodBank, District

class Command(BaseCommand):
    help = 'Add sample blood banks in Mumbai City'

    def handle(self, *args, **kwargs):
        try:
            # Get Mumbai City district
            district = District.objects.get(name='Mumbai City')

            # Sample blood banks data
            blood_banks_data = [
                {
                    'name': 'LifeLine Blood Bank',
                    'address': '123, Linking Road, Bandra West, Mumbai - 400050',
                    'contact_number': '+919876543201',
                    'email': 'info@lifelinebloodbank.com',
                    'license_number': 'MB123456',
                },
                {
                    'name': 'City Care Blood Center',
                    'address': '45, SV Road, Andheri West, Mumbai - 400058',
                    'contact_number': '+919876543202',
                    'email': 'contact@citycareblood.com',
                    'license_number': 'MB123457',
                }
            ]

            # Create blood banks
            for bank_data in blood_banks_data:
                blood_bank, created = BloodBank.objects.get_or_create(
                    license_number=bank_data['license_number'],
                    defaults={
                        'name': bank_data['name'],
                        'address': bank_data['address'],
                        'district': district,
                        'contact_number': bank_data['contact_number'],
                        'email': bank_data['email'],
                        'is_active': True
                    }
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully created blood bank: {bank_data["name"]}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Blood bank already exists: {bank_data["name"]}')
                    )

        except District.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Mumbai City district not found in the database')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating blood banks: {str(e)}')
            ) 