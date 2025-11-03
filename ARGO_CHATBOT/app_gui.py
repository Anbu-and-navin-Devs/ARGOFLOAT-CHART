import tkinter as tk
from tkinter import scrolledtext, ttk
from threading import Thread
import multiprocessing
import traceback

from brain import get_intelligent_answer
import visualizer
import pandas as pd
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None
import datetime
import json, os, io, zipfile
import sys
from statistics import mean, pstdev
import pyautogui

# Add imports for API server and map window launching
try:
    from api_server import start_api_server
except ImportError:
    start_api_server = None
try:
    from map_window import MapWindow
except ImportError:
    MapWindow = None
try:
    from tkintermapview import TkinterMapView
except ImportError:
    TkinterMapView = None

class ArgoGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FloatChat - Ocean Intelligence")
        self.configure(bg=visualizer.COLORS["bg_main"])
        self.colors = visualizer.COLORS
        self.fonts = visualizer.FONTS
        self.minsize(1300, 850)
        self.resizable(True, True)
        self.state('zoomed')  # Start maximized
        # Paned window for resizable left/right panels
        self.LEFT_PANEL_WIDTH = 440
        # Store splitter so we can implement lock/unlock
        self.splitter = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=6, bg=self.colors["bg_main"], bd=0, relief=tk.FLAT)
        self.splitter.pack(fill=tk.BOTH, expand=True)
        self.left_panel = tk.Frame(self.splitter, bg=self.colors["bg_panel"], width=self.LEFT_PANEL_WIDTH)
        self.right_panel = tk.Frame(self.splitter, bg=self.colors["bg_panel"])  # dynamic
        self.splitter.add(self.left_panel, minsize=320)
        self.splitter.add(self.right_panel)
        # Initial lock state BEFORE building rest so event bindings can rely on it
        self.left_locked = True
        # Bind mouse drag attempts on sash to prevent resizing while locked
        self.splitter.bind('<B1-Motion>', self._maybe_block_sash)
        self.splitter.bind('<ButtonRelease-1>', self._maybe_block_sash)
        self._create_chat_panel(self.left_panel)
        # Prepare map + output but do NOT show until first query (hero welcome instead)
        self.map_container = tk.Frame(self.right_panel, bg=self.colors["bg_panel"])
        if TkinterMapView is not None:
            self.map_widget = TkinterMapView(self.map_container, corner_radius=0)
            self.map_widget.pack(fill="both", expand=True)
        else:
            self.map_widget = None
            tk.Label(self.map_container, text="Map component not available", bg=self.colors["bg_panel"], fg=self.colors["status_error"]).pack(pady=40)
        self.output_frame = tk.Frame(self.right_panel, bg=self.colors["bg_panel"], height=320)
        self.action_bar = tk.Frame(self.right_panel, bg=self.colors["bg_panel"], height=40)
        self._build_action_bar(self.action_bar)
        # Hero welcome screen
        self.welcome_mode = True
        self._build_hero_welcome()
        # SQL / Intent collapsible panel (hidden by default)
        self.sql_panel = tk.Frame(self.right_panel, bg=self.colors["bg_surface"], height=140)
        self.sql_visible = False
        # Status bar at bottom of left panel
        self.status_bar = tk.Frame(self.left_panel, bg=self.colors["bg_panel"], height=20)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = tk.Label(self.status_bar, text="Idle", anchor="w", font=("Segoe UI", 10), bg=self.colors["bg_panel"], fg=self.colors["text_light"])
        self.status_label.pack(side=tk.LEFT, padx=8)
        self.status_meta = tk.Label(self.status_bar, text="", anchor="e", font=("Segoe UI", 10), bg=self.colors["bg_panel"], fg=self.colors["text_light"])
        self.status_meta.pack(side=tk.RIGHT, padx=8)
        # Overlay for expanded data (hidden until needed)
        self.data_overlay = None
        # Internal flags
        self.map_fullscreen = False
        self.data_expanded = False
        self.last_query_text = None
        self.last_response = None
        self.last_sql = None
        self.last_enriched_summary = None
        self.last_fig = None
        self.last_canvas = None
        # Query history persistence
        self.history_file = "query_history.json"
        self.query_history = self._load_history()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._update_status("idle", "Idle")
        # Attempt dark native title bar (Windows) shortly after realization
        self.after(250, self._enable_dark_title_bar)
        # Finalize initial sash position (enforce lock after geometry settles)
        self.after(30, lambda: self.splitter.sash_place(0, self.LEFT_PANEL_WIDTH, 0))

    # No need for center_window anymore; window is resizable and user can move/resize as desired.

    def _create_chat_panel(self, parent):
        chat_frame = tk.Frame(parent, bg=self.colors["bg_panel"], bd=0, relief=tk.FLAT)
        self.chat_frame = chat_frame
        chat_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_bar = tk.Frame(chat_frame, bg=self.colors["bg_panel"])
        header_bar.pack(fill=tk.X, padx=15, pady=(20, 6))
        self.header_label = tk.Label(header_bar, text="FloatChat", font=("Segoe UI", 26, "bold"), bg=self.colors["bg_panel"], fg=self.colors["accent_primary"])
        self.header_label.pack(side=tk.LEFT, anchor="w")
        self.header_label.bind('<Button-1>', self._return_from_fullscreen_or_overlay)
        self.map_toggle_button = tk.Button(header_bar, text="Inter Map", command=self._toggle_map_mode, font=("Segoe UI", 11, "bold"),
                                           bg=self.colors["bg_panel"], fg=self.colors["button_text"], activebackground=self.colors["bg_panel"],
                                           activeforeground=self.colors["accent_primary"], relief=tk.FLAT, bd=0, highlightbackground=self.colors["neon_border"],
                                           highlightcolor=self.colors["neon_border"], highlightthickness=1, cursor="hand2", padx=14, pady=10)
        self.map_toggle_button.pack(side=tk.RIGHT, anchor="e")
        # Left panel lock button (sash already locked initially)
        self.lock_button = tk.Button(header_bar, text="🔒", font=("Segoe UI", 11), command=self._toggle_left_lock,
                                     bg=self.colors["bg_panel"], fg=self.colors["accent_primary"], relief=tk.FLAT, bd=0, cursor="hand2")
        self.lock_button.pack(side=tk.RIGHT, padx=(0,10))

        # Theme feature removed (placeholder for spacing if needed)

        # Subheader
        subheader_label = tk.Label(chat_frame, text="        How can I assist you?", font=("Segoe UI", 16), bg=self.colors["bg_panel"], fg=self.colors["text_light"], anchor="w", justify="left")
        subheader_label.pack(fill=tk.X, padx=18, pady=(0, 6))

        # Suggestions
        suggested_frame = tk.Frame(chat_frame, bg=self.colors["bg_panel"]); suggested_frame.pack(fill=tk.X, padx=10, pady=(0,4))
        top_sugg_bar = tk.Frame(suggested_frame, bg=self.colors["bg_panel"]); top_sugg_bar.pack(fill=tk.X)
        tk.Label(top_sugg_bar, text="Quick Suggestions", font=("Segoe UI", 12, "bold"), bg=self.colors["bg_panel"], fg=self.colors["text_light"]).pack(side=tk.LEFT, anchor="w")
        queries = [
            "Compare BGC parameters in the Arabian Sea for the last 6 months",
            "What are the nearest ARGO floats to CHENNAI?"
        ]
        btn_container = tk.Frame(suggested_frame, bg=self.colors["bg_panel"]); btn_container.pack(fill=tk.X)
        for i in range(2): btn_container.grid_columnconfigure(i, weight=1)
        for idx, q in enumerate(queries):
            btn = tk.Button(btn_container, text=q, command=lambda q=q: self._on_suggested_query(q), font=("Segoe UI", 11),
                            bg=self.colors["bg_panel"], fg=self.colors["button_text"], activebackground=self.colors["bg_panel"], activeforeground=self.colors["accent_primary"],
                            relief=tk.FLAT, bd=0, highlightbackground=self.colors["neon_border"], highlightcolor=self.colors["neon_border"], highlightthickness=1,
                            cursor="hand2", padx=10, pady=6, wraplength=190, justify="left")
            btn.grid(row=0, column=idx, padx=4, pady=2, sticky="ew")

        # History section
        self.history_header = tk.Frame(chat_frame, bg=self.colors["bg_panel"]); self.history_header.pack(fill=tk.X, padx=14, pady=(2,2))
        self.history_toggle = tk.Label(self.history_header, text="History ▸", font=("Segoe UI", 12, "bold"), bg=self.colors["bg_panel"], fg=self.colors["text_light"], cursor="hand2")
        self.history_toggle.pack(side=tk.LEFT); self.history_toggle.bind('<Button-1>', self._toggle_history_panel)
        self.history_panel = tk.Frame(chat_frame, bg=self.colors["bg_panel"]); self.history_open = False; self._refresh_history_ui()

        # Input frame
        input_frame = tk.Frame(chat_frame, bg=self.colors["bg_panel"])
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(4,10))
        input_frame.grid_columnconfigure(0, weight=1)
        self._placeholder_text = "Type your query and press Enter..."
        self.user_input = tk.Entry(input_frame, font=("Segoe UI", 13), relief=tk.FLAT, bd=0, fg=self.colors["text_light"], bg=self.colors["bg_main"],
                                   highlightbackground=self.colors["neon_border"], highlightcolor=self.colors["neon_border"], highlightthickness=2,
                                   insertbackground=self.colors["accent_primary"])
        self.user_input.grid(row=0, column=0, sticky="ew", ipady=10, padx=(0,6))
        self.user_input.insert(0, self._placeholder_text)
        self.user_input.bind('<FocusIn>', self._clear_placeholder)
        self.user_input.bind('<FocusOut>', self._restore_placeholder)
        self.user_input.bind('<Return>', lambda e: (self.send_message(), 'break'))
        self.send_button = tk.Button(input_frame, text="➤", command=self.send_message, font=("Segoe UI", 13, "bold"), bg=self.colors["accent_primary"], fg=self.colors["bg_main"], relief=tk.FLAT, cursor='hand2', padx=16, pady=8)
        self.send_button.grid(row=0, column=1)

        # Chat history (packs above input)
        self.chat_history = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            state="disabled",
            font=("Segoe UI", 11),
            bg=self.colors["bg_chat"],
            fg=self.colors["text_dark"],
            relief=tk.FLAT,
            padx=14,
            pady=10,
            insertbackground=self.colors["accent_primary"]
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4,0))
        self.chat_history.tag_configure("user_message", font=("Segoe UI", 11, "bold"), foreground=self.colors["accent_primary"], spacing3=6)
        self.chat_history.tag_configure("bot_message", font=("Segoe UI", 11), foreground=self.colors["text_dark"], spacing3=6)
        self._show_welcome_message()
        self.map_expanded = False

    def _on_suggested_query(self, text):
        # Directly send preset message (no visible input box)
        self.send_message(preset_message=text)

    def _set_user_input(self, text):
        # Retained for compatibility if input is later restored
        if self.user_input:
            self._clear_placeholder()
            self.user_input.delete(0, tk.END)
            self.user_input.insert(0, text)
            self.user_input.focus()

    # Removed adaptive results panel logic. All output will be shown in self.output_frame below the map.

    def display_results(self, response_json):
        query_type = response_json.get("query_type", "General")
        data = response_json.get("data", [])
        summary = response_json.get("summary", "An error occurred.")
        sql = response_json.get("sql_query", "N/A")
        self.last_response = response_json
        self.last_sql = sql
        # Craft richer chat summary for user context
        enriched = self._compose_chat_summary(response_json, summary)
        self.last_enriched_summary = enriched
        self._display_message("FloatChat", enriched)
        # Add to query history (only user text, not system errors)
        if self.last_query_text:
            self._add_to_history(self.last_query_text)
        # Always update the map (safe check in case of closing)
        if hasattr(self, 'map_widget') and self.map_widget and self.map_widget.winfo_exists():
            try:
                visualizer.update_map_view(self.map_widget, data, query_type)
            except Exception:
                pass
        # Clear output frame
        for widget in self.output_frame.winfo_children():
            widget.destroy()
        # Error or no data
        if query_type == "Error" or not data:
            visualizer.create_error_display(self.output_frame, summary, sql)
            self._update_status("error", summary)
            return
        try:
            if query_type == "Statistic":
                container = tk.Frame(self.output_frame, bg=self.colors["bg_panel"])
                container.pack(fill="both", expand=True)
                container.grid_columnconfigure(0, weight=2)
                container.grid_columnconfigure(1, weight=1)
                container.grid_rowconfigure(0, weight=1)
                stat_frame = tk.Frame(container, bg=self.colors["bg_panel"])
                context_frame = tk.Frame(container, bg=self.colors["bg_panel"])
                stat_frame.grid(row=0, column=0, sticky="nsew")
                context_frame.grid(row=0, column=1, sticky="nsew")
                visualizer.create_statistic_card(stat_frame, data)
                visualizer.create_context_card(context_frame, summary, sql)
                self._update_action_bar(query_type, data)
            elif query_type == "Proximity":
                visualizer.create_table(self.output_frame, data)
                self._add_table_summary(self.output_frame, data)
                self._update_action_bar(query_type, data)
            elif query_type == "Trajectory":
                container = tk.Frame(self.output_frame, bg=self.colors["bg_panel"])
                container.pack(fill="both", expand=True)
                container.grid_columnconfigure(0, weight=1)
                container.grid_columnconfigure(1, weight=2)
                container.grid_rowconfigure(0, weight=1)
                summary_frame = tk.Frame(container, bg=self.colors["bg_panel"])
                table_frame = tk.Frame(container, bg=self.colors["bg_panel"])
                summary_frame.grid(row=0, column=0, sticky="nsew")
                table_frame.grid(row=0, column=1, sticky="nsew")
                visualizer.create_trajectory_summary_card(summary_frame, data)
                visualizer.create_table(table_frame, data)
                self._add_table_summary(table_frame, data)
                self._update_action_bar(query_type, data)
            elif query_type == "Profile":
                self._render_graph_static(self.output_frame, data, query_type)
                self._update_action_bar(query_type, data)
            elif query_type == "Time-Series":
                container = tk.Frame(self.output_frame, bg=self.colors["bg_panel"])
                container.pack(fill="both", expand=True)
                container.grid_columnconfigure(0, weight=3)
                container.grid_columnconfigure(1, weight=1)
                container.grid_rowconfigure(0, weight=1)
                graph_frame = tk.Frame(container, bg=self.colors["bg_panel"])
                stats_frame = tk.Frame(container, bg=self.colors["bg_panel"])
                graph_frame.grid(row=0, column=0, sticky="nsew")
                stats_frame.grid(row=0, column=1, sticky="nsew")
                self._render_graph_static(graph_frame, data, query_type)
                visualizer.create_summary_stats_cards(stats_frame, data)
                self._update_action_bar(query_type, data)
            elif query_type == "Scatter":
                self._render_graph_static(self.output_frame, data, query_type)
                self._update_action_bar(query_type, data)
            else:
                visualizer.create_table(self.output_frame, data)
                self._add_table_summary(self.output_frame, data)
                self._update_action_bar(query_type, data)
        except Exception as e:
            visualizer.create_error_display(self.output_frame, f"Display error: {str(e)}", sql)
        # Success status update
        self._update_status("success", f"{query_type} OK", rows=len(data))
        # Force action bar ordering every query
        self._ensure_action_bar()
        if getattr(self,'data_expanded', False):
            self._update_overlay_action_bar()
        # If SQL panel visible refresh its content
        if self.sql_visible:
            self._render_sql_panel()
    def _add_export_buttons(self, parent, data, query_type=None, summary_text=None):
        # Legacy call path: now simply update the persistent bar.
        self._update_action_bar(query_type, data)

    def _build_action_bar(self, parent):
        pad = 6
        self.btn_csv = tk.Button(parent, text="Data CSV", command=lambda: self._export_csv(self.last_response.get('data', []) if self.last_response else []), bg=self.colors["accent_secondary"], fg="white", font=self.fonts["body_bold"], relief=tk.FLAT)
        self.btn_xlsx = tk.Button(parent, text="XLSX", command=lambda: self._export_xlsx(self.last_response.get('data', []) if self.last_response else []), bg=self.colors["accent_secondary"], fg="white", font=self.fonts["body_bold"], relief=tk.FLAT)
        self.btn_viz = tk.Button(parent, text="Viz PNG", command=lambda: self._export_visual_only_png(self.last_response.get('query_type') if self.last_response else ''), bg=self.colors["accent_primary"], fg="white", font=self.fonts["body_bold"], relief=tk.FLAT)
        self.btn_full = tk.Button(parent, text="Full Shot", command=self._export_full_context_png, bg=self.colors["accent_primary"], fg="white", font=self.fonts["body_bold"], relief=tk.FLAT)
        self.btn_bundle = tk.Button(parent, text="Bundle ZIP", command=self._export_report_bundle, bg=self.colors["accent_secondary"], fg="white", font=self.fonts["body_bold"], relief=tk.FLAT)
        self.btn_map = tk.Button(parent, text="Map ⛶", command=self._toggle_map_fullscreen, bg=self.colors["bg_panel"], fg=self.colors["accent_primary"], font=self.fonts["body_bold"], relief=tk.FLAT)
        self.btn_expand = tk.Button(parent, text="Expand ⤢", command=self._toggle_data_expanded, bg=self.colors["bg_panel"], fg=self.colors["accent_primary"], font=self.fonts["body_bold"], relief=tk.FLAT)
        self.btn_sql = tk.Button(parent, text="SQL", command=self._toggle_sql_panel, bg=self.colors["bg_panel"], fg=self.colors["accent_primary"], font=self.fonts["body_bold"], relief=tk.FLAT)
        self.btn_help = tk.Button(parent, text="?", command=self._show_help, bg=self.colors["bg_panel"], fg=self.colors["accent_primary"], font=self.fonts["body_bold"], relief=tk.FLAT)
        for b in [self.btn_csv, self.btn_xlsx, self.btn_viz, self.btn_full, self.btn_bundle, self.btn_map, self.btn_expand, self.btn_sql]:
            b.pack(side="left", padx=pad)
        self.btn_help.pack(side="right", padx=pad)

    def _update_action_bar(self, query_type, data):
        if not hasattr(self, 'action_bar'):
            return
        try:
            is_graph = query_type in ["Time-Series", "Profile", "Scatter"]
            is_stat = query_type == "Statistic"
            self.btn_csv.config(text="Data CSV" if (is_graph or is_stat) else "Table CSV", state=tk.NORMAL if data else tk.DISABLED,
                                command=lambda d=data: self._export_csv(d))
            if is_graph or is_stat:
                if self.btn_xlsx.winfo_ismapped():
                    self.btn_xlsx.pack_forget()
            else:
                if not self.btn_xlsx.winfo_ismapped():
                    self.btn_xlsx.pack(side="left", padx=6, before=self.btn_viz)
                self.btn_xlsx.config(state=tk.NORMAL if data else tk.DISABLED, command=lambda d=data: self._export_xlsx(d))
            self.btn_viz.config(command=lambda qt=query_type: self._export_visual_only_png(qt))
            self.btn_full.config(state=tk.NORMAL if data else tk.DISABLED)
            self.btn_bundle.config(state=tk.NORMAL if data else tk.DISABLED)
            self.btn_expand.config(state=tk.NORMAL if data else tk.DISABLED)
            # Always allow SQL button once any response processed (even if placeholder SQL)
            self.btn_sql.config(state=tk.NORMAL if self.last_response else tk.DISABLED)
            self.btn_map.config(text="Map ⛶" if not self.map_fullscreen else "Map ↩")
        except Exception:
            pass

    def _build_overlay_action_bar(self, parent):
        pad = 6
        self.ov_btn_csv = tk.Button(parent, text="Data CSV", command=lambda: self._export_csv(self.last_response.get('data', []) if self.last_response else []), bg=self.colors["accent_secondary"], fg="white", font=self.fonts["body_bold"], relief=tk.FLAT)
        self.ov_btn_xlsx = tk.Button(parent, text="XLSX", command=lambda: self._export_xlsx(self.last_response.get('data', []) if self.last_response else []), bg=self.colors["accent_secondary"], fg="white", font=self.fonts["body_bold"], relief=tk.FLAT)
        self.ov_btn_viz = tk.Button(parent, text="Viz PNG", command=lambda: self._export_visual_only_png(self.last_response.get('query_type') if self.last_response else ''), bg=self.colors["accent_primary"], fg="white", font=self.fonts["body_bold"], relief=tk.FLAT)
        self.ov_btn_full = tk.Button(parent, text="Full Shot", command=self._export_full_context_png, bg=self.colors["accent_primary"], fg="white", font=self.fonts["body_bold"], relief=tk.FLAT)
        self.ov_btn_bundle = tk.Button(parent, text="Bundle ZIP", command=self._export_report_bundle, bg=self.colors["accent_secondary"], fg="white", font=self.fonts["body_bold"], relief=tk.FLAT)
        self.ov_btn_map = tk.Button(parent, text="Map ⛶", command=self._toggle_map_fullscreen, bg=self.colors["bg_panel"], fg=self.colors["accent_primary"], font=self.fonts["body_bold"], relief=tk.FLAT)
        self.ov_btn_expand = tk.Button(parent, text="Collapse ↩", command=self._toggle_data_expanded, bg=self.colors["bg_panel"], fg=self.colors["accent_primary"], font=self.fonts["body_bold"], relief=tk.FLAT)
        self.ov_btn_sql = tk.Button(parent, text="SQL", command=self._toggle_sql_panel, bg=self.colors["bg_panel"], fg=self.colors["accent_primary"], font=self.fonts["body_bold"], relief=tk.FLAT)
        self.ov_btn_help = tk.Button(parent, text="?", command=self._show_help, bg=self.colors["bg_panel"], fg=self.colors["accent_primary"], font=self.fonts["body_bold"], relief=tk.FLAT)
        for b in [self.ov_btn_csv, self.ov_btn_xlsx, self.ov_btn_viz, self.ov_btn_full, self.ov_btn_bundle, self.ov_btn_map, self.ov_btn_expand, self.ov_btn_sql]:
            b.pack(side="left", padx=pad)
        self.ov_btn_help.pack(side="right", padx=pad)

    def _update_overlay_action_bar(self):
        if not (getattr(self,'data_expanded', False) and getattr(self,'data_overlay', None) and self.data_overlay.winfo_exists() and hasattr(self,'ov_btn_csv')):
            return
        if not self.last_response:
            return
        try:
            qt = self.last_response.get('query_type')
            data = self.last_response.get('data', [])
            is_graph = qt in ["Time-Series", "Profile", "Scatter"]
            is_stat = qt == "Statistic"
            self.ov_btn_csv.config(text="Data CSV" if (is_graph or is_stat) else "Table CSV", state=tk.NORMAL if data else tk.DISABLED, command=lambda d=data: self._export_csv(d))
            if is_graph or is_stat:
                if self.ov_btn_xlsx.winfo_ismapped():
                    self.ov_btn_xlsx.pack_forget()
            else:
                if not self.ov_btn_xlsx.winfo_ismapped():
                    self.ov_btn_xlsx.pack(side="left", padx=6, before=self.ov_btn_viz)
                self.ov_btn_xlsx.config(state=tk.NORMAL if data else tk.DISABLED, command=lambda d=data: self._export_xlsx(d))
            self.ov_btn_viz.config(command=lambda qt=qt: self._export_visual_only_png(qt), state=tk.NORMAL if data else tk.DISABLED)
            for btn in [self.ov_btn_full, self.ov_btn_bundle]:
                btn.config(state=tk.NORMAL if data else tk.DISABLED)
            self.ov_btn_sql.config(state=tk.NORMAL if self.last_sql else tk.DISABLED)
            self.ov_btn_map.config(text="Map ⛶" if not self.map_fullscreen else "Map ↩")
        except Exception:
            pass

    # Ensure persistent action bar is always packed directly after output_frame
    def _ensure_action_bar(self):
        if getattr(self, 'welcome_mode', False):
            return
        if not hasattr(self, 'action_bar'):
            return
        try:
            # Force output frame to occupy all remaining space, bar fixed to bottom
            self.action_bar.pack_forget()
            if self.output_frame.winfo_manager():
                self.output_frame.pack_forget()
            self.output_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0,4))
            self.action_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(4,8))
        except Exception:
            pass
        if getattr(self,'data_expanded', False):
            self._update_overlay_action_bar()

    def _export_csv(self, data):
        from tkinter import filedialog, messagebox
        if not data:
            messagebox.showinfo("Export CSV", "No data to export.")
            return
        df = pd.DataFrame(data)
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            df.to_csv(file_path, index=False)
            # self._update_status(f"Exported CSV to {file_path}")

    def _export_xlsx(self, data):
        from tkinter import filedialog, messagebox
        if not data:
            messagebox.showinfo("Export XLSX", "No data to export.")
            return
        df = pd.DataFrame(data)
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[["Excel Workbook", "*.xlsx"]])
        if file_path:
            try:
                df.to_excel(file_path, index=False)
            except Exception as e:
                messagebox.showerror("Export XLSX", f"Failed: {e}")

    def _export_visual_only_png(self, query_type):
        """Export only the visualization region (graph/table/stat card) at current resolution.
        For graphs: if last_fig available, save high-quality figure directly; else fallback to canvas screenshot.
        """
        from tkinter import filedialog, messagebox
        target_widget = None
        # Try figure save path for graphs
        if query_type in ["Time-Series", "Profile", "Scatter"] and hasattr(self, 'last_fig') and self.last_fig:
            file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[["PNG files","*.png"]], title="Save Graph Image")
            if not file_path:
                return
            try:
                self.last_fig.savefig(file_path, facecolor=self.last_fig.get_facecolor(), dpi=180)
                return
            except Exception:
                pass  # fallback to screenshot
        # Locate a canvas or treeview inside output_frame
        for child in self.output_frame.winfo_children():
            # Drill down if container
            stack = [child]
            while stack:
                w = stack.pop()
                cls = str(w.__class__)
                if 'FigureCanvasTkAgg' in cls or isinstance(w, tk.Canvas):
                    target_widget = w
                    break
                if str(w.winfo_class()) == 'Treeview' or 'Treeview' in cls:
                    target_widget = w
                    break
                stack.extend(list(w.winfo_children()))
            if target_widget:
                break
        if not target_widget:
            messagebox.showinfo("Export", "No visualization widget found to export.")
            return
        x = target_widget.winfo_rootx(); y = target_widget.winfo_rooty()
        w = target_widget.winfo_width(); h = target_widget.winfo_height()
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[["PNG files","*.png"]], title="Save Visualization")
        if not file_path:
            return
        shot = pyautogui.screenshot(region=(x,y,w,h))
        shot.save(file_path)

    def _export_full_context_png(self):
        """Create a composite image with (left) query + AI reply text and (right) full right panel UI."""
        from tkinter import filedialog, messagebox
        if getattr(self,'welcome_mode', False):
            messagebox.showinfo("Export", "Nothing to export yet.")
            return
        # Capture right panel
        rp = self.right_panel
        rx, ry = rp.winfo_rootx(), rp.winfo_rooty()
        rw, rh = rp.winfo_width(), rp.winfo_height()
        right_img = pyautogui.screenshot(region=(rx, ry, rw, rh))
        # Prepare text block
        query_text = (self.last_query_text or "").strip()
        reply_text = (self.last_enriched_summary or (self.last_response.get('summary') if self.last_response else ''))
        from textwrap import wrap
        lines = []
        if query_text:
            lines.append("Query: " + query_text)
        if reply_text:
            lines.append("AI: " + reply_text)
        if Image is None:
            # Fallback: just save right panel plus no left text
            file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[["PNG files","*.png"]], title="Save Panel")
            if file_path:
                right_img.save(file_path)
            return
        font = None
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except Exception:
            font = ImageFont.load_default()
        # Wrap lines to fit width
        wrap_width = 46
        wrapped = []
        for l in lines:
            wrapped.extend(wrap(l, wrap_width))
            wrapped.append("")
        if wrapped and wrapped[-1] == "":
            wrapped.pop()
        line_height = 22
        pad = 14
        text_width = 420
        text_height = pad*2 + line_height*len(wrapped)
        composite_h = max(rh, text_height)
        composite_w = text_width + rw
        comp = Image.new("RGB", (composite_w, composite_h), (14,17,22))
        draw = ImageDraw.Draw(comp)
        y_cursor = pad
        for ln in wrapped:
            draw.text((pad, y_cursor), ln, fill=(230,237,243), font=font)
            y_cursor += line_height
        comp.paste(right_img, (text_width, 0))
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[["PNG files","*.png"]], title="Save Full Context Screenshot")
        if file_path:
            comp.save(file_path)

    def _export_png(self):
        """Backward compatibility: previously single PNG export. Now maps to full context export."""
        self._export_full_context_png()

    def _export_report_bundle(self):
        """Create a ZIP bundle: data.csv, summary.txt, viz.png, meta.json"""
        from tkinter import filedialog, messagebox
        if not self.last_response or not self.last_response.get('data'):
            messagebox.showinfo("Bundle Export", "No data to export.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[["ZIP files","*.zip"]], title="Save Report Bundle")
        if not file_path:
            return
        data = self.last_response.get('data', [])
        df = pd.DataFrame(data)
        meta = {
            "query": self.last_query_text,
            "query_type": self.last_response.get('query_type'),
            "rows": len(df),
            "generated_at": datetime.datetime.utcnow().isoformat()+"Z",
            "sql": self.last_sql
        }
        # Prepare visualization image bytes
        png_bytes = None
        if hasattr(self, 'last_fig') and self.last_fig is not None:
            buf = io.BytesIO()
            try:
                self.last_fig.savefig(buf, format='png', dpi=160, facecolor=self.last_fig.get_facecolor())
                png_bytes = buf.getvalue()
            except Exception:
                png_bytes = None
        if png_bytes is None:
            # fallback screenshot of right panel
            try:
                rx, ry = self.right_panel.winfo_rootx(), self.right_panel.winfo_rooty()
                rw, rh = self.right_panel.winfo_width(), self.right_panel.winfo_height()
                shot = pyautogui.screenshot(region=(rx, ry, rw, rh))
                buf = io.BytesIO()
                shot.save(buf, format='PNG')
                png_bytes = buf.getvalue()
            except Exception:
                png_bytes = b''
        try:
            with zipfile.ZipFile(file_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('data.csv', df.to_csv(index=False))
                zf.writestr('summary.txt', (self.last_enriched_summary or ''))
                zf.writestr('meta.json', json.dumps(meta, indent=2))
                zf.writestr('visualization.png', png_bytes)
        except Exception as e:
            messagebox.showerror("Bundle Export", f"Failed: {e}")

    # ---------------- History Persistence -----------------
    def _load_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.query_history[-50:], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _add_to_history(self, query):
        if not query:
            return
        if len(self.query_history) == 0 or self.query_history[-1] != query:
            self.query_history.append(query)
            if len(self.query_history) > 50:
                self.query_history = self.query_history[-50:]
            self._save_history()
            self._refresh_history_ui()

    def _toggle_history_panel(self, event=None):
        self.history_open = not self.history_open
        self.history_toggle.config(text=f"History {'▾' if self.history_open else '▸'}")
        self._refresh_history_ui()

    def _refresh_history_ui(self):
        # Clear
        for w in self.history_panel.winfo_children():
            w.destroy()
        if self.history_open:
            self.history_panel.pack(fill=tk.X, padx=14, pady=(0,4))
            recent = self.query_history[-8:][::-1]
            for q in recent:
                btn = tk.Button(self.history_panel, text=q[:60], command=lambda q=q: self.send_message(preset_message=q), anchor='w', justify='left', wraplength=360,
                                bg=self.colors['bg_main'], fg=self.colors['button_text'], relief=tk.FLAT, bd=0, cursor='hand2', font=("Segoe UI",11))
                btn.pack(fill=tk.X, pady=1)
        else:
            self.history_panel.pack_forget()

    # ---------------- Theme Handling -----------------
    def _toggle_theme(self):
        self.theme_mode = 'high_contrast' if self.theme_mode == 'dark' else 'dark'
        self.colors = self.themes[self.theme_mode]
        # Minimal reapply: update major frame backgrounds & chat history colors
        try:
            for f in [self, self.left_panel, self.right_panel, getattr(self,'map_container',None), getattr(self,'output_frame',None)]:
                if f and f.winfo_exists():
                    f.configure(bg=self.colors['bg_panel'])
            self.chat_history.configure(bg=self.colors['bg_chat'])
            self.header_label.configure(fg=self.colors['accent_primary'])
            self.theme_toggle_btn.configure(bg=self.colors['bg_panel'])
        except Exception:
            pass


    def _add_table_summary(self, parent, data):
        """Add a compact summary line under a table: row count, float count, time span if present."""
        try:
            import pandas as _pd
            df = _pd.DataFrame(data)
            if df.empty:
                return
            parts = [f"rows: {len(df)}"]
            if 'float_id' in df.columns:
                parts.append(f"floats: {df['float_id'].nunique()}")
            time_col = None
            for c in ['timestamp','day']:
                if c in df.columns:
                    time_col = c; break
            if time_col:
                try:
                    t = _pd.to_datetime(df[time_col])
                    if not t.empty:
                        parts.append(f"range: {t.min().date()} → {t.max().date()}")
                except Exception:
                    pass
            bar = tk.Frame(parent, bg=self.colors['bg_panel'])
            bar.pack(fill=tk.X, padx=10, pady=(0,4))
            tk.Label(bar, text=" | ".join(parts), font=("Segoe UI",9), anchor='w', bg=self.colors['bg_panel'], fg=self.colors['text_light']).pack(side=tk.LEFT)
        except Exception:
            pass

    def _compose_chat_summary(self, response_json, base_summary:str) -> str:
        """Enhance AI reply with contextual metadata for clarity."""
        try:
            qtype = response_json.get('query_type')
            data = response_json.get('data') or []
            meta_parts = []
            if data:
                df = pd.DataFrame(data)
                meta_parts.append(f"rows={len(df)}")
                if 'timestamp' in df.columns:
                    try:
                        times = pd.to_datetime(df['timestamp'])
                        if not times.empty:
                            rng = f"{times.min().date()} → {times.max().date()}"
                            meta_parts.append(rng)
                    except Exception:
                        pass
                sensor_candidates = [c for c in df.columns if c.lower() not in ['latitude','longitude','float_id','timestamp','day','pressure','distance_km']]
                numeric = []
                for c in sensor_candidates:
                    try:
                        pd.to_numeric(df[c], errors='raise')
                        numeric.append(c)
                    except Exception:
                        continue
                if numeric:
                    meta_parts.append('sensors=' + ', '.join([n.replace('_',' ').title() for n in numeric[:4]]))
            header = f"{qtype} result" if qtype and qtype not in ['Error','General'] else "Result"
            meta_str = " | ".join(meta_parts)
            if meta_str:
                return f"{header} ({meta_str})\n{base_summary}".strip()
            return f"{header}\n{base_summary}".strip()
        except Exception:
            return base_summary

    def _show_help(self):
        from tkinter import messagebox
        messagebox.showinfo("Help", "Exports: CSV/XLSX, Viz PNG (visual only), Full Shot (query+AI+panel), Bundle ZIP (all assets). History panel shows recent queries. Theme button toggles high contrast. Drag splitter to resize panels. Time-Series insights auto-detect anomalies.")

    # Accessibility: keyboard shortcuts
    def bind_accessibility_shortcuts(self):
        self.bind('<Control-e>', lambda e: self._export_csv([]))
        self.bind('<Control-p>', lambda e: self._export_png())
        self.bind('<Control-h>', lambda e: self._show_help())
        self.bind('<Control-t>', lambda e: self._set_theme("dark"))
        self.bind('<Control-l>', lambda e: self._set_theme("light"))
        self.bind('<Control-f>', lambda e: self._set_font("large"))
        self.bind('<Control-d>', lambda e: self._set_font("default"))
        self.bind('<Control-m>', lambda e: self._toggle_map_mode())
        # Removed obsolete compose bar shortcut


    def _toggle_map_mode(self):
        """Toggle between normal layout and expanded interactive map view OR launch full MapWindow."""
        # Always allow launching (if already open bring to front)
        if MapWindow is not None:
            if getattr(self, 'external_map_ref', None) and self.external_map_ref.winfo_exists():
                try:
                    self.external_map_ref.lift(); self.external_map_ref.focus_force()
                    return
                except Exception:
                    pass
            self._launch_external_map()
            return
        if not hasattr(self, 'map_widget'):
            return
        if not getattr(self, 'map_expanded', False):
            # Expand map: hide output frame
            if self.output_frame.winfo_ismapped():
                self.output_frame.pack_forget()
            self.map_toggle_button.config(text="Show Results")
            self.map_expanded = True
        else:
            # Restore output frame
            if not self.output_frame.winfo_ismapped():
                self.output_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0,12))
            self.map_toggle_button.config(text="Interactive Map")
            self.map_expanded = False
    
    def _launch_external_map(self):
        """Launch the separate MapWindow and ensure API server is running."""
        # Start API server in background process once
        if not hasattr(self, 'api_process') or self.api_process is None or not self.api_process.is_alive():
            if start_api_server is not None:
                self.api_process = multiprocessing.Process(target=start_api_server, kwargs={"debug": False})
                self.api_process.daemon = True
                self.api_process.start()
        # Create map window
        if MapWindow is not None:
            try:
                self._update_status("running", "Opening interactive map…")
                win = MapWindow(self)
            except Exception as e:
                self._update_status("error", f"Map failed: {e}")
                return
            self.external_map_ref = win
            win.protocol("WM_DELETE_WINDOW", lambda w=win: self._on_external_map_close(w))
            self._update_status("success", "Map window open")

    def _on_external_map_close(self, window):
        try:
            window.on_closing()
        finally:
            if getattr(self, 'external_map_ref', None) is window:
                self.external_map_ref = None

    def send_message(self, event=None, preset_message=None):
        if preset_message is not None:
            message = preset_message.strip()
        else:
            if not self.user_input:
                return
            raw = self.user_input.get().strip()
            if raw == "" or raw == self._placeholder_text:
                return
            message = raw
        if not message:
            return
        # Activate hero -> main layout on first real query
        if getattr(self, 'welcome_mode', False):
            self._activate_from_hero()
        self._display_message("You", message)
        if self.user_input:
            self.user_input.delete(0, tk.END)
            self.user_input.config(state="disabled")
        if self.send_button:
            self.send_button.config(state="disabled")
        # Show a temporary 'Querying...' message in chat
        self.chat_history.config(state="normal")
        self.chat_history.insert(tk.END, "FloatChat is thinking...\n", "bot_message")
        self.chat_history.config(state="disabled"); self.chat_history.yview(tk.END)
        self.last_query_text = message
        self._update_status("running", "Querying…")
        Thread(target=self._get_ai_response, args=(message,), daemon=True).start()

    def _get_ai_response(self, message):
        try:
            response_json = get_intelligent_answer(message)
            self.after(0, self.display_results, response_json)
        except Exception as e:
            error_response = {"query_type": "Error", "summary": f"A critical error occurred: {e}", "sql_query": "N/A"}
            self.after(0, self.display_results, error_response)
        finally:
            self.after(0, self._reenable_input)

    # ---------------- Status / SQL / Expansion Helpers -----------------
    def _update_status(self, state, message, rows=None, latency=None):
        color_map = {
            "idle": self.colors["status_idle"],
            "running": self.colors["status_running"],
            "success": self.colors["status_success"],
            "error": self.colors["status_error"],
        }
        fg = color_map.get(state, self.colors["text_light"])
        self.status_label.config(text=message, fg=fg)
        meta_parts = []
        if rows is not None:
            meta_parts.append(f"rows: {rows}")
        if latency is not None:
            meta_parts.append(f"{latency} ms")
        self.status_meta.config(text=" | ".join(meta_parts))

    def _toggle_sql_panel(self):
        self.sql_visible = not self.sql_visible
        if self.sql_visible and not self.last_sql:
            self.last_sql = "-- No SQL generated yet. Ask a data question to see the translated query."
        if self.sql_visible:
            self._render_sql_panel()
            # Re-pack ordering to ensure SQL sits above action bar consistently
            try:
                self.sql_panel.pack_forget(); self.action_bar.pack_forget()
                if self.output_frame.winfo_manager():
                    self.output_frame.pack_forget()
                self.output_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0,4))
                self.sql_panel.pack(fill=tk.X, padx=12, pady=(0,8))
                self.action_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(4,8))
            except Exception:
                self.sql_panel.pack(fill=tk.X, padx=12, pady=(0,8))
        else:
            for w in self.sql_panel.winfo_children():
                w.destroy()
            self.sql_panel.pack_forget()
            self._ensure_action_bar()

    def _render_sql_panel(self):
        for w in self.sql_panel.winfo_children():
            w.destroy()
        hdr = tk.Frame(self.sql_panel, bg=self.colors["bg_surface"])
        hdr.pack(fill=tk.X, pady=(6,2), padx=8)
        tk.Label(hdr, text="SQL Query", font=("Segoe UI", 12, "bold"), bg=self.colors["bg_surface"], fg=self.colors["accent_primary"]).pack(side=tk.LEFT)
        if self.last_query_text:
            tk.Button(hdr, text="Re-run", command=lambda: self.send_message(preset_message=self.last_query_text), bg=self.colors["bg_panel"], fg=self.colors["accent_primary"], relief=tk.FLAT).pack(side=tk.RIGHT, padx=4)
        tk.Button(hdr, text="Copy", command=self._copy_sql, bg=self.colors["bg_panel"], fg=self.colors["accent_primary"], relief=tk.FLAT).pack(side=tk.RIGHT, padx=4)
        sql_box = tk.Text(self.sql_panel, height=6, wrap=tk.NONE, font=("Consolas", 11), bg=self.colors["bg_panel"], fg=self.colors["text_dark"], insertbackground=self.colors["accent_primary"])
        sql_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,8))
        sql_text = self.last_sql or "No SQL generated yet."
        sql_box.insert("1.0", sql_text)
        sql_box.config(state="disabled")

    def _copy_sql(self):
        if not self.last_sql:
            return
        self.clipboard_clear()
        # Fixed: actually add SQL text to clipboard
        try:
            self.clipboard_append(self.last_sql)
        except Exception:
            self._update_status("success", "SQL copied")

    def _toggle_map_fullscreen(self):
        """Fullscreen the map_container only (graph & bar hidden) or restore."""
        if self.data_expanded:
            self._toggle_data_expanded()
        if not self.map_fullscreen:
            if self.output_frame.winfo_ismapped():
                self.output_frame.pack_forget()
            if self.action_bar.winfo_ismapped():
                self.action_bar.pack_forget()
            if self.sql_visible:
                self._toggle_sql_panel()
            self.map_fullscreen = True
            self.map_container.pack_forget()
            self.map_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
            self.header_label.config(text="← FloatChat (Return)")
        else:
            self.map_container.pack_forget()
            self.map_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
            if not self.output_frame.winfo_ismapped():
                self.output_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0,4))
            self._ensure_action_bar()
            self.map_fullscreen = False
            self.header_label.config(text="FloatChat")
        self._update_status("idle", "Map fullscreen" if self.map_fullscreen else "Idle")
        if self.last_response:
            self._update_action_bar(self.last_response.get('query_type'), self.last_response.get('data', []))

    def _toggle_data_expanded(self):
        if self.map_fullscreen:
            self._toggle_map_fullscreen()
        if not self.data_expanded:
            self.data_expanded = True
            self._create_data_overlay()
        else:
            self._destroy_data_overlay()
            self.data_expanded = False
        self._update_status("idle", "Data expanded" if self.data_expanded else "Idle")
        if self.last_response:
            try:
                self._update_action_bar(self.last_response.get('query_type'), self.last_response.get('data', []))
            except Exception:
                pass
        self._ensure_action_bar()

    def _create_data_overlay(self):
        if self.data_overlay and self.data_overlay.winfo_exists():
            return
        # Sanitize alpha hex if present (Tk does not support #RRGGBBAA)
        ov_color = self._sanitize_color(self.colors.get("overlay_bg", "#000000"))
        self.data_overlay = tk.Frame(self.right_panel, bg=ov_color)
        self.data_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        inner = tk.Frame(self.data_overlay, bg=self.colors["bg_surface"], bd=1, relief=tk.FLAT)
        inner.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)
        topbar = tk.Frame(inner, bg=self.colors["bg_surface"])
        topbar.pack(fill=tk.X, pady=(8,4), padx=10)
        tk.Label(topbar, text="Expanded View", font=("Segoe UI", 14, "bold"), bg=self.colors["bg_surface"], fg=self.colors["accent_primary"]).pack(side=tk.LEFT)
        tk.Button(topbar, text="Close ✕", command=self._toggle_data_expanded, bg=self.colors["bg_panel"], fg=self.colors["accent_primary"], relief=tk.FLAT).pack(side=tk.RIGHT, padx=6)
        # Clone current output frame content by re-rendering last response
        content = tk.Frame(inner, bg=self.colors["bg_panel"])
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        if self.last_response:
            qt = self.last_response.get("query_type")
            data = self.last_response.get("data", [])
            try:
                if qt in ["Time-Series", "Profile", "Scatter"]:
                    fig, ax, canvas = visualizer.create_graph(content, data, qt)
                    self.last_fig = fig; self.last_canvas = canvas
                    if hasattr(self, '_attach_matplotlib_toolbar'):
                        self._attach_matplotlib_toolbar(content, canvas, position='top', light_theme=True)
                elif qt == "Statistic":
                    visualizer.create_statistic_card(content, data)
                else:
                    visualizer.create_table(content, data)
            except Exception:
                visualizer.create_error_display(content, "Could not expand view", self.last_sql or "")
        else:
            tk.Label(content, text="No content to expand yet.", bg=self.colors["bg_panel"], fg=self.colors["text_light"]).pack(pady=20)
        # Overlay action bar at bottom
        overlay_bar = tk.Frame(inner, bg=self.colors["bg_surface"])
        overlay_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(4,2))
        self._build_overlay_action_bar(overlay_bar)
        self._update_overlay_action_bar()

    def _destroy_data_overlay(self):
        if self.data_overlay and self.data_overlay.winfo_exists():
            self.data_overlay.destroy()
        self.data_overlay = None

    def _sanitize_color(self, color: str) -> str:
        """Return a Tk-compatible color (strip alpha if provided as #RRGGBBAA)."""
        if isinstance(color, str) and color.startswith('#') and len(color) == 9:
            return color[:7]
        return color

    def _return_from_fullscreen_or_overlay(self, event=None):
        """Header click: exit fullscreen map or data expansion if active."""
        changed = False
        if self.data_expanded:
            self._toggle_data_expanded()
            changed = True
        if self.map_fullscreen:
            self._toggle_map_fullscreen()
            changed = True
        if changed:
            self._update_status("idle", "Returned")
    
    # ---------------- Additional helpers -----------------
    def _build_hero_welcome(self):
        self.hero_frame = tk.Frame(self.right_panel, bg=self.colors["bg_panel"])
        self.hero_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)
        banner = tk.Canvas(self.hero_frame, height=160, highlightthickness=0, bd=0, bg=self.colors["bg_panel"])
        banner.pack(fill=tk.X, pady=(0,25))
        for i in range(0,120):
            r = 14 + int((30-14)*i/120); g = 17 + int((40-17)*i/120); b = 22 + int((64-22)*i/120)
            banner.create_rectangle(0, i*160/120, 3000, (i+1)*160/120, outline="", fill=f"#{r:02x}{g:02x}{b:02x}")
        banner.create_text(40, 55, anchor="w", text="FloatChat Ocean Intelligence", font=("Segoe UI", 26, "bold"), fill=self.colors["text_dark"])
        banner.create_text(42, 108, anchor="w", text="Conversational ARGO Science & Operational Ocean Intelligence", font=("Segoe UI", 14), fill=self.colors["text_light"])
        tk.Label(self.hero_frame, text="Welcome to FloatChat Intelligence", font=("Segoe UI", 30, "bold"), bg=self.colors["bg_panel"], fg=self.colors["accent_primary"]).pack(anchor="w")
        desc = (
            "FloatChat now opens ready to query the freshest ARGO profiles in your database. Ask oceanographic questions in plain language and the assistant will translate them into verified SQL, run the query, and stream back curated datasets with visuals—no scripts required.\n\n"
            "Use the chat panel on the left to start right away. As soon as you submit your first question, this overview collapses and the live map + analytics workspace takes over."
        )
        tk.Label(self.hero_frame, text=desc, font=("Segoe UI", 14), justify="left", wraplength=1150, bg=self.colors["bg_panel"], fg=self.colors["text_light"]).pack(anchor="w", pady=(12,16))
        bullets = [
            "Natural‑language to verified SQL with guardrails for ARGO intents",
            "Modes for Profiles, Time-Series, Trajectories, Proximity, Statistics, and Scatter",
            "Live map window with period filters, nearest-float lookup, and trajectory metrics",
            "Exports for CSV/XLSX data, visualization PNGs, and full analytical bundles",
            "Latest-dataset awareness—status bar reflects the current DB range",
            "Optional overlay view for expanded plots and Matplotlib toolbars",
            "High-contrast dark theme tuned for long analysis sessions"
        ]
        bl_frame = tk.Frame(self.hero_frame, bg=self.colors["bg_panel"])
        bl_frame.pack(anchor="w", fill=tk.X)
        for b in bullets:
            tk.Label(bl_frame, text="•  "+b, font=("Segoe UI", 13), bg=self.colors["bg_panel"], fg=self.colors["text_dark"], anchor="w", justify="left", wraplength=1150).pack(anchor="w", pady=1)

    def _activate_from_hero(self):
        if not getattr(self,'welcome_mode', False):
            return
        if hasattr(self,'hero_frame') and self.hero_frame.winfo_exists():
            self.hero_frame.destroy()
        # Re-pack primary UI elements now that hero screen is gone
        self.map_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.output_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0,4))
        self.action_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(4,8))
        self.welcome_mode = False
        # Final enforcement to guarantee action bar presence
        self._ensure_action_bar()

    def _render_graph_static(self, master_frame, data, query_type):
        # Draw graph only (no toolbar in compact output panel per user preference)
        fig, ax, canvas = visualizer.create_graph(master_frame, data, query_type)
        if query_type in ["Time-Series", "Profile", "Scatter"]:
            self.last_fig = fig; self.last_canvas = canvas
        return fig, ax, canvas

    def _render_graph_interactive(self, master_frame, data, query_type):
        # Expanded overlay variant: toolbar on top
        fig, ax, canvas = visualizer.create_graph(master_frame, data, query_type)
        if query_type in ["Time-Series", "Profile", "Scatter"]:
            self.last_fig = fig; self.last_canvas = canvas
        if hasattr(self, '_attach_matplotlib_toolbar'):
            self._attach_matplotlib_toolbar(master_frame, canvas, position='top', light_theme=False)
        return fig, ax, canvas

    def on_closing(self):
        # Prevent further UI updates during shutdown
        self.closing = True
        try:
            if hasattr(self, 'map_widget') and self.map_widget.winfo_exists():
                self.map_widget.destroy()
        except Exception:
            pass
        if hasattr(self, 'map_process') and self.map_process and self.map_process.is_alive():
            try:
                self.map_process.terminate()
            except Exception:
                pass
        # Terminate API process if we started it
        if hasattr(self, 'api_process') and self.api_process and self.api_process.is_alive():
            try:
                self.api_process.terminate()
            except Exception:
                pass
        self.after(50, self.destroy)

    def _display_message(self, sender, message):
        self.chat_history.config(state="normal")
        self.chat_history.insert(tk.END, f"{sender}:\n{message}\n\n", "user_message" if sender == "You" else "bot_message")
        self.chat_history.config(state="disabled")
        self.chat_history.yview(tk.END)

    def _show_welcome_message(self):
        self.chat_history.config(state="normal")
        self.chat_history.insert(tk.END, "Welcome to FloatChat AI!\n", "bot_message")
        self.chat_history.config(state="disabled")

    def _reenable_input(self):
        if self.user_input:
            self.user_input.config(state="normal")
            if self.send_button:
                self.send_button.config(state="normal")
            self._restore_placeholder()  # show placeholder if empty
            self.user_input.focus()

    # ---------------- Input helpers -----------------
    def _clear_placeholder(self, event=None):
        if not self.user_input:
            return
        if self.user_input.get().strip() == self._placeholder_text:
            self.user_input.delete(0, tk.END)
            self.user_input.config(fg=self.colors["text_dark"])

    def _restore_placeholder(self, event=None):
        if not self.user_input:
            return
        if self.user_input.get().strip() == "":
            self.user_input.insert(0, self._placeholder_text)
            self.user_input.config(fg=self.colors["text_light"])

    def _update_output_panel(self):
        # Only update if expanded and map_widget exists
        if not hasattr(self, 'latest_response_json'):
            return
        response_json = self.latest_response_json
        query_type = response_json.get("query_type", "General")
        data = response_json.get("data", [])
        visualizer.update_map_view(self.map_widget, data, query_type)
        # ...add other output panel visualizer calls as needed...
    def _attach_matplotlib_toolbar(self, parent, canvas, position='bottom', light_theme=False):
        """Attach a Matplotlib navigation toolbar to a FigureCanvasTk widget.
        position: 'top' inserts above the canvas; 'bottom' below. light_theme toggles bg color."""
        try:
            from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        except Exception:
            return
        bg = '#ffffff' if light_theme else self.colors.get('graph_toolbar_bg', '#2c3136')
        frame = tk.Frame(parent, bg=bg, bd=0, highlightthickness=0)
        target = canvas.get_tk_widget()
        if position == 'top':
            frame.pack(fill=tk.X, padx=8, pady=(4,4), before=target)
        else:
            frame.pack(fill=tk.X, padx=8, pady=(4,4))
        try:
            toolbar = NavigationToolbar2Tk(canvas, frame)
            toolbar.update()
            for child in toolbar.winfo_children():
                try: child.configure(bg=bg)
                except Exception: pass
            if hasattr(toolbar, '_message_label'):
                toolbar._message_label.config(bg=bg, fg=('#222' if light_theme else self.colors.get('text_light','#cccccc')))
        except Exception:
            def _redraw():
                try: canvas.draw()
                except Exception: pass
            tk.Button(frame, text='Redraw', command=_redraw, bg=bg, fg=('#222' if light_theme else self.colors.get('text_light','#cccccc')), relief=tk.FLAT).pack(side=tk.LEFT, padx=4)

    # ---------------- Left panel lock/unlock -----------------
    def _toggle_left_lock(self):
        self.left_locked = not getattr(self, 'left_locked', True)
        if self.left_locked:
            self.lock_button.config(text="🔒")
            # Snap sash now
            try:
                self.splitter.sash_place(0, self.LEFT_PANEL_WIDTH, 0)
            except Exception:
                pass
        else:
            self.lock_button.config(text="🔓")

    def _enforce_left_lock(self):
        # Deprecated (used by older builds) – kept as safe no-op
        return

    def _maybe_block_sash(self, event):
        """Prevent user from dragging the sash when left panel is locked."""
        if getattr(self, 'left_locked', True):
            try:
                # Continuously force position
                self.splitter.sash_place(0, self.LEFT_PANEL_WIDTH, 0)
            except Exception:
                pass
            return "break"
        # allow normal behavior otherwise

    # --- Native Windows dark title bar (best effort) ---
    def _enable_dark_title_bar(self):
        try:
            import sys
            if sys.platform != 'win32':
                return
            import ctypes
            hwnd = self.winfo_id()
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = ArgoGUI()
    app.bind_accessibility_shortcuts()
    app.mainloop()