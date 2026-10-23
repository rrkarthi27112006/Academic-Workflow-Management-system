from .models import Notification


def create_notification(user, notification_type, message, link=''):
    return Notification.objects.create(
        user=user, notification_type=notification_type, message=message, link=link
    )


def notify_task_assigned(task):
    notifications = [
        Notification(
            user=student.user,
            notification_type='task_assigned',
            message=f'New task assigned: "{task.title}" ({task.subject.name})',
            link=f'/tasks/student/{task.id}/',
        )
        for student in task.target_students()
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)


def notify_new_submission(submission):
    create_notification(
        submission.task.teacher.user,
        'new_submission',
        f'{submission.student.user.get_full_name() or submission.student.user.username} submitted "{submission.task.title}"',
        link=f'/tasks/teacher/{submission.task_id}/',
    )


def notify_reviewed(submission):
    student_user = submission.student.user
    task_id = submission.task_id
    create_notification(
        student_user, 'reviewed',
        f'Your submission for "{submission.task.title}" has been reviewed.',
        link=f'/tasks/student/{task_id}/',
    )
    if submission.feedback:
        create_notification(
            student_user, 'feedback',
            f'New feedback on "{submission.task.title}".',
            link=f'/tasks/student/{task_id}/',
        )


def notify_announcement(announcement):
    from accounts.models import StudentProfile
    if announcement.target_all_students:
        students = StudentProfile.objects.all()
    elif announcement.target_class:
        students = announcement.target_class.students.all()
    else:
        return

    notifications = [
        Notification(
            user=s.user,
            notification_type='announcement',
            message=f'New announcement: {announcement.title}',
            link='/notifications/announcements/',
        )
        for s in students
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)


def notify_missing_work(student, teacher_user, count):
    create_notification(
        teacher_user, 'missing_work',
        f'{student.user.get_full_name() or student.user.username} has {count} task(s) with missing work.',
        link='/academics/students/',
    )
