from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from accounts.decorators import teacher_required
from accounts.models import StudentProfile
from .models import ClassRoom, Subject
from .forms import ClassRoomForm


@teacher_required
def class_list(request):
    classes = ClassRoom.objects.filter(class_teacher=request.user.teacher_profile).prefetch_related('students__user', 'subjects')
    return render(request, 'academics/class_list.html', {'classes': classes})


@teacher_required
def class_create(request):
    teacher = request.user.teacher_profile
    form = ClassRoomForm(request.POST or None, teacher=teacher)
    if request.method == 'POST' and form.is_valid():
        classroom = form.save(commit=False)
        classroom.class_teacher = teacher
        if teacher.school:
            classroom.school = teacher.school
        classroom.save()
        form.save_m2m()
        messages.success(request, f'Class "{classroom.name}" created with {classroom.students.count()} student(s).')
        return redirect('academics:class_list')
    return render(request, 'academics/class_form.html', {'form': form, 'title': 'Create Class'})


@teacher_required
def class_edit(request, pk):
    classroom = get_object_or_404(ClassRoom, pk=pk)
    form = ClassRoomForm(request.POST or None, instance=classroom, teacher=request.user.teacher_profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Class "{classroom.name}" updated.')
        return redirect('academics:class_list')
    return render(request, 'academics/class_form.html', {'form': form, 'title': 'Edit Class'})


@teacher_required
def class_delete(request, pk):
    classroom = get_object_or_404(ClassRoom, pk=pk)
    if request.method == 'POST':
        classroom.delete()
        messages.success(request, 'Class deleted.')
        return redirect('academics:class_list')
    return render(request, 'academics/confirm_delete.html', {'object': classroom, 'type': 'class'})


@teacher_required
def subject_list(request):
    teacher = request.user.teacher_profile
    subjects = Subject.objects.filter(teachers=teacher).prefetch_related('teachers__user', 'classes')
    if not subjects.exists():
        subjects = Subject.objects.all().prefetch_related('teachers__user', 'classes')
    return render(request, 'academics/subject_list.html', {'subjects': subjects})


@teacher_required
def student_list(request):
    class_filter = request.GET.get('class', '')
    students = StudentProfile.objects.select_related('user').prefetch_related('classes').all()
    if class_filter:
        students = students.filter(classes__id=class_filter).distinct()
    classes = ClassRoom.objects.filter(class_teacher=request.user.teacher_profile)
    return render(request, 'academics/student_list.html', {
        'students': students, 'classes': classes, 'class_filter': class_filter,
    })
