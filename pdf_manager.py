from fpdf import FPDF
from PIL import Image
import os
import traceback

class PDFManager:
    def __init__(self):
        pass

    def export(self, queue, output_filename="output.pdf", resize_params=None):
        if not queue:
            return False, "No items to export"

        try:
            # We'll use Helvetica (standard font)
            pdf = FPDF()
            
            for i, item in enumerate(queue):
                pdf.add_page()
                
                # A4 dimensions (210mm x 297mm)
                # Default margins (10mm each side)
                base_max_width = 190
                base_max_height = 277
                
                # Apply resizing if provided and valid
                try:
                    if resize_params:
                        if 'width' in resize_params and str(resize_params['width']).strip():
                            base_max_width = min(190, float(resize_params['width']))
                        if 'height' in resize_params and str(resize_params['height']).strip():
                            base_max_height = min(277, float(resize_params['height']))
                except ValueError:
                    # If invalid number, just use defaults
                    pass

                if item['type'] == 'image':
                    img_path = item['path']
                    if not os.path.exists(img_path):
                        print(f"Warning: Image not found at {img_path}")
                        continue
                    
                    # Load image to get dimensions
                    img = Image.open(img_path)
                    width, height = img.size
                    
                    current_max_height = base_max_height
                    caption_text = item.get('caption', '')
                    
                    # If there's a caption, we need to leave some space at the bottom
                    if caption_text:
                        current_max_height -= 20 # Leave 20mm for caption

                    # Scale down to fit into the defined box while maintaining aspect ratio
                    ratio = min(base_max_width / width, current_max_height / height)
                    scaled_width = width * ratio
                    scaled_height = height * ratio
                    
                    # Center the image horizontally and vertically
                    x = (210 - scaled_width) / 2
                    y = (current_max_height - scaled_height) / 2 + 10 # Offset a bit from top
                    
                    pdf.image(img_path, x=x, y=y, w=scaled_width, h=scaled_height)
                    
                    # Add caption if exists
                    if caption_text:
                        pdf.set_y(y + scaled_height + 5)
                        pdf.set_font("Helvetica", size=10)
                        # Multi-cell with auto width
                        pdf.multi_cell(0, 10, txt=caption_text, align='C')
                    
                elif item['type'] == 'blank':
                    # Add text to the blank page
                    content = item.get('text', '')
                    if content:
                        pdf.set_font("Helvetica", size=12)
                        # Center vertically (A4 height is 297mm)
                        pdf.set_y(50) 
                        pdf.multi_cell(0, 10, txt=content, align='C')
            
            # Save the file
            pdf.output(output_filename)
            return True, f"Successfully exported to {output_filename}"
            
        except PermissionError:
            return False, f"Permission Denied: Could not save to '{output_filename}'. Please close the PDF if it is open in another app."
        except Exception as e:
            print(f"Export Error Traceback: {traceback.format_exc()}")
            return False, f"Export Error: {str(e)}"
