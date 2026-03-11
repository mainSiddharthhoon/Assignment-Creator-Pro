import tkinter as tk
from tkinter import messagebox, ttk
import json
import os
import datetime
import threading
from ai_client import AIClient

class ConversationManager:
    """Manages chat history and sessions in JSON."""
    def __init__(self, history_file="ai_history.json"):
        self.history_file = history_file
        self.sessions = self._load_history()
        self.current_session_id = None

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading AI history: {e}")
                return {}
        return {}

    def _save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.sessions, f, indent=4)
        except Exception as e:
            print(f"Error saving AI history: {e}")

    def create_session(self, title):
        """Creates a new session with a specific title."""
        session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.sessions[session_id] = {
            "title": title,
            "created_at": datetime.datetime.now().isoformat(),
            "messages": []
        }
        self.current_session_id = session_id
        self._save_history()
        return session_id

    def add_message(self, role, content):
        """Adds a message to the current session. Must have a session ID."""
        if not self.current_session_id:
            return None # Should be handled by UI
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.sessions[self.current_session_id]["messages"].append(message)
        self._save_history()
        return message

    def get_session_history(self, session_id):
        return self.sessions.get(session_id, {}).get("messages", [])

    def get_all_sessions(self):
        """Returns a list of sessions sorted by date."""
        sessions = []
        for sid, sdata in self.sessions.items():
            sessions.append({
                "id": sid, 
                "title": sdata.get("title", "Untitled Chat"), 
                "time": sid
            })
        return sorted(sessions, key=lambda x: x['time'], reverse=True)

    def delete_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]
            if self.current_session_id == session_id:
                self.current_session_id = None
            self._save_history()

    def clear_current_session(self):
        if self.current_session_id:
            self.sessions[self.current_session_id]["messages"] = []
            self._save_history()

class AIWindow(tk.Toplevel):
    """Independent AI Assistant window using tk.Toplevel."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("AI Assistant - Assignment Creator Pro")
        self.geometry("900x700")
        self.minsize(700, 500)
        self.configure(bg="#f8f9fa")
        
        # Data Manager & Client
        self.manager = ConversationManager()
        self.ai_client = AIClient()
        self.sessions_data = []
        self.is_thinking = False
        
        self.setup_ui()
        
        # Load most recent session if available
        all_sessions = self.manager.get_all_sessions()
        if all_sessions:
            self.on_session_selected_by_id(all_sessions[0]["id"])
        else:
            self.new_chat() # Start with fresh UI

    def setup_ui(self):
        # Main container with PanedWindow
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#f8f9fa", sashrelief=tk.RAISED, sashwidth=4)
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        # 1. Left Sidebar: Conversation List
        self.sidebar = tk.Frame(self.paned, bg="#e9ecef", width=250)
        self.sidebar.pack_propagate(False)
        self.paned.add(self.sidebar, width=250)
        
        tk.Label(self.sidebar, text="CONVERSATIONS", bg="#e9ecef", font=("Segoe UI", 9, "bold"), fg="#495057").pack(pady=10)
        
        self.session_listbox = tk.Listbox(self.sidebar, font=("Segoe UI", 10), bg="white", bd=0, highlightthickness=1, highlightcolor="#dee2e6")
        self.session_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.session_listbox.bind("<<ListboxSelect>>", self.on_session_selected)
        
        btn_frame = tk.Frame(self.sidebar, bg="#e9ecef")
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(btn_frame, text="+ New Chat", command=self.new_chat, bg="#28a745", fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=10).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(btn_frame, text="Delete", command=self.delete_chat, bg="#dc3545", fg="white", font=("Segoe UI", 9), relief=tk.FLAT, padx=10).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        # 2. Right Side: Chat Area
        self.chat_main_frame = tk.Frame(self.paned, bg="white")
        self.paned.add(self.chat_main_frame)
        
        # Chat Display (Scrollable)
        self.chat_container = tk.Frame(self.chat_main_frame, bg="white")
        self.chat_container.pack(fill=tk.BOTH, expand=True)
        
        self.chat_display = tk.Text(self.chat_container, wrap=tk.WORD, font=("Segoe UI", 11), bg="white", bd=0, padx=20, pady=20, state=tk.DISABLED)
        self.chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar = tk.Scrollbar(self.chat_container, command=self.chat_display.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_display.config(yscrollcommand=self.scrollbar.set)
        
        # 3. Bottom: Input Area
        self.input_area = tk.Frame(self.chat_main_frame, bg="#f8f9fa", bd=1, relief=tk.SOLID)
        self.input_area.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=20)
        
        self.msg_input = tk.Text(self.input_area, height=4, font=("Segoe UI", 11), bd=0, padx=10, pady=10)
        self.msg_input.pack(fill=tk.X)
        self.msg_input.bind("<Return>", self.on_enter_pressed)
        
        actions = tk.Frame(self.input_area, bg="#f8f9fa", padx=10, pady=5)
        actions.pack(fill=tk.X)
        tk.Button(actions, text="Clear History", command=self.clear_chat, font=("Segoe UI", 9), bg="#6c757d", fg="white", relief=tk.FLAT).pack(side=tk.LEFT)
        self.send_btn = tk.Button(actions, text="Send Message", command=self.send_message, font=("Segoe UI", 10, "bold"), bg="#0078d4", fg="white", width=15, relief=tk.FLAT)
        self.send_btn.pack(side=tk.RIGHT)
        
        self.refresh_sessions()

    def on_enter_pressed(self, event):
        """Handle Enter to send, Shift+Enter for newline."""
        if event.state & 0x1: # Shift is pressed
            return # Let default behavior happen (insert newline)
        else:
            self.send_message()
            return "break" # Prevent default newline insertion

    def refresh_sessions(self):
        """Refreshes the sidebar list with title deduplication logic."""
        self.session_listbox.delete(0, tk.END)
        self.sessions_data = self.manager.get_all_sessions()
        
        title_counts = {}
        for s in self.sessions_data:
            base_title = s["title"]
            if base_title in title_counts:
                title_counts[base_title] += 1
                display_title = f"{base_title} ({title_counts[base_title]})"
            else:
                title_counts[base_title] = 1
                display_title = base_title
            
            self.session_listbox.insert(tk.END, display_title)

    def on_session_selected(self, event):
        selection = self.session_listbox.curselection()
        if selection:
            session_id = self.sessions_data[selection[0]]["id"]
            self.load_session(session_id)

    def on_session_selected_by_id(self, session_id):
        self.manager.current_session_id = session_id
        self.load_session(session_id)
        # Highlight in listbox
        for i, s in enumerate(self.sessions_data):
            if s["id"] == session_id:
                self.session_listbox.selection_set(i)
                break

    def load_session(self, session_id):
        self.manager.current_session_id = session_id
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
        history = self.manager.get_session_history(session_id)
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            self.append_message(role, msg["content"], msg["timestamp"])

    def append_message(self, role, content, timestamp=None, is_placeholder=False):
        self.chat_display.config(state=tk.NORMAL)
        
        # Prepare timestamp
        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%H:%M")
        else:
            try: timestamp = datetime.datetime.fromisoformat(timestamp).strftime("%H:%M")
            except: pass
            
        tag = role.lower()
        if is_placeholder:
            tag = "thinking"
        
        # Insert Role and Time Header
        header_tag = f"{tag}_header" if not is_placeholder else "thinking_header"
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "time")
        self.chat_display.insert(tk.END, f"{role}\n", header_tag)
        
        # Insert Content with margins
        msg_tag = tag
        if is_placeholder:
            self.chat_display.insert(tk.END, f"{content}\n\n", ("thinking", "placeholder"))
        else:
            self.chat_display.insert(tk.END, f"{content}\n\n", msg_tag)
        
        # Configure Styling Tags
        self.chat_display.tag_config("time", foreground="#adb5bd", font=("Segoe UI", 9))
        self.chat_display.tag_config("user_header", foreground="#0078d4", font=("Segoe UI", 10, "bold"))
        self.chat_display.tag_config("assistant_header", foreground="#28a745", font=("Segoe UI", 10, "bold"))
        self.chat_display.tag_config("thinking_header", foreground="#6c757d", font=("Segoe UI", 10, "italic"))
        
        # Simulated "Bubbles" using margins
        self.chat_display.tag_config("user", foreground="#212529", lmargin1=15, lmargin2=15, spacing1=5, spacing3=5)
        self.chat_display.tag_config("assistant", foreground="#212529", lmargin1=15, lmargin2=15, spacing1=5, spacing3=5)
        self.chat_display.tag_config("thinking", foreground="#6c757d", lmargin1=15, lmargin2=15, spacing1=5, spacing3=5, font=("Segoe UI", 10, "italic"))
        self.chat_display.tag_config("error", foreground="#dc3545", lmargin1=15, lmargin2=15, spacing1=5, spacing3=5, font=("Segoe UI", 10, "bold"))
        
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def send_message(self):
        if self.is_thinking: return # Prevent multiple sends
        
        text = self.msg_input.get("1.0", tk.END).strip()
        if not text: return # Prevent empty messages
        
        # 1. Handle New Session Creation (Lazy Creation)
        if self.manager.current_session_id is None:
            title = text[:50].replace("\n", " ").strip()
            if len(text) > 50: title += "..."
            self.manager.create_session(title)
            self.refresh_sessions()
            self.session_listbox.selection_clear(0, tk.END)
            self.session_listbox.selection_set(0)
        
        # 2. UI Updates
        self.msg_input.delete("1.0", tk.END)
        self.append_message("User", text)
        self.manager.add_message("user", text)
        
        # 3. Add Thinking Placeholder
        self.is_thinking = True
        self.send_btn.config(state=tk.DISABLED)
        self.append_message("Assistant", "Thinking...", is_placeholder=True)
        
        # 4. Start Background Thread for AI Response
        history = self.manager.get_session_history(self.manager.current_session_id)
        # Convert manager history to AIClient format
        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        
        threading.Thread(target=self._fetch_ai_response, args=(messages,), daemon=True).start()

    def _fetch_ai_response(self, messages):
        """Background thread worker for AI calls."""
        result = self.ai_client.get_completion(messages)
        # Schedule UI update in main thread
        self.after(0, lambda: self._update_ai_response_ui(result))

    def _update_ai_response_ui(self, result):
        """Safely update UI with AI response from main thread."""
        self._remove_placeholder()
        self.is_thinking = False
        self.send_btn.config(state=tk.NORMAL)
        
        if result["success"]:
            response_text = result["content"]
            self.append_message("Assistant", response_text)
            self.manager.add_message("assistant", response_text)
        else:
            error_msg = f"Error: {result['error']}\n\nPlease ensure LM Studio is running at http://127.0.0.1:1234"
            self.append_message("Assistant", error_msg)
            # Tag the error message with 'error' style
            self.chat_display.config(state=tk.NORMAL)
            # Find the last inserted text and tag it as error
            self.chat_display.tag_add("error", "end-3l", "end-1c")
            self.chat_display.config(state=tk.DISABLED)

    def _remove_placeholder(self):
        """Removes the 'Thinking...' placeholder from chat display."""
        self.chat_display.config(state=tk.NORMAL)
        # Find the range of the placeholder tag
        ranges = self.chat_display.tag_ranges("placeholder")
        if ranges:
            # We also want to remove the header (the line before the placeholder content)
            # The placeholder content starts at ranges[0]. The header is usually 2 lines before.
            start_idx = self.chat_display.index(f"{ranges[0]} - 2 lines")
            self.chat_display.delete(start_idx, tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def new_chat(self):
        """Clears the UI to prepare for a new conversation. Does NOT save until message sent."""
        if self.is_thinking: return
        self.manager.current_session_id = None
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.session_listbox.selection_clear(0, tk.END)
        self.msg_input.delete("1.0", tk.END)
        self.msg_input.focus_set()

    def delete_chat(self):
        if self.is_thinking: return
        selection = self.session_listbox.curselection()
        if not selection: return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this conversation?"):
            session_id = self.sessions_data[selection[0]]["id"]
            self.manager.delete_session(session_id)
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state=tk.DISABLED)
            self.refresh_sessions()
            
            all_sessions = self.manager.get_all_sessions()
            if all_sessions:
                self.on_session_selected_by_id(all_sessions[0]["id"])
            else:
                self.new_chat()

    def clear_chat(self):
        if self.is_thinking: return
        if self.manager.current_session_id and messagebox.askyesno("Confirm Clear", "Clear all messages in this conversation?"):
            self.manager.clear_current_session()
            self.load_session(self.manager.current_session_id)
