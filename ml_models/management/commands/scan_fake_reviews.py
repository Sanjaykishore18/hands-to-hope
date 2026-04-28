"""
Management command: scan_fake_reviews
======================================
Retroactively runs the fake-review ML model on all existing reviews
that have not yet been scanned (is_fake=False and no flag set).

Usage:
    python manage.py scan_fake_reviews
    python manage.py scan_fake_reviews --force   # re-scan ALL reviews
"""

from django.core.management.base import BaseCommand
from jobs.models import Review


class Command(BaseCommand):
    help = 'Run fake-review ML detection on existing reviews in the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-scan all reviews, not just unscanned ones.',
        )

    def handle(self, *args, **options):
        from ml_models.predictor import is_fake_review, build_fake_review_features

        reviews = Review.objects.select_related('hirer', 'worker', 'offer')
        total = reviews.count()
        self.stdout.write(f'Found {total} total reviews.')

        flagged = 0
        errors = 0

        for review in reviews:
            try:
                features = build_fake_review_features(review, review.hirer)
                result = is_fake_review(features)
                Review.objects.filter(pk=review.pk).update(is_fake=result)
                if result:
                    flagged += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [FAKE]  Review #{review.pk} by {review.hirer} '
                            f'for {review.worker} — rating {review.rating}★'
                        )
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f'  [ERROR] Review #{review.pk}: {e}')
                )

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Scanned {total} reviews: '
            f'{flagged} flagged as fake, {errors} errors.'
        ))
