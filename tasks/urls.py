from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('teacher/', views.teacher_task_list, name='teacher_task_list'),
    path('teacher/create/', views.task_create, name='task_create'),
    path('teacher/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('teacher/<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('teacher/<int:pk>/', views.teacher_task_detail, name='teacher_task_detail'),

    path('student/', views.student_task_list, name='student_task_list'),
    path('student/<int:pk>/', views.student_task_detail, name='student_task_detail'),

    path('submit/<int:pk>/', views.submit_task, name='submit_task'),
    path('review/<int:pk>/', views.review_submission, name='review_submission'),
]
