from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('accounts/signup/worker/', views.worker_signup, name='worker_signup'),
    path('accounts/signup/hirer/', views.hirer_signup, name='hirer_signup'),
    path('accounts/verify-email/', views.verify_email, name='verify_email'),
    path('accounts/resend-otp/', views.resend_otp, name='resend_otp'),
    path('accounts/login/', views.user_login, name='login'),
    path('accounts/logout/', views.user_logout, name='logout'),
]
