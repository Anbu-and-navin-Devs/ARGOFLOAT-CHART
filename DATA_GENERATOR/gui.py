"""Tkinter GUI entrypoint for the data generator."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from state_manager import load_last_success_timestamp
from update_manager import UpdateResult, perform_update


class DataGeneratorGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("FloatChart Data Generator")
        self.resizable(False, False)

        self.status_var = tk.StringVar()
        self.status_var.set(self._status_message())

        self._build_layout()

    def _build_layout(self) -> None:
        header = tk.Label(self, text="ARGO Data Updater", font=("Segoe UI", 16, "bold"))
        header.grid(row=0, column=0, columnspan=2, padx=16, pady=(16, 8))

        status_label = tk.Label(self, textvariable=self.status_var, anchor="w")
        status_label.grid(row=1, column=0, columnspan=2, sticky="we", padx=16)

        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self,
            orient="horizontal",
            length=420,
            mode="determinate",
            maximum=100,
            variable=self.progress_var,
        )
        self.progress_bar.grid(row=2, column=0, columnspan=2, padx=16, pady=(4, 12))

        self.update_button = tk.Button(
            self,
            text="Update Latest Data",
            width=24,
            command=self._handle_update,
        )
        self.update_button.grid(row=3, column=0, padx=(16, 8), pady=12)

        self.quit_button = tk.Button(self, text="Close", width=12, command=self.destroy)
        self.quit_button.grid(row=3, column=1, padx=(8, 16), pady=12)

        self.output_box = scrolledtext.ScrolledText(self, width=80, height=20, state="disabled")
        self.output_box.grid(row=4, column=0, columnspan=2, padx=16, pady=(0, 16))

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
        self._set_progress(100)

    def _present_summary(self, result: UpdateResult) -> None:
        self._append_output("\nSummary")
        self._append_output("-" * 40)
        self._append_output(f"Requested window: {result.requested_start.isoformat()} → {result.requested_end.isoformat()}")
        if result.actual_min_timestamp and result.actual_max_timestamp:
            self._append_output(
                f"Returned window: {result.actual_min_timestamp.isoformat()} → {result.actual_max_timestamp.isoformat()}"
            )
        self._append_output(f"Rows downloaded: {result.downloaded_rows}")
        self._append_output(f"Rows inserted: {result.inserted_rows}")
        self._append_output(f"Unique floats: {result.unique_floats}")
        self._append_output("Archive created." if result.archive_created else "Archive updated.")
        self._append_output("-" * 40)


def main() -> None:
    app = DataGeneratorGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
