from django.contrib import admin
from .models import Task, Submission


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'subject', 'class_assigned', 'student', 'task_type', 'difficulty', 'due_date')
    list_filter = ('task_type', 'difficulty', 'importance', 'subject')
    search_fields = ('title', 'description')


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('task', 'student', 'status', 'marks_obtained', 'submitted_at', 'reviewed_at')
    list_filter = ('status',)
    search_fields = ('task__title', 'student__user__username')
