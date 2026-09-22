# pyrefly: ignore [missing-import]
from django.contrib import admin
# pyrefly: ignore [missing-import]
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
from .models import StudentProfile, TeacherProfile


class TeacherProfileInline(admin.StackedInline):
    model = TeacherProfile
    can_delete = False
    verbose_name_plural = 'Teacher Profile'
    extra = 0


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Student Profile'
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = (TeacherProfileInline, StudentProfileInline)


# Re-register UserAdmin with inlines
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'roll_number', 'school')
    list_filter = ('school',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'roll_number')


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'qualification', 'phone')
    list_filter = ('school',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

