from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import WorkerProfile, WorkerReference, WorkerPortfolio, WorkerVerification


class WorkerReferenceInline(admin.TabularInline):
    model = WorkerReference
    extra = 0


class WorkerPortfolioInline(admin.TabularInline):
    model = WorkerPortfolio
    extra = 0


class WorkerVerificationInline(admin.TabularInline):
    model = WorkerVerification
    fk_name = 'new_worker'
    extra = 0
    readonly_fields = ['verifier', 'decision', 'verifier_rating', 'is_fake_review', 'comments', 'submitted_at']


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'primary_skill', 'district', 'state',
        'verification_badge', 'verifier_progress',
        'average_rating', 'rating_score', 'is_available'
    ]
    list_filter = ['verification_status', 'state', 'primary_skill', 'is_available']
    search_fields = ['full_name', 'aadhar_number', 'district']
    readonly_fields = ['average_rating', 'total_ratings', 'rating_score', 'verified_at']
    inlines = [WorkerReferenceInline, WorkerPortfolioInline, WorkerVerificationInline]

    actions = ['verify_workers', 'reject_workers', 'force_reprocess_verification']

    def verification_badge(self, obj):
        colours = {
            'verified': '#2ecc71',
            'pending': '#f39c12',
            'rejected': '#e74c3c',
        }
        colour = colours.get(obj.verification_status, '#999')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            colour, obj.verification_status.upper()
        )
    verification_badge.short_description = 'Status'

    def verifier_progress(self, obj):
        total = WorkerVerification.objects.filter(new_worker=obj).count()
        done  = WorkerVerification.objects.filter(new_worker=obj).exclude(decision='pending').count()
        fake  = WorkerVerification.objects.filter(new_worker=obj, is_fake_review=True).count()
        if total == 0:
            return 'No verifiers assigned'
        colour = '#2ecc71' if done == total else '#f39c12'
        label  = f'{done}/{total} responded'
        if fake:
            label += f' · {fake} fake⚠️'
        return format_html('<span style="color:{};">{}</span>', colour, label)
    verifier_progress.short_description = 'Peer Verifiers'

    def verify_workers(self, request, queryset):
        for worker in queryset:
            worker.verification_status = 'verified'
            worker.verified_at = timezone.now()
            worker.save()
        self.message_user(request, f'{queryset.count()} worker(s) marked as Verified.')
    verify_workers.short_description = '✅ Mark selected as Verified (admin override)'

    def reject_workers(self, request, queryset):
        updated = queryset.update(verification_status='rejected')
        self.message_user(request, f'{updated} worker(s) marked as Rejected.')
    reject_workers.short_description = '❌ Mark selected as Rejected (admin override)'

    def force_reprocess_verification(self, request, queryset):
        from .views import _process_verification_result
        processed = 0
        for worker in queryset.filter(verification_status='pending'):
            _process_verification_result(worker)
            worker.refresh_from_db()
            if worker.verification_status != 'pending':
                processed += 1
        self.message_user(
            request,
            f'Re-processed {queryset.count()} worker(s). {processed} changed status.'
        )
    force_reprocess_verification.short_description = '🔄 Re-process verification (fix stuck pending)'


@admin.register(WorkerVerification)
class WorkerVerificationAdmin(admin.ModelAdmin):
    list_display = ['new_worker', 'verifier', 'decision', 'verifier_rating', 'is_fake_review', 'submitted_at']
    list_filter  = ['decision', 'is_fake_review']
    search_fields = ['new_worker__full_name', 'verifier__full_name']
    readonly_fields = ['is_fake_review']


@admin.register(WorkerPortfolio)
class WorkerPortfolioAdmin(admin.ModelAdmin):
    list_display = ['worker', 'caption', 'uploaded_at']