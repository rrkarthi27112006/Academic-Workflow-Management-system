from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group
from .models import StudentProfile, TeacherProfile


class TeacherProfileInline(admin.StackedInline):
    model = TeacherProfile
    can_delete = False
    extra = 0


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = (TeacherProfileInline, StudentProfileInline)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


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
