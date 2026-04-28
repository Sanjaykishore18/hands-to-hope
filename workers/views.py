from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Avg

from .models import WorkerProfile, WorkerReference, WorkerPortfolio, WorkerVerification
from .forms import WorkerProfileForm, WorkerReferenceFormSet, WorkerPortfolioForm
from jobs.models import JobOffer, Review


def worker_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.user_type != 'worker':
            messages.error(request, 'Access denied.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def profile_setup(request):
    """Step 1: Profile + References"""
    if request.user.user_type != 'worker':
        return redirect('home')

    try:
        profile = request.user.worker_profile
        if profile.verification_status != 'pending' or WorkerReference.objects.filter(worker=profile).exists():
            return redirect('worker_dashboard')
    except WorkerProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        form = WorkerProfileForm(request.POST, request.FILES, instance=profile)
        formset = WorkerReferenceFormSet(request.POST, instance=profile)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                worker_profile = form.save(commit=False)
                worker_profile.user = request.user
                worker_profile.save()
                formset.instance = worker_profile
                formset.save()

            # Assign verifiers
            _assign_verifiers(worker_profile)
            messages.success(request, 'Profile submitted! Awaiting verification from 3 workers in your area.')
            return redirect('worker_dashboard')
    else:
        form = WorkerProfileForm(instance=profile)
        formset = WorkerReferenceFormSet(instance=profile)

    return render(request, 'workers/profile_setup.html', {'form': form, 'formset': formset})


def _assign_verifiers(new_worker):
    """Auto-assign 3 verified workers from same area with highest ratings"""
    potential_verifiers = WorkerProfile.objects.filter(
        verification_status='verified',
        state=new_worker.state,
        district=new_worker.district,
    ).exclude(user=new_worker.user).order_by('-average_rating', '-rating_score')[:3]

    if potential_verifiers.count() < 3:
        # Expand to state level if not enough in district
        potential_verifiers = WorkerProfile.objects.filter(
            verification_status='verified',
            state=new_worker.state,
        ).exclude(user=new_worker.user).order_by('-average_rating', '-rating_score')[:3]

    for verifier in potential_verifiers:
        WorkerVerification.objects.get_or_create(
            new_worker=new_worker,
            verifier=verifier
        )


@worker_required
def worker_dashboard(request):
    try:
        profile = request.user.worker_profile
    except WorkerProfile.DoesNotExist:
        return redirect('worker_profile_setup')

    offers = JobOffer.objects.filter(worker=profile).order_by('-created_at')
    portfolio = WorkerPortfolio.objects.filter(worker=profile)
    reviews = Review.objects.filter(worker=profile, is_approved=True).order_by('-created_at')

    # Pending verifications to do
    pending_to_verify = WorkerVerification.objects.filter(
        verifier=profile,
        decision='pending'
    ).select_related('new_worker')

    context = {
        'profile': profile,
        'offers': offers,
        'portfolio': portfolio,
        'reviews': reviews,
        'pending_to_verify': pending_to_verify,
        'accepted_offers': offers.filter(status='accepted'),
        'pending_offers': offers.filter(status='pending'),
    }
    return render(request, 'workers/dashboard.html', context)


@worker_required
def upload_portfolio(request):
    profile = get_object_or_404(WorkerProfile, user=request.user)
    if request.method == 'POST':
        form = WorkerPortfolioForm(request.POST, request.FILES)
        if form.is_valid():
            portfolio = form.save(commit=False)
            portfolio.worker = profile
            portfolio.save()
            messages.success(request, 'Image uploaded successfully!')
            return redirect('worker_dashboard')
    else:
        form = WorkerPortfolioForm()
    return render(request, 'workers/upload_portfolio.html', {'form': form})


@worker_required
def delete_portfolio(request, pk):
    portfolio = get_object_or_404(WorkerPortfolio, pk=pk, worker__user=request.user)
    portfolio.delete()
    messages.success(request, 'Image deleted.')
    return redirect('worker_dashboard')


@worker_required
def respond_offer(request, offer_id):
    profile = get_object_or_404(WorkerProfile, user=request.user)
    offer = get_object_or_404(JobOffer, id=offer_id, worker=profile, status='pending')

    action = request.POST.get('action')
    if action == 'accept':
        offer.status = 'accepted'
        offer.save()
        # Mark worker as unavailable
        profile.is_available = False
        profile.save()
        messages.success(request, f'You accepted the job from {offer.hirer.company_name or offer.hirer.user.email}!')
    elif action == 'reject':
        offer.status = 'rejected'
        offer.save()
        messages.info(request, 'Job offer rejected.')

    return redirect('worker_dashboard')


@worker_required
def verify_worker(request, verification_id):
    """A verified worker submits their verification decision"""
    profile = get_object_or_404(WorkerProfile, user=request.user)
    verification = get_object_or_404(WorkerVerification, id=verification_id, verifier=profile, decision='pending')

    if request.method == 'POST':
        decision = request.POST.get('decision')
        comments = request.POST.get('comments', '')
        if decision in ['approved', 'rejected']:
            verification.decision = decision
            verification.comments = comments
            verification.submitted_at = timezone.now()
            verification.save()

            # Check if all 3 verifiers have responded
            _process_verification_result(verification.new_worker)
            messages.success(request, 'Your verification has been submitted.')

    return redirect('worker_dashboard')


def _process_verification_result(new_worker):
    """Process blockchain-style consensus verification.
    Works with 1, 2, or 3 verifiers — whoever was available in the area.
    Resolves as soon as ALL assigned verifiers have responded.
    """
    verifications = WorkerVerification.objects.filter(new_worker=new_worker)
    total_assigned = verifications.count()
    completed = verifications.exclude(decision='pending')
    completed_count = completed.count()

    # No verifiers assigned at all — admin must manually verify
    if total_assigned == 0:
        return

    # Wait until every assigned verifier has responded
    if completed_count < total_assigned:
        return

    # All have responded — apply majority rule
    approved = completed.filter(decision='approved').count()
    rejected = completed.filter(decision='rejected').count()

    if approved >= rejected:
        # Majority (or tie) approved → verified
        new_worker.verification_status = 'verified'
        new_worker.verified_at = timezone.now()
        new_worker.save()

        for v in completed.filter(decision='approved'):
            v.verifier.rating_score += 0.25
            v.verifier.save(update_fields=['rating_score'])
        for v in completed.filter(decision='rejected'):
            v.verifier.rating_score = max(0, v.verifier.rating_score - 0.5)
            v.verifier.save(update_fields=['rating_score'])
    else:
        # Majority rejected
        new_worker.verification_status = 'rejected'
        new_worker.save()

        for v in completed.filter(decision='rejected'):
            v.verifier.rating_score += 0.25
            v.verifier.save(update_fields=['rating_score'])
        for v in completed.filter(decision='approved'):
            v.verifier.rating_score = max(0, v.verifier.rating_score - 0.5)
            v.verifier.save(update_fields=['rating_score'])

@worker_required
def toggle_availability(request):
    profile = get_object_or_404(WorkerProfile, user=request.user)
    profile.is_available = not profile.is_available
    profile.save()
    status = 'available' if profile.is_available else 'unavailable'
    messages.success(request, f'You are now marked as {status}.')
    return redirect('worker_dashboard')


@worker_required
def edit_profile(request):
    profile = get_object_or_404(WorkerProfile, user=request.user)
    if request.method == 'POST':
        form = WorkerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated!')
            return redirect('worker_dashboard')
    else:
        form = WorkerProfileForm(instance=profile)
    return render(request, 'workers/edit_profile.html', {'form': form})


def public_worker_profile(request, worker_id):
    """Public profile visible to hirers"""
    profile = get_object_or_404(WorkerProfile, id=worker_id, verification_status='verified')
    reviews = Review.objects.filter(worker=profile, is_approved=True).order_by('-created_at')
    portfolio = WorkerPortfolio.objects.filter(worker=profile)
    return render(request, 'workers/public_profile.html', {
        'profile': profile,
        'reviews': reviews,
        'portfolio': portfolio
    })
