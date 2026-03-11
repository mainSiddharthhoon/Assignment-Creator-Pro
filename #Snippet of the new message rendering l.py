# Snippet of the new message rendering logic in ai_window.py
def append_message(self, role, content, timestamp=None):
    # ...
    # Insert Content with margins to simulate structure
    self.chat_display.insert(tk.END, f"{content}\n\n", tag)
    
    # Configure Styling Tags for role distinction
    self.chat_display.tag_config("user_header", foreground="#0078d4", font=("Segoe UI", 10, "bold"))
    self.chat_display.tag_config("assistant_header", foreground="#28a745", font=("Segoe UI", 10, "bold"))
    self.chat_display.tag_config("user", lmargin1=15, lmargin2=15, spacing1=5)