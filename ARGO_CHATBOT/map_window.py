import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkintermapview import TkinterMapView
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
import threading
import pandas as pd
import time
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import zipfile, io, os
try:
    import visualizer  # reuse COLORS / FONTS for unified dark theme
except ImportError:
    class _Fallback:
        COLORS = {
            "bg_main": "#0E1116","bg_panel": "#181D24","bg_surface": "#202630","text_dark": "#E6EDF3","text_light": "#8A98A8",
            "accent_primary": "#2E8BFF","accent_secondary": "#6C5CE7","status_success": "#2E7D32","status_error": "#D32F2F"
        }
        FONTS = {"body": ("Segoe UI", 11), "body_bold": ("Segoe UI",11,"bold")}
    visualizer = _Fallback()

API_BASE_URL = "http://127.0.0.1:5000/api"

# Default subplot layout parameters captured from user screenshots (desired default look)
EXPANDED_LAYOUTS = {
    'dual': {  # Temperature & Salinity side-by-side
        'left': 0.05,
        'right': 0.775,
        'top': 0.935,
        'bottom': 0.282,
        'wspace': 0.18
    },
    'temp': {  # Single temperature plot
        'left': 0.05,
        'right': 0.773,
        'top': 0.933,
        'bottom': 0.26
    },
    'sal': {   # Single salinity plot
        'left': 0.057,
        'right': 0.747,
        'top': 0.947,
        'bottom': 0.255
    }
}

def _haversine_km(lat1, lon1, lat2, lon2):
    """Compute great-circle distance between two points (lat/lon in degrees)."""
    R = 6371.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a)) if a <= 1 else 0
    return R * c

class MapWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Interactive ARGO Map Explorer")
        # Fixed size window (non-resizable) consistent with app theme
        # Fullscreen similar to app_gui maximizing screen real estate
        try:
            self.state('zoomed')  # Windows specific maximize
        except Exception:
            self.geometry("1600x900")
        self.resizable(True, True)
        self.configure(bg=visualizer.COLORS["bg_main"])

        self.api_online = False
        self.click_marker = None
        self.float_markers = []
        self.current_floats_data = []
        self.selected_float_id = None
        self.locations = []
        self.trajectory_path = None
        self.is_closing = False # Safety flag to prevent errors on close
        # Recent data caches for export/actions
        self.last_profile_df = None
        self.last_traj_distance_km = 0.0
        self.last_traj_points = 0
        self.last_traj_start = None
        self.last_traj_end = None
        # Main container frame
        main_frame = tk.Frame(self, bg=visualizer.COLORS["bg_main"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=2)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        # Period filter state
        self.selected_year = None
        self.selected_month = None
        self.available_periods = {}
        # Marker click debounce timestamp
        self._last_marker_click_time = 0.0
        # Proximity threshold (degrees) to treat a map click as a marker click (lat & lon)
        self._marker_proximity_threshold = 0.08  # ~8-9 km depending on latitude
        # Time until which map clicks are suppressed after selecting a marker
        self._suppress_clear_until = 0.0
        # Track last search location to avoid redundant clearing
        self._current_search_location = None
        self._search_min_delta = 0.02  # ~2 km threshold to re-run search
        # Period fetch retry attempts
        self._period_fetch_attempts = 0

        self._create_map_panel(main_frame)
        self._create_data_panel(main_frame)
        self._clear_data_panel()

        threading.Thread(target=self._check_api_status, daemon=True).start()
        threading.Thread(target=self._fetch_periods, daemon=True).start()

    def _create_map_panel(self, parent):
        map_frame = tk.Frame(parent, bg=visualizer.COLORS["bg_panel"], bd=1, relief=tk.FLAT, highlightthickness=1, highlightbackground=visualizer.COLORS.get("border_light","#2E3843"))
        map_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        search_frame = tk.Frame(map_frame, bg=visualizer.COLORS["bg_surface"])
        search_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 2))
        # Layout: Home | Year | Month | (spacer) | Search label + entry + button (right)
        self.home_button = tk.Button(search_frame, text="Home", command=self._go_home, bg=visualizer.COLORS["accent_secondary"], fg="white", relief=tk.FLAT, font=visualizer.FONTS.get("body_bold", ("Segoe UI",11,"bold")))
        self.home_button.grid(row=0, column=0, padx=(6,6), pady=4, sticky='w')
        # Year / Month selectors (enabled once data fetched)
        tk.Label(search_frame, text="Year:", bg=visualizer.COLORS["bg_surface"], fg=visualizer.COLORS["text_light"], font=visualizer.FONTS.get("body",("Segoe UI",10))).grid(row=0, column=1, padx=(4,2), sticky='w')
        self.year_combo = ttk.Combobox(search_frame, state='disabled', width=8, values=[])
        self.year_combo.grid(row=0, column=2, padx=2, sticky='w')
        self.year_combo.bind('<<ComboboxSelected>>', self._on_year_change)
        tk.Label(search_frame, text="Month:", bg=visualizer.COLORS["bg_surface"], fg=visualizer.COLORS["text_light"], font=visualizer.FONTS.get("body",("Segoe UI",10))).grid(row=0, column=3, padx=(8,2), sticky='w')
        self.month_combo = ttk.Combobox(search_frame, state='disabled', width=10, values=[])
        self.month_combo.grid(row=0, column=4, padx=2, sticky='w')
        self.month_combo.bind('<<ComboboxSelected>>', self._on_month_change)
        # Spacer
        search_frame.grid_columnconfigure(5, weight=1)
        # Search controls aligned right
        tk.Label(search_frame, text="Search:", bg=visualizer.COLORS["bg_surface"], fg=visualizer.COLORS["text_dark"], font=visualizer.FONTS.get("body",("Segoe UI",11))).grid(row=0, column=6, padx=(4,2), pady=4, sticky='e')
        # Reduced width for better fit
        self.search_entry = tk.Entry(search_frame, relief=tk.FLAT, width=14, bg=visualizer.COLORS["bg_main"], fg=visualizer.COLORS["text_dark"])
        self.search_entry.grid(row=0, column=7, padx=2, pady=4, sticky='e')
        self.search_button = tk.Button(search_frame, text="Find", command=self._on_search, bg=visualizer.COLORS["accent_primary"], fg="white", relief=tk.FLAT, font=visualizer.FONTS.get("body_bold",("Segoe UI",10,"bold")), width=6)
        self.search_button.grid(row=0, column=8, padx=(4,8), pady=4, sticky='e')
        for c in range(9):
            if c != 5:
                search_frame.grid_columnconfigure(c, weight=0)
        # Ensure right alignment by giving last column minimal weight
        search_frame.grid_columnconfigure(8, weight=0)
        self.search_entry.config(insertbackground="white")
        self.search_entry.bind("<Return>", self._on_search)
        self.map_widget = TkinterMapView(map_frame, width=800, height=750, corner_radius=0)
        self.map_widget.pack(fill=tk.BOTH, expand=True)
        self.map_widget.set_position(10, 80)
        self.map_widget.set_zoom(4)
        status_frame = tk.Frame(map_frame, bg=visualizer.COLORS["bg_surface"])
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = tk.Label(status_frame, text="Checking API status...", anchor=tk.W, bg=visualizer.COLORS["bg_surface"], fg=visualizer.COLORS["text_light"], font=visualizer.FONTS.get("body",("Segoe UI",11)))
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.api_status_label = tk.Label(status_frame, text="API: Unknown", anchor=tk.E, width=15, bg=visualizer.COLORS["bg_surface"], fg=visualizer.COLORS["text_dark"], font=visualizer.FONTS.get("body_bold",("Segoe UI",11,"bold")))
        self.api_status_label.pack(side=tk.RIGHT, padx=4, pady=2)

    def _create_data_panel(self, parent):
        data_frame = tk.Frame(parent, bg=visualizer.COLORS["bg_panel"], bd=1, relief=tk.FLAT, highlightthickness=1, highlightbackground=visualizer.COLORS.get("border_light","#2E3843"))
        data_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        data_frame.grid_rowconfigure(4, weight=1)
        data_frame.grid_columnconfigure(0, weight=1)

        self.data_label = tk.Label(data_frame, text="Float Profile Data", font=visualizer.FONTS.get("body_bold",("Segoe UI",12,"bold")), bg=visualizer.COLORS["bg_panel"], fg=visualizer.COLORS["accent_primary"])
        self.data_label.grid(row=0, column=0, sticky='w', padx=10, pady=(10,4))

        # Metadata / trajectory info area (scrollable)
        meta_container = tk.Frame(data_frame, bg=visualizer.COLORS["bg_panel"])
        meta_container.grid(row=1, column=0, sticky='nsew', padx=10)
        meta_container.grid_columnconfigure(0, weight=1)
        meta_container.grid_rowconfigure(0, weight=1)
        self.meta_text = tk.Text(meta_container, height=6, wrap='word', bg=visualizer.COLORS["bg_main"], fg=visualizer.COLORS["text_dark"], relief=tk.FLAT, font=visualizer.FONTS.get("body", ("Segoe UI",10)))
        meta_scroll = ttk.Scrollbar(meta_container, orient='vertical', command=self.meta_text.yview)
        self.meta_text.configure(yscrollcommand=meta_scroll.set)
        self.meta_text.grid(row=0, column=0, sticky='nsew')
        meta_scroll.grid(row=0, column=1, sticky='ns')
        self._write_meta("Select a float to view trajectory & profile details.")

        table_frame = tk.Frame(data_frame, bg=visualizer.COLORS["bg_panel"])
        table_frame.grid(row=2, column=0, sticky='ew', padx=10, pady=4)
        table_frame.grid_columnconfigure(0, weight=1)
        # Dark style for Treeview
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure("Dark.Treeview",
                        background=visualizer.COLORS["bg_main"],
                        fieldbackground=visualizer.COLORS["bg_main"],
                        foreground=visualizer.COLORS["text_dark"],
                        bordercolor=visualizer.COLORS.get("border_light", "#2E3843"),
                        rowheight=22)
        style.map("Dark.Treeview",
                  background=[('selected', visualizer.COLORS["accent_primary"])],
                  foreground=[('selected', 'white')])

        self.tree = ttk.Treeview(table_frame, columns=("Timestamp", "Pressure", "Temp", "Salinity"), show="headings", height=8, style="Dark.Treeview")
        self.tree.heading("Timestamp", text="Timestamp"); self.tree.heading("Pressure", text="Pressure (dbar)")
        self.tree.heading("Temp", text="Temp (°C)"); self.tree.heading("Salinity", text="Salinity (PSU)")
        self.tree.column("Timestamp", width=140); self.tree.column("Pressure", width=100, anchor="center")
        self.tree.column("Temp", width=100, anchor="center"); self.tree.column("Salinity", width=100, anchor="center")
        self.tree.grid(row=0, column=0, sticky='ew')
        
        # Plot frame (expandable)
        plot_frame = tk.Frame(data_frame, bg=visualizer.COLORS["bg_panel"])
        plot_frame.grid(row=3, column=0, sticky='nsew', padx=10, pady=(4,6))
        plot_frame.grid_rowconfigure(0, weight=1)
        plot_frame.grid_columnconfigure(0, weight=1)

        self.fig, (self.ax_temp, self.ax_sal) = plt.subplots(1, 2, figsize=(6, 3.6))
        self.fig.set_facecolor(visualizer.COLORS["bg_panel"])
        for ax in (self.ax_temp, self.ax_sal):
            ax.set_facecolor(visualizer.COLORS["bg_panel"])
            ax.tick_params(colors=visualizer.COLORS["text_light"])
            ax.title.set_color(visualizer.COLORS["text_dark"])
            ax.xaxis.label.set_color(visualizer.COLORS["text_light"])
            ax.yaxis.label.set_color(visualizer.COLORS["text_light"])
        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas_plot.get_tk_widget().grid(row=0, column=0, sticky='nsew')
        self.fig.tight_layout(pad=3.0)

        # Bottom action bar (exports / expand each / bundle)
        action_frame = tk.Frame(data_frame, bg=visualizer.COLORS["bg_panel"])
        action_frame.grid(row=4, column=0, sticky='ew', padx=10, pady=(2,10))
        for i in range(9):
            action_frame.grid_columnconfigure(i, weight=1)
        btn_kwargs = dict(bg=visualizer.COLORS.get("accent_primary","#2E8BFF"), fg="white", relief=tk.FLAT,
                           font=visualizer.FONTS.get("body", ("Segoe UI",10)))
        self.btn_export_profile = tk.Button(action_frame, text="Export Profile", command=self._export_profile, state='disabled', **btn_kwargs)
        self.btn_export_traj = tk.Button(action_frame, text="Export Traj", command=self._export_traj, state='disabled', **btn_kwargs)
        self.btn_export_all = tk.Button(action_frame, text="Export All", command=self._export_all_bundle, state='disabled', **btn_kwargs)
        self.btn_expand_temp = tk.Button(action_frame, text="Expand Temp", command=lambda: self._expand_single('temp'), state='disabled', **btn_kwargs)
        self.btn_expand_sal = tk.Button(action_frame, text="Expand Sal", command=lambda: self._expand_single('sal'), state='disabled', **btn_kwargs)
        self.btn_expand_both = tk.Button(action_frame, text="Expand Both", command=self._expand_plots, state='disabled', **btn_kwargs)
        self.btn_copy_stats = tk.Button(action_frame, text="Copy Stats", command=self._copy_stats, state='disabled', **btn_kwargs)
        self.btn_clear = tk.Button(action_frame, text="Clear", command=self._clear_data_panel, **btn_kwargs)
        buttons = [self.btn_export_profile, self.btn_export_traj, self.btn_export_all,
                   self.btn_expand_temp, self.btn_expand_sal, self.btn_expand_both,
                   self.btn_copy_stats, self.btn_clear]
        for idx, b in enumerate(buttons):
            b.grid(row=0, column=idx, padx=2, pady=2, sticky='ew')
        self._ensure_button_state()

    def on_closing(self):
        # Mark closing to stop future callbacks; only destroy this window.
        self.is_closing = True
        try:
            if self.map_widget and self.map_widget.winfo_exists():
                self.map_widget.destroy()
        except Exception:
            pass
        self.destroy()

    def safe_after(self, delay, func, *args):
        if not self.is_closing:
            self.after(delay, func, *args)

    def _check_api_status(self, attempts=0):
        try:
            response = requests.get(f"{API_BASE_URL}/status", timeout=4)
            if response.status_code == 200 and response.json().get("status") == "online":
                self.api_online = True
                self.safe_after(0, self._update_api_status_ui, True)
                threading.Thread(target=self._fetch_locations, daemon=True).start()
                return
            else:
                self.safe_after(0, self._update_api_status_ui, False, "Unexpected response")
        except requests.exceptions.RequestException:
            self.safe_after(0, self._update_api_status_ui, False, "Server offline")
        # Retry a few times silently if still offline
        if attempts < 4 and not self.api_online:
            self.safe_after(1500, self._check_api_status, attempts+1)

    def _fetch_locations(self):
        try:
            response = requests.get(f"{API_BASE_URL}/locations", timeout=5)
            self.locations = response.json()
        except Exception as e:
            self.safe_after(0, self.update_status, f"Could not fetch locations: {e}", "red")

    def _fetch_periods(self):
        try:
            response = requests.get(f"{API_BASE_URL}/available_periods", timeout=6)
            js = response.json()
            periods = js.get('periods') if isinstance(js, dict) else {}
            if periods:
                self.available_periods = periods
                years = sorted(periods.keys(), reverse=True)
                self.safe_after(0, self._populate_years, years)
        except Exception:
            pass

    def _populate_years(self, years):
        # Enable and populate year combo
        self.year_combo['values'] = years
        if years:
            self.year_combo.config(state='readonly')
            self.year_combo.current(0)
            self.selected_year = int(years[0])
            self._populate_months(years[0])

    def _populate_months(self, year_str):
        months = self.available_periods.get(year_str, [])
        month_map = {m: datetime(1900, m, 1).strftime('%b') for m in months}
        display = [f"{m:02d}-{month_map[m]}" for m in months]
        self.month_combo['values'] = display
        if months:
            self.month_combo.config(state='readonly')
            self.month_combo.current(0)
            self.selected_month = months[0]
        else:
            self.month_combo.config(state='disabled')

    def _on_year_change(self, event=None):
        year_str = self.year_combo.get()
        if not year_str:
            return
        self.selected_year = int(year_str)
        self._populate_months(year_str)

    def _on_month_change(self, event=None):
        sel = self.month_combo.get()
        if not sel:
            return
        try:
            self.selected_month = int(sel.split('-')[0])
        except Exception:
            self.selected_month = None

    def _on_search(self, event=None):
        if not self.api_online:
            self.update_status("API is offline. Cannot search.", "red"); return
        query = self.search_entry.get().lower().strip()
        if not query: return
        for loc in self.locations:
            if loc['name'] == query:
                self.map_widget.set_position(loc['lat'], loc['lon'])
                self.on_map_click((loc['lat'], loc['lon'])); return
        self.update_status(f"Location '{query}' not found.", "orange")

    def _update_api_status_ui(self, is_online, message=None):
        if self.is_closing:
            return
        if is_online:
            self.api_status_label.config(text="API: Online", fg="white", bg=visualizer.COLORS.get("status_success","#2E7D32"))
            self.map_widget.add_left_click_map_command(self.on_map_click)
            self.update_status("Click on the map or search.", visualizer.COLORS.get("text_light","#999"))
        else:
            self.api_status_label.config(text="API: Offline", fg="white", bg=visualizer.COLORS.get("status_error","#C62828"))
            self.update_status(f"API offline: {message}", "red")

    def on_map_click(self, coords):
        lat, lon = coords
        # Debounce: if a marker was clicked very recently, ignore this map click
        if (time.time() - self._last_marker_click_time) < 0.30:
            return
        # If click is near an existing float marker, treat as marker selection to avoid moving blue marker
        nearest_marker = None
        nearest_dist = 999
        for mk in self.float_markers:
            try:
                dlat = abs(getattr(mk, 'float_lat', 999) - lat)
                dlon = abs(getattr(mk, 'float_lon', 999) - lon)
                if dlat <= self._marker_proximity_threshold and dlon <= self._marker_proximity_threshold:
                    approx_dist = dlat + dlon
                    if approx_dist < nearest_dist:
                        nearest_dist = approx_dist
                        nearest_marker = mk
            except Exception:
                continue
        if nearest_marker is not None:
            # Simulate marker click without altering search location
            self.on_marker_click(nearest_marker)
            return
        self.update_status(f"Searching for floats near {lat:.2f}, {lon:.2f}...", "blue")
        if self.click_marker: self.click_marker.delete()
        if self.trajectory_path: self.trajectory_path.delete()
        self.click_marker = self.map_widget.set_marker(lat, lon, text="Search Location", marker_color_circle="blue", marker_color_outside="lightblue")
        self._clear_data_panel()
        self.selected_float_id = None 
        threading.Thread(target=self._fetch_nearest_floats, args=(lat, lon), daemon=True).start()

    def _fetch_nearest_floats(self, lat, lon):
        try:
            base = f"{API_BASE_URL}/nearest_floats?lat={lat}&lon={lon}"
            if self.selected_year and self.selected_month:
                base += f"&year={self.selected_year}&month={self.selected_month}"
            url = base
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            self.current_floats_data = response.json()
            self.safe_after(0, self._update_map_markers)
        except requests.exceptions.RequestException as e:
            self.safe_after(0, self.update_status, f"API Error: {e}", "red")

    def _update_map_markers(self):
        if self.is_closing: return
        for marker in self.float_markers: marker.delete()
        self.float_markers.clear()
        if not self.current_floats_data:
            self.update_status("No floats found in this area.", "orange"); return
        for f_data in self.current_floats_data:
            is_selected = (f_data['float_id'] == self.selected_float_id)
            circle_color, outside_color = ("green", "darkgreen") if is_selected else ("red", "darkred")
            marker = self.map_widget.set_marker(f_data["latitude"], f_data["longitude"], text=f"Float {f_data['float_id']}",
                command=self.on_marker_click, marker_color_circle=circle_color, marker_color_outside=outside_color)
            marker.float_info = f_data
            marker.float_lat = f_data["latitude"]
            marker.float_lon = f_data["longitude"]
            self.float_markers.append(marker)
        if not self.selected_float_id:
            self.update_status(f"Found {len(self.current_floats_data)} floats. Click a red marker.", "green")

    def on_marker_click(self, marker):
        clicked_id = marker.float_info['float_id']
        if self.selected_float_id == clicked_id:
            return
        # Record the time to suppress subsequent map click echo
        self._last_marker_click_time = time.time()
        self.selected_float_id = clicked_id
        self._update_map_markers()
        self.update_status(f"Fetching data for float {self.selected_float_id}...", "blue")
        threading.Thread(target=self._fetch_float_profile, args=(self.selected_float_id,), daemon=True).start()
        threading.Thread(target=self._fetch_float_trajectory, args=(self.selected_float_id,), daemon=True).start()

    def _fetch_float_trajectory(self, float_id):
        try:
            extra = ""
            if self.selected_year and self.selected_month:
                extra = f"?year={self.selected_year}&month={self.selected_month}"
            url = f"{API_BASE_URL}/float_trajectory/{float_id}{extra}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            self.safe_after(0, self._update_map_trajectory, response.json(), float_id)
        except requests.exceptions.RequestException as e:
            self.safe_after(0, self.update_status, f"Trajectory API Error: {e}", "red")

    def _update_map_trajectory(self, trajectory_data, float_id):
        if self.is_closing: return
        if self.trajectory_path: self.trajectory_path.delete()
        if not trajectory_data or "error" in trajectory_data:
            self.update_status(f"No trajectory data for float {self.selected_float_id}", "orange")
            return
        path_pts = trajectory_data.get("path") if isinstance(trajectory_data, dict) else None
        if not path_pts:
            self.update_status(f"Trajectory format unexpected for float {self.selected_float_id}", "red")
            return
        self.trajectory_path = self.map_widget.set_path(path_pts)
        start_ts = trajectory_data.get("start_timestamp")
        end_ts = trajectory_data.get("end_timestamp")
        npts = trajectory_data.get("num_points")
        total_km = 0.0
        if path_pts and len(path_pts) > 1:
            for (a_lat,a_lon),(b_lat,b_lon) in zip(path_pts[:-1], path_pts[1:]):
                try:
                    total_km += _haversine_km(a_lat, a_lon, b_lat, b_lon)
                except Exception:
                    continue
        fmt_start, fmt_end, duration_txt = start_ts, end_ts, ""
        try:
            ds = datetime.fromisoformat(start_ts.replace('Z','')) if start_ts else None
            de = datetime.fromisoformat(end_ts.replace('Z','')) if end_ts else None
            if ds and de:
                fmt_start = ds.strftime('%Y-%m-%d %H:%M UTC')
                fmt_end = de.strftime('%Y-%m-%d %H:%M UTC')
                hours = int((de-ds).total_seconds()//3600)
                duration_txt = f"Duration: {hours} h"
        except Exception:
            pass
        period_line = f"Period Filter: {self.selected_year}-{self.selected_month:02d}" if (self.selected_year and self.selected_month) else "Period Filter: ALL"
        lines = [
            f"Float {float_id} Trajectory",
            f"Points: {npts}",
            f"Distance: {total_km:.1f} km" if total_km else "Distance: N/A",
            f"Start: {fmt_start}",
            f"End:   {fmt_end}",
            duration_txt,
            period_line
        ]
        self._write_meta("\n".join([l for l in lines if l]))
        self.last_traj_distance_km = total_km
        self.last_traj_points = npts
        self.last_traj_start = fmt_start
        self.last_traj_end = fmt_end

    def _fetch_float_profile(self, float_id):
        try:
            extra = ""
            if self.selected_year and self.selected_month:
                extra = f"?year={self.selected_year}&month={self.selected_month}"
            url = f"{API_BASE_URL}/float_profile/{float_id}{extra}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            self.safe_after(0, self._update_data_panel, response.json(), float_id)
        except requests.exceptions.RequestException as e:
            self.safe_after(0, self.update_status, f"API Error for float {float_id}: {e}", "red")
            
    def _clear_profile_area(self):
        """Clear table & plots but preserve meta text (trajectory info)."""
        if self.is_closing: return
        for item in self.tree.get_children(): self.tree.delete(item)
        self.ax_temp.clear(); self.ax_sal.clear()
        self.data_label.config(text="Float Profile Data")
        self.ax_temp.set_title("Temperature"); self.ax_sal.set_title("Salinity")
        self.fig.supylabel("Pressure (dbar)")
        self.canvas_plot.draw()
        self.last_profile_df = None
        self._ensure_button_state()

    def _clear_data_panel(self):
        if self.is_closing: return
        for item in self.tree.get_children(): self.tree.delete(item)
        self.ax_temp.clear(); self.ax_sal.clear()
        self.data_label.config(text="Float Profile Data")
        self.ax_temp.set_title("Temperature"); self.ax_sal.set_title("Salinity")
        self.fig.supylabel("Pressure (dbar)")
        self.canvas_plot.draw()
        self._write_meta("Select a float to view trajectory & profile details.")
        self.last_profile_df = None
        self.last_traj_distance_km = 0.0
        self.last_traj_points = 0
        self.last_traj_start = None
        self.last_traj_end = None
        self._ensure_button_state()

    def _update_data_panel(self, profile_data, float_id):
        if self.is_closing: return
        # Only clear profile area so we keep trajectory metadata
        self._clear_profile_area()
        if not profile_data or "error" in profile_data:
            self.update_status(f"No profile data for float {float_id}", "orange")
            return
            
        df = pd.DataFrame(profile_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        self.data_label.config(text=f"Profile for Float: {float_id} on {df['timestamp'][0].date()}")
        for _, row in df.iterrows():
            self.tree.insert("", "end", values=(
                row['timestamp'].strftime('%Y-%m-%d %H:%M'),
                f"{row['pressure']:.1f}",
                f"{row['temperature']:.3f}" if pd.notna(row['temperature']) else "N/A",
                f"{row['salinity']:.3f}" if pd.notna(row['salinity']) else "N/A"
            ))
        # Plot temperature
        self.ax_temp.plot(df['temperature'], df['pressure'], 'b-o', markersize=4)
        self.ax_temp.set_xlabel("Temp (°C)")
        self.ax_temp.set_title("Temperature", color=visualizer.COLORS["text_dark"])
        self.ax_temp.invert_yaxis()
        self.ax_temp.grid(True, linestyle='--', alpha=0.6)

        # Plot salinity
        self.ax_sal.plot(df['salinity'], df['pressure'], 'g-o', markersize=4)
        self.ax_sal.set_xlabel("Salinity (PSU)")
        self.ax_sal.set_title("Salinity", color=visualizer.COLORS["text_dark"])
        self.ax_sal.invert_yaxis()
        self.ax_sal.tick_params(axis='y', labelleft=False)
        self.ax_sal.grid(True, linestyle='--', alpha=0.6)
        
        self.fig.supylabel("Pressure (dbar)")
        self.canvas_plot.draw()
        self.update_status(f"Displaying profile for float {float_id}", "green")
        try:
            ts_fmt = df['timestamp'][0].strftime('%Y-%m-%d %H:%M UTC')
        except Exception:
            ts_fmt = str(df['timestamp'][0])
        self.last_profile_df = df
        self._append_meta(f"\nProfile Timestamp: {ts_fmt} (Rows: {len(df)})")
        self._ensure_button_state()

    # Export & helper actions
    def _export_profile(self):
        if not hasattr(self, 'last_profile_df') or self.last_profile_df is None:
            self.update_status("No profile to export", "orange"); return
        fid = self.selected_float_id or 'unknown'
        default = f"profile_{fid}.csv"
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=default, filetypes=[["CSV","*.csv"]])
        if not path: return
        try:
            self.last_profile_df.to_csv(path, index=False)
            self.update_status(f"Saved {path}", visualizer.COLORS.get('status_success','green'))
        except Exception as e:
            self.update_status(f"Export failed: {e}", 'red')

    def _export_traj(self):
        if not hasattr(self, 'trajectory_path') or not self.trajectory_path:
            self.update_status("No trajectory to export", "orange"); return
        coords = getattr(self.trajectory_path, 'position_list', [])
        if not coords:
            self.update_status("No trajectory path points", "orange"); return
        fid = self.selected_float_id or 'unknown'
        default = f"trajectory_{fid}.csv"
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=default, filetypes=[["CSV","*.csv"]])
        if not path: return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('latitude,longitude\n')
                for la, lo in coords:
                    f.write(f"{la},{lo}\n")
            self.update_status(f"Saved {path}", visualizer.COLORS.get('status_success','green'))
        except Exception as e:
            self.update_status(f"Traj export failed: {e}", 'red')
        self._ensure_button_state()

    def _expand_plots(self):
        if not hasattr(self, 'last_profile_df') or self.last_profile_df is None:
            self.update_status("No profile loaded", 'orange'); return
        win = tk.Toplevel(self); win.title(f"Float {self.selected_float_id} Expanded Profile")
        try:
            win.state('zoomed')
        except Exception:
            win.attributes('-fullscreen', True)
        fig, (ax1, ax2) = plt.subplots(1,2, figsize=(12,6), facecolor='white')
        df = self.last_profile_df
        ax1.plot(df['temperature'], df['pressure'], 'b.-')
        ax1.invert_yaxis(); ax1.set_xlabel('Temp (°C)'); ax1.set_ylabel('Pressure (dbar)'); ax1.set_title('Temperature')
        ax2.plot(df['salinity'], df['pressure'], 'g.-')
        ax2.invert_yaxis(); ax2.set_xlabel('Salinity (PSU)'); ax2.set_title('Salinity'); ax2.tick_params(labelleft=False)
        for ax in (ax1, ax2): ax.grid(True, linestyle='--', alpha=0.6)
        # Apply preferred dual-layout spacings
        lay = EXPANDED_LAYOUTS['dual']
        fig.subplots_adjust(left=lay['left'], right=lay['right'], top=lay['top'], bottom=lay['bottom'], wspace=lay['wspace'])
        try:
            # Resize figure to better fill screen
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            dpi = fig.dpi if fig.dpi else 100
            fig.set_size_inches((sw-140)/dpi, (sh-220)/dpi, forward=True)
        except Exception:
            pass
        container = tk.Frame(win, bg='#ffffff')
        container.pack(fill='both', expand=True)
        canvas = FigureCanvasTkAgg(fig, master=container)
        try:
            from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
            tb_frame = tk.Frame(container, bg='#ffffff', bd=0, highlightthickness=0)
            tb_frame.pack(side=tk.TOP, fill=tk.X)
            toolbar = NavigationToolbar2Tk(canvas, tb_frame)
            toolbar.update()
        except Exception:
            pass
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def _expand_single(self, which):
        if not hasattr(self, 'last_profile_df') or self.last_profile_df is None:
            self.update_status("No profile loaded", 'orange'); return
        df = self.last_profile_df
        title_map = {'temp': 'Temperature', 'sal': 'Salinity'}
        win = tk.Toplevel(self); win.title(f"Float {self.selected_float_id} {title_map.get(which,'Plot')}")
        try:
            win.state('zoomed')
        except Exception:
            win.attributes('-fullscreen', True)
        fig, ax = plt.subplots(figsize=(8,6), facecolor='white')
        if which == 'temp':
            ax.plot(df['temperature'], df['pressure'], 'b.-')
            ax.set_xlabel('Temp (°C)'); ax.set_ylabel('Pressure (dbar)'); ax.set_title('Temperature')
        else:
            ax.plot(df['salinity'], df['pressure'], 'g.-')
            ax.set_xlabel('Salinity (PSU)'); ax.set_ylabel('Pressure (dbar)'); ax.set_title('Salinity')
        ax.invert_yaxis(); ax.grid(True, linestyle='--', alpha=0.6)
        lay = EXPANDED_LAYOUTS.get(which, EXPANDED_LAYOUTS['temp'])
        fig.subplots_adjust(left=lay['left'], right=lay['right'], top=lay['top'], bottom=lay['bottom'])
        try:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            dpi = fig.dpi if fig.dpi else 100
            fig.set_size_inches((sw-160)/dpi, (sh-240)/dpi, forward=True)
        except Exception:
            pass
        container = tk.Frame(win, bg='#ffffff')
        container.pack(fill='both', expand=True)
        canvas = FigureCanvasTkAgg(fig, master=container)
        try:
            from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
            tb_frame = tk.Frame(container, bg='#ffffff', bd=0, highlightthickness=0)
            tb_frame.pack(side=tk.TOP, fill=tk.X)
            toolbar = NavigationToolbar2Tk(canvas, tb_frame)
            toolbar.update()
        except Exception:
            pass
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def _copy_stats(self):
        try:
            txt = self.meta_text.get('1.0', tk.END).strip()
            self.clipboard_clear(); self.clipboard_append(txt)
            self.update_status('Stats copied', visualizer.COLORS.get('status_success','green'))
        except Exception:
            self.update_status('Copy failed', 'red')

    def _export_all_bundle(self):
        if not self.selected_float_id:
            self.update_status('No float selected', 'orange'); return
        files_created = []
        fid = self.selected_float_id
        # Ensure individual csvs exist (reuse functions)
        if self.last_profile_df is not None:
            self._export_profile()
            files_created.append(f'profile_{fid}.csv')
        if self.trajectory_path is not None:
            self._export_traj()
            files_created.append(f'trajectory_{fid}.csv')
        stats_text = self.meta_text.get('1.0', tk.END)
        stats_fn = f'stats_{fid}.txt'
        try:
            with open(stats_fn,'w',encoding='utf-8') as f:
                f.write(stats_text)
            files_created.append(stats_fn)
        except Exception:
            pass
        if not files_created:
            self.update_status('Nothing to bundle', 'orange'); return
        bundle_name = filedialog.asksaveasfilename(defaultextension='.zip', initialfile=f'float_{fid}_bundle.zip', filetypes=[["ZIP","*.zip"]])
        if not bundle_name: return
        try:
            with zipfile.ZipFile(bundle_name,'w',compression=zipfile.ZIP_DEFLATED) as z:
                for fn in files_created:
                    if os.path.exists(fn):
                        z.write(fn)
            self.update_status(f'Created {bundle_name}', visualizer.COLORS.get('status_success','green'))
        except Exception as e:
            self.update_status(f'Bundle failed: {e}', 'red')
        self._ensure_button_state()

    def _ensure_button_state(self):
        has_profile = self.last_profile_df is not None
        has_traj = self.trajectory_path is not None and getattr(self.trajectory_path,'position_list',None)
        state_prof = 'normal' if has_profile else 'disabled'
        state_traj = 'normal' if has_traj else 'disabled'
        both = 'normal' if (has_profile or has_traj) else 'disabled'
        # Profile related
        if hasattr(self,'btn_export_profile'): self.btn_export_profile.config(state=state_prof)
        if hasattr(self,'btn_expand_temp'): self.btn_expand_temp.config(state=state_prof)
        if hasattr(self,'btn_expand_sal'): self.btn_expand_sal.config(state=state_prof)
        if hasattr(self,'btn_expand_both'): self.btn_expand_both.config(state=state_prof)
        if hasattr(self,'btn_export_traj'): self.btn_export_traj.config(state=state_traj)
        if hasattr(self,'btn_copy_stats'): self.btn_copy_stats.config(state=both)
        if hasattr(self,'btn_export_all'): self.btn_export_all.config(state=both)

    # ---- Metadata text helpers ----
    def _write_meta(self, text):
        if self.is_closing: return
        self.meta_text.configure(state='normal')
        self.meta_text.delete('1.0', tk.END)
        self.meta_text.insert(tk.END, text)
        self.meta_text.configure(state='disabled')

    def _append_meta(self, text):
        if self.is_closing: return
        self.meta_text.configure(state='normal')
        self.meta_text.insert(tk.END, f"\n{text}")
        self.meta_text.configure(state='disabled')
        self.meta_text.see(tk.END)

    def update_status(self, message, color=None):
        if self.is_closing: return
        if color is None:
            color = visualizer.COLORS.get("text_light","#bbbbbb")
        self.status_label.config(text=message, fg=color)

    def _go_home(self):
        """Close this window (return to app_gui) without stopping API."""
        try:
            self.destroy()
        except Exception:
            pass

def open_map_window(parent):
    """Helper to launch the MapWindow from another GUI (e.g., app_gui). Returns the instance."""
    win = MapWindow(parent)
    win.protocol("WM_DELETE_WINDOW", win.on_closing)
    return win

if __name__ == "__main__":
    import time, requests

    class LoaderWindow(tk.Toplevel):
        def __init__(self, master):
            super().__init__(master)
            self.title("Starting Map Explorer")
            self.geometry("420x140")
            self.resizable(False, False)
            self.configure(bg=visualizer.COLORS["bg_main"])
            lbl = tk.Label(self, text="Starting API / Waiting for service...", fg=visualizer.COLORS["accent_primary"], bg=visualizer.COLORS["bg_main"], font=visualizer.FONTS.get("body_bold", ("Segoe UI",12,"bold")))
            lbl.pack(pady=16)
            self.status = tk.Label(self, text="Checking...", fg=visualizer.COLORS["text_light"], bg=visualizer.COLORS["bg_main"], font=visualizer.FONTS.get("body", ("Segoe UI",10)))
            self.status.pack()
            self.progress = ttk.Progressbar(self, mode='indeterminate')
            self.progress.pack(fill='x', padx=30, pady=12)
            self.progress.start(10)

        def update_msg(self, msg, color=None):
            if color:
                self.status.configure(fg=color)
            self.status.configure(text=msg)

    def wait_for_api(max_wait=20):
        start = time.time()
        while time.time() - start < max_wait:
            try:
                r = requests.get(f"{API_BASE_URL}/status", timeout=3)
                if r.status_code == 200 and r.json().get("status") == "online":
                    return True, None
            except Exception as e:
                last_err = str(e)
            time.sleep(1.2)
        return False, locals().get('last_err')

    root = tk.Tk(); root.withdraw()
    loader = LoaderWindow(root)
    root.update_idletasks()

    def _after_wait():
        ok, err = wait_for_api()
        if ok:
            loader.update_msg("API online. Launching map...", visualizer.COLORS.get("status_success", "green"))
            loader.after(600, lambda: (
                loader.destroy(),
                _launch_map()
            ))
        else:
            loader.update_msg(f"API not available. Check server. ({err})", visualizer.COLORS.get("status_error","red"))
            loader.progress.stop()

    def _launch_map():
        app = MapWindow(master=root)
        app.protocol("WM_DELETE_WINDOW", app.on_closing)

    loader.after(100, _after_wait)
    root.mainloop()

