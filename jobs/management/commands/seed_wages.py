from django.core.management.base import BaseCommand
from jobs.models import WageRate


SAMPLE_WAGES = [
    # (state, district, skill, daily_rate)
    ('Bihar', '', 'agriculture', 300),
    ('Bihar', '', 'construction', 350),
    ('Bihar', '', 'domestic', 250),
    ('Bihar', '', 'plumbing', 400),
    ('Bihar', '', 'electrical', 450),
    ('Bihar', 'Patna', 'construction', 400),
    ('Bihar', 'Patna', 'plumbing', 500),
    ('Bihar', 'Patna', 'electrical', 550),
    ('Bihar', 'Patna', 'domestic', 300),

    ('Uttar Pradesh', '', 'agriculture', 280),
    ('Uttar Pradesh', '', 'construction', 330),
    ('Uttar Pradesh', '', 'domestic', 240),
    ('Uttar Pradesh', '', 'masonry', 380),
    ('Uttar Pradesh', 'Lucknow', 'construction', 420),
    ('Uttar Pradesh', 'Lucknow', 'electrical', 500),

    ('Maharashtra', '', 'agriculture', 350),
    ('Maharashtra', '', 'construction', 500),
    ('Maharashtra', '', 'carpentry', 550),
    ('Maharashtra', 'Pune', 'construction', 600),
    ('Maharashtra', 'Pune', 'electrical', 650),
    ('Maharashtra', 'Mumbai', 'domestic', 450),

    ('Rajasthan', '', 'construction', 320),
    ('Rajasthan', '', 'agriculture', 270),
    ('Rajasthan', '', 'masonry', 360),

    ('Tamil Nadu', '', 'agriculture', 320),
    ('Tamil Nadu', '', 'construction', 450),
    ('Tamil Nadu', '', 'welding', 500),
    ('Tamil Nadu', 'Chennai', 'electrical', 600),

    ('West Bengal', '', 'agriculture', 290),
    ('West Bengal', '', 'construction', 340),
    ('West Bengal', '', 'tailoring', 300),

    ('Madhya Pradesh', '', 'agriculture', 260),
    ('Madhya Pradesh', '', 'construction', 310),

    ('Gujarat', '', 'construction', 400),
    ('Gujarat', '', 'agriculture', 330),

    ('Karnataka', '', 'agriculture', 340),
    ('Karnataka', '', 'construction', 450),
    ('Karnataka', 'Bangalore', 'domestic', 500),

    ('Punjab', '', 'agriculture', 380),
    ('Punjab', '', 'driving', 450),
    ('Haryana', '', 'agriculture', 370),
    ('Haryana', '', 'construction', 420),

    ('Jharkhand', '', 'agriculture', 260),
    ('Jharkhand', '', 'construction', 300),

    ('Odisha', '', 'agriculture', 250),
    ('Odisha', '', 'construction', 290),
]


class Command(BaseCommand):
    help = 'Seed sample wage rates for different states and skills'

    def handle(self, *args, **options):
        created_count = 0
        for state, district, skill, rate in SAMPLE_WAGES:
            _, created = WageRate.objects.get_or_create(
                state=state,
                district=district,
                skill=skill,
                defaults={'daily_rate': rate}
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} wage rate entries!')
        )
        self.stdout.write(f'Total wage rates: {WageRate.objects.count()}')
