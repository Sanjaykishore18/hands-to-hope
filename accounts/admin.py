from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from .models import User, OTPVerification


@admin.register(User)
class UserAdmin(ModelAdmin, BaseUserAdmin):
    list_display = ['email', 'user_type', 'is_email_verified', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_email_verified', 'is_active']
    search_fields = ['email', 'phone']
    ordering = ['-date_joined']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal', {'fields': ('phone', 'user_type')}),
        ('Status', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_email_verified')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone', 'user_type', 'password1', 'password2'),
        }),
    )


@admin.register(OTPVerification)
class OTPAdmin(ModelAdmin):
    list_display = ['user', 'otp', 'purpose', 'created_at', 'is_used']
    list_filter = ['purpose', 'is_used']