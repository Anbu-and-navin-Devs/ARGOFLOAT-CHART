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
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DATA_GENERATOR.env_utils import load_environment
from DATA_GENERATOR.config import REGION_LABEL, CANONICAL_COLUMNS

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
    "accent_warning": "#FFA726",
    "border": "#2E3843",
}


def get_db_engine():
    """Get database engine."""
    load_environment()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set in environment variables.")
    return create_engine(database_url)


def get_db_stats():
    """Get database statistics."""
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text('''
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT float_id) as unique_floats,
                    MIN("timestamp") as min_date,
                    MAX("timestamp") as max_date
                FROM argo_data
            '''))
            row = result.fetchone()
            return {
                "total_records": row[0] or 0,
                "unique_floats": row[1] or 0,
                "min_date": row[2],
                "max_date": row[3]
            }
    except Exception as e:
        return {"error": str(e)}


class DataGeneratorGUI(tk.Tk):
    """Desktop application for managing ARGO data pipeline."""

    def __init__(self) -> None:
        super().__init__()
        self.title("🌊 FloatChart Data Generator")
        self.configure(bg=COLORS["bg_main"])
        self.resizable(True, True)
        self.minsize(750, 650)
        
        # Center window on screen
        self.geometry("800x700")
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.winfo_screenheight() // 2) - (700 // 2)
        self.geometry(f"+{x}+{y}")
        
        # Configure ttk styles
        self._configure_styles()
        self._build_layout()
        
        # Load initial DB stats
        self.after(100, self._refresh_db_stats)

    def _configure_styles(self) -> None:
        """Configure ttk styles for dark theme."""
        style = ttk.Style()
        style.theme_use('clam')
        
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
        
        region_label = tk.Label(
            header_frame,
            text=f"📍 Region: {REGION_LABEL}",
            font=("Segoe UI", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text_secondary"]
        )
        region_label.pack(anchor="w", pady=(5, 0))
        
        # Database Status Panel
        db_frame = tk.Frame(main_frame, bg=COLORS["bg_panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        db_frame.pack(fill=tk.X, pady=(0, 15))
        
        db_inner = tk.Frame(db_frame, bg=COLORS["bg_panel"])
        db_inner.pack(fill=tk.X, padx=15, pady=12)
        
        db_title = tk.Label(
            db_inner,
            text="📊 Database Status",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["bg_panel"],
            fg=COLORS["text_primary"]
        )
        db_title.pack(anchor="w")
        
        self.db_status_var = tk.StringVar(value="Loading...")
        db_status_label = tk.Label(
            db_inner, 
            textvariable=self.db_status_var, 
            font=("Segoe UI", 10),
            bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"],
            anchor="w",
            justify="left"
        )
        db_status_label.pack(anchor="w", fill=tk.X, pady=(5, 0))
        
        # Date Selection Panel
        date_frame = tk.Frame(main_frame, bg=COLORS["bg_panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        date_frame.pack(fill=tk.X, pady=(0, 15))
        
        date_inner = tk.Frame(date_frame, bg=COLORS["bg_panel"])
        date_inner.pack(fill=tk.X, padx=15, pady=12)
        
        date_title = tk.Label(
            date_inner,
            text="📅 Select Date Range for Data Fetch",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["bg_panel"],
            fg=COLORS["text_primary"]
        )
        date_title.pack(anchor="w")
        
        date_hint = tk.Label(
            date_inner,
            text="Choose the date range to fetch ARGO data. Existing data will be preserved, only new records added.",
            font=("Segoe UI", 9),
            bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"],
            wraplength=700
        )
        date_hint.pack(anchor="w", pady=(2, 10))
        
        # Date pickers row
        date_row = tk.Frame(date_inner, bg=COLORS["bg_panel"])
        date_row.pack(fill=tk.X)
        
        # Start date
        start_frame = tk.Frame(date_row, bg=COLORS["bg_panel"])
        start_frame.pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Label(
            start_frame,
            text="From:",
            font=("Segoe UI", 10),
            bg=COLORS["bg_panel"],
            fg=COLORS["text_primary"]
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        # Default: 30 days ago
        default_start = datetime.now() - timedelta(days=30)
        self.start_year = tk.Spinbox(start_frame, from_=2020, to=2030, width=5, value=default_start.year)
        self.start_year.pack(side=tk.LEFT, padx=2)
        tk.Label(start_frame, text="-", bg=COLORS["bg_panel"], fg=COLORS["text_primary"]).pack(side=tk.LEFT)
        self.start_month = tk.Spinbox(start_frame, from_=1, to=12, width=3, format="%02.0f", value=default_start.month)
        self.start_month.pack(side=tk.LEFT, padx=2)
        tk.Label(start_frame, text="-", bg=COLORS["bg_panel"], fg=COLORS["text_primary"]).pack(side=tk.LEFT)
        self.start_day = tk.Spinbox(start_frame, from_=1, to=31, width=3, format="%02.0f", value=default_start.day)
        self.start_day.pack(side=tk.LEFT, padx=2)
        
        # End date
        end_frame = tk.Frame(date_row, bg=COLORS["bg_panel"])
        end_frame.pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Label(
            end_frame,
            text="To:",
            font=("Segoe UI", 10),
            bg=COLORS["bg_panel"],
            fg=COLORS["text_primary"]
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        today = datetime.now()
        self.end_year = tk.Spinbox(end_frame, from_=2020, to=2030, width=5, value=today.year)
        self.end_year.pack(side=tk.LEFT, padx=2)
        tk.Label(end_frame, text="-", bg=COLORS["bg_panel"], fg=COLORS["text_primary"]).pack(side=tk.LEFT)
        self.end_month = tk.Spinbox(end_frame, from_=1, to=12, width=3, format="%02.0f", value=today.month)
        self.end_month.pack(side=tk.LEFT, padx=2)
        tk.Label(end_frame, text="-", bg=COLORS["bg_panel"], fg=COLORS["text_primary"]).pack(side=tk.LEFT)
        self.end_day = tk.Spinbox(end_frame, from_=1, to=31, width=3, format="%02.0f", value=today.day)
        self.end_day.pack(side=tk.LEFT, padx=2)
        
        # Quick select buttons
        quick_frame = tk.Frame(date_row, bg=COLORS["bg_panel"])
        quick_frame.pack(side=tk.LEFT, padx=(20, 0))
        
        tk.Label(
            quick_frame,
            text="Quick:",
            font=("Segoe UI", 9),
            bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"]
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        for days, label in [(7, "7d"), (30, "30d"), (90, "90d")]:
            btn = tk.Button(
                quick_frame,
                text=label,
                font=("Segoe UI", 8),
                bg=COLORS["bg_surface"],
                fg=COLORS["text_primary"],
                relief=tk.FLAT,
                cursor="hand2",
                padx=8,
                pady=2,
                command=lambda d=days: self._set_quick_date(d)
            )
            btn.pack(side=tk.LEFT, padx=2)
        
        # Progress bar
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            date_inner,
            orient="horizontal",
            length=400,
            mode="determinate",
            maximum=100,
            variable=self.progress_var,
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill=tk.X, pady=(15, 0))
        
        # Action Buttons
        button_frame = tk.Frame(main_frame, bg=COLORS["bg_main"])
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.fetch_button = tk.Button(
            button_frame,
            text="⬇️  Fetch Data",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["accent_primary"],
            fg="white",
            activebackground="#1a7aef",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=10,
            command=self._handle_fetch,
        )
        self.fetch_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.refresh_button = tk.Button(
            button_frame,
            text="🔄  Refresh Stats",
            font=("Segoe UI", 11),
            bg=COLORS["bg_surface"],
            fg=COLORS["text_primary"],
            activebackground=COLORS["bg_panel"],
            activeforeground=COLORS["text_primary"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=10,
            command=self._refresh_db_stats,
        )
        self.refresh_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_button = tk.Button(
            button_frame,
            text="🗑️  Clear All",
            font=("Segoe UI", 11),
            bg=COLORS["accent_danger"],
            fg="white",
            activebackground="#c0392b",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=10,
            command=self._handle_clear,
        )
        self.clear_button.pack(side=tk.LEFT, padx=(0, 10))
        
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
            height=12, 
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

    def _get_start_date(self) -> datetime:
        """Get start date from spinboxes."""
        return datetime(
            int(self.start_year.get()),
            int(self.start_month.get()),
            int(self.start_day.get()),
            tzinfo=timezone.utc
        )

    def _get_end_date(self) -> datetime:
        """Get end date from spinboxes."""
        return datetime(
            int(self.end_year.get()),
            int(self.end_month.get()),
            int(self.end_day.get()),
            23, 59, 59,
            tzinfo=timezone.utc
        )

    def _set_quick_date(self, days: int) -> None:
        """Set date range to last N days."""
        end = datetime.now()
        start = end - timedelta(days=days)
        
        self.start_year.delete(0, tk.END)
        self.start_year.insert(0, str(start.year))
        self.start_month.delete(0, tk.END)
        self.start_month.insert(0, str(start.month))
        self.start_day.delete(0, tk.END)
        self.start_day.insert(0, str(start.day))
        
        self.end_year.delete(0, tk.END)
        self.end_year.insert(0, str(end.year))
        self.end_month.delete(0, tk.END)
        self.end_month.insert(0, str(end.month))
        self.end_day.delete(0, tk.END)
        self.end_day.insert(0, str(end.day))

    def _refresh_db_stats(self) -> None:
        """Refresh database statistics display."""
        stats = get_db_stats()
        if "error" in stats:
            self.db_status_var.set(f"❌ Database error: {stats['error']}")
        elif stats["total_records"] == 0:
            self.db_status_var.set("📭 Database is empty. Use 'Fetch Data' to download ARGO observations.")
        else:
            min_date = stats["min_date"].strftime("%Y-%m-%d") if stats["min_date"] else "N/A"
            max_date = stats["max_date"].strftime("%Y-%m-%d") if stats["max_date"] else "N/A"
            self.db_status_var.set(
                f"📊 Records: {stats['total_records']:,}  |  "
                f"🚢 Floats: {stats['unique_floats']}  |  "
                f"📅 Range: {min_date} → {max_date}"
            )

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

    def _set_buttons_state(self, state: str) -> None:
        """Enable or disable all action buttons."""
        self.fetch_button.configure(state=state)
        self.refresh_button.configure(state=state)
        self.clear_button.configure(state=state)
        self.quit_button.configure(state=state)

    def _handle_fetch(self) -> None:
        """Start data fetch in background thread."""
        self._set_buttons_state(tk.DISABLED)
        self._set_progress(0)
        
        try:
            start = self._get_start_date()
            end = self._get_end_date()
        except ValueError as e:
            messagebox.showerror("Invalid Date", f"Please enter valid dates: {e}")
            self._set_buttons_state(tk.NORMAL)
            return
        
        if start > end:
            messagebox.showerror("Invalid Date Range", "Start date must be before end date.")
            self._set_buttons_state(tk.NORMAL)
            return
        
        threading.Thread(target=self._run_fetch, args=(start, end), daemon=True).start()

    def _run_fetch(self, start_dt: datetime, end_dt: datetime) -> None:
        """Run the data fetch operation."""
        from DATA_GENERATOR.pipeline.netcdf_fetcher import fetch_argo_data
        from DATA_GENERATOR.pipeline.db_loader import load_into_postgres
        
        self._append_output(f"🚀 Starting data fetch...")
        self._append_output(f"📅 Date range: {start_dt.date()} to {end_dt.date()}")
        self._append_output(f"📍 Region: {REGION_LABEL}")
        
        try:
            self._set_progress(10)
            
            # Fetch data from Argovis
            df = fetch_argo_data(start_dt, end_dt, self._append_output)
            
            self._set_progress(50)
            
            if df.empty:
                self._append_output("ℹ️ No data found for the selected date range.")
                self.after(0, self._finalize_fetch)
                return
            
            self._append_output(f"📊 Downloaded {len(df):,} records from {df['float_id'].nunique()} floats")
            
            # Load into database
            self._append_output("💾 Saving to database...")
            self._set_progress(70)
            
            total_rows, inserted_rows, _ = load_into_postgres(df)
            
            self._set_progress(100)
            self._append_output(f"✅ Inserted {inserted_rows:,} new records (skipped {total_rows - inserted_rows:,} duplicates)")
            self._append_output("🎉 Data fetch complete!")
            
        except Exception as e:
            self._append_output(f"❌ Error: {str(e)}")
            self.after(0, lambda: messagebox.showerror("Fetch Failed", str(e)))
        
        self.after(0, self._finalize_fetch)

    def _finalize_fetch(self) -> None:
        """Clean up after fetch operation."""
        self._set_buttons_state(tk.NORMAL)
        self._refresh_db_stats()

    def _handle_clear(self) -> None:
        """Clear all data from database."""
        if not messagebox.askyesno(
            "Confirm Clear",
            "Are you sure you want to delete ALL data from the database?\n\nThis action cannot be undone."
        ):
            return
        
        try:
            engine = get_db_engine()
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM argo_data"))
            self._append_output("🗑️ All data cleared from database.")
            self._refresh_db_stats()
        except Exception as e:
            messagebox.showerror("Clear Failed", str(e))
            self._append_output(f"❌ Clear failed: {e}")


def main() -> None:
    app = DataGeneratorGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
