from django.urls import path
from .views import dashboard, settings_view, portfolio_view, log_school_day, bulk_log_school_day, delete_school_day, delete_student, download_report, upload_work_sample, delete_work_sample, update_family_settings, add_edit_student, add_subject, delete_subject, add_edit_school_day

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('portfolio/', portfolio_view, name='portfolio'),
    path('settings/', settings_view, name='settings'),
    path('log_school_day', log_school_day, name='log_school_day'),
    path('bulk_log_school_day/', bulk_log_school_day, name='bulk_log_school_day'),
    path('delete_school_day/<int:day_id>/', delete_school_day, name='delete_school_day'),
    path('delete_student/<int:student_id>/', delete_student, name='delete_student'),
    path('download_report/', download_report, name='download_report'),
    path('upload_work_sample/', upload_work_sample, name='upload_work_sample'),
    path('delete_work_sample/<int:sample_id>/', delete_work_sample, name='delete_work_sample'),
    path('student/add_edit/', add_edit_student, name='add_edit_student'),
    path('subject/add/', add_subject, name='add_subject'),
    path('subject/delete/<int:subject_id>/', delete_subject, name='delete_subject'),
    path('settings/family/', update_family_settings, name='update_family_settings'),
    path('day/add_edit/', add_edit_school_day, name='add_edit_school_day'),
]
