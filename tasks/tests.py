from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from academics.models import School, ClassRoom, Subject
from accounts.models import TeacherProfile, StudentProfile
from tasks.models import Task
from submissions.models import Submission
from notifications.models import Notification


class EduTrackWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(name='Test School')

        # Teacher 1
        self.teacher_user = User.objects.create_user(username='teacher1', password='password123')
        self.teacher = TeacherProfile.objects.create(user=self.teacher_user, school=self.school)

        # Teacher 2
        self.teacher2_user = User.objects.create_user(username='teacher2', password='password123')
        self.teacher2 = TeacherProfile.objects.create(user=self.teacher2_user, school=self.school)

        # Student 1
        self.student_user = User.objects.create_user(username='student1', password='password123')
        self.student = StudentProfile.objects.create(user=self.student_user, school=self.school, roll_number='S1')

        # Class created by Teacher 1 with Student 1 selected
        self.classroom = ClassRoom.objects.create(name='Class 10-A', school=self.school, class_teacher=self.teacher)
        self.classroom.students.add(self.student)

        # Subject with multiple teachers
        self.subject = Subject.objects.create(name='Mathematics', code='M101')
        self.subject.teachers.add(self.teacher, self.teacher2)
        self.subject.classes.add(self.classroom)

    def test_multi_teacher_subject(self):
        self.assertEqual(self.subject.teachers.count(), 2)
        self.assertIn(self.teacher, self.subject.teachers.all())
        self.assertIn(self.teacher2, self.subject.teachers.all())

    def test_class_student_enrollment(self):
        self.assertEqual(self.classroom.student_count, 1)
        self.assertIn(self.student, self.classroom.students.all())

    def test_task_target_students(self):
        task = Task.objects.create(
            title='Math Homework',
            subject=self.subject,
            teacher=self.teacher,
            class_assigned=self.classroom,
            due_date=timezone.now() + timedelta(days=2),
            max_marks=10,
        )
        targets = task.target_students()
        self.assertEqual(targets.count(), 1)
        self.assertIn(self.student, targets)

    def test_smart_priority_scoring(self):
        urgent_task = Task.objects.create(
            title='Urgent Hard Task',
            subject=self.subject,
            teacher=self.teacher,
            class_assigned=self.classroom,
            difficulty='hard',
            estimated_hours=3.0,
            importance='critical',
            due_date=timezone.now() + timedelta(hours=10),
            max_marks=20,
        )
        self.assertEqual(urgent_task.smart_priority_label(), 'HIGH')
        self.assertIn('High priority because', urgent_task.smart_priority_reason())

    def test_student_submission_and_teacher_review_workflow(self):
        task = Task.objects.create(
            title='Algebra Assignment',
            subject=self.subject,
            teacher=self.teacher,
            class_assigned=self.classroom,
            due_date=timezone.now() + timedelta(days=2),
            max_marks=20,
        )

        # 1. Student submits work
        self.client.login(username='student1', password='password123')
        submission = Submission.objects.create(task=task, student=self.student)
        
        response = self.client.post(f'/submissions/submit/{submission.id}/', {
            'text_answer': 'Here are my solutions to questions 1 to 5.',
        })
        self.assertEqual(response.status_code, 302)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'submitted')
        self.assertEqual(submission.submission_count, 1)

        # Check teacher received notification
        teacher_notifs = Notification.objects.filter(user=self.teacher_user, notification_type='new_submission')
        self.assertTrue(teacher_notifs.exists())

        # 2. Teacher reviews work
        self.client.login(username='teacher1', password='password123')
        review_response = self.client.post(f'/submissions/review/{submission.id}/', {
            'marks_obtained': 18,
            'feedback': 'Excellent work! Pay attention to question 4 sign error.',
            'is_resubmission_allowed': False,
        })
        self.assertEqual(review_response.status_code, 302)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'reviewed')
        self.assertEqual(submission.marks_obtained, 18)


        # Check student received review notification
        student_notifs = Notification.objects.filter(user=self.student_user, notification_type='reviewed')
        self.assertTrue(student_notifs.exists())

    def test_admin_group_unregistered(self):
        from django.contrib import admin
        from django.contrib.auth.models import Group
        self.assertNotIn(Group, admin.site._registry)

    def test_class_creation_with_subjects(self):
        self.client.login(username='teacher1', password='password123')
        subject2 = Subject.objects.create(name='Science', code='SCI101')
        subject2.teachers.add(self.teacher)

        # Create class with 2 subjects
        response = self.client.post('/academics/classes/create/', {
            'name': 'Class 10-B',
            'subjects': [self.subject.id, subject2.id],
            'students': [self.student.id],
        })
        self.assertEqual(response.status_code, 302)
        new_class = ClassRoom.objects.get(name='Class 10-B')
        self.assertEqual(new_class.subjects.count(), 2)
        self.assertIn(self.subject, new_class.subjects.all())
        self.assertIn(subject2, new_class.subjects.all())

    def test_task_creation_for_whole_class(self):
        self.client.login(username='teacher1', password='password123')
        due = timezone.now() + timedelta(days=3)
        response = self.client.post('/tasks/teacher/create/', {
            'title': 'Chapter 1 Exercises',
            'description': 'Solve problems 1 through 10.',
            'class_assigned': self.classroom.id,
            'subject': self.subject.id,
            'task_type': 'homework',
            'difficulty': 'medium',
            'importance': 'normal',
            'estimated_hours': 1.5,
            'max_marks': 15,
            'due_date': due.strftime('%Y-%m-%dT%H:%M'),
        })
        self.assertEqual(response.status_code, 302)
        created_task = Task.objects.get(title='Chapter 1 Exercises')
        self.assertIsNone(created_task.student)
        self.assertEqual(created_task.class_assigned, self.classroom)
        self.assertEqual(created_task.target_students().count(), 1)
        self.assertIn(self.student, created_task.target_students())


