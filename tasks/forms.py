# pyrefly: ignore [missing-import]
from django import forms
# pyrefly: ignore [missing-import]
from django.db import models
from .models import Task
from accounts.models import StudentProfile


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
        from academics.models import Subject, ClassRoom

        self.fields['class_assigned'].required = True
        self.fields['subject'].required = True

        if teacher is not None:
            teacher_classes = ClassRoom.objects.filter(class_teacher=teacher).prefetch_related('subjects')
            self.fields['class_assigned'].queryset = teacher_classes if teacher_classes.exists() else ClassRoom.objects.all().prefetch_related('subjects')

            teacher_subjects = Subject.objects.filter(
                models.Q(teachers=teacher) | models.Q(classes__in=self.fields['class_assigned'].queryset)
            ).distinct()
            self.fields['subject'].queryset = teacher_subjects if teacher_subjects.exists() else Subject.objects.all()
        else:
            self.fields['class_assigned'].queryset = ClassRoom.objects.all().prefetch_related('subjects')
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
                if 'subject' in self.errors:
                    del self.errors['subject']
            else:
                self.add_error('subject', 'Please select one of the subjects defined for this class.')
        elif subject and class_subjects.exists():
            if subject not in class_subjects:
                self.add_error('subject', f'"{subject.name}" is not assigned to {class_assigned.name}. Please select a subject taught in this class.')

        return cleaned_data

    def save(self, commit=True):
        task = super().save(commit=False)
        task.student = None  # Tasks are assigned to the whole class
        if commit:
            task.save()
        return task


