from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import random
import string


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'admin')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPES = (
        ('worker', 'Informal Worker'),
        ('hirer', 'Job Provider'),
        ('admin', 'Admin'),
    )

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPES)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def is_worker(self):
        return self.user_type == 'worker'

    @property
    def is_hirer(self):
        return self.user_type == 'hirer'


class OTPVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    purpose = models.CharField(max_length=20, default='email_verify')

    def is_expired(self):
        from django.conf import settings
        expiry = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)
        return timezone.now() > self.created_at + timezone.timedelta(minutes=expiry)

    @staticmethod
    def generate_otp():
        return ''.join(random.choices(string.digits, k=6))

    def __str__(self):
        return f"OTP for {self.user.email}"
