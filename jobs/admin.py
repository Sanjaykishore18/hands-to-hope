from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import JobOffer, Review, WageRate


@admin.register(WageRate)
class WageRateAdmin(ModelAdmin):
    list_display = ['skill', 'district', 'state', 'daily_rate', 'updated_at']
    list_filter = ['state', 'skill']
    search_fields = ['district', 'state', 'skill']
    list_editable = ['daily_rate']
    ordering = ['state', 'district', 'skill']


@admin.register(JobOffer)
class JobOfferAdmin(ModelAdmin):
    list_display = ['hirer', 'worker', 'work_date', 'status', 'offered_wage', 'created_at']
    list_filter = ['status', 'work_date']
    search_fields = ['hirer__full_name', 'worker__full_name']
    readonly_fields = ['created_at', 'completed_at']


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ['worker', 'hirer', 'rating', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_approved']
    search_fields = ['worker__full_name', 'hirer__full_name']
    list_editable = ['is_approved']
    readonly_fields = ['created_at']