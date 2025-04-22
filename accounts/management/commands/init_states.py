from django.core.management.base import BaseCommand
from accounts.models import State, District

class Command(BaseCommand):
    help = 'Initialize states and districts'

    def handle(self, *args, **kwargs):
        # Sample states and districts
        states_data = {
            'Maharashtra': ['Mumbai', 'Pune', 'Nagpur', 'Thane', 'Nashik'],
            'Delhi': ['North Delhi', 'South Delhi', 'East Delhi', 'West Delhi', 'Central Delhi'],
            'Karnataka': ['Bangalore', 'Mysore', 'Hubli', 'Mangalore', 'Belgaum'],
            'Tamil Nadu': ['Chennai', 'Coimbatore', 'Madurai', 'Salem', 'Tiruchirappalli'],
            'Gujarat': ['Ahmedabad', 'Surat', 'Vadodara', 'Rajkot', 'Bhavnagar'],
        }

        for state_name, districts in states_data.items():
            state, created = State.objects.get_or_create(name=state_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created state: {state_name}'))
            
            for district_name in districts:
                district, created = District.objects.get_or_create(
                    state=state,
                    name=district_name
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created district: {district_name} in {state_name}'))

        self.stdout.write(self.style.SUCCESS('Successfully initialized states and districts')) 