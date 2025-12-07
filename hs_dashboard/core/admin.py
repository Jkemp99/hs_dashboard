from django.contrib import admin
from .models import Student, SchoolDay

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade_level', 'custom_grade_level')
    
    class Media:
        js = ('admin/js/jquery.init.js', 'core/js/student_admin.js')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        return super().add_view(request, form_url, extra_context=extra_context)

@admin.register(SchoolDay)
class SchoolDayAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'created_at')
    list_filter = ('student', 'date')
