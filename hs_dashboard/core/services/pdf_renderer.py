
from fpdf import FPDF
import io

class CompliancePDF(FPDF):
    def header(self):
        # We'll handle header manually in body to control data
        pass
    
    def footer(self):
        self.set_y(-15)
        self.set_font("Times", "I", 8)
        # We need the generation date, but footer doesn't easily access instance data passed creatively.
        # So we'll skip the auto-footer and draw it manually at the end of the page loop if needed,
        # or use a class attribute set before generation.
        if hasattr(self, 'generation_date_str'):
             self.cell(0, 10, f"Generated via Homeschool Dashboard on {self.generation_date_str}", align="C")

def render_compliance_report(context):
    """
    Renders the Compliance Report using FPDF2 based on the prepared context.
    """
    pdf = CompliancePDF(orientation='P', unit='mm', format='Letter')
    pdf.generation_date_str = context['generated_date'].strftime("%B %d, %Y")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(13, 13, 13) # ~0.5 inch margins

    # -- Header Section --
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 8, "Compliance Record pursuant to SC Code § 59-65-47", align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 6, f"Association: {context['association_name']}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Academic Year: {context['academic_year']}", align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)

    # -- Student Info Table --
    # Manual positioning for a clean look
    pdf.set_font("Helvetica", "B", 10)
    
    # 3 Column layout
    # Student Name | Grade | Total Days
    
    start_y = pdf.get_y()
    
    pdf.cell(25, 6, "Student Name:", align="L")
    pdf.set_font("Helvetica", "U", 10) # Underline data
    pdf.cell(60, 6, context['student'].name, align="L")
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(15, 6, "Grade:", align="L")
    pdf.set_font("Helvetica", "U", 10)
    pdf.cell(30, 6, context['student'].grade_level, align="L")
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(20, 6, "Total Days:", align="L")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(20, 6, str(context['stats']['total_days']), align="L", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(8)

    # -- The Grid --
    # Columns: Month (25mm) | 31 Days (4.5mm each) | Total (15mm)
    # Total Width: 25 + (31 * 4.5) + 15 = 25 + 139.5 + 15 = 179.5 mm
    # Page width is 215.9mm (Letter). Margins 13+13=26. Printable=189.9mm.
    # 179.5 fits easily.

    col_w_month = 25
    col_w_day = 4.5
    col_w_total = 15
    row_h = 5.5

    pdf.set_font("Helvetica", "B", 7)
    
    # Header Row
    pdf.cell(col_w_month, row_h, "Month", border=1, align="C")
    for d in range(1, 32):
        pdf.cell(col_w_day, row_h, str(d), border=1, align="C")
    pdf.cell(col_w_total, row_h, "Total", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    
    # Data Rows
    pdf.set_font("Helvetica", "", 8)
    
    months_data = context['months_data']
    
    for month in months_data:
        # Month Label
        pdf.cell(col_w_month, row_h, month['name'], border=1, align="L")
        
        day_count = 0
        days_list = month['days'] # List of dicts {code, label}
        
        for day_info in days_list:
            code = day_info['code']
            label = day_info['label'] # 'X' or ''
            
            if code == 'INVALID':
                # Grey fill
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(col_w_day, row_h, "", border=1, fill=True)
                pdf.set_fill_color(255, 255, 255) # Reset
            elif code == 'ATTENDED':
                # Bold X
                pdf.set_font("Helvetica", "B", 8)
                pdf.cell(col_w_day, row_h, "X", border=1, align="C")
                pdf.set_font("Helvetica", "", 8)
                day_count += 1
            else:
                # Empty
                pdf.cell(col_w_day, row_h, "", border=1)
                
        # Monthly Total
        pdf.cell(col_w_total, row_h, str(day_count) if day_count > 0 else "", border=1, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)

    # -- Subject Summary --
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Subject Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    
    subjects = context['subjects'] # List of (subject, count)
    if subjects:
        # Render in 2 columns?
        col_width = 90
        count = 0
        
        for subj_name, days in subjects:
            text = f"- {subj_name}: {days} days"
            pdf.cell(col_width, 5, text, align="L")
            count += 1
            if count % 2 == 0:
                pdf.ln(5)
        if count % 2 != 0:
            pdf.ln(5)
    else:
        pdf.cell(0, 5, "No subjects recorded.", new_x="LMARGIN", new_y="NEXT")
        
    pdf.ln(5)
    
    # -- Stats --
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, f"Total Days Attended: {context['stats']['total_days']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Days Remaining: {context['stats']['days_remaining']}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(8)
    
    # -- Portfolio Statement --
    pdf.set_font("Times", "I", 11)
    pdf.multi_cell(0, 5, "A portfolio of work samples has been maintained for this student and is available for review upon request.")
    
    pdf.ln(5)
    
    # -- Certification --
    # Ensure closure on one page if possible, else break
    if pdf.get_y() > 220:
        pdf.add_page()
        
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Parental Certification", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", "", 10)
    pdf.multi_cell(0, 5, "I certify that the attendance and progress records included in this report are accurate and comply with the requirements of South Carolina Code Section 59-65-47.")
    pdf.ln(10)
    
    # Signature Lines
    pdf.set_font("Times", "", 10)
    
    y = pdf.get_y()
    pdf.line(pdf.get_x(), y, pdf.get_x() + 100, y) # Sig Line
    pdf.line(pdf.get_x() + 120, y, pdf.get_x() + 170, y) # Date Line
    
    pdf.ln(2)
    pdf.cell(100, 5, "Parent/Guardian Signature", align="L")
    pdf.set_x(pdf.get_x() + 20)
    pdf.cell(50, 5, "Date", align="L", new_x="LMARGIN", new_y="NEXT")

    return pdf.output() # Returns bytearray
