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
    """Randomly assign 2 verified workers from the same district to verify the newcomer.
    Falls back to state level if fewer than 2 are available in the district.
    """
    import random

    # Try district first
    candidates = list(
        WorkerProfile.objects.filter(
            verification_status='verified',
            state=new_worker.state,
            district=new_worker.district,
        ).exclude(user=new_worker.user)
    )

    if len(candidates) < 2:
        # Expand to state level
        candidates = list(
            WorkerProfile.objects.filter(
                verification_status='verified',
                state=new_worker.state,
            ).exclude(user=new_worker.user)
        )

    # Pick 2 at random
    chosen = random.sample(candidates, min(2, len(candidates)))
    for verifier in chosen:
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

    # ML: compute trust score for this worker
    trust_score    = None
    trust_label    = 'Unknown'
    trust_color    = 'secondary'
    trust_features = {}
    try:
        from ml_models.predictor import compute_trust_score, build_trust_features_from_worker
        trust_features = build_trust_features_from_worker(profile)
        trust_score    = compute_trust_score(trust_features)
        if trust_score >= 75:
            trust_label, trust_color = 'High Trust', 'success'
        elif trust_score >= 50:
            trust_label, trust_color = 'Moderate Trust', 'warning'
        else:
            trust_label, trust_color = 'Low Trust', 'danger'
    except Exception:
        pass

    context = {
        'profile': profile,
        'offers': offers,
        'portfolio': portfolio,
        'reviews': reviews,
        'pending_to_verify': pending_to_verify,
        'accepted_offers': offers.filter(status='accepted'),
        'pending_offers': offers.filter(status='pending'),
        'trust_score':    trust_score,
        'trust_label':    trust_label,
        'trust_color':    trust_color,
        'trust_features': trust_features,
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
    """A verified worker views a new worker's profile and submits their peer verification."""
    profile = get_object_or_404(WorkerProfile, user=request.user)
    verification = get_object_or_404(
        WorkerVerification, id=verification_id, verifier=profile, decision='pending'
    )
    new_worker = verification.new_worker

    if request.method == 'POST':
        decision  = request.POST.get('decision')
        comments  = request.POST.get('comments', '').strip()
        rating_raw = request.POST.get('verifier_rating')

        if decision not in ['approved', 'rejected']:
            messages.error(request, 'Please select Approve or Reject.')
            return redirect('verify_worker', verification_id=verification_id)

        try:
            verifier_rating = int(rating_raw)
            if not (1 <= verifier_rating <= 5):
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, 'Please give a rating between 1 and 5.')
            return redirect('verify_worker', verification_id=verification_id)

        verification.decision       = decision
        verification.comments       = comments
        verification.verifier_rating = verifier_rating
        verification.submitted_at   = timezone.now()

        # ── ML: Detect fake verification review ─────────────────────────────────────────
        try:
            from ml_models.predictor import is_fake_review, build_fake_verification_features
            features = build_fake_verification_features(verification, verifier_rating, comments)
            fake = is_fake_review(features)
            verification.is_fake_review = fake
            if fake:
                # Immediate penalty for submitting a fake-looking verification
                profile.rating_score = max(0, round(float(profile.rating_score) - 0.5, 2))
                profile.save(update_fields=['rating_score'])
                messages.warning(
                    request,
                    '⚠️ Our AI has flagged your review as potentially fake. '
                    'Your rating score has been reduced.'
                )
        except Exception:
            pass  # Never break verification flow due to ML error

        verification.save()
        _process_verification_result(new_worker)

        if not verification.is_fake_review:
            messages.success(request, 'Your verification has been submitted. Thank you!')
        return redirect('worker_dashboard')

    # GET — show the new worker’s profile + verification form
    references = new_worker.references.all()
    portfolio  = new_worker.portfolio.all()
    return render(request, 'workers/verify_worker.html', {
        'verification': verification,
        'new_worker':   new_worker,
        'references':   references,
        'portfolio':    portfolio,
    })


def _process_verification_result(new_worker):
    """Process 2-verifier peer consensus.
    - Both approve  → verified; each earns +0.25 (if not fake)
    - Both reject   → rejected; each earns +0.25 (if not fake)
    - 1-1 tie       → stays pending; admin resolves
    - 0 assigned    → stays pending; admin resolves
    """
    verifications = WorkerVerification.objects.filter(new_worker=new_worker)
    total_assigned = verifications.count()
    completed = verifications.exclude(decision='pending')
    completed_count = completed.count()

    if total_assigned == 0 or completed_count < total_assigned:
        return  # Wait until all assigned verifiers have responded

    approved = completed.filter(decision='approved').count()
    rejected = completed.filter(decision='rejected').count()

    if approved == rejected:  # Tie (1-1 or 0-0)
        # Leave pending — admin will decide via admin panel
        return

    if approved > rejected:
        new_worker.verification_status = 'verified'
        new_worker.verified_at = timezone.now()
        new_worker.save()
        winning_decision = 'approved'
    else:
        new_worker.verification_status = 'rejected'
        new_worker.save()
        winning_decision = 'rejected'

    # Reward verifiers on the winning side (skip fake reviewers)
    for v in completed.filter(decision=winning_decision, is_fake_review=False):
        v.verifier.rating_score = round(float(v.verifier.rating_score) + 0.25, 2)
        v.verifier.save(update_fields=['rating_score'])

    # Penalise verifiers on the losing side
    for v in completed.exclude(decision=winning_decision):
        v.verifier.rating_score = max(0, round(float(v.verifier.rating_score) - 0.25, 2))
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
    """Public profile visible to hirers — with ML trust score & fake review flags."""
    profile = get_object_or_404(WorkerProfile, id=worker_id, verification_status='verified')
    reviews = Review.objects.filter(worker=profile, is_approved=True).order_by('-created_at')
    portfolio = WorkerPortfolio.objects.filter(worker=profile)

    # ── ML: Compute trust score ───────────────────────────────────────────────
    trust_score = None
    trust_label = 'Unknown'
    trust_color = 'secondary'
    try:
        from ml_models.predictor import compute_trust_score, build_trust_features_from_worker
        features = build_trust_features_from_worker(profile)
        trust_score = compute_trust_score(features)
        if trust_score >= 75:
            trust_label, trust_color = 'High Trust', 'success'
        elif trust_score >= 50:
            trust_label, trust_color = 'Moderate Trust', 'warning'
        else:
            trust_label, trust_color = 'Low Trust', 'danger'
    except Exception:
        pass  # Never break the page if ML fails

    real_reviews = reviews.filter(is_fake=False)
    fake_review_count = reviews.filter(is_fake=True).count()

    return render(request, 'workers/public_profile.html', {
        'profile': profile,
        'reviews': real_reviews,
        'fake_review_count': fake_review_count,
        'portfolio': portfolio,
        'trust_score': trust_score,
        'trust_label': trust_label,
        'trust_color': trust_color,
    })
