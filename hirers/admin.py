from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import HirerProfile


@admin.register(HirerProfile)
class HirerProfileAdmin(ModelAdmin):
    list_display = ['full_name', 'company_name', 'district', 'state', 'user']
    list_filter = ['state']
    search_fields = ['full_name', 'company_name', 'district']