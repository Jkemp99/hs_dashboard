from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import date
from .models import Student, SchoolDay, Subject, WorkSample, GlobalSubject, Grade
from django.db.models import Count, Prefetch
from django.http import HttpResponse, FileResponse
from django.db import IntegrityError

from .utils import get_required_subjects, render_to_pdf

from django.utils.text import slugify

# PDF Imports

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
    school_days = SchoolDay.objects.filter(student__user=request.user).select_related('student').prefetch_related('subjects').order_by('-date', '-created_at')[:50]

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
    ).select_related('student').prefetch_related('subjects')

    # Organize logs by day
    logs_by_date = {}
    for log in monthly_logs:
        date_obj = log.date
        if date_obj not in logs_by_date:
            logs_by_date[date_obj] = []
        
        logs_by_date[date_obj].append({
            'student': log.student.name,
            'subjects': [s.display_name for s in log.subjects.all()], 
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
        db_subjects = set(s.display_name for s in student.subjects.all())
        
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
        'students': all_students,
    })

@login_required
def update_family_settings(request):
    if request.method == 'POST':
        association_id = request.POST.get('association_id')
        profile = request.user.profile
        from .models import Association
        
        if association_id:
            assoc = get_object_or_404(Association, id=association_id)
            profile.association = assoc
        else:
            profile.association = None
        profile.save()
    return redirect('settings')

@login_required
def add_edit_student(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        grade_level = request.POST.get('grade_level')
        custom_grade = request.POST.get('custom_grade_level')

        academic_year_start_month = request.POST.get('academic_year_start_month')
        academic_year_end_month = request.POST.get('academic_year_end_month')
        student_id = request.POST.get('student_id')
        
        grading_system = request.POST.get('grading_system', 'quarters')
        
        if student_id:
            student = get_object_or_404(Student, id=student_id, user=request.user)
            student.name = name
            student.grade_level = grade_level
            student.custom_grade_level = custom_grade
            student.grading_system = grading_system

            if academic_year_start_month:
                student.academic_year_start_month = int(academic_year_start_month)
            if academic_year_end_month:
                student.academic_year_end_month = int(academic_year_end_month)
            student.save()
        else:
            user = request.user
            student = Student(
                user=user, 
                name=name, 
                grade_level=grade_level, 
                custom_grade_level=custom_grade,
                grading_system=grading_system
            )
            if academic_year_start_month:
                student.academic_year_start_month = int(academic_year_start_month)
            if academic_year_end_month:
                student.academic_year_end_month = int(academic_year_end_month)
            student.save()
    
    # HTMX: Return updated student list
    students = Student.objects.filter(user=request.user).annotate(subject_count=Count('subjects'))
    for student in students:
        student.has_subjects = student.subject_count > 0
        
    global_subjects = GlobalSubject.objects.all()
    
    # Month choices for dropdowns
    import calendar as cal_module
    months = [(i, cal_module.month_name[i]) for i in range(1, 13)]
    
    return render(request, 'core/partials/student_list.html', {
        'students': students,
        'grade_choices': Student.GRADE_CHOICES,
        'global_subjects': global_subjects,
        'months': months,
    })

@login_required
def add_subject(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        global_subject_id = request.POST.get('global_subject_id')
        custom_name = request.POST.get('custom_name', '').strip()
        
        student = get_object_or_404(Student, id=student_id, user=request.user)
        
        if global_subject_id and global_subject_id != 'custom':
            # Check if student already has this global subject
            exists = Subject.objects.filter(
                student=student, 
                global_subject_id=global_subject_id
            ).exists()
            if not exists:
                Subject.objects.create(student=student, global_subject_id=global_subject_id)
        elif custom_name:
            # Check for existing custom subject with same name
            exists = Subject.objects.filter(
                student=student,
                name__iexact=custom_name
            ).exists()
            if not exists:
                Subject.objects.create(student=student, name=custom_name)
    return redirect('settings')

@login_required
def delete_subject(request, subject_id):
    if request.method == 'POST':
        subject = get_object_or_404(Subject, id=subject_id, student__user=request.user)
        subject.delete()
    return redirect('settings')

@login_required
def initialize_subjects(request, student_id):
    student = get_object_or_404(Student, id=student_id, user=request.user)
    required_subjects = get_required_subjects(student.grade_level)
    
    for subject_name in required_subjects:
        # Find matching GlobalSubject
        global_subj = GlobalSubject.objects.filter(name__iexact=subject_name).first()
        
        if global_subj:
            # Check if already exists to avoid duplicates
            if not Subject.objects.filter(student=student, global_subject=global_subj).exists():
                Subject.objects.create(student=student, global_subject=global_subj)
        else:
            # Fallback to custom name if no global match found
            if not Subject.objects.filter(student=student, name__iexact=subject_name).exists():
                Subject.objects.create(student=student, name=subject_name)
                
    return redirect('settings')

@login_required
def add_edit_school_day(request):
    if request.method == 'POST':
        day_id = request.POST.get('day_id')
        student_id = request.POST.get('student_id')
        date_str = request.POST.get('date')
        
        student = get_object_or_404(Student, id=student_id, user=request.user)
        
        if day_id:
            day = get_object_or_404(SchoolDay, id=day_id, student__user=request.user)
            day.student = student
            day.date = date_str
            subjects_list = request.POST.getlist('subjects_completed')
            day.notes = request.POST.get('notes')
            day.save()
            
            # Update subjects with GlobalSubject-aware resolution
            subject_objs = []
            for s_name in subjects_list:
                if s_name:
                    subj = Subject.objects.filter(student=student, global_subject__name__iexact=s_name).first()
                    if not subj:
                        subj = Subject.objects.filter(student=student, name__iexact=s_name).first()
                    if not subj:
                        global_subj = GlobalSubject.objects.filter(name__iexact=s_name).first()
                        if global_subj:
                            subj = Subject.objects.create(student=student, global_subject=global_subj)
                        else:
                            subj = Subject.objects.create(student=student, name=s_name)
                    subject_objs.append(subj)
            day.subjects.set(subject_objs)
        else:
            day = SchoolDay.objects.create(student=student, date=date_str)
            subjects_list = request.POST.getlist('subjects_completed')
            # Add subjects with GlobalSubject-aware resolution
            for s_name in subjects_list:
                if s_name:
                    subj = Subject.objects.filter(student=student, global_subject__name__iexact=s_name).first()
                    if not subj:
                        subj = Subject.objects.filter(student=student, name__iexact=s_name).first()
                    if not subj:
                        global_subj = GlobalSubject.objects.filter(name__iexact=s_name).first()
                        if global_subj:
                            subj = Subject.objects.create(student=student, global_subject=global_subj)
                        else:
                            subj = Subject.objects.create(student=student, name=s_name)
                    day.subjects.add(subj)
        
        next_url = request.GET.get('next') or request.POST.get('next')
        if next_url:
            return redirect(next_url)
    return redirect('settings')

@login_required
def settings_view(request):
        
    # Display students
    # Display students with subject count annotation
    students = Student.objects.filter(user=request.user).annotate(subject_count=Count('subjects'))
    
    # Add helper attribute for template
    for student in students:
        student.has_subjects = student.subject_count > 0
    
    # Display recent attendance history (last 50 records)
    school_days = SchoolDay.objects.filter(student__user=request.user).select_related('student').prefetch_related('subjects').order_by('-date', '-created_at')[:50]
    
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

    
    # Get all Associations
    from .models import Association
    associations = Association.objects.all()
    
    # Get all GlobalSubjects for the subject dropdown
    global_subjects = GlobalSubject.objects.all()

    # Month choices for dropdowns
    import calendar as cal_module
    months = [(i, cal_module.month_name[i]) for i in range(1, 13)]

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
        'associations': associations,
        'global_subjects': global_subjects,
        'months': months,
    })

@login_required
def dashboard(request):
    # Optimizing query to prevent N+1 problem
    students = Student.objects.filter(user=request.user).annotate(
        days_completed_count=Count('school_days')
    ).prefetch_related(
        'subjects',
        'subjects__global_subject',
        Prefetch('work_samples', queryset=WorkSample.objects.order_by('-date_uploaded'))
    )
    
    students_data = []
    for student in students:
        # Use annotated count
        days_completed = student.days_completed_count
        progress_percentage = min(100, int((days_completed / 180) * 100))
        days_remaining = max(0, 180 - days_completed)
        
        # Get explicitly assigned subjects
        db_subjects = [s.display_name for s in student.subjects.all()]
        
        # If student has assigned subjects, use them
        if db_subjects:
            required_subjects = sorted(list(set(db_subjects)))
        else:
             # Fallback to default if no subjects assigned
             required_subjects = get_required_subjects(student.grade_level)
        
        # Calculate 6-week compliance window
        six_weeks_ago = timezone.now().date() - timezone.timedelta(days=42)

        # Check compliance using prefetched data
        all_samples = list(student.work_samples.all())
        
        valid_subjects = {
            s.subject for s in all_samples if s.date_uploaded >= six_weeks_ago
        }
        
        missing_samples = [
            s for s in required_subjects if s not in valid_subjects
        ]

        # Get recent uploads from prefetched list
        recent_samples = all_samples[:5]

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
                # subjects_completed=subjects_completed # Removed
            )
            
            # Handle M2M Subjects
            if subjects_completed:
                for s_name in subjects_completed:
                    if s_name:
                        # Try to find existing subject for this student
                        subj = Subject.objects.filter(student=student, global_subject__name__iexact=s_name).first()
                        if not subj:
                            subj = Subject.objects.filter(student=student, name__iexact=s_name).first()
                        if not subj:
                            # Check if matches a GlobalSubject
                            global_subj = GlobalSubject.objects.filter(name__iexact=s_name).first()
                            if global_subj:
                                subj = Subject.objects.create(student=student, global_subject=global_subj)
                            else:
                                subj = Subject.objects.create(student=student, name=s_name)
                        day.subjects.add(subj)
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
            
            for student in students:
                # Get subjects depending on specific student selection
                subjects = request.POST.getlist(f'subjects_{student.id}')
                
                # Create Day
                day = SchoolDay.objects.create(
                    student=student, 
                    date=date_obj, 
                    notes=notes,
                )
                
                # Add Subjects
                if subjects:
                    for s_name in subjects:
                        if s_name:
                            # Try to find existing subject for this student
                            subj = Subject.objects.filter(student=student, global_subject__name__iexact=s_name).first()
                            if not subj:
                                subj = Subject.objects.filter(student=student, name__iexact=s_name).first()
                            if not subj:
                                # Check if matches a GlobalSubject
                                global_subj = GlobalSubject.objects.filter(name__iexact=s_name).first()
                                if global_subj:
                                    subj = Subject.objects.create(student=student, global_subject=global_subj)
                                else:
                                    subj = Subject.objects.create(student=student, name=s_name)
                            day.subjects.add(subj)
            
            # SchoolDay.objects.bulk_create(school_days) # Removed in favor of loop for M2M
            
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
    student.delete()
    
    # HTMX: Return updated student list
    students = Student.objects.filter(user=request.user).annotate(subject_count=Count('subjects'))
    for student in students:
        student.has_subjects = student.subject_count > 0
        
    global_subjects = GlobalSubject.objects.all()
    
    # Month choices for dropdowns
    import calendar as cal_module
    months = [(i, cal_module.month_name[i]) for i in range(1, 13)]
    
    return render(request, 'core/partials/student_list.html', {
        'students': students,
        'grade_choices': Student.GRADE_CHOICES,
        'global_subjects': global_subjects,
        'months': months,
    })

# PDF Imports

from core.services.pdf_service import prepare_compliance_data



@login_required
def download_report(request):
    student_id = request.GET.get('student_id')
    student = get_object_or_404(Student, id=student_id, user=request.user)

    # Determine Academic Year dynamically
    # Determine Academic Year dynamically
    start_month = student.academic_year_start_month or 8
    end_month = student.academic_year_end_month or 7
    
    import calendar
    
    # Check for specific year request
    requested_year = request.GET.get('year')
    
    if requested_year:
        start_year = int(requested_year)
        # Calculate end_year based on months
        if start_month > end_month:
            end_year = start_year + 1
        else:
            end_year = start_year
            
        # Set Label
        if start_year != end_year:
            academic_year_label = f"{start_year}-{end_year}"
        else:
            academic_year_label = f"{start_year}"
            
        # Set Dates
        _, last_day = calendar.monthrange(end_year, end_month)
        start_date = date(start_year, start_month, 1)
        end_date = date(end_year, end_month, last_day)
        
    else:
        # Fallback to Auto-Detect logic
        today = timezone.now().date()
        
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

    # 3. Call Async Task (Synchronously for now)
    # TODO: Switch to .delay() once Redis is fully configured
    from core.tasks import async_generate_report
    
    try:
        pdf_content = async_generate_report(student.id, str(start_date), str(end_date))
        
        if pdf_content:
            response = HttpResponse(pdf_content, content_type='application/pdf')
            safe_name = slugify(student.name)
            filename = f"Compliance_Record_{safe_name}_{academic_year_label}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        return HttpResponse("Error generating PDF: No content returned", status=500)
    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)


@login_required
def download_portfolio(request):
    student_id = request.GET.get('student_id')
    student = get_object_or_404(Student, id=student_id, user=request.user)

    # Determine Academic Year dynamically (Same logic as download_report)
    start_month = student.academic_year_start_month or 8
    end_month = student.academic_year_end_month or 7
    
    import calendar
    
    # Check for specific year request
    requested_year = request.GET.get('year')
    
    if requested_year:
        start_year = int(requested_year)
        # Calculate end_year based on months
        if start_month > end_month:
            end_year = start_year + 1
        else:
            end_year = start_year
            
        if start_year != end_year:
            academic_year_label = f"{start_year}-{end_year}"
        else:
            academic_year_label = f"{start_year}"
            
        _, last_day = calendar.monthrange(end_year, end_month)
        start_date = date(start_year, start_month, 1)
        end_date = date(end_year, end_month, last_day)
        
    else:
        # Fallback to Auto-Detect logic
        today = timezone.now().date()
        
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
    
        _, last_day = calendar.monthrange(end_year, end_month)
        start_date = date(start_year, start_month, 1)
        end_date = date(end_year, end_month, last_day)
    
        # Check for Data & Apply Fallback if Needed (checking samples instead of school_days)
        has_data = WorkSample.objects.filter(student=student, date_uploaded__range=[start_date, end_date]).exists()
    
        if not has_data:
            # Fallback: Find the last uploaded sample
            last_uploaded = WorkSample.objects.filter(student=student).order_by('-date_uploaded').first()
            if last_uploaded:
                ref_date = last_uploaded.date_uploaded
                
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

    # Query Samples
    samples = WorkSample.objects.filter(
        student=student,
        date_uploaded__range=[start_date, end_date]
    ).order_by('subject', 'date_uploaded')

    context = {
        'student': student,
        'academic_year': academic_year_label,
        'samples': samples,
        'start_date': start_date,
        'end_date': end_date,
    }

    pdf_response = render_to_pdf('pdfs/portfolio_report.html', context)
    
    if pdf_response.status_code == 200:
        safe_name = slugify(student.name)
        filename = f"Portfolio_Samples_{safe_name}_{academic_year_label}.pdf"
        pdf_response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return pdf_response
    else:
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

@login_required
def save_grade(request):
    if request.method == "POST":
        student_id = request.POST.get('student_id')
        subject_id = request.POST.get('subject_id')
        term = request.POST.get('term')
        score = request.POST.get('score')
        
        # Verify student belongs to user
        student = get_object_or_404(Student, id=student_id, user=request.user)
        subject = get_object_or_404(Subject, id=subject_id, student=student)
        
        if term and score:
            Grade.objects.update_or_create(
                student=student,
                subject=subject,
                term=term,
                defaults={'score': score}
            )
            
        return HttpResponse("")
    return HttpResponse(status=400)

@login_required
def gradebook_view(request, student_id):
    student = get_object_or_404(Student, id=student_id, user=request.user)
    subjects = student.subjects.all().order_by('name', 'global_subject__name')
    grades = Grade.objects.filter(student=student)
    
    # Define terms based on student setting
    if student.grading_system == 'semesters':
        terms = ['Fall', 'Spring']
    else:
        terms = ['Q1', 'Q2', 'Q3', 'Q4']

    # Organize grades for quick lookup: {(subject_id, term): score}
    grade_map = {(g.subject_id, g.term): g.score for g in grades}
    
    grade_rows = []
    for subject in subjects:
        cells = []
        for term in terms:
            cells.append({
                'term': term,
                'score': grade_map.get((subject.id, term), '')
            })
            
        grade_rows.append({
            'subject': subject,
            'cells': cells
        })
        
    return render(request, 'core/gradebook.html', {
        'student': student,
        'grade_rows': grade_rows,
        'terms': terms,
    })
