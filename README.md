# Assignment Creator Pro (ACP) - Version 1.5

Welcome to the **Assignment Creator Pro** (ACP) journal and documentation. This project was born from a simple yet powerful need: **To help students create professional, organized, and clean college assignments from screenshots and notes without the hassle of manual formatting.**

---

## 📖 The "Problem" (Why this exists)
Students often need to document their work (code, software outputs, research) for college assignments. Traditionally, this involves:
1. Taking a screenshot.
2. Pasting it into Word or PowerPoint.
3. Manually resizing and centering it.
4. Adding captions and page numbers.
5. Fighting with formatting when a new image is added.
6. Exporting to a PDF that often looks "cluttered."

**The Goal:** Create a tool that automates the layout, handles high-quality image capture, and exports a "ready-to-submit" PDF with one click.

---

## 💡 The "Solution" (How we solved it)
We built a specialized **Document Editor** specifically for assignments. Instead of a blank canvas, ACP uses a **Page-based Structure**.
- **Automated Layouts:** You don't "drag and drop" randomly. You add elements (Images, Text, Code Blocks), and the app places them perfectly.
- **Smart Captures:** A built-in screenshot manager that captures exactly what you need and puts it into a "Queue."
- **Professional PDF Engine:** A custom-built exporter that handles headers, footers, page numbering, and Figure captions (Figure 1, Figure 2...) automatically.
- **AI Companion:** A local AI Assistant that lives in its own window to help you write descriptions or explain your screenshots.

---

## 🏗️ Project Structure (How it's built)

The project is divided into specialized "Modules" (files). Think of these as different departments in a factory:

### 1. The Brains ([models.py](file:///c:/Unique Projects/ScreenshotToPDF/models.py))
- **Concepts:** `Element`, `Page`, and `Document`.
- **What it does:** This file defines what an "Assignment" is. A `Document` has many `Pages`, and a `Page` has many `Elements` (like an image or a block of text).
- **Non-Dev Tip:** If you want to change how many margins a page has or what metadata (Name, Subject) is stored, this is the place.

### 2. The Engine ([main.py](file:///c:/Unique Projects/ScreenshotToPDF/main.py))
- **Concepts:** Tkinter UI, Event Handling, Undo/Redo.
- **What it does:** This is the main window you see. it connects the buttons you click to the logic in other files. It also manages the "Undo/Redo" system by taking "snapshots" of your work every time you change something.

### 3. The Camera ([screenshot_manager.py](file:///c:/Unique Projects/ScreenshotToPDF/screenshot_manager.py))
- **Concepts:** Screen Grabbing (`mss` library).
- **What it does:** Handles the "Capture" button. It hides the app window, takes a screenshot of the area you select, and saves it to a temporary folder.

### 4. The Printer ([pdf_exporter.py](file:///c:/Unique Projects/ScreenshotToPDF/pdf_exporter.py))
- **Concepts:** FPDF, PIL (Image processing), Unicode Fonts.
- **What it does:** This is the most complex part. It takes your virtual `Document` and "paints" it onto a PDF file. It handles drawing red boxes/arrows on images and ensuring your name appears at the top of every page.

### 5. The Assistant ([ai_window.py](file:///c:/Unique Projects/ScreenshotToPDF/ai_window.py) & [ai_client.py](file:///c:/Unique Projects/ScreenshotToPDF/ai_client.py))
- **Concepts:** Local LLM Integration (LM Studio), Threading.
- **What it does:** A separate window that talks to a local AI model. We used **Threading** so the app doesn't freeze while the AI is "thinking."

---

## 🔗 How everything is linked
1. You click **Capture** in `main.py`.
2. `screenshot_manager.py` takes the photo.
3. `models.py` creates a new `Element` with that photo.
4. You see it in the sidebar of `main.py`.
5. When you click **Export**, `pdf_exporter.py` reads the data from `models.py` and creates your final PDF.
6. If you're stuck, you open the **AI Assistant** (`ai_window.py`), which uses `ai_client.py` to get help from your local computer's AI.

---

## 🛠️ For the "Tinkerer" (What to improve/change)

If you want to play with the code, here is a quick guide:

| If you want to change... | Look in this file | Look for this function/class |
| :--- | :--- | :--- |
| **PDF Background Color** | `pdf_exporter.py` | `pdf.set_fill_color` |
| **Default Font Size** | `models.py` | `Element.__init__` (style dict) |
| **AI Model Name** | `ai_client.py` | `AIClient.__init__` |
| **Button Colors** | `main.py` | `setup_ui` sections |
| **Screenshot Quality** | `screenshot_manager.py` | `capture_screen` |

---

## 📓 The Project Journal (Development History)

### Phase 1: The Core (v1.0)
We focused on the "Standard" features. We implemented the `.acp` file format so you can save your progress and come back later. We also solved the "Unicode Problem"—ensuring that special characters like math symbols or emojis don't break the PDF.

### Phase 2: The AI Integration
We initially tried to put the AI inside the main window, but it made the screen feel cramped. We decided to move it to a **Separate Toplevel Window**. This was a big win for usability.

### Phase 3: Stability & Polish
We noticed that local AI can be slow. We added "Context Trimming" (sending only the last 8 messages) so the AI doesn't get confused by long conversations. We also added a "Thinking..." indicator so the user knows the app hasn't crashed.

---

## 🚀 How to Run
1. Install Python.
2. Install requirements: `pip install fpdf2 pillow mss`.
3. (Optional) Run **LM Studio** on port 1234 for the AI features.
4. Run `python main.py`.

---

**Built with ❤️ for students, by a pair of developers who hate manual formatting.**
