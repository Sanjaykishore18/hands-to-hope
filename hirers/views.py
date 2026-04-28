from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import HirerProfile
from .forms import HirerProfileForm, WorkerSearchForm
from workers.models import WorkerProfile
from jobs.models import JobOffer, Review, WageRate
from jobs.forms import ReviewForm


def hirer_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.user_type != 'hirer':
            messages.error(request, 'Access denied.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def hirer_profile_setup(request):
    if request.user.user_type != 'hirer':
        return redirect('home')

    try:
        profile = request.user.hirer_profile
        return redirect('hirer_dashboard')
    except HirerProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        form = HirerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            hirer = form.save(commit=False)
            hirer.user = request.user
            hirer.save()
            messages.success(request, 'Profile created! You can now search for workers.')
            return redirect('hirer_dashboard')
    else:
        form = HirerProfileForm(instance=profile)

    return render(request, 'hirers/profile_setup.html', {'form': form})


@hirer_required
def hirer_dashboard(request):
    try:
        profile = request.user.hirer_profile
    except HirerProfile.DoesNotExist:
        return redirect('hirer_profile_setup')

    offers = JobOffer.objects.filter(hirer=profile).order_by('-created_at')
    completed_offers = offers.filter(status='completed')
    active_offers = offers.filter(status='accepted')
    pending_offers = offers.filter(status='pending')

    # Pending reviews to write
    to_review = completed_offers.filter(review__isnull=True)

    context = {
        'profile': profile,
        'offers': offers,
        'completed_offers': completed_offers,
        'active_offers': active_offers,
        'pending_offers': pending_offers,
        'to_review': to_review,
    }
    return render(request, 'hirers/dashboard.html', context)


@hirer_required
def search_workers(request):
    try:
        hirer = request.user.hirer_profile
    except HirerProfile.DoesNotExist:
        return redirect('hirer_profile_setup')

    form = WorkerSearchForm(request.GET or None)
    workers = WorkerProfile.objects.filter(
        verification_status='verified',
        is_available=True,
        district=hirer.district,
        state=hirer.state,
    ).order_by('-average_rating', '-rating_score')

    if form.is_valid():
        skill = form.cleaned_data.get('skill')
        if skill:
            workers = workers.filter(primary_skill=skill)

    wage_rates = {}
    trust_scores = {}
    for worker in workers:
        try:
            rate = WageRate.objects.get(state=worker.state, district=worker.district, skill=worker.primary_skill)
            wage_rates[worker.id] = rate.daily_rate
        except WageRate.DoesNotExist:
            try:
                rate = WageRate.objects.get(state=worker.state, district='', skill=worker.primary_skill)
                wage_rates[worker.id] = rate.daily_rate
            except WageRate.DoesNotExist:
                wage_rates[worker.id] = None

        # ML: compute trust score per worker
        try:
            from ml_models.predictor import compute_trust_score, build_trust_features_from_worker
            features = build_trust_features_from_worker(worker)
            score = compute_trust_score(features)
            if score >= 75:
                trust_scores[worker.id] = {'score': score, 'label': 'High Trust', 'color': 'success'}
            elif score >= 50:
                trust_scores[worker.id] = {'score': score, 'label': 'Moderate', 'color': 'warning'}
            else:
                trust_scores[worker.id] = {'score': score, 'label': 'Low Trust', 'color': 'danger'}
        except Exception:
            trust_scores[worker.id] = None

    context = {
        'form': form,
        'workers': workers,
        'wage_rates': wage_rates,
        'trust_scores': trust_scores,
        'search_date': request.GET.get('work_date'),
        'search_time': request.GET.get('work_time'),
        'duration': request.GET.get('duration_hours'),
        'today_date': timezone.now().date(),
    }
    return render(request, 'hirers/search_workers.html', context)


@hirer_required
def send_offer(request, worker_id):
    try:
        hirer = request.user.hirer_profile
    except HirerProfile.DoesNotExist:
        return redirect('hirer_profile_setup')

    worker = get_object_or_404(WorkerProfile, id=worker_id, verification_status='verified', is_available=True)

    if request.method == 'POST':
        work_date_str = request.POST.get('work_date')
        work_time_str = request.POST.get('work_time')
        duration = request.POST.get('duration_hours')
        description = request.POST.get('description', '')

        if not work_date_str:
            messages.error(request, 'Please select a work date.')
            return redirect('search_workers')

        from datetime import datetime, date, time as dtime
        try:
            work_date = datetime.strptime(work_date_str, '%Y-%m-%d').date()
            if work_date < date.today():
                messages.error(request, 'Work date cannot be in the past.')
                return redirect('search_workers')
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return redirect('search_workers')

        work_time = None
        if work_time_str:
            try:
                work_time = datetime.strptime(work_time_str, '%H:%M').time()
            except ValueError:
                pass

        # Check if offer already exists
        existing = JobOffer.objects.filter(
            hirer=hirer, worker=worker, work_date=work_date, status__in=['pending', 'accepted']
        ).exists()

        if existing:
            messages.warning(request, 'You already have a pending/active offer with this worker for that date.')
        else:
            # Get wage
            try:
                rate = WageRate.objects.get(state=worker.state, district=worker.district, skill=worker.primary_skill)
                offered_wage = rate.daily_rate
            except WageRate.DoesNotExist:
                offered_wage = None

            JobOffer.objects.create(
                hirer=hirer,
                worker=worker,
                work_date=work_date,
                work_time=work_time,
                duration_hours=int(duration) if duration else 8,
                description=description,
                offered_wage=offered_wage,
            )
            messages.success(request, f'Offer sent to {worker.full_name}! They will accept or reject it.')

    return redirect('hirer_dashboard')


@hirer_required
def mark_completed(request, offer_id):
    hirer = get_object_or_404(HirerProfile, user=request.user)
    offer = get_object_or_404(JobOffer, id=offer_id, hirer=hirer, status='accepted')
    offer.status = 'completed'
    offer.completed_at = timezone.now()
    offer.save()

    # Mark worker available again
    offer.worker.is_available = True
    offer.worker.save()

    messages.success(request, 'Job marked as completed. Please leave a review!')
    return redirect('write_review', offer_id=offer.id)


@hirer_required
def write_review(request, offer_id):
    hirer = get_object_or_404(HirerProfile, user=request.user)
    offer = get_object_or_404(JobOffer, id=offer_id, hirer=hirer, status='completed')

    if hasattr(offer, 'review'):
        messages.info(request, 'You have already reviewed this job.')
        return redirect('hirer_dashboard')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.offer = offer
            review.worker = offer.worker
            review.hirer = hirer
            review.save()

            # Update worker rating
            offer.worker.update_rating()
            messages.success(request, 'Review submitted! Thank you.')
            return redirect('hirer_dashboard')
    else:
        form = ReviewForm()

    return render(request, 'hirers/write_review.html', {'form': form, 'offer': offer, 'worker': offer.worker})


@hirer_required
def edit_profile(request):
    profile = get_object_or_404(HirerProfile, user=request.user)
    if request.method == 'POST':
        form = HirerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated!')
            return redirect('hirer_dashboard')
    else:
        form = HirerProfileForm(instance=profile)
    return render(request, 'hirers/edit_profile.html', {'form': form})
