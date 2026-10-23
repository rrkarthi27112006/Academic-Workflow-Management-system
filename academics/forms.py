# pyrefly: ignore [missing-import]
from django import forms
from .models import ClassRoom, Subject
from accounts.models import StudentProfile


class ClassRoomForm(forms.ModelForm):
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text='Select the subject(s) taught in this class (select all that apply if you handle multiple subjects).'
    )
    students = forms.ModelMultipleChoiceField(
        queryset=StudentProfile.objects.select_related('user').all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text='Select the students to include in this class.'
    )

    class Meta:
        model = ClassRoom
        fields = ['name', 'subjects', 'students']

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher is not None:
            teacher_subjects = Subject.objects.filter(teachers=teacher)
            if teacher_subjects.exists():
                self.fields['subjects'].queryset = teacher_subjects
            else:
                self.fields['subjects'].queryset = Subject.objects.all()
        else:
            self.fields['subjects'].queryset = Subject.objects.all()

        if self.instance.pk:
            self.fields['subjects'].initial = self.instance.subjects.all()

    def save(self, commit=True):
        classroom = super().save(commit=commit)
        if commit:
            if 'subjects' in self.cleaned_data:
                classroom.subjects.set(self.cleaned_data['subjects'])
        else:
            old_save_m2m = getattr(self, 'save_m2m', None)
            def save_m2m():
                if old_save_m2m:
                    old_save_m2m()
                if 'subjects' in self.cleaned_data:
                    classroom.subjects.set(self.cleaned_data['subjects'])
            self.save_m2m = save_m2m
        return classroom



class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'classes', 'teachers']
        widgets = {
            'classes': forms.CheckboxSelectMultiple,
            'teachers': forms.CheckboxSelectMultiple,
        }

