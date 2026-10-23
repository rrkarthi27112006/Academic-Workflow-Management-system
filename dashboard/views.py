from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from accounts.decorators import teacher_required, student_required
from notifications.models import Announcement
from notifications.views import _announcements_for_user
from tasks.models import Task
from . import services


def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard:redirect')
    return redirect('accounts:login')


@login_required
def role_redirect(request):
    user = request.user
    if hasattr(user, 'teacher_profile'):
        return redirect('dashboard:teacher_dashboard')
    if hasattr(user, 'student_profile'):
        return redirect('dashboard:student_dashboard')
    if user.is_staff or user.is_superuser:
        return redirect('admin:index')
    return redirect('accounts:login')


@teacher_required
def teacher_dashboard(request):
    teacher = request.user.teacher_profile
    stats = services.teacher_dashboard_stats(teacher)
    missing = services.students_with_missing_work(teacher)[:5]
    announcements = Announcement.objects.filter(teacher=teacher)[:5]
    return render(request, 'dashboard/teacher_dashboard.html', {
        **stats, 'missing_work': missing, 'announcements': announcements,
    })


@student_required
def student_dashboard(request):
    student = request.user.student_profile
    buckets = services.student_task_buckets(student)
    priority_tasks = services.smart_priority_for_student(student)
    conflicts = services.deadline_conflicts(student)
    missed = services.missed_task_warning(student)
    feedback = services.recent_feedback(student)
    announcements = _announcements_for_user(request.user)[:5]

    return render(request, 'dashboard/student_dashboard.html', {
        **buckets,
        'priority_tasks': [(t, t.smart_priority_reason()) for t in priority_tasks],
        'conflicts': conflicts,
        'missed': missed,
        'feedback': feedback,
        'announcements': announcements,
    })


@student_required
def student_progress(request):
    student = request.user.student_profile
    buckets = services.student_task_buckets(student)
    progress = services.subject_wise_progress(student)
    return render(request, 'dashboard/student_progress.html', {**buckets, 'progress': progress})


@student_required
def student_workload(request):
    student = request.user.student_profile
    return render(request, 'dashboard/student_workload.html', {
        'workload': services.workload_analysis(student),
        'conflicts': services.deadline_conflicts(student),
        'missed': services.missed_task_warning(student),
    })


@login_required
def deadlines_calendar(request):
    user = request.user
    if hasattr(user, 'student_profile'):
        tasks = services.get_tasks_for_student(user.student_profile)
    elif hasattr(user, 'teacher_profile'):
        tasks = list(Task.objects.filter(teacher=user.teacher_profile))
    else:
        tasks = []
    tasks.sort(key=lambda t: t.due_date)
    return render(request, 'dashboard/deadlines_calendar.html', {'tasks': tasks})


@teacher_required
def teacher_reports(request):
    return render(request, 'dashboard/teacher_reports.html', services.teacher_reports(request.user.teacher_profile))
