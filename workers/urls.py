from django.urls import path
from . import views

urlpatterns = [
    path('profile/setup/', views.profile_setup, name='worker_profile_setup'),
    path('dashboard/', views.worker_dashboard, name='worker_dashboard'),
    path('portfolio/upload/', views.upload_portfolio, name='upload_portfolio'),
    path('portfolio/delete/<int:pk>/', views.delete_portfolio, name='delete_portfolio'),
    path('offer/<int:offer_id>/respond/', views.respond_offer, name='respond_offer'),
    path('verify/<int:verification_id>/', views.verify_worker, name='verify_worker'),
    path('availability/toggle/', views.toggle_availability, name='toggle_availability'),
    path('profile/edit/', views.edit_profile, name='edit_worker_profile'),
    path('profile/<int:worker_id>/', views.public_worker_profile, name='public_worker_profile'),
]
