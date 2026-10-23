from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from accounts.decorators import teacher_required
from .models import Notification, Announcement
from .forms import AnnouncementForm
from .utils import notify_announcement


@teacher_required
def announcement_list(request):
    announcements = Announcement.objects.filter(teacher=request.user.teacher_profile)
    return render(request, 'notifications/teacher_announcement_list.html', {'announcements': announcements})


@teacher_required
def announcement_create(request):
    teacher = request.user.teacher_profile
    form = AnnouncementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        ann = form.save(commit=False)
        ann.teacher = teacher
        ann.save()
        notify_announcement(ann)
        messages.success(request, 'Announcement posted.')
        return redirect('notifications:announcement_list')
    return render(request, 'notifications/announcement_form.html', {'form': form})


def _announcements_for_user(user):
    if hasattr(user, 'student_profile'):
        return Announcement.objects.filter(
            Q(target_all_students=True) | Q(target_class__students=user.student_profile)
        ).distinct()
    return Announcement.objects.none()


def my_announcements(request):
    announcements = _announcements_for_user(request.user) if request.user.is_authenticated else Announcement.objects.none()
    return render(request, 'notifications/my_announcements.html', {'announcements': announcements})


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications/notification_list.html', {'notifications': notifications})
