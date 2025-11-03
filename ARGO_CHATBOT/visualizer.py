import pandas as pd
import tkinter as tk
from tkinter import ttk, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import traceback
from math import radians, cos, sin, asin, sqrt

COLORS = {
    # Core backgrounds
    "bg_main": "#0E1116",
    "bg_panel": "#181D24",
    "bg_surface": "#202630",
    "bg_alt": "#262E39",
    "bg_chat": "#12161C",
    # Text
    "text_dark": "#E6EDF3",
    "text_light": "#8A98A8",
    "text_inverse": "#101418",
    # Accents
    "accent_primary": "#2E8BFF",
    "accent_secondary": "#6C5CE7",
    "accent_warn": "#FFB020",
    "accent_danger": "#E2504C",
    # Borders / outlines
    "neon_border": "#2E8BFF",
    "border_light": "#2E3843",
    "border_glow": "#2E8BFF",
    # Buttons
    "button_bg": "#181D24",
    "button_hover": "#2E8BFF",
    "button_text": "#E6EDF3",
    # Overlays
    "overlay_bg": "#000000AA",
    # Status colors
    "status_idle": "#5A6470",
    "status_running": "#2E8BFF",
    "status_success": "#2E7D32",
    "status_error": "#D32F2F",
}
FONTS = {
    "header": ("Segoe UI", 22, "bold"),
    "body": ("Segoe UI", 12),
    "body_bold": ("Segoe UI", 12, "bold"),
    "statistic": ("Segoe UI", 48, "bold"),
    "statistic_label": ("Segoe UI", 18),
    "context_header": ("Segoe UI", 13, "bold"),
    "stat_card_header": ("Segoe UI", 12, "bold"),
    "stat_card_body": ("Segoe UI", 11),
    "suggested": ("Segoe UI", 13, "bold"),
    "input": ("Segoe UI", 13),
}

def _setup_plot_style():
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor(COLORS["bg_panel"])
    ax.set_facecolor(COLORS["bg_panel"])
    # Higher contrast ticks & labels
    tick_color = COLORS["text_dark"]
    ax.tick_params(axis='x', colors=tick_color, labelsize=11)
    ax.tick_params(axis='y', colors=tick_color, labelsize=11)
    ax.xaxis.label.set_color(COLORS["text_dark"]) ; ax.yaxis.label.set_color(COLORS["text_dark"])
    ax.title.set_color(COLORS["text_dark"])
    return fig, ax

def _draw_canvas(master_frame, fig):
    for widget in master_frame.winfo_children():
        widget.destroy()
    fig.tight_layout(pad=2.0)
    canvas = FigureCanvasTkAgg(fig, master=master_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    return canvas

def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [float(lon1), float(lat1), float(lon2), float(lat2)])
    dlon = lon2 - lon1; dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)); r = 6371
    return c * r

def create_trajectory_summary_card(master_frame, data):
    for widget in master_frame.winfo_children():
        widget.destroy()
    df = pd.DataFrame(data)
    card = tk.Frame(master_frame, bg=COLORS["bg_panel"])
    card.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
    # Robust: handle empty, single-row, or missing columns
    if df.empty or len(df) < 2 or not all(col in df.columns for col in ['latitude', 'longitude', 'timestamp']):
        msg = "No trajectory/path data available. Try a larger time window or different float."
        if len(df) == 1:
            msg = "Only one data point found. No path can be shown. Try a larger time window."
        tk.Label(card, text=msg, font=FONTS["context_header"], bg=COLORS["bg_panel"], fg="red").pack(anchor="w", padx=10, pady=(10, 5))
        return
    try:
        total_distance = 0
        for i in range(len(df) - 1):
            total_distance += haversine(df.iloc[i]['longitude'], df.iloc[i]['latitude'], df.iloc[i+1]['longitude'], df.iloc[i+1]['latitude'])
        start_date = pd.to_datetime(df['timestamp'].min())
        end_date = pd.to_datetime(df['timestamp'].max())
        duration = end_date - start_date
        tk.Label(card, text="Trajectory Summary", font=FONTS["context_header"], bg=COLORS["bg_panel"], fg=COLORS["text_dark"]).pack(anchor="w", padx=10, pady=(10, 5))
        tk.Label(card, text=f"Total Distance: {total_distance:.2f} km", font=FONTS["body_bold"], bg=COLORS["bg_panel"], fg=COLORS["text_dark"]).pack(anchor="w", padx=10)
        tk.Label(card, text=f"Duration: {duration.days} days", font=FONTS["body_bold"], bg=COLORS["bg_panel"], fg=COLORS["text_dark"]).pack(anchor="w", padx=10, pady=(0, 10))
    except Exception as e:
        tk.Label(card, text=f"Could not compute trajectory summary. Error: {e}", font=FONTS["context_header"], bg=COLORS["bg_panel"], fg="red").pack(anchor="w", padx=10, pady=(10, 5))

def create_summary_stats_cards(master_frame, data):
    df = pd.DataFrame(data); stats_frame = tk.Frame(master_frame, bg=COLORS["bg_main"]); stats_frame.pack(pady=10, padx=(0, 10), fill=tk.BOTH, expand=True)
    tk.Label(stats_frame, text="Summary Statistics", font=FONTS["context_header"], bg=COLORS["bg_main"], fg=COLORS["text_dark"]).pack(anchor="w", padx=10, pady=(10, 5))
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    sensor_cols = [col for col in numeric_cols if col not in ['latitude', 'longitude', 'pressure', 'float_id', 'distance_km']]
    for col in sensor_cols:
        card = tk.Frame(stats_frame, bg=COLORS["bg_panel"], bd=1, relief=tk.SOLID, highlightthickness=1, highlightbackground="#E0E0E0"); card.pack(fill=tk.X, padx=10, pady=5, ipady=5)
        col_name = col.replace('_', ' ').title(); mean_val = df[col].mean(); max_val = df[col].max(); min_val = df[col].min()
        card.grid_columnconfigure(0, weight=1); card.grid_columnconfigure(1, weight=1); card.grid_columnconfigure(2, weight=1)
        tk.Label(card, text=col_name, font=FONTS["stat_card_header"], bg=COLORS["bg_panel"], fg=COLORS["accent_primary"]).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(5,2))
        tk.Label(card, text=f"Avg: {mean_val:.2f}", font=FONTS["stat_card_body"], bg=COLORS["bg_panel"], fg=COLORS["text_dark"]).grid(row=1, column=0, sticky="w", padx=10, pady=(0,5))
        tk.Label(card, text=f"Max: {max_val:.2f}", font=FONTS["stat_card_body"], bg=COLORS["bg_panel"], fg=COLORS["text_dark"]).grid(row=1, column=1, sticky="w", padx=10, pady=(0,5))
        tk.Label(card, text=f"Min: {min_val:.2f}", font=FONTS["stat_card_body"], bg=COLORS["bg_panel"], fg=COLORS["text_dark"]).grid(row=1, column=2, sticky="w", padx=10, pady=(0,5))

def create_context_card(master_frame, summary, sql):
    for widget in master_frame.winfo_children(): widget.destroy()
    context_frame = tk.Frame(master_frame, bg=COLORS["bg_main"]); context_frame.pack(pady=10, padx=(0, 10), fill=tk.BOTH, expand=True)
    tk.Label(context_frame, text="Summary", font=FONTS["context_header"], bg=COLORS["bg_main"], fg=COLORS["text_dark"]).pack(anchor="w", padx=10, pady=(10, 5))
    # Add float and record info to summary if available
    extra_info = ""
    try:
        import re
        float_ids = re.findall(r'float\(s\): ([\d, ]+)', summary)
        if float_ids:
            extra_info += f"\nFloat(s) used: {float_ids[0]}"
    except Exception:
        pass
    tk.Label(context_frame, text=summary+extra_info, font=FONTS["body"], bg=COLORS["bg_main"], fg=COLORS["text_dark"], wraplength=350, justify=tk.LEFT).pack(anchor="w", padx=10, fill="x")

def update_map_view(map_widget, data, query_type):
    map_widget.delete_all_marker(); map_widget.delete_all_path()
    # Robust: handle empty data or missing columns
    if not data:
        map_widget.set_position(20, 80)  # Default center
        map_widget.set_zoom(3)
        return
    df = pd.DataFrame(data)
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        map_widget.set_position(20, 80)
        map_widget.set_zoom(3)
        return
    df.dropna(subset=['latitude', 'longitude'], inplace=True)
    if df.empty:
        map_widget.set_position(20, 80)
        map_widget.set_zoom(3)
        return
    center_lat, center_lon = df['latitude'].mean(), df['longitude'].mean()
    map_widget.set_position(center_lat, center_lon)
    map_widget.set_zoom(5)
    # Always mark some floats for any non-empty data
    sample_df = df
    if len(df) > 10:
        sample_df = df.sample(n=10, random_state=42)
    for _, row in sample_df.iterrows():
        marker_text = f"Float: {row.get('float_id', 'N/A')}\nTime: {row.get('timestamp', 'N/A')}"
        map_widget.set_marker(row['latitude'], row['longitude'], text=marker_text)
    # For Profile, Trajectory, keep special logic
    if query_type == "Profile":
        float_id = df['float_id'].iloc[0] if 'float_id' in df.columns else 'N/A'
        timestamp = df['timestamp'].iloc[0] if 'timestamp' in df.columns else 'N/A'
        marker_text = f"Float: {float_id}\nTime: {timestamp}"
        map_widget.set_marker(center_lat, center_lon, text=marker_text)
        return
    plot_path = (query_type == "Trajectory")
    # For large non-path queries, still show a summary marker
    if len(df) > 50 and not plot_path:
        marker_text = f"{len(df)} data points\nAvg Lat: {center_lat:.2f}\nAvg Lon: {center_lon:.2f}"
        map_widget.set_marker(center_lat, center_lon, text=marker_text)
    # Robust: only plot path if columns exist, group is valid, and at least 2 points
    if plot_path and 'float_id' in df.columns and 'latitude' in df.columns and 'longitude' in df.columns:
        for float_id, group in df.groupby('float_id'):
            if len(group) > 1 and all(col in group.columns for col in ['latitude', 'longitude']):
                group = group.sort_values('timestamp')
                path_points = list(zip(group['latitude'], group['longitude']))
                if len(path_points) > 1:
                    map_widget.set_path(path_points, color=COLORS["accent_primary"], width=3)

def create_graph(master_frame, data, query_type):
    df = pd.DataFrame(data)
    fig, ax = _setup_plot_style()
    try:
        if df.empty or len(df.columns) < 2:
            ax.text(0.5, 0.5, "No data available for graph.", ha='center', va='center')
        elif query_type == "Profile" and 'pressure' in df.columns:
            sensor_cols = [col for col in df.columns if df[col].dtype in ['float64', 'int64'] and col not in ['latitude', 'longitude', 'pressure', 'float_id']]
            if not sensor_cols:
                ax.text(0.5, 0.5, "No sensor data available for profile graph.", ha='center', va='center')
            else:
                ax.set_title("Float Profile Data"); ax.set_ylabel("Pressure (Depth in dbar)"); ax.set_xlabel("Sensor Value")
                for col in sensor_cols:
                    ax.plot(df[col], df['pressure'], marker='.', linestyle='-', label=col.replace('_', ' ').title())
                ax.invert_yaxis()
                leg = ax.legend()
                _style_legend(leg)
        elif query_type == "Time-Series":
            time_col = 'day' if 'day' in df.columns else 'timestamp'
            if time_col not in df.columns:
                ax.text(0.5, 0.5, f"Required time column '{time_col}' not in results.", ha='center', va='center')
            else:
                cols_to_exclude = ['latitude', 'longitude', 'float_id', 'timestamp', 'day']
                sensor_cols = [col for col in df.columns if col not in cols_to_exclude and pd.to_numeric(df[col], errors='coerce').notna().all()]
                if not sensor_cols:
                    ax.text(0.5, 0.5, "No plottable columns found for time-series graph.", ha='center', va='center')
                else:
                    df[time_col] = pd.to_datetime(df[time_col]); df = df.sort_values(time_col)
                    ax.set_xlabel("Date"); ax.set_ylabel("Sensor Value"); ax.set_title("Time-Series Data")
                    for col in sensor_cols:
                        ax.plot(df[time_col], df[col], marker='o', linestyle='-', label=col.replace('_', ' ').title())
                    leg = ax.legend()
                    _style_legend(leg)
                    fig.autofmt_xdate(rotation=25)
        elif query_type == "Scatter":
            sensor_cols = [col for col in df.columns if col not in ['float_id', 'timestamp', 'latitude', 'longitude', 'pressure']]
            if len(sensor_cols) < 2:
                ax.text(0.5, 0.5, "Scatter plot requires at least two sensor columns.", ha='center', va='center')
            else:
                x_col, y_col = sensor_cols[0], sensor_cols[1]
                df.dropna(subset=[x_col, y_col], inplace=True)
                ax.scatter(df[x_col], df[y_col], alpha=0.6, color=COLORS["accent_secondary"])
                ax.set_xlabel(x_col.title()); ax.set_ylabel(y_col.title()); ax.set_title(f"{x_col.title()} vs. {y_col.title()}", fontsize=14)
        else:
            ax.text(0.5, 0.5, "No recognized graph type for this data.", ha='center', va='center')
    except Exception as e:
        ax.text(0.5, 0.5, f"Could not generate graph.\nError: {e}", ha='center', va='center')
        traceback.print_exc()
    canvas = _draw_canvas(master_frame, fig)
    return fig, ax, canvas

def _style_legend(legend):
    if legend is None:
        return
    frame = legend.get_frame()
    frame.set_facecolor(COLORS["bg_surface"])
    frame.set_edgecolor(COLORS["border_light"])
    for text in legend.get_texts():
        text.set_color(COLORS["text_dark"])
        text.set_fontsize(10)

def create_table(master_frame, data):
    for widget in master_frame.winfo_children(): widget.destroy()
    df = pd.DataFrame(data)
    if df.empty:
        tk.Label(master_frame, text="No data available for table.", font=FONTS["body_bold"], fg="red", bg=COLORS["bg_panel"]).pack(pady=20)
        return
    style = ttk.Style(); style.theme_use("clam")
    # Use a larger, bold, high-contrast font for table cells and headers
    # Adjusted for better numeric glyph visibility (avoid clipping): lighter weight & slight rowheight increase
    visible_font = ("Segoe UI", 12)
    style.configure("Treeview", background=COLORS["bg_panel"], foreground=COLORS["text_dark"], rowheight=30, fieldbackground=COLORS["bg_panel"], font=visible_font)
    style.configure("Treeview.Heading", background=COLORS["accent_primary"], foreground=COLORS["button_text"], font=("Segoe UI", 12, "bold"), relief="flat")
    table_container = tk.Frame(master_frame, bg=COLORS["bg_panel"]); table_container.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
    cols = list(df.columns)
    tree = ttk.Treeview(table_container, columns=cols, show='headings')
    for col in cols:
        tree.heading(col, text=col.replace('_', ' ').title())
        tree.column(col, width=120, anchor='center')
    for _, row in df.iterrows():
        tree.insert("", "end", values=list(row.fillna('N/A')))
    vsb = ttk.Scrollbar(table_container, orient="vertical", command=tree.yview); tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side='right', fill='y'); tree.pack(side='left', fill='both', expand=True)

def create_statistic_card(master_frame, data):
    for widget in master_frame.winfo_children():
        widget.destroy()
    stat_frame = tk.Frame(master_frame, bg=COLORS["bg_panel"])
    stat_frame.pack(expand=True, padx=(10,0))
    df = pd.DataFrame(data)
    if df.empty or df.shape[1] == 0:
        tk.Label(stat_frame, text="No statistic data available.", font=FONTS["body_bold"], fg="red", bg=COLORS["bg_panel"]).pack(pady=20)
        return
    stat_value = df.iloc[0,0]
    stat_name = df.columns[0].replace('_', ' ').title()
    # Find float info and time info if present
    float_ids = df['float_id'].unique().tolist() if 'float_id' in df.columns else []
    timestamps = df['timestamp'].tolist() if 'timestamp' in df.columns else []
    subtitle = ""
    if float_ids:
        subtitle += f"Based on {len(df)} record(s) from float(s): {', '.join(str(fid) for fid in float_ids)}. "
    if timestamps:
        if len(set(timestamps)) == 1:
            subtitle += f"Time: {timestamps[0]}"
        elif len(set(timestamps)) > 1:
            subtitle += f"Time range: {min(timestamps)} to {max(timestamps)}"
    if not subtitle:
        subtitle = "Based on available data."
    tk.Label(stat_frame, text=stat_name, font=FONTS["statistic_label"], bg=COLORS["bg_panel"], fg=COLORS["text_light"]).pack(pady=(10,0))
    tk.Label(stat_frame, text=f"{stat_value:.2f}" if isinstance(stat_value, (int, float)) else stat_value, font=FONTS["statistic"], bg=COLORS["bg_panel"], fg=COLORS["text_dark"]).pack(pady=(0,5))
    tk.Label(stat_frame, text=subtitle, font=FONTS["body"], bg=COLORS["bg_panel"], fg=COLORS["text_light"], wraplength=350, justify=tk.LEFT).pack(pady=(0,10))

def create_scatter_plot(master_frame, data):
    df = pd.DataFrame(data); fig, ax = _setup_plot_style()
    try:
        sensor_cols = [col for col in df.columns if col not in ['float_id', 'timestamp', 'latitude', 'longitude', 'pressure']]
        if len(sensor_cols) < 2: raise ValueError("Scatter plot requires at least two sensor columns.")
        x_col, y_col = sensor_cols[0], sensor_cols[1]; df.dropna(subset=[x_col, y_col], inplace=True)
        ax.scatter(df[x_col], df[y_col], alpha=0.6, color=COLORS["accent_secondary"])
        ax.set_xlabel(x_col.title()); ax.set_ylabel(y_col.title()); ax.set_title(f"{x_col.title()} vs. {y_col.title()}", fontsize=14)
    except Exception as e:
        ax.text(0.5, 0.5, f"Could not generate scatter plot.\nError: {e}", ha='center', va='center')
    _draw_canvas(master_frame, fig)

def create_error_display(master_frame, summary, sql, available_floats=None):
    for widget in master_frame.winfo_children():
        widget.destroy()
    error_frame = tk.Frame(master_frame, bg=COLORS["bg_panel"])
    error_frame.pack(expand=True, fill="both", padx=20, pady=20)
    tk.Label(error_frame, text="An Error Occurred", font=FONTS["header"], bg=COLORS["bg_panel"], fg="red").pack(pady=(0, 10))
    msg = summary
    if available_floats:
        if isinstance(available_floats, list) and len(available_floats) > 0 and isinstance(available_floats[0], dict):
            # Show as table of floats
            float_ids = [str(f.get('float_id', '')) for f in available_floats]
            msg += f"\nAvailable float IDs: {', '.join(float_ids)}"
        elif isinstance(available_floats, list):
            msg += f"\nAvailable float IDs: {', '.join(str(fid) for fid in available_floats)}"
    tk.Label(error_frame, text=msg, font=FONTS["body"], bg=COLORS["bg_panel"], fg=COLORS["text_dark"], wraplength=700, justify=tk.LEFT).pack(pady=(0, 20), fill="x")