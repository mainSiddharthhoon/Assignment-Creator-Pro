import os
import datetime
import json

class Element:
    def __init__(self, type, content, x=0, y=0, w=None, h=None, style=None, caption="", annotations=None):
        self.type = type  # 'text', 'image', or 'code'
        self.content = content # text string or image path
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.caption = caption # For images
        self.annotations = annotations or [] # List of dicts
        self.style = style or {
            'font_size': 12,
            'bold': False,
            'alignment': 'L',
            'line_spacing': 1.0
        }

    def to_dict(self):
        return {
            'type': self.type,
            'content': self.content,
            'x': self.x,
            'y': self.y,
            'w': self.w,
            'h': self.h,
            'caption': self.caption,
            'annotations': self.annotations,
            'style': self.style
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class Page:
    def __init__(self, layout='image_top'):
        self.elements = []
        self.layout = layout

    def add_element(self, element):
        self.elements.append(element)

    def move_element(self, from_idx, to_idx):
        if 0 <= from_idx < len(self.elements) and 0 <= to_idx < len(self.elements):
            self.elements.insert(to_idx, self.elements.pop(from_idx))
            return True
        return False

    def remove_element(self, index):
        if 0 <= index < len(self.elements):
            return self.elements.pop(index)
        return None

    def to_dict(self):
        return {
            'layout': self.layout,
            'elements': [e.to_dict() for e in self.elements]
        }

    @classmethod
    def from_dict(cls, data):
        page = cls(layout=data.get('layout', 'image_top'))
        for e_data in data.get('elements', []):
            page.add_element(Element.from_dict(e_data))
        return page

class Document:
    def __init__(self, output_dir="temp_screenshots"):
        self.pages = []
        self.output_dir = output_dir
        
        # Metadata & Settings
        self.student_name = ""
        self.subject = ""
        self.experiment_title = ""
        self.custom_header = ""
        
        self.show_header = True
        self.show_footer = True
        self.auto_page_numbering = True
        self.auto_figure_caption = True
        
        # Page Settings
        self.page_size = "A4" # "A4", "Letter"
        self.orientation = "P" # "P", "L"
        self.margins = {'top': 10, 'bottom': 10, 'left': 10, 'right': 10}
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def add_page(self, page=None):
        if page is None:
            page = Page()
        self.pages.append(page)
        return page

    def remove_page(self, index):
        if 0 <= index < len(self.pages):
            return self.pages.pop(index)
        return None

    def move_page(self, from_idx, to_idx):
        if 0 <= from_idx < len(self.pages) and 0 <= to_idx < len(self.pages):
            self.pages.insert(to_idx, self.pages.pop(from_idx))
            return True
        return False

    def clear(self):
        self.pages = []

    def to_dict(self):
        """Full document serialization."""
        return {
            'metadata': {
                'student_name': self.student_name,
                'subject': self.subject,
                'experiment_title': self.experiment_title,
                'custom_header': self.custom_header,
                'show_header': self.show_header,
                'show_footer': self.show_footer,
                'auto_page_numbering': self.auto_page_numbering,
                'auto_figure_caption': self.auto_figure_caption,
                'page_size': self.page_size,
                'orientation': self.orientation,
                'margins': self.margins
            },
            'pages': [p.to_dict() for p in self.pages]
        }

    def save_to_file(self, filepath):
        """Saves project to .acp file (JSON)."""
        data = self.to_dict()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def load_from_file(self, filepath):
        """Loads project from .acp file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        meta = data.get('metadata', {})
        self.student_name = meta.get('student_name', "")
        self.subject = meta.get('subject', "")
        self.experiment_title = meta.get('experiment_title', "")
        self.custom_header = meta.get('custom_header', "")
        self.show_header = meta.get('show_header', True)
        self.show_footer = meta.get('show_footer', True)
        self.auto_page_numbering = meta.get('auto_page_numbering', True)
        self.auto_figure_caption = meta.get('auto_figure_caption', True)
        self.page_size = meta.get('page_size', "A4")
        self.orientation = meta.get('orientation', "P")
        self.margins = meta.get('margins', {'top': 10, 'bottom': 10, 'left': 10, 'right': 10})
        
        self.pages = [Page.from_dict(p_data) for p_data in data.get('pages', [])]
