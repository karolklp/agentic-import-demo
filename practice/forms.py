from django import forms
from .models import ImportJob, ImportFile


class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget for multiple file uploads"""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Custom field for multiple file uploads"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class ImportJobForm(forms.ModelForm):
    """Form for creating an import job with file uploads"""
    files = MultipleFileField(
        label='Upload Files',
        help_text='Select one or more files to import (CSV, JSON, or Excel)',
        required=True
    )

    class Meta:
        model = ImportJob
        fields = []  # We'll handle files separately

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Only assign user if authenticated (not AnonymousUser)
        if self.user and self.user.is_authenticated:
            instance.created_by = self.user
        instance.status = 'uploading'
        if commit:
            instance.save()
        return instance


class AnswerQuestionForm(forms.Form):
    """Form for answering import questions"""
    answer = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        label='Your Answer',
        required=True
    )
