from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from datetime import timedelta

from accounts.decorators import teacher_required, student_required
from .models import Task, TASK_TYPE_CHOICES, DIFFICULTY_CHOICES
from .forms import TaskForm
from submissions.models import Submission
from notifications.utils import notify_task_assigned


@teacher_required
def teacher_task_list(request):
    teacher = request.user.teacher_profile
    tasks = Task.objects.filter(teacher=teacher).select_related('subject', 'class_assigned', 'student')

    class_filter = request.GET.get('class', '')
    subject_filter = request.GET.get('subject', '')
    type_filter = request.GET.get('type', '')

    if class_filter:
        tasks = tasks.filter(class_assigned_id=class_filter)
    if subject_filter:
        tasks = tasks.filter(subject_id=subject_filter)
    if type_filter:
        tasks = tasks.filter(task_type=type_filter)

    from academics.models import ClassRoom, Subject
    return render(request, 'tasks/teacher_task_list.html', {
        'tasks': tasks,
        'classes': ClassRoom.objects.all(),
        'subjects': Subject.objects.all(),
        'task_types': TASK_TYPE_CHOICES,
        'class_filter': class_filter, 'subject_filter': subject_filter, 'type_filter': type_filter,
    })


@teacher_required
def task_create(request):
    teacher = request.user.teacher_profile
    from academics.models import ClassRoom
    teacher_classes = ClassRoom.objects.filter(class_teacher=teacher).prefetch_related('subjects')
    if not teacher_classes.exists():
        teacher_classes = ClassRoom.objects.all().prefetch_related('subjects')
    class_subjects_data = {
        str(c.id): [{'id': s.id, 'name': s.name} for s in c.subjects.all()]
        for c in teacher_classes
    }

    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES, teacher=teacher)
        if form.is_valid():
            task = form.save(commit=False)
            task.teacher = teacher
            task.save()
            notify_task_assigned(task)
            messages.success(request, f'Task "{task.title}" created and assigned to {task.class_assigned.name}.')
            return redirect('tasks:teacher_task_list')
    else:
        form = TaskForm(teacher=teacher)
    return render(request, 'tasks/task_form.html', {
        'form': form, 'title': 'Create Task', 'class_subjects_json': class_subjects_data,
    })


@teacher_required
def task_edit(request, pk):
    teacher = request.user.teacher_profile
    task = get_object_or_404(Task, pk=pk, teacher=teacher)
    from academics.models import ClassRoom
    teacher_classes = ClassRoom.objects.filter(class_teacher=teacher).prefetch_related('subjects')
    if not teacher_classes.exists():
        teacher_classes = ClassRoom.objects.all().prefetch_related('subjects')
    class_subjects_data = {
        str(c.id): [{'id': s.id, 'name': s.name} for s in c.subjects.all()]
        for c in teacher_classes
    }

    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES, instance=task, teacher=teacher)
        if form.is_valid():
            task = form.save()
            messages.success(request, 'Task updated successfully.')
            return redirect('tasks:teacher_task_list')
    else:
        form = TaskForm(instance=task, teacher=teacher)
    return render(request, 'tasks/task_form.html', {
        'form': form, 'title': 'Edit Task', 'class_subjects_json': class_subjects_data,
    })



@teacher_required
def task_delete(request, pk):
    teacher = request.user.teacher_profile
    task = get_object_or_404(Task, pk=pk, teacher=teacher)
    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Task deleted.')
        return redirect('tasks:teacher_task_list')
    return render(request, 'tasks/confirm_delete.html', {'object': task})


@teacher_required
def teacher_task_detail(request, pk):
    teacher = request.user.teacher_profile
    task = get_object_or_404(Task, pk=pk, teacher=teacher)
    students = task.target_students()
    submissions = Submission.objects.filter(task=task).select_related('student__user')
    submitted_student_ids = set(submissions.values_list('student_id', flat=True))
    not_submitted = students.exclude(id__in=submitted_student_ids)
    return render(request, 'tasks/teacher_task_detail.html', {
        'task': task, 'submissions': submissions, 'not_submitted': not_submitted,
    })


from django.db.models import Q

@student_required
def student_task_list(request):
    student = request.user.student_profile
    tasks = Task.objects.filter(
        Q(student=student) | Q(class_assigned__students=student)
    ).distinct().select_related('subject', 'teacher__user')


    view_filter = request.GET.get('view', 'all')
    subject_filter = request.GET.get('subject', '')
    type_filter = request.GET.get('type', '')
    priority_filter = request.GET.get('priority', '')
    status_filter = request.GET.get('status', '')
    search = request.GET.get('q', '')

    now = timezone.now()
    today_end = now.replace(hour=23, minute=59, second=59)

    # attach submission info
    sub_map = {s.task_id: s for s in Submission.objects.filter(student=student)}

    def status_of(task):
        sub = sub_map.get(task.id)
        if sub:
            return sub.effective_status()
        return 'overdue' if task.is_overdue() else 'pending'

    if subject_filter:
        tasks = tasks.filter(subject_id=subject_filter)
    if type_filter:
        tasks = tasks.filter(task_type=type_filter)
    if search:
        tasks = tasks.filter(title__icontains=search)

    tasks = list(tasks)

    if priority_filter:
        tasks = [t for t in tasks if t.smart_priority_label() == priority_filter.upper()]

    if status_filter:
        tasks = [t for t in tasks if status_of(t) == status_filter]

    if view_filter == 'today':
        tasks = [t for t in tasks if now <= t.due_date <= today_end]
    elif view_filter == 'upcoming':
        tasks = [t for t in tasks if t.due_date > today_end]
    elif view_filter == 'completed':
        tasks = [t for t in tasks if status_of(t) in ('submitted', 'reviewed')]
    elif view_filter == 'overdue':
        tasks = [t for t in tasks if status_of(t) == 'overdue']

    tasks.sort(key=lambda t: t.due_date)

    from academics.models import Subject
    return render(request, 'tasks/student_task_list.html', {
        'tasks': [(t, status_of(t)) for t in tasks],
        'subjects': Subject.objects.all(),
        'task_types': TASK_TYPE_CHOICES,
        'view_filter': view_filter, 'subject_filter': subject_filter, 'type_filter': type_filter,
        'priority_filter': priority_filter, 'status_filter': status_filter, 'search': search,
    })


@student_required
def student_task_detail(request, pk):
    student = request.user.student_profile
    task = get_object_or_404(Task, pk=pk)
    if student not in task.target_students():
        raise PermissionDenied('You do not have access to this task.')
    submission, _ = Submission.objects.get_or_create(task=task, student=student)
    return render(request, 'tasks/student_task_detail.html', {'task': task, 'submission': submission})
