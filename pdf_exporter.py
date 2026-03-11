from fpdf import FPDF
from PIL import Image
import os
import traceback

class PDFExporter:
    def __init__(self):
        # We'll use Windows system fonts for Unicode support
        self.font_dir = r"C:\Windows\Fonts"
        self.font_mapping = {
            'regular': 'arial.ttf',
            'bold': 'arialbd.ttf',
            'italic': 'ariali.ttf',
            'bold_italic': 'arialbi.ttf'
        }

    def _setup_fonts(self, pdf):
        """Register Unicode-compatible TrueType fonts."""
        try:
            reg = os.path.join(self.font_dir, self.font_mapping['regular'])
            bold = os.path.join(self.font_dir, self.font_mapping['bold'])
            italic = os.path.join(self.font_dir, self.font_mapping['italic'])
            bi = os.path.join(self.font_dir, self.font_mapping['bold_italic'])

            if all(os.path.exists(f) for f in [reg, bold, italic, bi]):
                pdf.add_font("CustomArial", style="", fname=reg)
                pdf.add_font("CustomArial", style="B", fname=bold)
                pdf.add_font("CustomArial", style="I", fname=italic)
                pdf.add_font("CustomArial", style="BI", fname=bi)
                return "CustomArial"
            else:
                return "Helvetica"
        except Exception as e:
            print(f"Font Setup Warning: {e}")
            return "Helvetica"

    def export(self, document, output_filename):
        if not document.pages:
            return False, "No pages to export"

        try:
            # Create PDF with orientation and units
            # Page size from document settings
            size = document.page_size # "A4" or "Letter"
            pdf = FPDF(orientation=document.orientation, unit="mm", format=size)
            pdf.set_auto_page_break(False)
            
            font_family = self._setup_fonts(pdf)
            
            figure_count = 1
            total_pages = len(document.pages)

            for page_idx, page in enumerate(document.pages):
                pdf.add_page()
                
                # Page Dimensions
                p_w = pdf.w
                p_h = pdf.h
                m_top = document.margins['top']
                m_bottom = document.margins['bottom']
                m_left = document.margins['left']
                m_right = document.margins['right']
                
                work_w = p_w - m_left - m_right
                work_h = p_h - m_top - m_bottom

                # --- Header ---
                if document.show_header:
                    pdf.set_font(font_family, style="B", size=8)
                    pdf.set_text_color(100, 100, 100)
                    
                    parts = []
                    if document.student_name.strip(): parts.append(document.student_name.strip())
                    if document.subject.strip(): parts.append(document.subject.strip())
                    header_left = " | ".join(parts)
                    
                    pdf.set_xy(m_left, 5) # Small offset from top
                    if header_left:
                        pdf.cell(0, 5, txt=header_left, align='L')
                    
                    if document.experiment_title.strip():
                        pdf.set_xy(m_left, 5)
                        pdf.cell(work_w, 5, txt=document.experiment_title.strip(), align='R')
                    
                    # Custom header line if exists
                    if document.custom_header.strip():
                        pdf.set_xy(m_left, 10)
                        pdf.cell(work_w, 5, txt=document.custom_header.strip(), align='C')

                pdf.set_text_color(0, 0, 0)

                # Rendering elements
                current_y = m_top + (15 if document.show_header else 0)
                
                for element in page.elements:
                    if element.type == 'image':
                        # Use figure count if enabled
                        fig_num = figure_count if document.auto_figure_caption else None
                        img_h = self._render_image(pdf, element, current_y, work_w, work_h / 2, m_left, fig_num)
                        if document.auto_figure_caption: figure_count += 1
                        current_y += img_h + 10
                    elif element.type in ['text', 'code']:
                        pdf.set_xy(m_left, current_y)
                        text_h = self._render_text(pdf, element, font_family, work_w)
                        current_y += text_h + 5

                # --- Footer ---
                if document.show_footer:
                    pdf.set_y(p_h - m_bottom)
                    pdf.set_font(font_family, style="I", size=8)
                    pdf.set_text_color(100, 100, 100)
                    if document.auto_page_numbering:
                        page_num_text = f"Page {page_idx + 1} of {total_pages}"
                        pdf.set_x(m_left)
                        pdf.cell(work_w, 5, txt=page_num_text, align='C')

            pdf.output(output_filename)
            return True, f"Successfully exported to {output_filename}"
            
        except Exception as e:
            print(traceback.format_exc())
            return False, f"Export Error: {str(e)}"

    def _render_image(self, pdf, element, y, max_w, max_h, margin_left, fig_num=None):
        img_path = element.content
        if not os.path.exists(img_path): return 0
        
        try:
            img = Image.open(img_path)
            w, h = img.size
            
            ratio = min(max_w / w, max_h / h)
            final_w = w * ratio
            final_h = h * ratio
            
            final_x = margin_left + (max_w - final_w) / 2
            pdf.image(img_path, x=final_x, y=y, w=final_w, h=final_h)
            
            # Annotations
            for ann in getattr(element, 'annotations', []):
                pdf.set_draw_color(255, 0, 0)
                pdf.set_line_width(0.5)
                ax1 = final_x + (ann['x1'] * final_w)
                ay1 = y + (ann['y1'] * final_h)
                ax2 = final_x + (ann['x2'] * final_w)
                ay2 = y + (ann['y2'] * final_h)
                if ann['type'] == 'rect':
                    pdf.rect(ax1, ay1, ax2 - ax1, ay2 - ay1)
                elif ann['type'] == 'arrow':
                    pdf.line(ax1, ay1, ax2, ay2)
                    pdf.circle(ax2, ay2, 1)

            # Caption
            caption_h = 0
            if fig_num is not None or element.caption:
                pdf.set_xy(margin_left, y + final_h + 2)
                pdf.set_font("CustomArial", style="I", size=9)
                full_caption = ""
                if fig_num is not None:
                    full_caption = f"Figure {fig_num}: "
                full_caption += element.caption if element.caption else "Screenshot"
                pdf.multi_cell(max_w, 5, txt=full_caption, align='C')
                caption_h = 10
                
            return final_h + caption_h
        except:
            return 0

    def _render_text(self, pdf, element, font_family, work_w):
        if not element.content: return 0
        
        style = ""
        current_font = font_family
        fill = False
        
        if element.type == 'code':
            pdf.set_fill_color(240, 240, 240)
            current_font = "Courier"
            fill = True
        else:
            if element.style.get('bold'): style += "B"

        pdf.set_font(current_font, style=style, size=element.style.get('font_size', 12))
        
        start_y = pdf.get_y()
        line_height = 8 if element.type == 'code' else 10
        pdf.multi_cell(work_w, element.style.get('line_spacing', 1.0) * line_height, 
                       txt=element.content, align=element.style.get('alignment', 'L'), fill=fill)
        return pdf.get_y() - start_y
