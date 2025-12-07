
import calendar
from datetime import date, timedelta
from core.models import SchoolDay

def prepare_compliance_data(student, start_date, end_date):
    """
    Prepares the data structure for the Compliance Record PDF.
    
    Args:
        student (Student): The student object.
        start_date (date): The calculated start date of the academic year.
        end_date (date): The calculated end date of the academic year.
        
    Returns:
        dict: Context dictionary including 'months_data', 'stats', 'subjects', 'student_info'.
    """
    
    # Parse dates if they are strings (from Celery task)
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)

    # 1. Fetch all relevant school days once
    school_days = SchoolDay.objects.filter(
        student=student,
        date__range=[start_date, end_date]
    ).prefetch_related('subjects')
    
    # Map dates to subjects for O(1) lookup
    # attendance_map = { date: [subject_names] }
    attendance_map = {
        day.date: [s.display_name for s in day.subjects.all()] 
        for day in school_days
    }
    
    # 2. Build the Matrix (Months)
    months_data = []
    
    current_date = start_date.replace(day=1)
    # We iterate until we pass end_date month/year
    # Safety break to prevent infinite loop
    while (current_date.year < end_date.year) or \
          (current_date.year == end_date.year and current_date.month <= end_date.month):
        
        m_num = current_date.month
        y_val = current_date.year
        m_name = calendar.month_name[m_num]
        
        # Determine valid days in this month
        _, last_day_of_month = calendar.monthrange(y_val, m_num)
        
        days_status = [] # List of 31 items
        
        for d in range(1, 32):
            if d > last_day_of_month:
                days_status.append({'code': 'INVALID', 'label': ''})
            else:
                check_date = date(y_val, m_num, d)
                if check_date in attendance_map:
                    days_status.append({'code': 'ATTENDED', 'label': 'X'})
                else:
                    days_status.append({'code': 'EMPTY', 'label': ''})
        
        monthly_total = sum(1 for day in days_status if day['code'] == 'ATTENDED')
        
        months_data.append({
            'name': m_name,
            'year': y_val,
            'days': days_status,
            'total': monthly_total
        })
        
        # Move to next month
        if m_num == 12:
            current_date = date(y_val + 1, 1, 1)
        else:
            current_date = date(y_val, m_num + 1, 1)
            
    # 3. Calculate Stats & Subjects
    total_days = len(attendance_map)
    days_required = 180
    days_remaining = max(0, days_required - total_days)
    
    subject_counts = {}
    for subjs in attendance_map.values():
        for s in subjs:
            subject_counts[s] = subject_counts.get(s, 0) + 1
            
    # Sort subjects alpha
    sorted_subjects = sorted(subject_counts.items())
    
    # 4. Student Info & Academic Year Label
    academic_year_label = f"{start_date.year}-{end_date.year}"
    if start_date.year == end_date.year:
        academic_year_label = f"{start_date.year}"
    
    # Association Logic
    association_name = 'Unknown Association'
    # Access association via the student's user profile
    if hasattr(student.user, 'profile') and student.user.profile.association:
        assoc = student.user.profile.association
        association_name = assoc.name
        days_required = assoc.required_days
        
        # recalculate days remaining based on association requirement
        days_remaining = max(0, days_required - total_days)
        
    context = {
        'student': student,
        'academic_year': academic_year_label,
        'months_data': months_data,
        'stats': {
            'total_days': total_days,
            'days_remaining': days_remaining
        },
        'subjects': sorted_subjects, # List of tuples (name, count)
        'generated_date': date.today(),
        'association_name': association_name,
    }
    
    return context
