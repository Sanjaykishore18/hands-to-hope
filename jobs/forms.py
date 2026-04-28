from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.IntegerField(
        min_value=1, max_value=5,
        widget=forms.HiddenInput(attrs={'id': 'rating-value'})
    )

    class Meta:
        model = Review
        fields = ['rating', 'review_text']
        widgets = {
            'review_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe the quality of work, punctuality, behavior, and overall experience...'
            }),
        }
        labels = {
            'review_text': 'Your Review',
        }

    def clean_review_text(self):
        text = self.cleaned_data.get('review_text', '')
        if len(text.strip()) < 30:
            raise forms.ValidationError('Please write a detailed review (at least 30 characters).')
        return text
