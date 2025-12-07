from django.urls import path
from .views import dashboard, settings_view, portfolio_view, log_school_day, bulk_log_school_day, delete_school_day, delete_student, download_report, upload_work_sample, delete_work_sample

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
]
