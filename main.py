import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import os
import sys
import json
import threading
from PIL import Image, ImageTk

# Robust import check
try:
    from screenshot_manager import ScreenshotManager
    from models import Document, Page, Element
    from pdf_exporter import PDFExporter
    from ai_window import AIWindow
    from ai_client import AIClient
    from ai_workflow import AIWorkflowManager
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please make sure all dependencies are installed: pip install mss pillow fpdf2")
    sys.exit(1)

class ScreenshotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Assignment Creator Pro v1.5")
        self.root.geometry("1250x850")
        self.root.configure(bg="#f0f2f5")
        
        # Core Architecture
        self.document = Document()
        self.screenshot_manager = ScreenshotManager()
        self.pdf_exporter = PDFExporter()
        
        # AI Integration
        self.ai_window_instance = None
        self.ai_client = AIClient()
        self.workflow_manager = AIWorkflowManager(self.ai_client)
        
        # State
        self.current_selected_page_index = -1
        self.preview_image = None
        self.thumbnail_images = {} 
        self.thumb_labels = {}     
        self.unsaved_changes = False
        self.current_project_path = None
        
        # Undo/Redo Stacks
        self.undo_stack = []
        self.redo_stack = []
        
        # UI Styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_ui(self):
        # 1. Main Container
        self.main_paned = tk.PanedWindow(self.root, orient=tk.VERTICAL, bg="#f0f2f5", sashrelief=tk.RAISED, borderwidth=0)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # 2. Upper Work Area
        self.work_paned = tk.PanedWindow(self.main_paned, orient=tk.HORIZONTAL, bg="#f0f2f5", sashrelief=tk.RAISED, borderwidth=0)
        self.main_paned.add(self.work_paned, height=650)
        
        # --- Visual Sidebar (Left) ---
        self.sidebar_container = tk.Frame(self.work_paned, bg="#e0e0e0", width=260, bd=0)
        self.sidebar_container.pack_propagate(False)
        self.work_paned.add(self.sidebar_container, width=260)
        
        tk.Label(self.sidebar_container, text="PAGES", bg="#e0e0e0", font=("Segoe UI", 10, "bold"), fg="#555555").pack(pady=10)
        
        # Scrollable Canvas for Thumbnails
        self.canvas_container = tk.Frame(self.sidebar_container, bg="#e0e0e0")
        self.canvas_container.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.canvas_container, bg="#e0e0e0", highlightthickness=0, width=240)
        self.scrollbar = tk.Scrollbar(self.canvas_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#e0e0e0")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=240)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Sidebar reorder buttons
        reorder_frame = tk.Frame(self.sidebar_container, bg="#d0d0d0", height=40)
        reorder_frame.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Button(reorder_frame, text="▲", command=self.move_page_up, width=4, relief=tk.FLAT).pack(side=tk.LEFT, expand=True, pady=5)
        tk.Button(reorder_frame, text="▼", command=self.move_page_down, width=4, relief=tk.FLAT).pack(side=tk.LEFT, expand=True, pady=5)
        tk.Button(reorder_frame, text="🗑️", command=self.remove_page, width=4, fg="red", relief=tk.FLAT).pack(side=tk.LEFT, expand=True, pady=5)

        # --- Preview Area (Center/Right) ---
        self.preview_frame = tk.Frame(self.work_paned, bg="#f0f2f5", bd=0)
        self.work_paned.add(self.preview_frame)
        
        # --- Top Options Bar ---
        self.top_options = tk.Frame(self.preview_frame, bg="#f0f2f5", pady=5)
        self.top_options.pack(fill=tk.X)
        
        # Layout templates
        tk.Label(self.top_options, text="Layout:", bg="#f0f2f5", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=10)
        self.layout_var = tk.StringVar(value="image_top")
        layouts = [("Img Top", "image_top"), ("Txt Top", "text_top"), ("Img Only", "image_only"), ("Txt Only", "text_only")]
        for text, mode in layouts:
            tk.Radiobutton(self.top_options, text=text, variable=self.layout_var, value=mode, 
                          command=self.on_layout_change, bg="#f0f2f5", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=2)

        # Separator
        tk.Frame(self.top_options, width=2, bg="#cccccc").pack(side=tk.LEFT, fill=tk.Y, padx=15)

        # Header/Footer Toggle
        self.header_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.top_options, text="Header", variable=self.header_var, command=self.on_settings_change, 
                       bg="#f0f2f5", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)
        self.footer_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.top_options, text="Footer", variable=self.footer_var, command=self.on_settings_change, 
                       bg="#f0f2f5", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)
        
        # AI Mode Toggle
        tk.Frame(self.top_options, width=2, bg="#cccccc").pack(side=tk.LEFT, fill=tk.Y, padx=15)
        self.ai_mode_btn = tk.Button(self.top_options, text="🤖 AI Assistant", command=self.open_ai_assistant, 
                                    bg="#f0f2f5", font=("Segoe UI", 9, "bold"), fg="#0078d4", relief=tk.FLAT)
        self.ai_mode_btn.pack(side=tk.LEFT, padx=10)

        # Custom Header Entry
        tk.Label(self.top_options, text="Custom Header:", bg="#f0f2f5", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)
        self.custom_header_entry = tk.Entry(self.top_options, width=20)
        self.custom_header_entry.pack(side=tk.LEFT, padx=5)
        self.custom_header_entry.bind("<KeyRelease>", lambda e: self.on_settings_change(push_undo=False))
        self.custom_header_entry.bind("<FocusIn>", lambda e: self._push_undo())

        # --- Sub-Options Bar ---
        self.sub_options = tk.Frame(self.preview_frame, bg="#f0f2f5", pady=2)
        self.sub_options.pack(fill=tk.X)
        
        tk.Label(self.sub_options, text="Format:", bg="#f0f2f5", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=10)
        self.bold_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.sub_options, text="Bold", variable=self.bold_var, command=self.on_format_change, 
                       bg="#f0f2f5", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)
        
        tk.Label(self.sub_options, text="Size:", bg="#f0f2f5", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)
        self.size_var = tk.StringVar(value="12")
        self.size_spin = tk.Spinbox(self.sub_options, from_=8, to=72, width=3, textvariable=self.size_var, command=self.on_format_change)
        self.size_spin.pack(side=tk.LEFT, padx=5)
        self.size_spin.bind("<Return>", lambda e: self.on_format_change())

        # Caption Field
        tk.Label(self.sub_options, text="Caption:", bg="#f0f2f5", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=15)
        self.caption_entry = tk.Entry(self.sub_options, width=25)
        self.caption_entry.pack(side=tk.LEFT, padx=5)
        self.caption_entry.bind("<KeyRelease>", self.on_caption_modified)
        self.caption_entry.bind("<FocusIn>", lambda e: self._push_undo())
        
        # Auto Figure Toggle
        self.auto_fig_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.sub_options, text="Auto Fig#", variable=self.auto_fig_var, command=self.on_settings_change, 
                       bg="#f0f2f5", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=5)

        # Annotations
        tk.Frame(self.sub_options, width=2, bg="#cccccc").pack(side=tk.LEFT, fill=tk.Y, padx=15)
        tk.Label(self.sub_options, text="Annotate:", bg="#f0f2f5", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.rect_btn = tk.Button(self.sub_options, text="⬜ Rect", command=lambda: self.set_annotation_mode('rect'), bg="#f0f2f5", font=("Segoe UI", 8))
        self.rect_btn.pack(side=tk.LEFT, padx=2)
        self.arrow_btn = tk.Button(self.sub_options, text="↗ Arrow", command=lambda: self.set_annotation_mode('arrow'), bg="#f0f2f5", font=("Segoe UI", 8))
        self.arrow_btn.pack(side=tk.LEFT, padx=2)
        tk.Button(self.sub_options, text="🧹 Clear", command=self.clear_annotations, bg="#f0f2f5", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=5)

        # Element Ordering
        tk.Frame(self.sub_options, width=2, bg="#cccccc").pack(side=tk.LEFT, fill=tk.Y, padx=15)
        tk.Label(self.sub_options, text="Order:", bg="#f0f2f5", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(self.sub_options, text="⏫ Up", command=self.move_element_up, bg="#f0f2f5", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2)
        tk.Button(self.sub_options, text="⏬ Down", command=self.move_element_down, bg="#f0f2f5", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2)
        
        # Alignment
        tk.Frame(self.sub_options, width=2, bg="#cccccc").pack(side=tk.LEFT, fill=tk.Y, padx=15)
        tk.Label(self.sub_options, text="Align:", bg="#f0f2f5", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(self.sub_options, text="⬅️", command=lambda: self.set_alignment('L'), bg="#f0f2f5", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2)
        tk.Button(self.sub_options, text="↔️", command=lambda: self.set_alignment('C'), bg="#f0f2f5", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2)
        tk.Button(self.sub_options, text="➡️", command=lambda: self.set_alignment('R'), bg="#f0f2f5", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2)

        # Main Work Canvas (Paper look)
        self.paper_container = tk.Frame(self.preview_frame, bg="#f0f2f5", pady=10)
        self.paper_container.pack(fill=tk.BOTH, expand=True)
        
        self.paper_frame = tk.Frame(self.paper_container, bg="#ffffff", bd=1, relief=tk.SOLID)
        self.paper_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, relwidth=0.85, relheight=0.95)
        
        self.image_canvas = tk.Canvas(self.paper_frame, bg="#ffffff", highlightthickness=0)
        self.text_editor = tk.Text(self.paper_frame, font=("Segoe UI", 12), bd=0, wrap=tk.WORD, undo=True, padx=20, pady=20)
        self.text_editor.bind("<<Modified>>", self.on_text_modified)
        self.text_editor.bind("<FocusIn>", lambda e: self._push_undo())
        self._create_text_editor_context_menu()
        self.text_editor.bind("<Button-3>", self._show_ai_context_menu)
        
        self.placeholder_label = tk.Label(self.paper_frame, text="Assignment Creator Pro v1.0", 
                                         font=("Segoe UI", 16, "italic"), bg="#ffffff", fg="#cccccc")
        self.placeholder_label.pack(expand=True)

        # Drawing state
        self.annotation_mode = None 
        self.start_x = None
        self.start_y = None
        self.current_shape = None

        # --- Control Center (Bottom) ---
        self.control_frame = tk.Frame(self.main_paned, bg="#ffffff", height=150, bd=1, relief=tk.SOLID)
        self.main_paned.add(self.control_frame, height=150)
        
        grid_frame = tk.Frame(self.control_frame, bg="#ffffff")
        grid_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # Project File Actions
        file_actions_frame = tk.Frame(grid_frame, bg="#ffffff")
        file_actions_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Button(file_actions_frame, text="💾 Save Project", command=self.save_project, bg="#6c757d", fg="white", 
                  font=("Segoe UI", 9, "bold"), width=15, pady=5, relief=tk.FLAT).pack(pady=2)
        tk.Button(file_actions_frame, text="📂 Open Project", command=self.load_project, bg="#6c757d", fg="white", 
                  font=("Segoe UI", 9, "bold"), width=15, pady=5, relief=tk.FLAT).pack(pady=2)
        tk.Button(file_actions_frame, text="⚙️ Page Settings", command=self.show_page_settings, bg="#6c757d", fg="white", 
                  font=("Segoe UI", 9, "bold"), width=15, pady=5, relief=tk.FLAT).pack(pady=2)

        # Assignment Settings
        settings_frame = tk.LabelFrame(grid_frame, text="Assignment Settings", bg="#ffffff", font=("Segoe UI", 9, "bold"))
        settings_frame.pack(side=tk.LEFT, padx=20, fill=tk.Y)
        
        tk.Label(settings_frame, text="Student Name:", bg="#ffffff").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.name_entry = tk.Entry(settings_frame, width=20)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)
        self.name_entry.bind("<KeyRelease>", lambda e: self.on_settings_change(push_undo=False))
        self.name_entry.bind("<FocusIn>", lambda e: self._push_undo())
        
        tk.Label(settings_frame, text="Subject:", bg="#ffffff").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.subject_entry = tk.Entry(settings_frame, width=20)
        self.subject_entry.grid(row=1, column=1, padx=5, pady=2)
        self.subject_entry.bind("<KeyRelease>", lambda e: self.on_settings_change(push_undo=False))
        self.subject_entry.bind("<FocusIn>", lambda e: self._push_undo())
        
        tk.Label(settings_frame, text="Exp. Title:", bg="#ffffff").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.title_entry = tk.Entry(settings_frame, width=20)
        self.title_entry.grid(row=2, column=1, padx=5, pady=2)
        self.title_entry.bind("<KeyRelease>", lambda e: self.on_settings_change(push_undo=False))
        self.title_entry.bind("<FocusIn>", lambda e: self._push_undo())

        # Middle: Actions
        actions_frame = tk.Frame(grid_frame, bg="#ffffff")
        actions_frame.pack(side=tk.LEFT, padx=20)
        
        undo_frame = tk.Frame(actions_frame, bg="#ffffff")
        undo_frame.pack(pady=2)
        tk.Button(undo_frame, text="↩️ Undo", command=self.undo, bg="#f8f9fa", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2)
        tk.Button(undo_frame, text="↪️ Redo", command=self.redo, bg="#f8f9fa", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2)

        tk.Button(actions_frame, text="📸 Take Screenshot", command=self.capture_screenshot, bg="#0078d4", fg="white", 
                  font=("Segoe UI", 10, "bold"), width=18, pady=5, relief=tk.FLAT).pack(pady=2)
        tk.Button(actions_frame, text="🖼️ Insert Image", command=self.insert_image, bg="#17a2b8", fg="white", 
                  font=("Segoe UI", 10, "bold"), width=18, pady=5, relief=tk.FLAT).pack(pady=2)
        tk.Button(actions_frame, text="📄 Add Note Page", command=self.add_blank_page, bg="#28a745", fg="white", 
                  font=("Segoe UI", 10, "bold"), width=18, pady=5, relief=tk.FLAT).pack(pady=2)
        tk.Button(actions_frame, text="💻 Add Code Block", command=self.add_code_page, bg="#6c757d", fg="white", 
                  font=("Segoe UI", 10, "bold"), width=18, pady=5, relief=tk.FLAT).pack(pady=2)

        # Right: Export & Reset
        export_frame = tk.Frame(grid_frame, bg="#ffffff")
        export_frame.pack(side=tk.RIGHT, padx=20)
        
        tk.Button(export_frame, text="💾 Export to PDF", command=self.export_pdf, bg="#ffc107", fg="black", 
                  font=("Segoe UI", 10, "bold"), width=18, pady=8, relief=tk.FLAT).pack(pady=5)
        tk.Button(export_frame, text="🧹 Reset Project", command=self.reset_project, bg="#dc3545", fg="white", 
                  font=("Segoe UI", 10, "bold"), width=18, pady=8, relief=tk.FLAT).pack(pady=5)

        # Status Bar
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W, font=("Segoe UI", 9))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.stats_label = tk.Label(self.status_bar, text="Pages: 0 | Images: 0 | Words: 0", bg="#f0f2f5", font=("Segoe UI", 8))
        self.stats_label.pack(side=tk.RIGHT, padx=10)

    def on_settings_change(self, push_undo=True):
        if push_undo: self._push_undo()
        self.unsaved_changes = True
        self.document.student_name = self.name_entry.get()
        self.document.subject = self.subject_entry.get()
        self.document.experiment_title = self.title_entry.get()
        self.document.custom_header = self.custom_header_entry.get()
        self.document.show_header = self.header_var.get()
        self.document.show_footer = self.footer_var.get()
        self.document.auto_figure_caption = self.auto_fig_var.get()

    def update_stats(self):
        page_count = len(self.document.pages)
        img_count = 0
        word_count = 0
        for page in self.document.pages:
            for el in page.elements:
                if el.type == 'image': img_count += 1
                elif el.type in ['text', 'code']: word_count += len(el.content.split())
        self.stats_label.config(text=f"Pages: {page_count} | Images: {img_count} | Words: {word_count}")

    def update_sidebar(self):
        self.update_stats()
        self.thumb_labels = {}
        for widget in self.scrollable_frame.winfo_children(): widget.destroy()
        self.thumbnail_images = {}
        for i, page in enumerate(self.document.pages):
            is_selected = (i == self.current_selected_page_index)
            bg_color = "#d1e9ff" if is_selected else "#e0e0e0"
            slide_frame = tk.Frame(self.scrollable_frame, bg=bg_color, pady=5, padx=5)
            slide_frame.pack(fill=tk.X, padx=5, pady=2)
            tk.Label(slide_frame, text=str(i+1), bg=bg_color, font=("Segoe UI", 10, "bold"), width=2).pack(side=tk.LEFT, padx=2)
            thumb_container = tk.Frame(slide_frame, bg="white", width=160, height=100, bd=2, relief=tk.SOLID, highlightbackground="#0078d4" if is_selected else "#cccccc")
            thumb_container.pack_propagate(False)
            thumb_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
            thumb_label = tk.Label(thumb_container, bg="white")
            thumb_label.pack(fill=tk.BOTH, expand=True)
            self.thumb_labels[i] = thumb_label
            self._render_thumbnail(i)
            def make_select_func(idx): return lambda e: self.select_page(idx)
            for w in [slide_frame, thumb_container, thumb_label]: w.bind("<Button-1>", make_select_func(i))

    def _render_thumbnail(self, index):
        page = self.document.pages[index]
        thumb_label = self.thumb_labels.get(index)
        if not thumb_label: return
        img_element = next((e for e in page.elements if e.type == 'image'), None)
        text_element = next((e for e in page.elements if e.type in ['text', 'code']), None)
        try:
            if img_element:
                img = Image.open(img_element.content)
                img.thumbnail((150, 90), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                thumb_label.config(image=photo, text="")
                self.thumbnail_images[index] = photo
            elif text_element:
                text_snippet = text_element.content[:80].replace('\n', ' ')
                thumb_label.config(text=text_snippet, font=("Segoe UI", 7), wraplength=140, justify=tk.LEFT, anchor="nw", image="")
            else:
                thumb_label.config(text="Empty Page", font=("Segoe UI", 8), image="")
        except: thumb_label.config(text="Error", image="")

    def select_page(self, index):
        if index < 0 or index >= len(self.document.pages): return
        self.current_selected_page_index = index
        self._refresh_selection_visuals()
        page = self.document.pages[index]
        self.layout_var.set(page.layout)
        text_element = next((e for e in page.elements if e.type in ['text', 'code']), None)
        img_element = next((e for e in page.elements if e.type == 'image'), None)
        if text_element:
            self.bold_var.set(text_element.style.get('bold', False))
            self.size_var.set(str(text_element.style.get('font_size', 12)))
        if img_element:
            self.caption_entry.delete(0, tk.END)
            self.caption_entry.insert(0, img_element.caption)
            self.caption_entry.config(state=tk.NORMAL)
        else:
            self.caption_entry.delete(0, tk.END)
            self.caption_entry.config(state=tk.DISABLED)
        self.render_page_elements(page)

    def _refresh_selection_visuals(self):
        for i, child in enumerate(self.scrollable_frame.winfo_children()):
            is_selected = (i == self.current_selected_page_index)
            bg_color = "#d1e9ff" if is_selected else "#e0e0e0"
            child.config(bg=bg_color)
            for sub in child.winfo_children():
                if isinstance(sub, tk.Label) and not sub.winfo_name().startswith('!label'): sub.config(bg=bg_color)
                if sub.winfo_name().startswith('!frame'): sub.config(highlightbackground="#0078d4" if is_selected else "#cccccc")

    def render_page_elements(self, page):
        self.placeholder_label.pack_forget()
        self.image_canvas.pack_forget()
        self.text_editor.pack_forget()
        if not page.elements:
            self.placeholder_label.pack(expand=True)
            return
        for element in page.elements:
            if element.type == 'image':
                self.show_image_preview(element)
            elif element.type in ['text', 'code']:
                self.show_text_editor(element.content, style=element.style, is_code=(element.type=='code'))

    def show_image_preview(self, element, pack=tk.TOP):
        try:
            path = element.content
            if not os.path.exists(path): return
            img = Image.open(path)
            h_limit = 350 if len(self.document.pages[self.current_selected_page_index].elements) > 1 else 550
            img.thumbnail((700, h_limit), Image.LANCZOS)
            self.preview_w, self.preview_h = img.size
            self.preview_image = ImageTk.PhotoImage(img)
            self.image_canvas.config(width=self.preview_w, height=self.preview_h)
            self.image_canvas.delete("all")
            self.image_canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_image)
            self.image_canvas.pack(pady=10, side=pack)
            for ann in element.annotations:
                x1, y1, x2, y2 = ann['x1'] * self.preview_w, ann['y1'] * self.preview_h, ann['x2'] * self.preview_w, ann['y2'] * self.preview_h
                if ann['type'] == 'rect': self.image_canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2)
                elif ann['type'] == 'arrow': self.image_canvas.create_line(x1, y1, x2, y2, fill="red", width=2, arrow=tk.LAST)
            self.image_canvas.bind("<ButtonPress-1>", self.on_draw_start)
            self.image_canvas.bind("<B1-Motion>", self.on_draw_move)
            self.image_canvas.bind("<ButtonRelease-1>", self.on_draw_end)
        except Exception as e: print(f"Preview Error: {e}")

    def show_text_editor(self, text, style=None, is_code=False, pack=tk.TOP):
        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert(tk.END, text)
        bg_color = "#f8f9fa" if is_code else "#ffffff"
        font_family = "Consolas" if is_code else "Segoe UI"
        font_size = style.get('font_size', 10) if is_code else style.get('font_size', 12)
        font_w = "bold" if (style and style.get('bold') and not is_code) else "normal"
        self.text_editor.configure(font=(font_family, font_size, font_w), bg=bg_color)
        self.text_editor.pack(fill=tk.BOTH, expand=True, side=pack)
        self.text_editor.edit_modified(False)

    def on_layout_change(self):
        if self.current_selected_page_index != -1:
            self._push_undo()
            page = self.document.pages[self.current_selected_page_index]
            page.layout = self.layout_var.get()
            if page.layout in ['image_top', 'text_top', 'text_only'] and not any(e.type == 'text' for e in page.elements):
                page.add_element(Element('text', ""))
            self.select_page(self.current_selected_page_index)
            self.update_sidebar()

    def on_format_change(self):
        if self.current_selected_page_index != -1:
            self._push_undo()
            page = self.document.pages[self.current_selected_page_index]
            txt = next((e for e in page.elements if e.type in ['text', 'code']), None)
            if txt:
                if txt.type == 'code':
                    txt.style['bold'] = False
                    self.bold_var.set(False)
                else:
                    txt.style['bold'] = self.bold_var.get()
                try: txt.style['font_size'] = int(self.size_var.get())
                except: pass
                self.render_page_elements(page)

    def on_caption_modified(self, event=None):
        if self.current_selected_page_index != -1:
            self.unsaved_changes = True
            page = self.document.pages[self.current_selected_page_index]
            img = next((e for e in page.elements if e.type == 'image'), None)
            if img: img.caption = self.caption_entry.get()

    def set_alignment(self, align):
        if self.current_selected_page_index != -1:
            self._push_undo()
            page = self.document.pages[self.current_selected_page_index]
            for element in page.elements:
                element.style['alignment'] = align
            self.render_page_elements(page)

    def on_text_modified(self, event=None):
        if self.text_editor.edit_modified() and self.current_selected_page_index != -1:
            # We don't push undo on EVERY keypress, but we update the model.
            # Undo is handled by the widget's internal stack for text.
            # However, to sync with global undo, we push state on focus change (handled elsewhere).
            self.unsaved_changes = True
            page = self.document.pages[self.current_selected_page_index]
            txt = next((e for e in page.elements if e.type in ['text', 'code']), None)
            if txt: txt.content = self.text_editor.get("1.0", tk.END).strip()
            self.text_editor.edit_modified(False)
            self._render_thumbnail(self.current_selected_page_index)

    def set_annotation_mode(self, mode):
        self.annotation_mode = mode
        self.status_bar.config(text=f"Mode: {mode}. Click/drag on image.")
        self.rect_btn.config(relief=tk.SUNKEN if mode == 'rect' else tk.RAISED)
        self.arrow_btn.config(relief=tk.SUNKEN if mode == 'arrow' else tk.RAISED)

    def clear_annotations(self):
        if self.current_selected_page_index != -1:
            self._push_undo()
            page = self.document.pages[self.current_selected_page_index]
            img = next((e for e in page.elements if e.type == 'image'), None)
            if img:
                img.annotations = []
                self.render_page_elements(page)

    def on_draw_start(self, event):
        if not self.annotation_mode: return
        self.start_x, self.start_y = event.x, event.y
        if self.annotation_mode == 'rect': self.current_shape = self.image_canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="red", width=2)
        elif self.annotation_mode == 'arrow': self.current_shape = self.image_canvas.create_line(event.x, event.y, event.x, event.y, fill="red", width=2, arrow=tk.LAST)

    def on_draw_move(self, event):
        if not self.annotation_mode or not self.start_x: return
        self.image_canvas.coords(self.current_shape, self.start_x, self.start_y, event.x, event.y)

    def on_draw_end(self, event):
        if not self.annotation_mode or not self.start_x: return
        self._push_undo()
        x1, y1, x2, y2 = self.start_x / self.preview_w, self.start_y / self.preview_h, event.x / self.preview_w, event.y / self.preview_h
        img = next((e for e in self.document.pages[self.current_selected_page_index].elements if e.type == 'image'), None)
        if img: img.annotations.append({'type': self.annotation_mode, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})
        self.start_x = None
        self.annotation_mode = None
        self.rect_btn.config(relief=tk.RAISED)
        self.arrow_btn.config(relief=tk.RAISED)

    def insert_image(self):
        filename = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")])
        if filename:
            self._push_undo()
            page = Page(layout='image_top')
            page.add_element(Element('image', filename, w=180, h=120))
            page.add_element(Element('text', ""))
            self.document.add_page(page)
            self.update_sidebar()
            self.select_page(len(self.document.pages) - 1)

    def move_element_up(self):
        if self.current_selected_page_index != -1:
            page = self.document.pages[self.current_selected_page_index]
            if len(page.elements) >= 2:
                self._push_undo()
                page.move_element(1, 0)
                self.render_page_elements(page)

    def move_element_down(self):
        if self.current_selected_page_index != -1:
            page = self.document.pages[self.current_selected_page_index]
            if len(page.elements) >= 2:
                self._push_undo()
                page.move_element(0, 1)
                self.render_page_elements(page)

    def capture_screenshot(self):
        self.root.iconify()
        self.root.after(600, self._perform_capture)

    def _perform_capture(self):
        try:
            self._push_undo()
            item = self.screenshot_manager.capture()
            self.root.deiconify()
            page = Page(layout='image_top')
            page.add_element(Element('image', item['path'], w=180, h=120))
            page.add_element(Element('text', ""))
            self.document.add_page(page)
            self.update_sidebar()
            self.select_page(len(self.document.pages) - 1)
        except Exception as e:
            self.root.deiconify()
            messagebox.showerror("Error", str(e))

    def add_blank_page(self):
        self._push_undo()
        page = Page(layout='text_only')
        page.add_element(Element('text', ""))
        self.document.add_page(page)
        self.update_sidebar()
        self.select_page(len(self.document.pages) - 1)
        self.text_editor.focus_set()

    def add_code_page(self):
        self._push_undo()
        page = Page(layout='text_only')
        page.add_element(Element('code', ""))
        self.document.add_page(page)
        self.update_sidebar()
        self.select_page(len(self.document.pages) - 1)
        self.text_editor.focus_set()

    def move_page_up(self):
        if self.current_selected_page_index > 0:
            self._push_undo()
            if self.document.move_page(self.current_selected_page_index, self.current_selected_page_index - 1):
                self.current_selected_page_index -= 1
                self.update_sidebar()
                self.select_page(self.current_selected_page_index)

    def move_page_down(self):
        if self.current_selected_page_index != -1 and self.current_selected_page_index < len(self.document.pages) - 1:
            self._push_undo()
            if self.document.move_page(self.current_selected_page_index, self.current_selected_page_index + 1):
                self.current_selected_page_index += 1
                self.update_sidebar()
                self.select_page(self.current_selected_page_index)

    def remove_page(self):
        if self.current_selected_page_index != -1:
            if messagebox.askyesno("Confirm", "Delete page?"):
                self._push_undo()
                self.document.remove_page(self.current_selected_page_index)
                self.current_selected_page_index = -1
                self.update_sidebar()
                self.render_page_elements(Page())

    def save_project(self):
        self.on_settings_change()
        if not self.current_project_path:
            self.current_project_path = filedialog.asksaveasfilename(defaultextension=".acp", filetypes=[("Assignment Project", "*.acp")])
        if self.current_project_path:
            try:
                self.document.save_to_file(self.current_project_path)
                self.unsaved_changes = False
                messagebox.showinfo("Success", "Project saved.")
            except Exception as e: messagebox.showerror("Error", str(e))

    def _load_from_path(self, filename):
        """Internal helper to load project from a path."""
        self.document.load_from_file(filename)
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, self.document.student_name)
        self.subject_entry.delete(0, tk.END)
        self.subject_entry.insert(0, self.document.subject)
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, self.document.experiment_title)
        self.custom_header_entry.delete(0, tk.END)
        self.custom_header_entry.insert(0, self.document.custom_header)
        self.header_var.set(self.document.show_header)
        self.footer_var.set(self.document.show_footer)
        self.auto_fig_var.set(self.document.auto_figure_caption)
        self.current_selected_page_index = -1
        self.update_sidebar()
        if self.document.pages: self.select_page(0)
        else: self.render_page_elements(Page())

    def load_project(self):
        if self.unsaved_changes and not messagebox.askyesno("Warning", "Unsaved changes. Continue?"): return
        filename = filedialog.askopenfilename(filetypes=[("Assignment Project", "*.acp")])
        if filename:
            try:
                self._load_from_path(filename)
                self.current_project_path = filename
                self.unsaved_changes = False
            except Exception as e: messagebox.showerror("Error", str(e))

    def show_page_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Page Settings")
        settings_win.geometry("350x450")
        settings_win.transient(self.root)
        settings_win.grab_set()
        
        main_f = tk.Frame(settings_win, padx=20, pady=20)
        main_f.pack(fill=tk.BOTH, expand=True)
        
        # 1. Page Size
        tk.Label(main_f, text="Page Size:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        size_var = tk.StringVar(value=self.document.page_size)
        size_cb = ttk.Combobox(main_f, textvariable=size_var, values=["A4", "Letter"], state="readonly", width=15)
        size_cb.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 2. Orientation
        tk.Label(main_f, text="Orientation:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        orient_var = tk.StringVar(value=self.document.orientation)
        tk.Radiobutton(main_f, text="Portrait", variable=orient_var, value="P").grid(row=1, column=1, sticky=tk.W)
        tk.Radiobutton(main_f, text="Landscape", variable=orient_var, value="L").grid(row=2, column=1, sticky=tk.W)
        
        # 3. Margins
        tk.Label(main_f, text="Margins (mm):", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky=tk.W, pady=10)
        
        m_frame = tk.Frame(main_f)
        m_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W)
        
        margin_vars = {}
        for i, side in enumerate(['top', 'bottom', 'left', 'right']):
            tk.Label(m_frame, text=f"{side.capitalize()}:").grid(row=i//2, column=(i%2)*2, padx=5, pady=2)
            var = tk.StringVar(value=str(self.document.margins[side]))
            tk.Entry(m_frame, textvariable=var, width=5).grid(row=i//2, column=(i%2)*2+1, padx=5, pady=2)
            margin_vars[side] = var
            
        def save_settings():
            self._push_undo()
            self.document.page_size = size_var.get()
            self.document.orientation = orient_var.get()
            try:
                for side in ['top', 'bottom', 'left', 'right']:
                    self.document.margins[side] = int(margin_vars[side].get())
                self.unsaved_changes = True
                settings_win.destroy()
                messagebox.showinfo("Success", "Page settings updated.")
            except ValueError:
                messagebox.showerror("Error", "Margins must be valid integers.")

        tk.Button(main_f, text="Apply Settings", command=save_settings, bg="#28a745", fg="white", 
                  font=("Segoe UI", 9, "bold"), pady=8).grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=20)

    def export_pdf(self):
        if not self.document.pages: return
        self.on_settings_change()
        filename = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if filename:
            success, msg = self.pdf_exporter.export(self.document, filename)
            if success: messagebox.showinfo("Success", msg)
            else: messagebox.showerror("Error", msg)

    def reset_project(self):
        if messagebox.askyesno("Reset", "Clear all slides?"):
            self._push_undo()
            self.document.clear()
            self.screenshot_manager.cleanup_temp_files()
            self.current_selected_page_index = -1
            self.name_entry.delete(0, tk.END)
            self.subject_entry.delete(0, tk.END)
            self.title_entry.delete(0, tk.END)
            self.current_project_path = None
            self.unsaved_changes = False
            self.update_sidebar()
            self.render_page_elements(Page())

    def _push_undo(self):
        """Saves current document state to the undo stack."""
        state = self.document.to_dict()
        state['current_page_index'] = self.current_selected_page_index
        
        # Only push if it's different from the top of the stack
        if self.undo_stack and self.undo_stack[-1] == state:
            return
            
        self.undo_stack.append(state)
        # Clear redo stack when a NEW action is performed
        self.redo_stack = []
        
        if len(self.undo_stack) > 50: 
            self.undo_stack.pop(0)
        self.unsaved_changes = True
        print(f"DEBUG: Undo pushed. Stack size: {len(self.undo_stack)}")

    def undo(self):
        if not self.undo_stack: 
            print("DEBUG: Undo stack empty.")
            return
            
        # 1. Save CURRENT state to redo stack before applying previous state
        current_state = self.document.to_dict()
        current_state['current_page_index'] = self.current_selected_page_index
        self.redo_stack.append(current_state)
        
        # 2. Get the PREVIOUS state from undo stack
        state = self.undo_stack.pop()
        
        # 3. Apply it
        self._apply_state(state)
        print(f"DEBUG: Undo performed. Undo size: {len(self.undo_stack)}, Redo size: {len(self.redo_stack)}")

    def redo(self):
        if not self.redo_stack: 
            print("DEBUG: Redo stack empty.")
            return
            
        # 1. Save CURRENT state to undo stack before applying next state
        current_state = self.document.to_dict()
        current_state['current_page_index'] = self.current_selected_page_index
        self.undo_stack.append(current_state)
        
        # 2. Get the NEXT state from redo stack
        state = self.redo_stack.pop()
        
        # 3. Apply it
        self._apply_state(state)
        print(f"DEBUG: Redo performed. Undo size: {len(self.undo_stack)}, Redo size: {len(self.redo_stack)}")

    def _apply_state(self, state):
        """Restores the application to a previously saved state."""
        try:
            # Sync metadata
            meta = state.get('metadata', {})
            self.document.student_name = meta.get('student_name', "")
            self.document.subject = meta.get('subject', "")
            self.document.experiment_title = meta.get('experiment_title', "")
            self.document.custom_header = meta.get('custom_header', "")
            self.document.show_header = meta.get('show_header', True)
            self.document.show_footer = meta.get('show_footer', True)
            self.document.auto_figure_caption = meta.get('auto_figure_caption', True)
            self.document.page_size = meta.get('page_size', "A4")
            self.document.orientation = meta.get('orientation', "P")
            self.document.margins = meta.get('margins', {'top': 10, 'bottom': 10, 'left': 10, 'right': 10})
            
            # Sync pages
            self.document.pages = [Page.from_dict(p_data) for p_data in state.get('pages', [])]
            
            # Sync UI fields
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, self.document.student_name)
            self.subject_entry.delete(0, tk.END)
            self.subject_entry.insert(0, self.document.subject)
            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, self.document.experiment_title)
            self.custom_header_entry.delete(0, tk.END)
            self.custom_header_entry.insert(0, self.document.custom_header)
            self.header_var.set(self.document.show_header)
            self.footer_var.set(self.document.show_footer)
            self.auto_fig_var.set(self.document.auto_figure_caption)
            
            # Refresh UI
            self.update_sidebar()
            target_page = state.get('current_page_index', -1)
            if 0 <= target_page < len(self.document.pages):
                self.select_page(target_page)
            elif self.document.pages:
                self.select_page(0)
            else:
                self.current_selected_page_index = -1
                self.render_page_elements(Page())
        except Exception as e:
            print(f"ERROR applying state: {e}")

    def on_closing(self):
        if self.unsaved_changes:
            if not messagebox.askyesno("Quit", "Unsaved changes will be lost. Quit?"): return
        self.root.destroy()

    def open_ai_assistant(self):
        """Opens the AI Assistant in a separate Toplevel window."""
        if self.ai_window_instance is None or not self.ai_window_instance.winfo_exists():
            self.ai_window_instance = AIWindow(self.root)
        else:
            self.ai_window_instance.lift()
            self.ai_window_instance.focus_force()

    def _create_text_editor_context_menu(self):
        self.ai_context_menu = tk.Menu(self.root, tearoff=0)
        actions = [
            ("Improve Writing", "improve"),
            ("Make Academic", "academic"),
            ("Expand", "expand"),
            ("Summarize", "summarize")
        ]
        for label, action_type in actions:
            self.ai_context_menu.add_command(
                label=label,
                command=lambda at=action_type: self._handle_ai_action(at)
            )

    def _show_ai_context_menu(self, event):
        if self.get_selected_text():
            self.ai_context_menu.tk_popup(event.x_root, event.y_root)

    def get_selected_text(self):
        """Safely gets the selected text from the text editor."""
        try:
            return self.text_editor.selection_get()
        except tk.TclError:
            return None

    def _handle_ai_action(self, action_type):
        """Placeholder for handling the AI action."""
        selected_text = self.get_selected_text()
        if not selected_text:
            self.status_bar.config(text="No text selected for AI action.")
            return

        print(f"DEBUG: AI Action '{action_type}' triggered for text: '{selected_text[:50]}...'")
        self.status_bar.config(text=f"Triggered AI Action: {action_type}...")

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenshotApp(root)
    root.mainloop()
