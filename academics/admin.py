from django.contrib import admin
from .models import School, ClassRoom, Subject


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'address')
    search_fields = ('name',)


class ClassSubjectInline(admin.TabularInline):
    model = Subject.classes.through
    extra = 1
    verbose_name = 'Subject'
    verbose_name_plural = 'Subjects Assigned to this Class'


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'class_teacher', 'get_subjects_display', 'student_count')
    list_filter = ('school', 'class_teacher')
    search_fields = ('name',)
    filter_horizontal = ('students',)
    inlines = [ClassSubjectInline]

    def get_subjects_display(self, obj):
        return ", ".join([s.name for s in obj.subjects.all()]) or "None"
    get_subjects_display.short_description = 'Subjects'



@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'get_teachers_display')
    list_filter = ('classes', 'teachers')
    search_fields = ('name', 'code')
    filter_horizontal = ('teachers', 'classes')

    def get_teachers_display(self, obj):
        return ", ".join([str(t) for t in obj.teachers.all()]) or "None"
    get_teachers_display.short_description = 'Teachers'

