from django.template.loader import get_template
from django.http import HttpResponse
from io import BytesIO

def get_required_subjects(grade_level):
    """
    Returns a list of required subjects based on the student's grade level.
    
    Grades 1-6: Reading, Writing, Math, Science, Social Studies
    Grades 7-12: Literature, Composition, Math, Science, Social Studies
    """
    
    elementary_subjects = ['Reading', 'Writing', 'Math', 'Science', 'Social Studies']
    secondary_subjects = ['Literature', 'Composition', 'Math', 'Science', 'Social Studies']
    
    # Normalize grade level string
    grade = str(grade_level).lower()
    
    # Check for secondary grades
    if any(x in grade for x in ['7th', '8th', '9th', '10th', '11th', '12th']):
        return secondary_subjects
        
    # Default to elementary for 1st-6th, Kindergarten, and others
    return elementary_subjects

def generate_pdf_bytes(template_src, context_dict={}):
    """Generates PDF bytes from a template and context."""
    from xhtml2pdf import pisa
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None

def render_to_pdf(template_src, context_dict={}):
    """Utility for direct view response (Deprecated for async use)."""
    pdf_content = generate_pdf_bytes(template_src, context_dict)
    if pdf_content:
        return HttpResponse(pdf_content, content_type='application/pdf')
    return HttpResponse("PDF Generation Error", status=500)
