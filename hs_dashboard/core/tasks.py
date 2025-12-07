from celery import shared_task
from .services.pdf_service import prepare_compliance_data
from .utils import generate_pdf_bytes
from .models import Student
from datetime import date
import base64

@shared_task
def async_generate_report(student_id, start_date_str=None, end_date_str=None):
    """
    Task to generate the compliance report.
    Returns the PDF content as a bytes object.
    """
    try:
        student = Student.objects.get(id=student_id)
        
        context = prepare_compliance_data(student, start_date_str, end_date_str)
        
        # Use the HTML template for styling
        pdf_content = generate_pdf_bytes('pdfs/attendance_report.html', context)
        
        return pdf_content
    except Exception as e:
        # Log error
        print(f"Error generating report: {e}")
        return None
