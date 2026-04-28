from django import forms
from .models import WorkerProfile, WorkerReference, WorkerPortfolio


class WorkerProfileForm(forms.ModelForm):
    class Meta:
        model = WorkerProfile
        fields = [
            'full_name', 'date_of_birth', 'gender', 'photo',
            'aadhar_number', 'aadhar_card_image',
            'village_town', 'district', 'state', 'pincode', 'full_address',
            'primary_skill', 'secondary_skills', 'years_of_experience', 'brief_intro',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name as per Aadhar'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'aadhar_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12-digit Aadhar Number', 'maxlength': '12'}),
            'aadhar_card_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'village_town': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Village / Town'}),
            'district': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'District'}),
            'state': forms.Select(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode', 'maxlength': '6'}),
            'full_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full Address'}),
            'primary_skill': forms.Select(attrs={'class': 'form-control'}),
            'secondary_skills': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Painting, Cleaning'}),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'brief_intro': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your experience and what kind of work you do...'}),
        }

    def clean_aadhar_number(self):
        aadhar = self.cleaned_data.get('aadhar_number', '')
        if not aadhar.isdigit() or len(aadhar) != 12:
            raise forms.ValidationError('Aadhar number must be exactly 12 digits')
        return aadhar

    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode', '')
        if not pincode.isdigit() or len(pincode) != 6:
            raise forms.ValidationError('Pincode must be exactly 6 digits')
        return pincode


class WorkerReferenceForm(forms.ModelForm):
    class Meta:
        model = WorkerReference
        fields = ['name', 'phone', 'relation', 'village_town']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reference Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'relation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Former Employer'}),
            'village_town': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Village/Town'}),
        }


WorkerReferenceFormSet = forms.inlineformset_factory(
    WorkerProfile,
    WorkerReference,
    form=WorkerReferenceForm,
    extra=2,
    min_num=1,
    validate_min=True,
    can_delete=True
)


class WorkerPortfolioForm(forms.ModelForm):
    class Meta:
        model = WorkerPortfolio
        fields = ['image', 'caption']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Caption for this image'}),
        }


class AvailabilityForm(forms.Form):
    is_available = forms.BooleanField(required=False, label='I am available for work')
