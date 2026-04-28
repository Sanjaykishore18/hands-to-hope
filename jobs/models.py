from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class WageRate(models.Model):
    """Admin-defined wages per region and skill"""
    state = models.CharField(max_length=50)
    district = models.CharField(max_length=100, blank=True, help_text='Leave blank for state-level rate')
    skill = models.CharField(max_length=50)
    daily_rate = models.DecimalField(max_digits=8, decimal_places=2, help_text='Daily wage in INR')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('state', 'district', 'skill')
        ordering = ['state', 'district', 'skill']

    def __str__(self):
        loc = f"{self.district}, {self.state}" if self.district else self.state
        return f"{self.skill} - {loc}: ₹{self.daily_rate}/day"


class JobOffer(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    hirer = models.ForeignKey('hirers.HirerProfile', on_delete=models.CASCADE, related_name='offers_sent')
    worker = models.ForeignKey('workers.WorkerProfile', on_delete=models.CASCADE, related_name='offers_received')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    work_date = models.DateField()
    work_time = models.TimeField(null=True, blank=True)
    duration_hours = models.PositiveIntegerField(default=8, help_text='Expected hours of work')
    description = models.TextField(blank=True, help_text='Description of work to be done')
    offered_wage = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.hirer} → {self.worker} on {self.work_date} [{self.status}]"

    @property
    def total_wage(self):
        if self.offered_wage and self.duration_hours:
            return round(float(self.offered_wage) * self.duration_hours / 8, 2)
        return None


class Review(models.Model):
    offer = models.OneToOneField(JobOffer, on_delete=models.CASCADE, related_name='review')
    worker = models.ForeignKey('workers.WorkerProfile', on_delete=models.CASCADE, related_name='reviews')
    hirer = models.ForeignKey('hirers.HirerProfile', on_delete=models.CASCADE, related_name='reviews_given')
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Rating from 1 to 5 stars'
    )
    review_text = models.TextField(help_text='Describe the worker\'s performance in detail')
    is_approved = models.BooleanField(default=True, help_text='Admin can hide inappropriate reviews')
    is_fake = models.BooleanField(default=False, help_text='Flagged as fake by ML model')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.hirer} for {self.worker}: {self.rating}★"

    def save(self, *args, **kwargs):
        # Run fake-review detection only on new reviews (no pk yet before super)
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            try:
                from ml_models.predictor import is_fake_review, build_fake_review_features
                features = build_fake_review_features(self, self.hirer)
                self.is_fake = is_fake_review(features)
                Review.objects.filter(pk=self.pk).update(is_fake=self.is_fake)
            except Exception:
                pass  # Never break review submission due to ML error
        self.worker.update_rating()
