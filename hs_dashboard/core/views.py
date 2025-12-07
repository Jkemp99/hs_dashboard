from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import date
from .models import Student, SchoolDay, Subject, WorkSample
from django.db.models import Count
from django.http import HttpResponse, FileResponse
from django.db import IntegrityError
from fpdf import FPDF
from .utils import get_required_subjects
import io
import os
import json
from django.utils.text import slugify

# PDF Imports
# from django.template.loader import render_to_string
# from xhtml2pdf import pisa
from core.services.pdf_service import prepare_compliance_data

@login_required
def portfolio_view(request):
    # 1. Base Query
    work_samples = WorkSample.objects.filter(student__user=request.user)
    
    # 2. Filtering
    sample_year = request.GET.get('sample_year')
    sample_month = request.GET.get('sample_month')
    
    if sample_year:
        try:
            work_samples = work_samples.filter(date_uploaded__year=int(sample_year))
        except ValueError:
            pass
            
    if sample_month:
        try:
            work_samples = work_samples.filter(date_uploaded__month=int(sample_month))
        except ValueError:
            pass

    # 3. Sorting (Student -> Subject -> Date Descending)
    work_samples = work_samples.order_by('student__name', 'subject', '-date_uploaded')

    # 4. Get available years for filter dropdown
    available_years = sorted(set(
        WorkSample.objects.filter(student__user=request.user)
        .dates('date_uploaded', 'year')
        .values_list('date_uploaded__year', flat=True)
    ), reverse=True)

    # ... (Rest of existing code: Attendance History fetching)
    school_days = SchoolDay.objects.filter(student__user=request.user).select_related('student').order_by('-date', '-created_at')[:50]

    # 3. Calendar Logic
    import calendar
    from datetime import date
    
    today = timezone.now().date()
    
    # Get month and year from request, default to today
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except (ValueError, TypeError):
        year = today.year
        month = today.month
        
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    # Calculate previous and next month/year
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
        
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    # Get all days with attendance for this user in this month
    monthly_logs = SchoolDay.objects.filter(
        student__user=request.user,
        date__year=year,
        date__month=month
    ).select_related('student')

    # Organize logs by day
    logs_by_date = {}
    for log in monthly_logs:
        date_obj = log.date
        if date_obj not in logs_by_date:
            logs_by_date[date_obj] = []
        
        logs_by_date[date_obj].append({
            'student': log.student.name,
            'subjects': log.subjects_completed, 
            'notes': log.notes
        })
    
    calendar_weeks = []
    # Get dates with work samples for this month
    work_sample_dates = set(
        WorkSample.objects.filter(
            student__user=request.user,
            date_uploaded__year=year,
            date_uploaded__month=month
        ).values_list('date_uploaded', flat=True)
    )

    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({'day': 0, 'is_logged': False, 'logs': [], 'has_sample': False})
            else:
                date_obj = date(year, month, day)
                logs = logs_by_date.get(date_obj, [])
                is_logged = len(logs) > 0
                has_sample = date_obj in work_sample_dates
                
                week_data.append({
                    'day': day, 
                    'is_logged': is_logged,
                    'logs': logs,
                    'has_sample': has_sample
                })
        calendar_weeks.append(week_data)

    # Get subjects for all students to populate edit modal
    all_students = Student.objects.filter(user=request.user).prefetch_related('subjects')
    student_subjects_map = {}
    for student in all_students:
        # Get DB subjects
        db_subjects = set(s.name for s in student.subjects.all())
        
        # Get Default subjects based on grade
        if not student.custom_grade_level:
             default_subjects = set(get_required_subjects(student.grade_level))
        else:
             default_subjects = set()

        # Merge and sort
        all_subjects = sorted(list(db_subjects.union(default_subjects)))
        
        student_subjects_map[student.id] = all_subjects

    # Prepare Filter Options
    selected_year_val = int(sample_year) if sample_year and sample_year.isdigit() else None
    selected_month_val = int(sample_month) if sample_month and sample_month.isdigit() else None

    year_options = []
    for y in available_years:
        year_options.append({
            'value': y,
            'selected': y == selected_year_val
        })

    month_options = []
    for m in range(1, 13):
        month_options.append({
            'value': m,
            'name': calendar.month_name[m],
            'selected': m == selected_month_val
        })

    return render(request, 'core/portfolio.html', {
        'work_samples': work_samples,
        'school_days': school_days,
        'calendar_weeks': calendar_weeks,
        'current_month_name': month_name,
        'current_year': year,
        'current_date': today,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        # Filter Context (Pre-calculated)
        'year_options': year_options,
        'month_options': month_options,
        'student_subjects_map': student_subjects_map,
        'selected_sample_year': selected_year_val,
        'selected_sample_month': selected_month_val,
    })

@login_required
def settings_view(request):
    # Handle form submission for adding/editing/deleting students and days
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'delete_student':
            student_id = request.POST.get('student_id')
            student = get_object_or_404(Student, id=student_id, user=request.user)
            student.delete()
            return redirect('settings')
            
        elif action == 'delete_day':
            day_id = request.POST.get('day_id')
            # Ensure the day belongs to a student owned by the user
            day = get_object_or_404(SchoolDay, id=day_id, student__user=request.user)
            day.delete()
            return redirect('settings')
            
        elif action == 'add_edit_day':
            day_id = request.POST.get('day_id')
            student_id = request.POST.get('student_id')
            date_str = request.POST.get('date')
            
            # Ensure student belongs to user
            student = get_object_or_404(Student, id=student_id, user=request.user)
            
            if day_id:
                # Edit existing day
                day = get_object_or_404(SchoolDay, id=day_id, student__user=request.user)
                day.student = student
                day.date = date_str
                
                # Handle subjects
                subjects = request.POST.getlist('subjects_completed')
                day.subjects_completed = subjects
                day.notes = request.POST.get('notes')  # Ensure notes are also updated if passed
                
                day.save()
            else:
                # Create new day
                SchoolDay.objects.create(student=student, date=date_str)
            
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('settings')

        elif action == 'add_edit_student':
            # Add/Edit Student
            name = request.POST.get('name')
            grade_level = request.POST.get('grade_level')
            custom_grade = request.POST.get('custom_grade_level')
            tracking_mode = request.POST.get('tracking_mode', 'attendance')
            academic_year_start_month = request.POST.get('academic_year_start_month')
            academic_year_end_month = request.POST.get('academic_year_end_month')
            student_id = request.POST.get('student_id')
            
            if student_id:
                # Edit existing student
                student = get_object_or_404(Student, id=student_id, user=request.user)
                student.name = name
                student.grade_level = grade_level
                student.custom_grade_level = custom_grade
                student.tracking_mode = tracking_mode
                if academic_year_start_month:
                    student.academic_year_start_month = int(academic_year_start_month)
                if academic_year_end_month:
                    student.academic_year_end_month = int(academic_year_end_month)
                student.save()
            else:
                # Add new student
                user = request.user
                student = Student(user=user, name=name, grade_level=grade_level, custom_grade_level=custom_grade, tracking_mode=tracking_mode)
                if academic_year_start_month:
                    student.academic_year_start_month = int(academic_year_start_month)
                if academic_year_end_month:
                    student.academic_year_end_month = int(academic_year_end_month)
                student.save()
            return redirect('settings')

        elif action == 'add_subject':
            student_id = request.POST.get('student_id')
            subject_name = request.POST.get('subject_name')
            student = get_object_or_404(Student, id=student_id, user=request.user)
            Subject.objects.create(student=student, name=subject_name)
            return redirect('settings')

        elif action == 'delete_subject':
            subject_id = request.POST.get('subject_id')
            subject = get_object_or_404(Subject, id=subject_id, student__user=request.user)
            subject.delete()
            return redirect('settings')
        
    # Display students
    students = Student.objects.filter(user=request.user)
    
    # Display recent attendance history (last 50 records)
    school_days = SchoolDay.objects.filter(student__user=request.user).select_related('student').order_by('-date', '-created_at')[:50]
    
    # Calendar Logic
    import calendar
    from datetime import date
    
    today = timezone.now().date()
    
    # Get month and year from request, default to today
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except (ValueError, TypeError):
        year = today.year
        month = today.month
        
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    # Calculate previous and next month/year
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
        
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    # Get all days with attendance for this user in this month
    logged_dates = set(SchoolDay.objects.filter(
        student__user=request.user,
        date__year=year,
        date__month=month
    ).values_list('date', flat=True))
    
    calendar_weeks = []
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                current_date_obj = date(year, month, day)
                is_logged = current_date_obj in logged_dates
                week_data.append({'day': day, 'is_logged': is_logged})
        calendar_weeks.append(week_data)

    return render(request, 'core/settings.html', {
        'students': students, 
        'grade_choices': Student.GRADE_CHOICES,
        'school_days': school_days,
        'calendar_weeks': calendar_weeks,
        'current_month_name': month_name,
        'current_year': year,
        'current_date': today,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
    })

@login_required
def dashboard(request):
    # Fetch all students for the logged-in user, prefetching subjects
    students = Student.objects.filter(user=request.user).prefetch_related('subjects')
    
    students_data = []
    for student in students:
        days_completed = student.school_days.count()
        progress_percentage = min(100, int((days_completed / 180) * 100))
        days_remaining = max(0, 180 - days_completed)
        
        required_subjects = get_required_subjects(student.grade_level)
        
        # Calculate 6-week compliance window
        six_weeks_ago = timezone.now().date() - timezone.timedelta(days=42)

        # Check compliance
        missing_samples = []
        for subject in required_subjects:
            # Check if there is a sample in the last 6 weeks
            has_recent_sample = WorkSample.objects.filter(
                student=student,
                subject=subject,
                date_uploaded__gte=six_weeks_ago
            ).exists()
            
            if not has_recent_sample:
                missing_samples.append(subject)

        # Get recent uploads
        recent_samples = student.work_samples.order_by('-date_uploaded')[:5]

        students_data.append({
            'student': student,
            'days_completed': days_completed,
            'days_remaining': days_remaining,
            'progress_percentage': progress_percentage,
            'is_complete': days_completed >= 180,
            'required_subjects': required_subjects,
            'missing_samples': missing_samples,
            'recent_samples': recent_samples
        })
    
    context = {
        'students_data': students_data,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def log_school_day(request):
    if request.method == "POST":
        student_id = request.POST.get('student_id')
        notes = request.POST.get('notes')
        date_str = request.POST.get('date')
        subjects_completed = request.POST.getlist('subjects_completed')
        
        student = get_object_or_404(Student, id=student_id, user=request.user)

        if date_str:
            date_obj = date_str
        else:
            date_obj = timezone.now().date()
        
        try:
            day = SchoolDay.objects.create(
                student=student, 
                date=date_obj, 
                notes=notes,
                subjects_completed=subjects_completed
            )
        except IntegrityError:
            # Handle duplicate date (silently fail or return error - simple return for now)
            # ideally we return an error message to HTMX
             return HttpResponse("Error: Date already logged", status=400)
             
        # HTMX response: return updated counts
        days_completed = student.school_days.count()
        days_remaining = max(0, 180 - days_completed)
        
        return render(request, 'core/partials/stats.html', {
            'days_completed': days_completed,
            'days_remaining': days_remaining,
            'student': student
        })
            
    return HttpResponse(status=400)

@login_required
def bulk_log_school_day(request):
    if request.method == "POST":
        student_ids = request.POST.getlist('student_ids')
        notes = request.POST.get('notes')
        date_str = request.POST.get('date')
        
        # Default to today if no date provided
        if not date_str:
            date_obj = timezone.now().date()
        else:
            date_obj = date_str
            
        if student_ids:
            # Filter students to ensure they belong to the user
            students = Student.objects.filter(id__in=student_ids, user=request.user)
            
            school_days = []
            for student in students:
                # Get subjects depending on specific student selection
                subjects = request.POST.getlist(f'subjects_{student.id}')
                school_days.append(SchoolDay(
                    student=student, 
                    date=date_obj, 
                    notes=notes,
                    subjects_completed=subjects
                ))
            
            SchoolDay.objects.bulk_create(school_days)
            
        return redirect('dashboard')
    return redirect('dashboard')

@login_required
def delete_school_day(request, day_id):
    # This might be used by a direct link or fetch
    day = get_object_or_404(SchoolDay, id=day_id, student__user=request.user)
    day.delete()
    
    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url:
        return redirect(next_url)
        
    return redirect('settings')

@login_required
def delete_student(request, student_id):
    student = get_object_or_404(Student, id=student_id, user=request.user)
    student.delete()
    return redirect('settings')
    return redirect('dashboard')

# PDF Imports
# from django.template.loader import render_to_string
# from xhtml2pdf import pisa
from core.services.pdf_service import prepare_compliance_data
from core.services.pdf_renderer import render_compliance_report
from django.utils.text import slugify

@login_required
def download_report(request):
    student_id = request.GET.get('student_id')
    student = get_object_or_404(Student, id=student_id, user=request.user)

    # Determine Academic Year dynamically
    today = timezone.now().date()
    start_month = student.academic_year_start_month or 8
    end_month = student.academic_year_end_month or 7
    
    # 1. Calculate Initial Range
    if start_month <= end_month:
        start_year = today.year
        end_year = today.year
        academic_year_label = f"{start_year}"
    else:
        if today.month >= start_month:
             start_year = today.year
             end_year = today.year + 1
        elif today.month <= end_month:
             start_year = today.year - 1
             end_year = today.year
        else:
            if today.month < start_month: 
                start_year = today.year
                end_year = today.year + 1
            else:
                start_year = today.year
                end_year = today.year + 1
        academic_year_label = f"{start_year}-{end_year}"

    import calendar
    _, last_day = calendar.monthrange(end_year, end_month)
    start_date = date(start_year, start_month, 1)
    end_date = date(end_year, end_month, last_day)

    # 2. Check for Data & Apply Fallback if Needed
    has_data = SchoolDay.objects.filter(student=student, date__range=[start_date, end_date]).exists()

    if not has_data:
        # Fallback: Find the last logged day and base year on that
        last_logged = SchoolDay.objects.filter(student=student).order_by('-date').first()
        if last_logged:
            ref_date = last_logged.date
            
            if start_month <= end_month:
                start_year = ref_date.year
                end_year = ref_date.year
                academic_year_label = f"{start_year}"
            else:
                if ref_date.month >= start_month:
                     start_year = ref_date.year
                     end_year = ref_date.year + 1
                elif ref_date.month <= end_month:
                     start_year = ref_date.year - 1
                     end_year = ref_date.year
                else:
                    if ref_date.month < start_month: 
                        start_year = ref_date.year
                        end_year = ref_date.year + 1
                    else:
                        start_year = ref_date.year
                        end_year = ref_date.year + 1
                academic_year_label = f"{start_year}-{end_year}"
                
            _, last_day = calendar.monthrange(end_year, end_month)
            start_date = date(start_year, start_month, 1)
            end_date = date(end_year, end_month, last_day)

    # 3. Prepare Data Context via Service
    context = prepare_compliance_data(student, start_date, end_date)
    
    # 4. Handle Preview Mode
    if request.GET.get('preview'):
        return render(request, 'pdfs/attendance_report.html', context)
    
    # 5. Generate PDF
    from core.utils import render_to_pdf
    
    pdf = render_to_pdf('pdfs/attendance_report.html', context)
    if pdf:
        safe_name = slugify(student.name)
        filename = f"Compliance_Record_{safe_name}_{academic_year_label}.pdf"
        pdf['Content-Disposition'] = f'attachment; filename="{filename}"'
        return pdf
        
    return HttpResponse("Error generating PDF", status=500)


@login_required
def upload_work_sample(request):
    if request.method == "POST":
        student_id = request.POST.get('student_id')
        subject = request.POST.get('subject')
        file = request.FILES.get('file')
        
        student = get_object_or_404(Student, id=student_id, user=request.user)
        
        WorkSample.objects.create(
            student=student,
            subject=subject,
            file=file
        )
        # Return success for HTMX or redirect
        return redirect('dashboard')
    return redirect('dashboard')

@login_required
def delete_work_sample(request, sample_id):
    sample = get_object_or_404(WorkSample, id=sample_id, student__user=request.user)
    if request.method == "POST":
        sample.delete()
    return redirect('dashboard')
