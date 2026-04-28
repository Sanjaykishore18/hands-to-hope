"""
ML Models Predictor
===================
Provides two main functions for the HandsToHope project:

1. compute_trust_score(worker_features: dict) -> float
   Uses trust_score_rf.pkl (RandomForestRegressor, 24 features)
   Returns a trust score (typically 0–100).

2. is_fake_review(review_features: dict) -> bool
   Uses fake_review_rf.pkl (RandomForestClassifier, 14 features)
   Returns True if the review is likely fake, False if genuine.
"""

import os
import joblib
import numpy as np

MODELS_DIR = os.path.join(os.path.dirname(__file__), 'saved_models')

# ── Lazy-loaded singletons ────────────────────────────────────────────────────
_trust_model = None
_fake_model = None


def _get_trust_model():
    global _trust_model
    if _trust_model is None:
        _trust_model = joblib.load(os.path.join(MODELS_DIR, 'trust_score_rf.pkl'))
    return _trust_model


def _get_fake_model():
    global _fake_model
    if _fake_model is None:
        _fake_model = joblib.load(os.path.join(MODELS_DIR, 'fake_review_rf.pkl'))
    return _fake_model


# ── Trust Score Model (Regressor) ─────────────────────────────────────────────
# Feature order expected by trust_score_rf.pkl:
TRUST_FEATURES = [
    'id_verified', 'phone_verified', 'profile_photo', 'profile_completeness',
    'expert_score_weighted', 'certifications_count', 'experience_years',
    'skill_match_score', 'job_completion_rate', 'on_time_rate',
    'repeat_hire_rate', 'photo_proof_rate', 'customer_confirm_rate',
    'cancellation_rate', 'clean_avg_rating', 'clean_sentiment_avg',
    'review_consistency', 'fake_review_count', 'total_reviews',
    'rating_sentiment_gap', 'account_age_days', 'response_rate',
    'dispute_rate', 'trend_score',
]


def compute_trust_score(features: dict) -> float:
    """
    Predict the trust score for a worker.

    Args:
        features (dict): A dict with any subset of TRUST_FEATURES.
                         Missing keys are filled with safe defaults (0).

    Returns:
        float: Trust score (clamped to 0–100).
    """
    model = _get_trust_model()
    row = [float(features.get(f, 0)) for f in TRUST_FEATURES]
    score = model.predict(np.array(row).reshape(1, -1))[0]
    return round(float(np.clip(score, 0, 100)), 2)


def build_trust_features_from_worker(profile) -> dict:
    """
    Build a trust-score feature dict from a WorkerProfile instance.
    Computes what we can from the database; the rest defaults to 0.
    """
    from django.utils import timezone
    from jobs.models import Review, JobOffer

    reviews = Review.objects.filter(worker=profile, is_approved=True)
    total_reviews = reviews.count()
    fake_reviews = reviews.filter(is_fake=True).count()
    clean_reviews = reviews.filter(is_fake=False)

    offers = JobOffer.objects.filter(worker=profile)
    completed = offers.filter(status='completed').count()
    total_offers = offers.count()

    clean_avg_rating = list(clean_reviews.values_list('rating', flat=True))
    clean_avg = (sum(clean_avg_rating) / len(clean_avg_rating)) if clean_avg_rating else 0

    account_age = (timezone.now() - profile.created_at).days if profile.created_at else 0

    return {
        'id_verified':           1 if profile.verification_status == 'verified' else 0,
        'phone_verified':        1,  # Aadhar-verified workers are phone-verified
        'profile_photo':         1 if profile.photo else 0,
        'profile_completeness':  _profile_completeness(profile),
        'experience_years':      profile.years_of_experience,
        'job_completion_rate':   (completed / total_offers) if total_offers > 0 else 0,
        'clean_avg_rating':      clean_avg,
        'fake_review_count':     fake_reviews,
        'total_reviews':         total_reviews,
        'account_age_days':      account_age,
        # defaults — enrich later with real telemetry
        'expert_score_weighted': float(profile.rating_score),
        'certifications_count':  0,
        'skill_match_score':     0,
        'on_time_rate':          0,
        'repeat_hire_rate':      0,
        'photo_proof_rate':      0,
        'customer_confirm_rate': 0,
        'cancellation_rate':     0,
        'clean_sentiment_avg':   0,
        'review_consistency':    0,
        'rating_sentiment_gap':  0,
        'response_rate':         0,
        'dispute_rate':          0,
        'trend_score':           0,
    }


def _profile_completeness(profile) -> float:
    """Returns a 0–1 score based on how many profile fields are filled."""
    fields = [
        bool(profile.photo),
        bool(profile.date_of_birth),
        bool(profile.brief_intro),
        bool(profile.secondary_skills),
        bool(profile.aadhar_card_image),
    ]
    return round(sum(fields) / len(fields), 2)


# ── Fake Review Model (Classifier) ────────────────────────────────────────────
# Feature order expected by fake_review_rf.pkl:
FAKE_REVIEW_FEATURES = [
    'account_age_days', 'total_reviews_by_user', 'rating_variance',
    'avg_time_between_reviews', 'spike_flag', 'review_length', 'rating',
    'sentiment_score', 'sentiment_extreme', 'rating_sentiment_gap',
    'job_confirmed', 'photo_proof', 'skill_match', 'mismatch',
]


def is_fake_review(features: dict) -> bool:
    """
    Predict whether a review is fake.

    Args:
        features (dict): A dict with any subset of FAKE_REVIEW_FEATURES.
                         Missing keys are filled with 0.

    Returns:
        bool: True = likely fake, False = likely genuine.
    """
    model = _get_fake_model()
    row = [float(features.get(f, 0)) for f in FAKE_REVIEW_FEATURES]
    prediction = model.predict(np.array(row).reshape(1, -1))[0]
    return bool(prediction == 1)


def build_fake_review_features(review, hirer_profile) -> dict:
    """
    Build a fake-review feature dict from a Review + HirerProfile instance.
    """
    from django.utils import timezone
    from jobs.models import Review as ReviewModel

    # Hirer's account age
    hirer_account_age = (
        (timezone.now() - hirer_profile.created_at).days
        if hasattr(hirer_profile, 'created_at') and hirer_profile.created_at
        else 0
    )

    # How many reviews has this hirer written?
    hirer_reviews = ReviewModel.objects.filter(hirer=hirer_profile)
    total_by_user = hirer_reviews.count()

    # Rating variance across all their reviews
    ratings = list(hirer_reviews.values_list('rating', flat=True))
    rating_variance = float(np.var(ratings)) if len(ratings) > 1 else 0.0

    review_length = len(review.review_text or '')
    rating = review.rating

    # Simple sentiment proxy: length > 30 chars = not extreme
    sentiment_extreme = 1 if rating in [1, 5] else 0
    sentiment_score = (rating - 3) / 2  # normalise -1 to 1

    # job_confirmed: was the job marked completed?
    job_confirmed = 1 if review.offer.status == 'completed' else 0

    # photo_proof: did the worker have portfolio photos?
    from workers.models import WorkerPortfolio
    photo_proof = 1 if WorkerPortfolio.objects.filter(worker=review.worker).exists() else 0

    return {
        'account_age_days':         hirer_account_age,
        'total_reviews_by_user':    total_by_user,
        'rating_variance':          rating_variance,
        'avg_time_between_reviews': 0,   # enrich later
        'spike_flag':               0,   # enrich later
        'review_length':            review_length,
        'rating':                   rating,
        'sentiment_score':          sentiment_score,
        'sentiment_extreme':        sentiment_extreme,
        'rating_sentiment_gap':     0,   # enrich later
        'job_confirmed':            job_confirmed,
        'photo_proof':              photo_proof,
        'skill_match':              1,   # offer was made → skill matched
        'mismatch':                 0,
    }


def build_fake_verification_features(verification, verifier_rating: int, comments: str) -> dict:
    """
    Build fake-review feature dict for a peer WorkerVerification submission.
    Reuses the same fake_review_rf.pkl model by mapping verification data
    to the same 14-feature vector.

    Args:
        verification: WorkerVerification instance (not yet saved — used for verifier FK).
        verifier_rating (int): 1-5 score given by the verifier.
        comments (str): The verifier's written experience with the new worker.
    """
    from django.utils import timezone
    from workers.models import WorkerVerification, WorkerPortfolio

    verifier = verification.verifier

    # Verifier account age
    verifier_age = (timezone.now() - verifier.created_at).days if verifier.created_at else 0

    # How many verifications has this verifier submitted so far?
    past_verifications = WorkerVerification.objects.filter(
        verifier=verifier
    ).exclude(decision='pending')
    total_by_user = past_verifications.count()

    # Rating variance across their past verifications
    past_ratings = list(
        past_verifications.exclude(verifier_rating__isnull=True)
        .values_list('verifier_rating', flat=True)
    )
    rating_variance = float(np.var(past_ratings)) if len(past_ratings) > 1 else 0.0

    comment_length  = len(comments)
    sentiment_score = (verifier_rating - 3) / 2   # normalise to [-1, 1]
    sentiment_extreme = 1 if verifier_rating in [1, 5] else 0

    # photo_proof: verifier has portfolio photos (shows they're an active real worker)
    photo_proof = 1 if WorkerPortfolio.objects.filter(worker=verifier).exists() else 0

    # skill_match: both in same district → likely genuinely know each other
    skill_match = 1 if verifier.district == verification.new_worker.district else 0

    return {
        'account_age_days':         verifier_age,
        'total_reviews_by_user':    total_by_user,
        'rating_variance':          rating_variance,
        'avg_time_between_reviews': 0,
        'spike_flag':               0,
        'review_length':            comment_length,
        'rating':                   verifier_rating,
        'sentiment_score':          sentiment_score,
        'sentiment_extreme':        sentiment_extreme,
        'rating_sentiment_gap':     0,
        'job_confirmed':            0,   # peer verification, not a job
        'photo_proof':              photo_proof,
        'skill_match':              skill_match,
        'mismatch':                 0,
    }
