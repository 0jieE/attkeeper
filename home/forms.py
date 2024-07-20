from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field
import calendar
import datetime
from .models import Shift, Member, Account, Period, Attendance, Preference, Position, Branch
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm, PasswordChangeForm, UsernameField, PasswordResetForm, SetPasswordForm


class LoginForm(forms.Form):
  username = UsernameField(label=_("Your Username"), widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}))
  password = forms.CharField(
      label=_("Your Password"),
      strip=False,
      widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
  )

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = Account
        fields = ('username',)

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = Account
        fields = ('username', 'is_staff', 'is_admin', 'is_member')

class AccountUpdateForm(forms.ModelForm):
    old_password = forms.CharField(widget=forms.PasswordInput, required=True)
    new_password = forms.CharField(widget=forms.PasswordInput, required=True)
    new_password_confirmation = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = Account
        fields = ['username', 'old_password', 'new_password', 'new_password_confirmation']

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get("old_password")
        new_password = cleaned_data.get("new_password")
        new_password_confirmation = cleaned_data.get("new_password_confirmation")

        # Validate old password
        if not self.instance.check_password(old_password):
            self.add_error('old_password', 'Old password is incorrect.')

        # Validate new passwords match
        if new_password and new_password != new_password_confirmation:
            self.add_error('new_password_confirmation', 'New passwords do not match.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get("new_password")
        if new_password:
            user.set_password(new_password)
        if commit:
            user.save()
        return user


class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ['shift_name', 'hours', 'am_in', 'am_out', 'pm_in_start_time', 'pm_in', 'pm_out', 'period_type']
        widgets = {
            'shift_name': forms.TextInput(attrs={'class': 'form-control'}),
            'period_type': forms.Select(attrs={'class': 'form-control'}),
            'hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'am_in': forms.TimeInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM AM/PM'}),
            'am_out': forms.TimeInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM AM/PM'}),
            'pm_in_start_time': forms.TimeInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM AM/PM'}),
            'pm_in': forms.TimeInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM AM/PM'}),
            'pm_out': forms.TimeInput(attrs={'class': 'form-control', 'placeholder': 'HH:MM AM/PM'}),
        }

    def __init__(self, *args, **kwargs):
        super(ShiftForm, self).__init__(*args, **kwargs)

        # Format time input fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.TimeInput):
                field.widget.format = '%I:%M %p'
                field.input_formats = ['%I:%M %p']
                field.widget.attrs.update({'class': 'form-control', 'placeholder': 'HH:MM AM/PM'})

        # Hide fields initially if period_type is Single
        period_type = self.initial.get('period_type', self.instance.period_type)
        if period_type == Shift.SINGLE:
            self.fields['am_out'].widget.attrs.update({'style': 'display:none;'})
            self.fields['pm_in_start_time'].widget.attrs.update({'style': 'display:none;'})
            self.fields['pm_in'].widget.attrs.update({'style': 'display:none;'})



class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'biometric_id', 'last_name', 'first_name', 'middle_name', 
            'ext_name', 'address', 'contact_no', 'shift', 'position','branch',
        ]
        
        widgets = {
            'biometric_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'ext_name': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.Select(attrs={'class': 'form-control'}),
            'brancd': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'cols': 40}),
            'contact_no': forms.TextInput(attrs={'class': 'form-control'}),
            'shift': forms.Select(attrs={'class': 'form-control'}),
        }

class PeriodForm(forms.ModelForm):
    class Meta:
        model = Period
        fields = ['start_date', 'end_date', 'description']

# class AttendanceForm(forms.ModelForm):
#     class Meta:
#         model = Attendance
#         fields = ['member','period','days','in_am_time','out_am_time','in_pm_time','out_pm_time','in_ot_time','out_ot_time','total_reg_time','total_ot_time','total_all_time','total_under_over_time']


class UploadFileForm(forms.Form):
    file = forms.FileField(label='Select a file')

    def __init__(self, *args, **kwargs):
        super(UploadFileForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Upload'))

class PeriodSelectionForm(forms.Form):
    year = forms.ChoiceField(choices=[(r, r) for r in range(2014, datetime.date.today().year+1)], label="Year")
    month = forms.ChoiceField(choices=[(i, datetime.date(2008, i, 1).strftime('%B')) for i in range(1, 13)], label="Month")


class GenerateDTRForm(forms.Form):
    current_year = datetime.datetime.now().year
    years = [(year, year) for year in range(current_year - 10, current_year + 1)]
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]

    year = forms.ChoiceField(choices=years, required=True, label='Year')
    month = forms.ChoiceField(choices=months, required=True, label='Month')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = 'generate_dtr'
        self.helper.layout = Layout(
            Field('year'),
            Field('month'),
            Submit('submit', 'Generate', css_class='btn btn-primary')
        )

class PreferenceForm(forms.ModelForm):
    class Meta:
        model = Preference
        fields = ['logo', 'company_name', 'description']

class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['position_name']
        widgets = {
            'position_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter position name'}),
        }

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['branch_name', 'signatory']
        widgets = {
            'branch_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter branch name'}),
            'signatory': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter signatory name'}),
        }