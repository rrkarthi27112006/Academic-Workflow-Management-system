"""
URL configuration for edutrack project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from dashboard import views as home_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_views.landing_page, name='landing'),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('academics/', include('academics.urls')),
    path('tasks/', include('tasks.urls')),
    path('submissions/', include(('tasks.urls', 'tasks'), namespace='submissions')),
    path('notifications/', include('notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
