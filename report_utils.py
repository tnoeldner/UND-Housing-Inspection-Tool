import pandas as pd
import streamlit as st
from io import BytesIO
from collections import defaultdict
from fpdf import FPDF

def format_items_table(items_data):
    # Group items by category, always include all items
    grouped = defaultdict(list)
    for cat, name, rating, notes in items_data:
        grouped[cat].append((name if name is not None else "", rating if rating is not None else "", notes if notes is not None else ""))
    # Render tables for each category
    for cat, items in grouped.items():
        st.markdown(f"**{cat}**")
        df = pd.DataFrame(items, columns=["Item", "Rank", "Comments"])
        st.table(df)

# PDF generation utility
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'UND Housing Inspection Report', 0, 1, 'C')
        self.ln(5)
    def section_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, title, 0, 1, 'L')
        self.ln(2)
    def section_table(self, cat, items):
        self.set_font('Arial', 'B', 11)
        self.cell(0, 7, cat, 0, 1, 'L')
        self.set_font('Arial', '', 10)
        self.cell(60, 6, 'Item', 1)
        self.cell(20, 6, 'Rank', 1)
        self.cell(90, 6, 'Comments', 1)
        self.ln()
        for name, rating, notes in items:
            self.cell(60, 6, str(name), 1)
            self.cell(20, 6, str(rating), 1)
            self.cell(90, 6, str(notes), 1)
            self.ln()
        self.ln(2)

def generate_pdf_report(building, inspection_date, inspector, inspection_type, items_data, ai_report=None):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, f"Building: {building}", 0, 1)
    pdf.cell(0, 8, f"Inspection Type: {inspection_type}", 0, 1)
    pdf.cell(0, 8, f"Date: {inspection_date}", 0, 1)
    pdf.cell(0, 8, f"Inspector: {inspector}", 0, 1)
    pdf.ln(4)
    pdf.section_title('Ratings & Notes')
    grouped = defaultdict(list)
    for cat, name, rating, notes in items_data:
        grouped[cat].append((name, rating, notes))
    for cat, items in grouped.items():
        pdf.section_table(cat, items)
    if ai_report:
        pdf.section_title('AI Summary')
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 6, ai_report)
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return BytesIO(pdf_bytes)
