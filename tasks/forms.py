import os
from django import forms
from django.conf import settings
from django.db.models import Q
from .models import Task, Submission
from academics.models import Subject, ClassRoom


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'class_assigned', 'subject',
            'task_type', 'difficulty', 'importance', 'estimated_hours',
            'max_marks', 'due_date', 'attachment',
        ]
        labels = {
            'class_assigned': 'Assign to Class',
            'subject': 'Subject',
        }
        help_texts = {
            'class_assigned': 'Task will be assigned to all students in this class.',
        }
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        self.teacher = teacher
        super().__init__(*args, **kwargs)

        self.fields['class_assigned'].required = True
        self.fields['subject'].required = True

        classes_qs = ClassRoom.objects.all().prefetch_related('subjects')
        if teacher is not None:
            teacher_classes = classes_qs.filter(class_teacher=teacher)
            self.fields['class_assigned'].queryset = teacher_classes if teacher_classes.exists() else classes_qs
            teacher_subjects = Subject.objects.filter(
                Q(teachers=teacher) | Q(classes__in=self.fields['class_assigned'].queryset)
            ).distinct()
            self.fields['subject'].queryset = teacher_subjects if teacher_subjects.exists() else Subject.objects.all()
        else:
            self.fields['class_assigned'].queryset = classes_qs
            self.fields['subject'].queryset = Subject.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        class_assigned = cleaned_data.get('class_assigned')
        subject = cleaned_data.get('subject')

        if not class_assigned:
            self.add_error('class_assigned', 'Please select a class for this task.')
            return cleaned_data

        class_subjects = class_assigned.subjects.all()
        if not subject and class_subjects.exists():
            if class_subjects.count() == 1:
                cleaned_data['subject'] = class_subjects.first()
                self.errors.pop('subject', None)
            else:
                self.add_error('subject', 'Please select one of the subjects defined for this class.')
        elif subject and class_subjects.exists() and subject not in class_subjects:
            self.add_error('subject', f'"{subject.name}" is not assigned to {class_assigned.name}. Please select a subject taught in this class.')

        return cleaned_data

    def save(self, commit=True):
        task = super().save(commit=False)
        task.student = None  # Tasks are assigned to the whole class
        if commit:
            task.save()
        return task


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['text_answer', 'file', 'image']
        widgets = {'text_answer': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Write your answer here...'})}

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if f:
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
                raise forms.ValidationError('Unsupported file type. Allowed: PDF, DOC, DOCX, PPT, PPTX, JPG, PNG.')
            if f.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                raise forms.ValidationError(f'File too large. Max size is {settings.MAX_UPLOAD_SIZE_MB} MB.')
        return f

    def clean_image(self):
        img = self.cleaned_data.get('image')
        if img:
            ext = os.path.splitext(img.name)[1].lower()
            if ext not in ('.jpg', '.jpeg', '.png'):
                raise forms.ValidationError('Images must be JPG or PNG.')
        return img


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['marks_obtained', 'feedback', 'is_resubmission_allowed']
        widgets = {'feedback': forms.Textarea(attrs={'rows': 4})}
