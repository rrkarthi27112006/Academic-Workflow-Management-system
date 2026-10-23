"""
Business logic for dashboards: smart priority, deadline conflicts,
workload analysis, missed-task warnings, and academic progress.
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q

from tasks.models import Task, Submission
from academics.models import ClassRoom


def get_tasks_for_student(student):
    return list(Task.objects.filter(
        Q(student=student) | Q(class_assigned__students=student)
    ).distinct().select_related('subject', 'teacher__user'))


def get_submission_map(student):
    return {s.task_id: s for s in Submission.objects.filter(student=student)}


def task_status(task, sub_map):
    sub = sub_map.get(task.id)
    return sub.effective_status() if sub else ('overdue' if task.is_overdue() else 'pending')


def student_task_buckets(student):
    """Return categorized tasks and counts for a student's dashboard."""
    now = timezone.now()
    today_end = now.replace(hour=23, minute=59, second=59)
    tasks = get_tasks_for_student(student)
    sub_map = get_submission_map(student)

    pending, completed, overdue, today, upcoming = [], [], [], [], []

    for t in tasks:
        status = task_status(t, sub_map)
        if status == 'overdue':
            overdue.append(t)
        elif status in ('submitted', 'reviewed'):
            completed.append(t)
        else:
            pending.append(t)

        if now <= t.due_date <= today_end:
            today.append(t)
        elif t.due_date > today_end:
            upcoming.append(t)

    upcoming.sort(key=lambda t: t.due_date)
    total = len(tasks)
    completion_rate = round((len(completed) / total) * 100, 1) if total else 0

    return {
        'all_tasks': tasks,
        'pending': pending,
        'completed': completed,
        'overdue': overdue,
        'today': today,
        'upcoming': upcoming[:5],
        'completion_rate': completion_rate,
        'sub_map': sub_map,
    }


def smart_priority_for_student(student, limit=3):
    """Top priority tasks the student should work on first."""
    sub_map = get_submission_map(student)
    tasks = get_tasks_for_student(student)
    actionable = [
        t for t in tasks
        if task_status(t, sub_map) in ('pending', 'in_progress', 'overdue')
    ]
    actionable.sort(key=lambda t: t.smart_priority_score(), reverse=True)
    return actionable[:limit]


def deadline_conflicts(student, window_hours=24):
    """Detect a heavy workload: multiple demanding tasks due close together."""
    now = timezone.now()
    window_end = now + timedelta(hours=window_hours)
    sub_map = get_submission_map(student)
    tasks = get_tasks_for_student(student)

    clustered = [
        t for t in tasks
        if now <= t.due_date <= window_end and task_status(t, sub_map) in ('pending', 'in_progress')
    ]
    total_hours = sum(float(t.estimated_hours) for t in clustered)

    return {
        'conflict': len(clustered) >= 2 and total_hours >= 3,
        'tasks': clustered,
        'total_hours': round(total_hours, 1),
        'window_hours': window_hours,
    }


def workload_analysis(student):
    now = timezone.now()
    week_end = now + timedelta(days=7)
    today_end = now.replace(hour=23, minute=59, second=59)
    sub_map = get_submission_map(student)
    tasks = get_tasks_for_student(student)

    due_today = [t for t in tasks if now <= t.due_date <= today_end]
    due_this_week = [t for t in tasks if now <= t.due_date <= week_end]
    pending = [t for t in tasks if task_status(t, sub_map) in ('pending', 'in_progress')]
    completed = [t for t in tasks if task_status(t, sub_map) in ('submitted', 'reviewed')]
    overdue = [t for t in tasks if task_status(t, sub_map) == 'overdue']

    estimated_hours = sum(float(t.estimated_hours) for t in pending)
    total = len(tasks)
    completion_pct = round((len(completed) / total) * 100, 1) if total else 0

    return {
        'due_today': due_today,
        'due_this_week': due_this_week,
        'estimated_hours': round(estimated_hours, 1),
        'completed': completed,
        'pending': pending,
        'overdue': overdue,
        'completion_pct': completion_pct,
    }


def missed_task_warning(student, lookback_days=14, threshold=3):
    """Count tasks that became overdue without any submission in the recent period."""
    now = timezone.now()
    lookback_start = now - timedelta(days=lookback_days)
    sub_map = get_submission_map(student)
    tasks = get_tasks_for_student(student)

    missed = [
        t for t in tasks
        if lookback_start <= t.due_date <= now and task_status(t, sub_map) == 'overdue'
    ]
    return {'count': len(missed), 'tasks': missed, 'warn': len(missed) >= threshold}


def subject_wise_progress(student):
    sub_map = get_submission_map(student)
    tasks = get_tasks_for_student(student)
    by_subject = {}
    for t in tasks:
        stats = by_subject.setdefault(t.subject.name, {'total': 0, 'completed': 0})
        stats['total'] += 1
        if task_status(t, sub_map) in ('submitted', 'reviewed'):
            stats['completed'] += 1

    result = []
    for subject, data in sorted(by_subject.items()):
        pct = round((data['completed'] / data['total']) * 100) if data['total'] else 0
        result.append({'subject': subject, 'percent': pct, 'completed': data['completed'], 'total': data['total']})
    return result


def recent_feedback(student, limit=5):
    return Submission.objects.filter(
        student=student, status='reviewed'
    ).exclude(feedback='').order_by('-reviewed_at')[:limit]


# ---------------- Teacher-side services ----------------

def teacher_dashboard_stats(teacher):
    tasks = Task.objects.filter(teacher=teacher)
    classes = ClassRoom.objects.filter(class_teacher=teacher)
    student_ids = set(classes.values_list('students', flat=True)) | set(
        tasks.filter(student__isnull=False).values_list('student_id', flat=True)
    )
    student_ids.discard(None)

    submissions = Submission.objects.filter(task__teacher=teacher)
    now = timezone.now()

    return {
        'total_classes': classes.count(),
        'total_students': len(student_ids),
        'active_tasks': tasks.filter(due_date__gte=now).count(),
        'pending_reviews': submissions.filter(status='submitted').count(),
        'overdue_submissions': submissions.filter(status__in=['pending', 'in_progress']).count(),
        'recent_tasks': tasks.order_by('-created_at')[:5],
        'recent_submissions': submissions.order_by('-updated_at')[:5],
        'upcoming_deadlines': tasks.filter(due_date__gte=now).order_by('due_date')[:5],
    }


def students_with_missing_work(teacher, threshold=1):
    tasks = list(Task.objects.filter(teacher=teacher))
    result = []
    students_seen = set()
    for task in tasks:
        for student in task.target_students():
            if student.id in students_seen:
                continue
            students_seen.add(student.id)
            sub_map = get_submission_map(student)
            missing = [t for t in tasks if student in t.target_students() and task_status(t, sub_map) == 'overdue']
            if len(missing) >= threshold:
                result.append({'student': student, 'missing_count': len(missing)})
    result.sort(key=lambda r: -r['missing_count'])
    return result


def teacher_reports(teacher):
    tasks = list(Task.objects.filter(teacher=teacher))
    submissions = Submission.objects.filter(task__teacher=teacher)
    classes = ClassRoom.objects.filter(class_teacher=teacher)

    sub_status_cache = {(s.task_id, s.student_id): s.status for s in submissions}
    class_completion = []
    for c in classes:
        class_tasks = [t for t in tasks if t.class_assigned_id == c.id]
        possible, done = 0, 0
        for t in class_tasks:
            for student in t.target_students():
                possible += 1
                if sub_status_cache.get((t.id, student.id)) in ('submitted', 'reviewed'):
                    done += 1
        pct = round((done / possible) * 100) if possible else 0
        class_completion.append({'class': c, 'percent': pct})

    most_overdue = sorted([t for t in tasks if t.is_overdue()], key=lambda t: t.due_date)[:5]

    return {
        'class_completion': class_completion,
        'missing_students': students_with_missing_work(teacher),
        'most_overdue': most_overdue,
        'submission_stats': {
            'total': submissions.count(),
            'reviewed': submissions.filter(status='reviewed').count(),
            'pending_review': submissions.filter(status='submitted').count(),
            'not_submitted': submissions.filter(status__in=['pending', 'in_progress']).count(),
        },
    }
