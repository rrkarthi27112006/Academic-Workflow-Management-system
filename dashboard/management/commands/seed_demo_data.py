from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from academics.models import School, ClassRoom, Subject
from accounts.models import TeacherProfile, StudentProfile
from tasks.models import Task, Submission
from notifications.models import Announcement
from notifications.utils import notify_task_assigned, notify_announcement


class Command(BaseCommand):
    help = 'Seed EduTrack with demo data: admin, teachers, students, classes with student picker, multi-teacher subjects, tasks, submissions.'

    def handle(self, *args, **options):
        now = timezone.now()

        school, _ = School.objects.get_or_create(name='Greenwood High School', defaults={'address': 'Chennai, Tamil Nadu'})

        # ---- Administrator ----
        admin_user, created = User.objects.get_or_create(
            username='admin', defaults={'first_name': 'System', 'last_name': 'Administrator', 'email': 'admin@edutrack.local', 'is_staff': True, 'is_superuser': True}
        )
        if created:
            admin_user.set_password('admin1234')
            admin_user.save()
        else:
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()

        # ---- Teachers ----
        anitha_user, created = User.objects.get_or_create(
            username='anitha', defaults={'first_name': 'Anitha', 'last_name': 'Teacher', 'email': 'anitha@edutrack.local'}
        )
        if created:
            anitha_user.set_password('demo1234')
            anitha_user.save()
        anitha, _ = TeacherProfile.objects.get_or_create(
            user=anitha_user, defaults={'school': school, 'qualification': 'M.Sc, B.Ed'}
        )

        rajesh_user, created = User.objects.get_or_create(
            username='rajesh', defaults={'first_name': 'Rajesh', 'last_name': 'Kumar', 'email': 'rajesh@edutrack.local'}
        )
        if created:
            rajesh_user.set_password('demo1234')
            rajesh_user.save()
        rajesh, _ = TeacherProfile.objects.get_or_create(
            user=rajesh_user, defaults={'school': school, 'qualification': 'M.Tech, Ph.D'}
        )

        # ---- Students ----
        rahul_user, created = User.objects.get_or_create(
            username='rahul', defaults={'first_name': 'Rahul', 'last_name': 'Kumar', 'email': 'rahul@edutrack.local'}
        )
        if created:
            rahul_user.set_password('demo1234')
            rahul_user.save()
        rahul, _ = StudentProfile.objects.get_or_create(
            user=rahul_user, defaults={'school': school, 'roll_number': '10A-07'}
        )

        priya_user, created = User.objects.get_or_create(
            username='priya', defaults={'first_name': 'Priya', 'last_name': 'Raman', 'email': 'priya@edutrack.local'}
        )
        if created:
            priya_user.set_password('demo1234')
            priya_user.save()
        priya, _ = StudentProfile.objects.get_or_create(
            user=priya_user, defaults={'school': school, 'roll_number': '10A-12'}
        )

        # ---- Classes (Created by teachers with student enrollment) ----
        class_10a, _ = ClassRoom.objects.get_or_create(name='Class 10-A', school=school, defaults={'class_teacher': anitha})
        class_10a.class_teacher = anitha
        class_10a.students.set([rahul, priya])
        class_10a.save()

        class_10b, _ = ClassRoom.objects.get_or_create(name='Class 10-B (CS Special)', school=school, defaults={'class_teacher': rajesh})
        class_10b.class_teacher = rajesh
        class_10b.students.set([rahul, priya])
        class_10b.save()

        # ---- Subjects (Created by Admin with Multiple Teachers Assigned) ----
        math_subj, _ = Subject.objects.get_or_create(name='Mathematics', defaults={'code': 'MATH101'})
        math_subj.teachers.set([anitha, rajesh])
        math_subj.classes.set([class_10a, class_10b])

        science_subj, _ = Subject.objects.get_or_create(name='Science', defaults={'code': 'SCI102'})
        science_subj.teachers.set([anitha])
        science_subj.classes.set([class_10a])

        english_subj, _ = Subject.objects.get_or_create(name='English', defaults={'code': 'ENG103'})
        english_subj.teachers.set([anitha])
        english_subj.classes.set([class_10a])

        cs_subj, _ = Subject.objects.get_or_create(name='Computer Science', defaults={'code': 'CS104'})
        cs_subj.teachers.set([rajesh, anitha])
        cs_subj.classes.set([class_10a, class_10b])

        subjects = {
            'Mathematics': math_subj,
            'Science': science_subj,
            'English': english_subj,
            'Computer Science': cs_subj,
        }

        # ---- Sample Tasks (demonstrates Smart Priority & Workload) ----
        task_specs = [
            dict(
                title='Mathematics Project: Geometry in Architecture',
                description='Prepare a project analyzing geometric shapes used in famous buildings, with diagrams.',
                subject=subjects['Mathematics'], task_type='project', difficulty='hard',
                estimated_hours=3, max_marks=20, due_in=timedelta(hours=20), importance='important',
            ),
            dict(
                title='Science Worksheet: Chemical Reactions',
                description='Complete the worksheet on balancing chemical equations, questions 1-15.',
                subject=subjects['Science'], task_type='worksheet', difficulty='medium',
                estimated_hours=2, max_marks=10, due_in=timedelta(hours=22), importance='normal',
            ),
            dict(
                title='English Reading: Chapter 5 Summary',
                description='Read Chapter 5 of the assigned novel and write a one-page summary.',
                subject=subjects['English'], task_type='reading', difficulty='easy',
                estimated_hours=1, max_marks=5, due_in=timedelta(hours=23), importance='normal',
            ),
            dict(
                title='Computer Science Quiz: Python Basics',
                description='Short quiz covering variables, loops, and functions in Python.',
                subject=subjects['Computer Science'], task_type='quiz', difficulty='medium',
                estimated_hours=0.5, max_marks=10, due_in=timedelta(days=5), importance='normal',
            ),
            dict(
                title='Mathematics Revision: Algebra Sheet',
                description='Revise algebraic identities ahead of the upcoming class test.',
                subject=subjects['Mathematics'], task_type='revision', difficulty='easy',
                estimated_hours=1, max_marks=10, due_in=timedelta(days=6), importance='normal',
            ),
            dict(
                title='Science Class Activity: Plant Cell Model',
                description='Build a simple labelled model of a plant cell using household materials.',
                subject=subjects['Science'], task_type='class_activity', difficulty='medium',
                estimated_hours=2, max_marks=15, due_in=timedelta(days=-2), importance='normal',
            ),
        ]

        created_tasks = []
        for spec in task_specs:
            due_in = spec.pop('due_in')
            task, was_created = Task.objects.get_or_create(
                title=spec['title'], teacher=anitha,
                defaults={
                    **spec, 'class_assigned': class_10a, 'due_date': now + due_in,
                }
            )
            created_tasks.append(task)
            if was_created:
                notify_task_assigned(task)

        # ---- One reviewed submission for Rahul, to populate progress/feedback ----
        overdue_task = next((t for t in created_tasks if t.is_overdue()), None)
        if overdue_task:
            sub, _ = Submission.objects.get_or_create(task=overdue_task, student=rahul)
            if sub.status != 'reviewed':
                sub.text_answer = 'Completed the plant cell model with labelled parts as requested.'
                sub.mark_submitted()
                sub.status = 'reviewed'
                sub.reviewed_at = now
                sub.marks_obtained = 13
                sub.feedback = 'Neatly labelled model. Add the cell wall thickness next time.'
                sub.save()

        # ---- Announcement ----
        ann, was_created = Announcement.objects.get_or_create(
            teacher=anitha, title='Unit Test Schedule Released',
            defaults={
                'message': 'The Unit 2 test schedule has been posted. Check the deadlines page for subject-wise dates.',
                'target_class': class_10a,
            }
        )
        if was_created:
            notify_announcement(ann)

        self.stdout.write(self.style.SUCCESS('EduTrack database seeded successfully.'))
        self.stdout.write('----------------------------------------------------')
        self.stdout.write('Admin Panel Login:')
        self.stdout.write('  Admin:   admin   (password: admin1234)')
        self.stdout.write('Teacher Logins:')
        self.stdout.write('  Teacher: anitha  (password: demo1234)')
        self.stdout.write('  Teacher: rajesh  (password: demo1234)')
        self.stdout.write('Student Logins:')
        self.stdout.write('  Student: rahul   (password: demo1234)')
        self.stdout.write('  Student: priya   (password: demo1234)')
        self.stdout.write('----------------------------------------------------')

