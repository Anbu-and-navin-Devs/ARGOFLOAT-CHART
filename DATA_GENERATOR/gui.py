"""
FloatChart Data Generator - Desktop Application
Tkinter GUI for fetching ARGO float data and loading into PostgreSQL database.
"""
from __future__ import annotations

import math
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import List

from sqlalchemy import create_engine, text

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DATA_GENERATOR.env_utils import load_environment
from DATA_GENERATOR.pipeline.state_manager import load_last_success_timestamp
from DATA_GENERATOR.update_manager import UpdateResult, perform_update
from DATA_GENERATOR.config import REGION_LABEL

# Color scheme matching the web app
COLORS = {
    "bg_main": "#0E1116",
    "bg_panel": "#181D24",
    "bg_surface": "#202630",
    "text_primary": "#E6EDF3",
    "text_secondary": "#8A98A8",
    "accent_primary": "#2E8BFF",
    "accent_success": "#2E7D32",
    "accent_danger": "#E2504C",
    "border": "#2E3843",
}


def _format_coord(value: float | None) -> str:
    """Format coordinate values safely for display."""
    if value is None:
        return "NA"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "NA"
    if math.isnan(numeric):
        return "NA"
    return f"{numeric:.3f}"


def collect_db_snapshot() -> List[str]:
    """Return aggregate metrics and recent rows from the Postgres target."""
    load_environment()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set in environment variables.")

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            row = connection.execute(
                text('SELECT COUNT(*) AS cnt, MIN("timestamp") AS min_ts, MAX("timestamp") AS max_ts FROM argo_data')
            ).fetchone()
            if row is None:
                raise RuntimeError("No results returned; is the 'argo_data' table present?")

            cnt, min_ts, max_ts = row
            sample = connection.execute(
                text('SELECT "float_id","timestamp","latitude","longitude" FROM argo_data ORDER BY "timestamp" DESC LIMIT 5')
            ).fetchall()
    finally:
        engine.dispose()

    lines = [
        f"argo_data rows: {cnt}",
        f"min(timestamp): {min_ts}",
        f"max(timestamp): {max_ts}",
        "Latest 5 rows:",
    ]
    if sample:
        for float_id, ts, lat, lon in sample:
            lat_str = _format_coord(lat)
            lon_str = _format_coord(lon)
            lines.append(f"  {float_id} @ {ts} ({lat_str}, {lon_str})")
    else:
        lines.append("  (no records available)")
    return lines


class DataGeneratorGUI(tk.Tk):
    """Desktop application for managing ARGO data pipeline."""

    def __init__(self) -> None:
        super().__init__()
        self.title("🌊 FloatChart Data Generator")
        self.configure(bg=COLORS["bg_main"])
        self.resizable(True, True)
        self.minsize(600, 500)
        
        # Center window on screen
        self.geometry("700x600")
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.winfo_screenheight() // 2) - (600 // 2)
        self.geometry(f"+{x}+{y}")

        self.status_var = tk.StringVar(value=self._status_message())
        
        # Configure ttk styles
        self._configure_styles()
        self._build_layout()

    def _configure_styles(self) -> None:
        """Configure ttk styles for dark theme."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Progress bar style
        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=COLORS["bg_surface"],
            background=COLORS["accent_primary"],
            bordercolor=COLORS["border"],
            lightcolor=COLORS["accent_primary"],
            darkcolor=COLORS["accent_primary"],
        )

    def _build_layout(self) -> None:
        # Main container
        main_frame = tk.Frame(self, bg=COLORS["bg_main"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header_frame = tk.Frame(main_frame, bg=COLORS["bg_main"])
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = tk.Label(
            header_frame, 
            text="🌊 FloatChart Data Generator", 
            font=("Segoe UI", 20, "bold"),
            bg=COLORS["bg_main"],
            fg=COLORS["accent_primary"]
        )
        title_label.pack(anchor="w")
        
        subtitle_label = tk.Label(
            header_frame, 
            text="ARGO Float Data Pipeline Manager", 
            font=("Segoe UI", 11),
            bg=COLORS["bg_main"],
            fg=COLORS["text_secondary"]
        )
        subtitle_label.pack(anchor="w")
        
        # Region info
        region_label = tk.Label(
            header_frame,
            text=f"📍 Region: {REGION_LABEL}",
            font=("Segoe UI", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text_secondary"]
        )
        region_label.pack(anchor="w", pady=(5, 0))
        
        # Status panel
        status_frame = tk.Frame(main_frame, bg=COLORS["bg_panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        status_inner = tk.Frame(status_frame, bg=COLORS["bg_panel"])
        status_inner.pack(fill=tk.X, padx=15, pady=12)
        
        status_title = tk.Label(
            status_inner,
            text="Status",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"]
        )
        status_title.pack(anchor="w")
        
        status_label = tk.Label(
            status_inner, 
            textvariable=self.status_var, 
            font=("Segoe UI", 11),
            bg=COLORS["bg_panel"],
            fg=COLORS["text_primary"],
            anchor="w"
        )
        status_label.pack(anchor="w", fill=tk.X)
        
        # Progress bar
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            status_inner,
            orient="horizontal",
            length=400,
            mode="determinate",
            maximum=100,
            variable=self.progress_var,
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill=tk.X, pady=(10, 0))

        # Buttons frame
        button_frame = tk.Frame(main_frame, bg=COLORS["bg_main"])
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Update button
        self.update_button = tk.Button(
            button_frame,
            text="⬇️  Update Latest Data",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["accent_primary"],
            fg="white",
            activebackground="#1a7aef",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=10,
            command=self._handle_update,
        )
        self.update_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Database stats button
        self.stats_button = tk.Button(
            button_frame,
            text="📊  Database Snapshot",
            font=("Segoe UI", 11),
            bg=COLORS["bg_surface"],
            fg=COLORS["text_primary"],
            activebackground=COLORS["bg_panel"],
            activeforeground=COLORS["text_primary"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=10,
            command=self._handle_show_db_stats,
        )
        self.stats_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Close button
        self.quit_button = tk.Button(
            button_frame,
            text="Close",
            font=("Segoe UI", 11),
            bg=COLORS["bg_surface"],
            fg=COLORS["text_secondary"],
            activebackground=COLORS["bg_panel"],
            activeforeground=COLORS["text_primary"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=10,
            command=self.destroy
        )
        self.quit_button.pack(side=tk.RIGHT)

        # Output log frame
        log_frame = tk.Frame(main_frame, bg=COLORS["bg_panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        log_header = tk.Label(
            log_frame,
            text="📋 Activity Log",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"],
            anchor="w"
        )
        log_header.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        self.output_box = scrolledtext.ScrolledText(
            log_frame, 
            width=80, 
            height=15, 
            state="disabled",
            bg=COLORS["bg_surface"],
            fg=COLORS["text_primary"],
            font=("Consolas", 10),
            relief=tk.FLAT,
            insertbackground=COLORS["text_primary"],
            selectbackground=COLORS["accent_primary"],
            highlightthickness=0,
            padx=10,
            pady=10
        )
        self.output_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def _status_message(self) -> str:
        ts = load_last_success_timestamp()
        return f"Last successful update: {ts.isoformat()}"

    def _append_output_sync(self, message: str) -> None:
        self.output_box.configure(state="normal")
        self.output_box.insert(tk.END, f"{message}\n")
        self.output_box.see(tk.END)
        self.output_box.configure(state="disabled")

    def _append_output(self, message: str) -> None:
        self.after(0, self._append_output_sync, message)

    def _set_progress_sync(self, value: int) -> None:
        self.progress_var.set(min(max(value, 0), 100))

    def _set_progress(self, value: int) -> None:
        self.after(0, self._set_progress_sync, value)

    def _handle_update(self) -> None:
        self.update_button.configure(state=tk.DISABLED)
        self.quit_button.configure(state=tk.DISABLED)
        self.stats_button.configure(state=tk.DISABLED)
        self._set_progress(0)
        threading.Thread(target=self._run_update, daemon=True).start()

    def _run_update(self) -> None:
        self._append_output("Starting update...")
        try:
            result = perform_update(
                progress_callback=self._append_output,
                progress_step_callback=self._set_progress,
            )
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._handle_failure, exc)
        else:
            self.after(0, self._handle_success, result)
        finally:
            self.after(0, self._finalize_update)

    def _handle_success(self, result: UpdateResult) -> None:
        self._present_summary(result)
        self.status_var.set(self._status_message())

    def _handle_failure(self, exc: Exception) -> None:
        messagebox.showerror("Update Failed", str(exc))
        self._append_output(f"❌ Update failed: {exc}")

    def _finalize_update(self) -> None:
        self.update_button.configure(state=tk.NORMAL)
        self.quit_button.configure(state=tk.NORMAL)
        self.stats_button.configure(state=tk.NORMAL)
        self._set_progress(100)

    def _present_summary(self, result: UpdateResult) -> None:
        self._append_output("\nSummary")
        self._append_output("-" * 40)
        self._append_output(
            f"Requested window: {result.requested_start.isoformat()} → {result.requested_end.isoformat()}"
        )
        if result.actual_min_timestamp and result.actual_max_timestamp:
            self._append_output(
                f"Returned window: {result.actual_min_timestamp.isoformat()} → {result.actual_max_timestamp.isoformat()}"
            )
        self._append_output(f"Rows downloaded: {result.downloaded_rows}")
        self._append_output(f"Rows inserted: {result.inserted_rows}")
        self._append_output(f"Unique floats: {result.unique_floats}")
        self._append_output(
            "Checkpoint updated." if result.checkpoint_updated else "Checkpoint unchanged."
        )
        self._append_output("-" * 40)

    def _handle_show_db_stats(self) -> None:
        self.stats_button.configure(state=tk.DISABLED)
        threading.Thread(target=self._run_db_stats, daemon=True).start()

    def _run_db_stats(self) -> None:
        self._append_output("Fetching database snapshot...")
        try:
            lines = collect_db_snapshot()
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._db_stats_failure, exc)
        else:
            self.after(0, self._db_stats_success, lines)

    def _db_stats_success(self, lines: List[str]) -> None:
        self._append_output("\nDatabase Snapshot")
        self._append_output("-" * 40)
        for line in lines:
            self._append_output(line)
        self._append_output("-" * 40)
        self.stats_button.configure(state=tk.NORMAL)

    def _db_stats_failure(self, exc: Exception) -> None:
        messagebox.showerror("Database Snapshot Failed", str(exc))
        self._append_output(f"❌ Database snapshot failed: {exc}")
        self.stats_button.configure(state=tk.NORMAL)


def main() -> None:
    app = DataGeneratorGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
