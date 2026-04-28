from django import forms
from .models import HirerProfile
from workers.models import STATES_CHOICES


class HirerProfileForm(forms.ModelForm):
    class Meta:
        model = HirerProfile
        fields = ['full_name', 'company_name', 'photo', 'village_town', 'district', 'state', 'pincode', 'full_address']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Full Name'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company / Farm Name (optional)'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'village_town': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Village / Town'}),
            'district': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'District'}),
            'state': forms.Select(attrs={'class': 'form-control'}, choices=STATES_CHOICES),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode', 'maxlength': '6'}),
            'full_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full Address'}),
        }


class WorkerSearchForm(forms.Form):
    skill = forms.ChoiceField(
        choices=[('', 'Any Skill')] + [
            ('construction', 'Construction'), ('agriculture', 'Agriculture'),
            ('domestic', 'Domestic Work'), ('plumbing', 'Plumbing'),
            ('electrical', 'Electrical'), ('carpentry', 'Carpentry'),
            ('painting', 'Painting'), ('driving', 'Driving'),
            ('loading', 'Loading & Unloading'), ('cleaning', 'Cleaning'),
            ('gardening', 'Gardening'), ('cooking', 'Cooking'),
            ('tailoring', 'Tailoring'), ('masonry', 'Masonry'),
            ('welding', 'Welding'), ('other', 'Other'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    work_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    work_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'})
    )
    duration_hours = forms.IntegerField(
        required=False, min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Hours of work', 'min': '1'})
    )
