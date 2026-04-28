from django.urls import path
from . import views

urlpatterns = [
    path('profile/setup/', views.hirer_profile_setup, name='hirer_profile_setup'),
    path('dashboard/', views.hirer_dashboard, name='hirer_dashboard'),
    path('search/', views.search_workers, name='search_workers'),
    path('offer/<int:worker_id>/', views.send_offer, name='send_offer'),
    path('job/<int:offer_id>/complete/', views.mark_completed, name='mark_completed'),
    path('job/<int:offer_id>/review/', views.write_review, name='write_review'),
    path('profile/edit/', views.edit_profile, name='edit_hirer_profile'),
]
