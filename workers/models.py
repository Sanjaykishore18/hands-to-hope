from django.db import models
from django.conf import settings
from django.utils import timezone


VERIFICATION_STATUS = (
    ('pending', 'Pending'),
    ('verified', 'Verified'),
    ('rejected', 'Rejected'),
)

STATES_CHOICES = [
    ('Andhra Pradesh', 'Andhra Pradesh'), ('Arunachal Pradesh', 'Arunachal Pradesh'),
    ('Assam', 'Assam'), ('Bihar', 'Bihar'), ('Chhattisgarh', 'Chhattisgarh'),
    ('Goa', 'Goa'), ('Gujarat', 'Gujarat'), ('Haryana', 'Haryana'),
    ('Himachal Pradesh', 'Himachal Pradesh'), ('Jharkhand', 'Jharkhand'),
    ('Karnataka', 'Karnataka'), ('Kerala', 'Kerala'), ('Madhya Pradesh', 'Madhya Pradesh'),
    ('Maharashtra', 'Maharashtra'), ('Manipur', 'Manipur'), ('Meghalaya', 'Meghalaya'),
    ('Mizoram', 'Mizoram'), ('Nagaland', 'Nagaland'), ('Odisha', 'Odisha'),
    ('Punjab', 'Punjab'), ('Rajasthan', 'Rajasthan'), ('Sikkim', 'Sikkim'),
    ('Tamil Nadu', 'Tamil Nadu'), ('Telangana', 'Telangana'), ('Tripura', 'Tripura'),
    ('Uttar Pradesh', 'Uttar Pradesh'), ('Uttarakhand', 'Uttarakhand'),
    ('West Bengal', 'West Bengal'), ('Delhi', 'Delhi'),
]

SKILL_CATEGORIES = [
    ('construction', 'Construction & Building'),
    ('agriculture', 'Agriculture & Farming'),
    ('domestic', 'Domestic Work'),
    ('plumbing', 'Plumbing'),
    ('electrical', 'Electrical Work'),
    ('carpentry', 'Carpentry'),
    ('painting', 'Painting'),
    ('driving', 'Driving'),
    ('loading', 'Loading & Unloading'),
    ('cleaning', 'Cleaning'),
    ('gardening', 'Gardening'),
    ('cooking', 'Cooking'),
    ('tailoring', 'Tailoring'),
    ('masonry', 'Masonry'),
    ('welding', 'Welding'),
    ('other', 'Other'),
]


class WorkerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='worker_profile')
    full_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    photo = models.ImageField(upload_to='workers/photos/', blank=True, null=True)
    aadhar_number = models.CharField(max_length=12, unique=True)
    aadhar_card_image = models.ImageField(upload_to='workers/aadhar/', blank=True, null=True)

    # Location
    village_town = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=50, choices=STATES_CHOICES)
    pincode = models.CharField(max_length=6)
    full_address = models.TextField()

    # Skills
    primary_skill = models.CharField(max_length=50, choices=SKILL_CATEGORIES)
    secondary_skills = models.CharField(max_length=200, blank=True, help_text='Comma-separated')
    years_of_experience = models.PositiveIntegerField(default=0)
    brief_intro = models.TextField(help_text='Tell about your work experience')

    # Availability
    is_available = models.BooleanField(default=True)

    # Ratings
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_ratings = models.PositiveIntegerField(default=0)
    rating_score = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                        help_text='Blockchain-style score for verification accuracy')

    # Verification
    verification_status = models.CharField(max_length=10, choices=VERIFICATION_STATUS, default='pending')
    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.user.email})"

    def update_rating(self):
        from jobs.models import Review
        reviews = Review.objects.filter(worker=self, is_approved=True)
        if reviews.exists():
            total = sum(r.rating for r in reviews)
            self.average_rating = round(total / reviews.count(), 2)
            self.total_ratings = reviews.count()
            self.save(update_fields=['average_rating', 'total_ratings'])


class WorkerReference(models.Model):
    """People who can vouch for the worker"""
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='references')
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    relation = models.CharField(max_length=50, help_text='e.g., Former employer, Neighbour')
    village_town = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} - Reference for {self.worker.full_name}"


class WorkerPortfolio(models.Model):
    """Images of worker's past work"""
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='portfolio')
    image = models.ImageField(upload_to='workers/portfolio/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Portfolio image by {self.worker.full_name}"


class WorkerVerification(models.Model):
    """
    Blockchain-like verification: 3 existing verified workers verify a new worker.
    If 2 agree and 1 disagrees → the disagreer's rating_score is penalized.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    new_worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='verifications_received')
    verifier = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='verifications_given')
    decision = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    comments = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('new_worker', 'verifier')

    def __str__(self):
        return f"{self.verifier.full_name} → {self.new_worker.full_name}: {self.decision}"
