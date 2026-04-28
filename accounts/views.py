from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import User, OTPVerification
from .forms import WorkerSignupForm, HirerSignupForm, LoginForm, OTPForm


SKILL_CATEGORIES = [
    ('construction', 'Construction & Building'), ('agriculture', 'Agriculture & Farming'),
    ('domestic', 'Domestic Work'), ('plumbing', 'Plumbing'), ('electrical', 'Electrical Work'),
    ('carpentry', 'Carpentry'), ('painting', 'Painting'), ('driving', 'Driving'),
    ('loading', 'Loading & Unloading'), ('cleaning', 'Cleaning'), ('gardening', 'Gardening'),
    ('cooking', 'Cooking'), ('tailoring', 'Tailoring'), ('masonry', 'Masonry'),
    ('welding', 'Welding'), ('other', 'Other'),
]

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html', {'skills': SKILL_CATEGORIES})


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    user = request.user
    if user.user_type == 'worker':
        return redirect('worker_dashboard')
    elif user.user_type == 'hirer':
        return redirect('hirer_dashboard')
    else:
        return redirect('/admin/')


def worker_signup(request):
    if request.method == 'POST':
        form = WorkerSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            _send_otp(user, 'email_verify')
            request.session['verify_user_id'] = user.id
            messages.success(request, 'OTP sent to your email. Please verify.')
            return redirect('verify_email')
    else:
        form = WorkerSignupForm()
    return render(request, 'accounts/worker_signup.html', {'form': form})


def hirer_signup(request):
    if request.method == 'POST':
        form = HirerSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            _send_otp(user, 'email_verify')
            request.session['verify_user_id'] = user.id
            messages.success(request, 'OTP sent to your email. Please verify.')
            return redirect('verify_email')
    else:
        form = HirerSignupForm()
    return render(request, 'accounts/hirer_signup.html', {'form': form})


def verify_email(request):
    user_id = request.session.get('verify_user_id')
    if not user_id:
        return redirect('login')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('login')

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp']
            try:
                otp = OTPVerification.objects.filter(
                    user=user,
                    otp=otp_code,
                    is_used=False,
                    purpose='email_verify'
                ).latest('created_at')

                if otp.is_expired():
                    messages.error(request, 'OTP has expired. Please resend.')
                else:
                    otp.is_used = True
                    otp.save()
                    user.is_email_verified = True
                    user.save()
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    request.session.pop('verify_user_id', None)
                    messages.success(request, 'Email verified! Complete your profile.')
                    if user.user_type == 'worker':
                        return redirect('worker_profile_setup')
                    else:
                        return redirect('hirer_profile_setup')
            except OTPVerification.DoesNotExist:
                messages.error(request, 'Invalid OTP. Please try again.')
    else:
        form = OTPForm()

    return render(request, 'accounts/verify_email.html', {'form': form, 'email': user.email})


def resend_otp(request):
    user_id = request.session.get('verify_user_id')
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            _send_otp(user, 'email_verify')
            messages.success(request, 'New OTP sent to your email.')
        except User.DoesNotExist:
            pass
    return redirect('verify_email')


def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_email_verified:
                request.session['verify_user_id'] = user.id
                _send_otp(user, 'email_verify')
                messages.warning(request, 'Please verify your email first.')
                return redirect('verify_email')
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('home')


def _send_otp(user, purpose):
    # Invalidate old OTPs
    OTPVerification.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)

    otp_code = OTPVerification.generate_otp()
    OTPVerification.objects.create(user=user, otp=otp_code, purpose=purpose)

    try:
        send_mail(
            'HandsToHope - Email Verification OTP',
            f'Your OTP is: {otp_code}\nValid for 10 minutes.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,  # Change to False so you see errors
        )
    except Exception:
        pass  # In development, OTP is printed to console via console backend

    # Also print for development convenience
    print(f"[DEV] OTP for {user.email}: {otp_code}")
