from django.db import models
from django.utils import timezone


TASK_TYPE_CHOICES = [
    ('homework', 'Homework'),
    ('project', 'Project'),
    ('worksheet', 'Worksheet'),
    ('reading', 'Reading'),
    ('class_activity', 'Class Activity'),
    ('quiz', 'Quiz'),
    ('revision', 'Revision Task'),
]

DIFFICULTY_CHOICES = [
    ('easy', 'Easy'),
    ('medium', 'Medium'),
    ('hard', 'Hard'),
]

IMPORTANCE_CHOICES = [
    ('normal', 'Normal'),
    ('important', 'Important'),
    ('critical', 'Critical'),
]

STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('in_progress', 'In Progress'),
    ('submitted', 'Submitted'),
    ('reviewed', 'Reviewed'),
    ('overdue', 'Overdue'),
]


def task_attachment_path(instance, filename):
    return f'task_attachments/{instance.pk or "new"}/{filename}'


def submission_file_path(instance, filename):
    return f'submissions/{instance.task_id}/{instance.student_id}/{filename}'


def submission_image_path(instance, filename):
    return f'submissions/{instance.task_id}/{instance.student_id}/images/{filename}'


class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    teacher = models.ForeignKey('accounts.TeacherProfile', on_delete=models.CASCADE, related_name='tasks')
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, related_name='tasks')

    class_assigned = models.ForeignKey(
        'academics.ClassRoom', on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks'
    )
    student = models.ForeignKey(
        'accounts.StudentProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='individual_tasks',
        help_text='Set this to assign the task to a single student instead of a whole class.'
    )

    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, default='homework')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    importance = models.CharField(max_length=10, choices=IMPORTANCE_CHOICES, default='normal')

    estimated_hours = models.DecimalField(max_digits=4, decimal_places=1, default=1.0,
                                           help_text='Estimated completion time, in hours.')
    max_marks = models.PositiveIntegerField(default=10)
    due_date = models.DateTimeField()

    attachment = models.FileField(upload_to=task_attachment_path, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        return self.title

    def target_students(self):
        """Return a queryset of StudentProfiles this task applies to."""
        from accounts.models import StudentProfile
        if self.student_id:
            return StudentProfile.objects.filter(pk=self.student_id)
        if self.class_assigned_id:
            return self.class_assigned.students.all()
        return StudentProfile.objects.none()

    def is_overdue(self):
        return timezone.now() > self.due_date

    def hours_remaining(self):
        delta = self.due_date - timezone.now()
        return round(delta.total_seconds() / 3600, 1)

    def smart_priority_score(self):
        hours_left = max(self.hours_remaining(), 0.1)
        urgency = 100 / hours_left
        difficulty_weight = {'easy': 1, 'medium': 2, 'hard': 3}.get(self.difficulty, 2)
        effort_weight = float(self.estimated_hours)
        marks_weight = self.max_marks / 10.0
        importance_bonus = {'normal': 0, 'important': 5, 'critical': 12}.get(self.importance, 0)
        return round((urgency * 1.5) + (difficulty_weight * 4) + (effort_weight * 2) + marks_weight + importance_bonus, 2)

    def smart_priority_label(self):
        score = self.smart_priority_score()
        if self.is_overdue() or score >= 30:
            return 'HIGH'
        if score >= 15:
            return 'MEDIUM'
        return 'LOW'

    def smart_priority_reason(self):
        parts = []
        if self.is_overdue():
            parts.append('it is overdue')
        else:
            hrs = self.hours_remaining()
            if hrs <= 24:
                parts.append('it is due within 24 hours')
            else:
                days = round(hrs / 24)
                parts.append(f'it is due in about {days} day{"s" if days != 1 else ""}')

        if self.difficulty == 'hard':
            parts.append('has high difficulty')
        elif self.difficulty == 'medium':
            parts.append('has moderate difficulty')

        parts.append(f'requires approximately {self.estimated_hours} hour(s)')

        if self.importance == 'critical':
            parts.append('is marked critical by the teacher')

        label = self.smart_priority_label().title()
        reason = ', '.join(parts)
        if ', ' in reason:
            head, tail = reason.rsplit(', ', 1)
            reason = f'{head}, and {tail}'
        return f'{label} priority because {reason}.'


class Submission(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey('accounts.StudentProfile', on_delete=models.CASCADE, related_name='submissions')

    text_answer = models.TextField(blank=True)
    file = models.FileField(upload_to=submission_file_path, blank=True, null=True)
    image = models.ImageField(upload_to=submission_image_path, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    marks_obtained = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)

    is_resubmission_allowed = models.BooleanField(default=False)
    submission_count = models.PositiveIntegerField(default=0)

    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'submissions_submission'
        unique_together = ('task', 'student')
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.student} -> {self.task}'

    def effective_status(self):
        if self.status in ('pending', 'in_progress') and self.task.is_overdue():
            return 'overdue'
        return self.status

    def mark_submitted(self):
        self.status = 'submitted'
        self.submitted_at = timezone.now()
        self.submission_count += 1
