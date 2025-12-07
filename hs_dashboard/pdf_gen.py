from fpdf import FPDF
from logic import SchoolYear
from datetime import datetime
import os

# FPDF2 doesn't support full CSS/HTML, so we'll use a simpler approach
# or we can use the HTMLMixin if we accept limitations.
# Let's try to use basic FPDF commands to recreate the look, 
# or use write_html with a simplified template. 
# Given the user wants "HTML template", I will try to use write_html.

def generate_report():
    # 1. Get Data
    school = SchoolYear()
    school.log_days(150)
    
    days_completed = school.current_day_count
    days_remaining = 180 - days_completed if days_completed < 180 else 0
    status = "In Progress" if days_remaining > 0 else "Completed"
    current_date = datetime.now().strftime("%B %d, %Y")

    # 2. Read Template
    with open('report_template.html', 'r') as f:
        template_content = f.read()

    # 3. Replace Placeholders
    html_content = template_content.replace('{{ days_completed }}', str(days_completed))
    html_content = html_content.replace('{{ days_remaining }}', str(days_remaining))
    html_content = html_content.replace('{{ status }}', status)
    html_content = html_content.replace('{{ date }}', current_date)

    # 4. Generate PDF using FPDF
    print("Generating PDF with fpdf2...")
    pdf = FPDF()
    pdf.add_page()
    
    # FPDF write_html doesn't support <style> blocks well, so it might ignore CSS.
    # But let's try it.
    try:
        pdf.write_html(html_content)
        pdf.output("my_report.pdf")
        print(f"PDF generated successfully: {os.path.abspath('my_report.pdf')}")
    except Exception as e:
        print(f"Error generating PDF: {e}")

if __name__ == "__main__":
    generate_report()
