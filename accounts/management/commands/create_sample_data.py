from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import State, District, BloodBank, BloodStock
import random

class Command(BaseCommand):
    help = 'Creates sample data for blood banks and stocks'

    def handle(self, *args, **kwargs):
        # Create states
        states_data = [
            "Maharashtra", "Delhi", "Karnataka", "Tamil Nadu", "Gujarat"
        ]
        
        self.stdout.write('Creating states...')
        states = []
        for state_name in states_data:
            state, created = State.objects.get_or_create(name=state_name)
            states.append(state)
            if created:
                self.stdout.write(f'Created state: {state_name}')

        # Create districts
        districts_data = {
            "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Thane"],
            "Delhi": ["New Delhi", "North Delhi", "South Delhi", "East Delhi"],
            "Karnataka": ["Bangalore", "Mysore", "Hubli", "Mangalore"],
            "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Salem"],
            "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot"]
        }

        self.stdout.write('Creating districts...')
        districts = []
        for state in states:
            for district_name in districts_data[state.name]:
                district, created = District.objects.get_or_create(
                    name=district_name,
                    state=state
                )
                districts.append(district)
                if created:
                    self.stdout.write(f'Created district: {district_name} in {state.name}')

        # Create blood banks
        self.stdout.write('Creating blood banks...')
        for district in districts:
            for i in range(2):  # 2 blood banks per district
                name = f"{district.name} Blood Bank {i+1}"
                # Format district name for email (remove spaces, lowercase)
                district_email = district.name.lower().replace(' ', '')
                
                blood_bank, created = BloodBank.objects.get_or_create(
                    name=name,
                    defaults={
                        'address': f"Address {i+1}, {district.name}",
                        'district': district,
                        'contact_number': f"+91{random.randint(7000000000, 9999999999)}",
                        'email': f"bloodbank{i+1}@{district_email}.com",
                        'license_number': f"BB{random.randint(100000, 999999)}",
                        'is_active': True
                    }
                )

                if created:
                    self.stdout.write(f'Created blood bank: {name}')
                else:
                    self.stdout.write(f'Using existing blood bank: {name}')
                    
                # Create or update blood stocks for this blood bank
                for blood_group, _ in BloodStock.BLOOD_GROUP_CHOICES:
                    for component, _ in BloodStock.COMPONENT_CHOICES:
                        # Different stock levels based on component type
                        if component == 'Whole Blood':
                            units = random.randint(50, 100)  # More whole blood
                        else:
                            units = random.randint(10, 30)   # Less for components
                            
                        expiry_date = timezone.now().date() + timezone.timedelta(days=random.randint(60, 90))
                        
                        stock, created = BloodStock.objects.update_or_create(
                            blood_bank=blood_bank,
                            blood_group=blood_group,
                            component=component,
                            defaults={
                                'units_available': units,
                                'expiry_date': expiry_date
                            }
                        )
                        
                        action = 'Created' if created else 'Updated'
                        self.stdout.write(f'{action} stock: {blood_group} {component} ({units} units) at {blood_bank.name}')

        self.stdout.write(self.style.SUCCESS('Successfully created sample data')) 