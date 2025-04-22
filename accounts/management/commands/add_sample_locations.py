from django.core.management.base import BaseCommand
from accounts.models import State, District

class Command(BaseCommand):
    help = 'Add sample state and district data'

    def handle(self, *args, **kwargs):
        try:
            # Create Maharashtra state
            maharashtra, created = State.objects.get_or_create(name='Maharashtra')
            
            # Create districts in Maharashtra
            districts = [
                'Nanded',
                'Aurangabad',
                'Pune',
                'Mumbai City',
                'Nagpur',
                'Nashik'
            ]

            for district_name in districts:
                district, created = District.objects.get_or_create(
                    name=district_name,
                    state=maharashtra
                )
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully created district: {district_name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'District already exists: {district_name}')
                    )

            self.stdout.write(
                self.style.SUCCESS('Successfully added state and districts')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating sample locations: {str(e)}')
            ) 