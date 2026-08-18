from __future__ import annotations

import argparse
import base64
import sys
import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
import numpy as np

from .core import (
    Circle,
    DetectionSettings,
    detect_circles,
    label_in_current_order,
    normalize_radii,
    order_circles,
    read_media_frame,
    swap_circle_identities,
)
from .roi_io import load_roi_csv, save_roi_bundle, validate_circles


class RoiEditorApp:
    def __init__(self, root: tk.Tk, initial_media: str | None = None, initial_detect: bool = False) -> None:
        self.root = root
        self.root.title("Dish ROI Editor")
        self.root.minsize(900, 650)

        self.media_path: Path | None = None
        self.image: np.ndarray | None = None
        self.media_metadata: dict[str, int | float | str] = {}
        self.circles: list[Circle] = []
        self.selected_index: int | None = None
        self.swap_source_index: int | None = None
        self.drag_mode: str | None = None
        self.add_mode = False
        self.ordering_dirty = False
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.photo: tk.PhotoImage | None = None
        self.resize_job: str | None = None

        self.frame_var = tk.IntVar(value=0)
        self.average_var = tk.IntVar(value=30)
        self.min_radius_var = tk.IntVar(value=108)
        self.max_radius_var = tk.IntVar(value=180)
        self.sensitivity_var = tk.DoubleVar(value=40.0)
        self.columns_var = tk.IntVar(value=7)
        self.expected_count_var = tk.IntVar(value=35)
        self.uniform_radii_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Open an image or video to begin.")

        self._build_controls()
        self._build_canvas()
        self._bind_shortcuts()

        if initial_media:
            def open_initial_media() -> None:
                self.load_media(Path(initial_media))
                if initial_detect and self.image is not None:
                    self.run_detection()

            self.root.after(0, open_initial_media)

    def _build_controls(self) -> None:
        controls = ttk.Frame(self.root, padding=6)
        controls.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(controls, text="Open media", command=self.choose_media).grid(row=0, column=0, padx=2, pady=2)
        ttk.Button(controls, text="Open ROI", command=self.choose_roi).grid(row=0, column=1, padx=2, pady=2)
        ttk.Button(controls, text="Detect", command=self.run_detection).grid(row=0, column=2, padx=2, pady=2)
        ttk.Button(controls, text="Order", command=self.order_current).grid(row=0, column=3, padx=2, pady=2)
        ttk.Button(controls, text="Normalize radii", command=self.normalize_current_radii).grid(row=0, column=4, padx=2, pady=2)
        ttk.Button(controls, text="Add circle", command=self.enable_add_mode).grid(row=0, column=5, padx=2, pady=2)
        ttk.Button(controls, text="Delete selected", command=self.delete_selected).grid(row=0, column=6, padx=2, pady=2)
        ttk.Button(controls, text="Save ROI", command=self.choose_save_path).grid(row=0, column=7, padx=2, pady=2)

        fields = [
            ("Frame", self.frame_var, 0, 1_000_000),
            ("Median frames", self.average_var, 1, 120),
            ("Min radius", self.min_radius_var, 1, 2_000),
            ("Max radius", self.max_radius_var, 2, 4_000),
            ("Sensitivity", self.sensitivity_var, 1, 500),
            ("Columns (0=infer)", self.columns_var, 0, 100),
            ("Expected (0=any)", self.expected_count_var, 0, 1_000),
        ]
        for index, (label, variable, lower, upper) in enumerate(fields):
            row = 1 + index // 4
            column = (index % 4) * 2
            ttk.Label(controls, text=label).grid(row=row, column=column, padx=(4, 1), pady=3, sticky=tk.E)
            ttk.Spinbox(controls, textvariable=variable, from_=lower, to=upper, width=7).grid(
                row=row, column=column + 1, padx=(1, 4), pady=3, sticky=tk.W
            )

        ttk.Button(controls, text="PTH2 preset", command=self.apply_pth2_preset).grid(row=2, column=6, padx=4)
        ttk.Checkbutton(controls, text="Same size", variable=self.uniform_radii_var).grid(
            row=2, column=7, padx=4, sticky=tk.W
        )

    def _build_canvas(self) -> None:
        self.canvas = tk.Canvas(self.root, background="#202020", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._schedule_background_refresh)
        self.canvas.bind("<ButtonPress-1>", self.on_left_press)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_release)
        self.canvas.bind("<ButtonPress-3>", self.on_right_press)
        self.canvas.bind("<ButtonPress-2>", self.on_right_press)
        self.canvas.bind("<Control-ButtonPress-1>", self.on_right_press)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda event: self.resize_selected(1))
        self.canvas.bind("<Button-5>", lambda event: self.resize_selected(-1))

        status = ttk.Label(self.root, textvariable=self.status_var, anchor=tk.W, padding=(6, 4))
        status.pack(side=tk.BOTTOM, fill=tk.X)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Delete>", lambda _event: self.delete_selected())
        self.root.bind("<Command-s>", lambda _event: self.choose_save_path())
        self.root.bind("<Control-s>", lambda _event: self.choose_save_path())
        self.root.bind("<Escape>", lambda _event: self.cancel_modes())

    def apply_pth2_preset(self) -> None:
        self.min_radius_var.set(108)
        self.max_radius_var.set(180)
        self.sensitivity_var.set(40.0)
        self.columns_var.set(7)
        self.expected_count_var.set(35)
        self.uniform_radii_var.set(True)
        self.status_var.set("Applied the PTH2 5 x 7 detection preset.")

    def choose_media(self) -> None:
        path = filedialog.askopenfilename(
            title="Open image or video",
            filetypes=[
                ("Images and videos", "*.avi *.mp4 *.mov *.mkv *.png *.jpg *.jpeg *.tif *.tiff *.bmp"),
                ("All files", "*"),
            ],
        )
        if path:
            self.load_media(Path(path))

    def load_media(self, path: Path) -> None:
        try:
            image, metadata = read_media_frame(path, self.frame_var.get(), self.average_var.get())
        except Exception as error:
            messagebox.showerror("Could not open media", str(error))
            return
        self.media_path = path
        self.image = image
        self.media_metadata = metadata
        self.circles = []
        self.ordering_dirty = False
        self.selected_index = None
        self.swap_source_index = None
        self._refresh_background()
        self.status_var.set(
            f"Loaded {path.name}: {image.shape[1]} x {image.shape[0]}, "
            f"using {metadata.get('frames_used', 1)} frame(s)."
        )

    def choose_roi(self) -> None:
        path = filedialog.askopenfilename(title="Open ROI CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*")])
        if not path:
            return
        try:
            circles = load_roi_csv(path)
            self.circles = label_in_current_order(circles, max(0, self.columns_var.get()))
        except Exception as error:
            messagebox.showerror("Could not open ROI", str(error))
            return
        self.selected_index = None
        self.swap_source_index = None
        self.ordering_dirty = False
        self._draw_overlay()
        self.status_var.set(f"Loaded {len(self.circles)} circles from {Path(path).name}.")

    def _settings(self) -> DetectionSettings:
        return DetectionSettings(
            min_radius=self.min_radius_var.get(),
            max_radius=self.max_radius_var.get(),
            sensitivity=self.sensitivity_var.get(),
        )

    def run_detection(self) -> None:
        if self.image is None or self.media_path is None:
            messagebox.showinfo("No media", "Open an image or video first.")
            return
        try:
            image, metadata = read_media_frame(
                self.media_path,
                self.frame_var.get(),
                self.average_var.get(),
            )
            circles = detect_circles(image, self._settings())
            if self.uniform_radii_var.get():
                circles = normalize_radii(circles)
            ordered_circles = order_circles(circles, max(0, self.columns_var.get()))
        except Exception as error:
            messagebox.showerror("Detection failed", str(error))
            return
        self.image = image
        self.media_metadata = metadata
        self.circles = ordered_circles
        self.selected_index = None
        self.swap_source_index = None
        self.ordering_dirty = False
        self._refresh_background()
        self.status_var.set(f"Detected {len(self.circles)} circle(s). Inspect and refine before saving.")

    def order_current(self) -> None:
        self.circles = order_circles(self.circles, max(0, self.columns_var.get()))
        self.selected_index = None
        self.swap_source_index = None
        self.ordering_dirty = False
        self._draw_overlay()
        self.status_var.set(f"Ordered and labelled {len(self.circles)} circle(s).")

    def normalize_current_radii(self) -> None:
        self.circles = normalize_radii(self.circles)
        self._draw_overlay()
        self.status_var.set("Set all radii to the detected median. Manual resizing remains available.")

    def enable_add_mode(self) -> None:
        if self.image is None:
            messagebox.showinfo("No media", "Open an image or video first.")
            return
        self.add_mode = True
        self.status_var.set("Add mode: click the centre of the missing dish. Press Escape to cancel.")

    def cancel_modes(self) -> None:
        self.add_mode = False
        self.swap_source_index = None
        self.drag_mode = None
        self._draw_overlay()
        self.status_var.set("Cancelled the current edit mode.")

    def delete_selected(self) -> None:
        if self.selected_index is None or not (0 <= self.selected_index < len(self.circles)):
            return
        deleted = self.circles.pop(self.selected_index)
        self.ordering_dirty = True
        self.selected_index = None
        self.swap_source_index = None
        self._draw_overlay()
        self.status_var.set(f"Deleted {deleted.label or 'circle'}. Re-run Order when ready.")

    def choose_save_path(self) -> None:
        if self.image is None:
            messagebox.showinfo("No media", "Open an image or video first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Bonsai ROI file",
            defaultextension=".csv",
            initialfile="ROIdef.csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return
        self.save(Path(path))

    def save(self, path: Path) -> None:
        assert self.image is not None
        expected_count = max(0, self.expected_count_var.get())
        if self.ordering_dirty:
            messagebox.showerror("ROI ordering required", "A circle was added or deleted. Run Order before saving.")
            return
        errors = validate_circles(self.circles, self.image.shape, expected_count)
        if errors:
            messagebox.showerror("ROI validation failed", "\n".join(errors))
            return
        settings = {
            "frame_index": self.frame_var.get(),
            "average_frames": self.average_var.get(),
            "min_radius": self.min_radius_var.get(),
            "max_radius": self.max_radius_var.get(),
            "sensitivity": self.sensitivity_var.get(),
            "columns": self.columns_var.get(),
            "expected_count": expected_count,
            "uniform_radii": self.uniform_radii_var.get(),
            "media_metadata": self.media_metadata,
        }
        try:
            roi_path, qc_path, metadata_path = save_roi_bundle(
                path,
                self.circles,
                self.image,
                self.media_path,
                settings,
                expected_count,
            )
        except Exception as error:
            messagebox.showerror("Could not save ROI", str(error))
            return
        self.status_var.set(f"Saved and verified {roi_path.name}; QC: {qc_path.name}; metadata: {metadata_path.name}.")
        messagebox.showinfo("ROI saved", f"Saved and verified:\n{roi_path}\n\nQC image:\n{qc_path}")

    def _schedule_background_refresh(self, _event: tk.Event) -> None:
        if self.resize_job:
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(100, self._refresh_background)

    def _refresh_background(self) -> None:
        self.resize_job = None
        self.canvas.delete("all")
        if self.image is None:
            self.photo = None
            return
        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())
        image_height, image_width = self.image.shape[:2]
        self.scale = min(canvas_width / image_width, canvas_height / image_height)
        display_width = max(1, int(round(image_width * self.scale)))
        display_height = max(1, int(round(image_height * self.scale)))
        self.offset_x = (canvas_width - display_width) / 2
        self.offset_y = (canvas_height - display_height) / 2
        resized = cv2.resize(self.image, (display_width, display_height), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        ok, encoded = cv2.imencode(".png", rgb)
        if not ok:
            raise RuntimeError("Could not render the preview image.")
        self.photo = tk.PhotoImage(data=base64.b64encode(encoded.tobytes()))
        self.canvas.create_image(self.offset_x, self.offset_y, image=self.photo, anchor=tk.NW, tags="background")
        self._draw_overlay()

    def _draw_overlay(self) -> None:
        self.canvas.delete("overlay")
        for index, circle in enumerate(self.circles):
            x, y = self.image_to_canvas(circle.x, circle.y)
            radius = circle.radius * self.scale
            color = "#00ff66"
            width = 2
            if index == self.selected_index:
                color = "#00d9ff"
                width = 3
            if index == self.swap_source_index:
                color = "#ff9f1c"
                width = 4
            self.canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                outline=color,
                width=width,
                tags="overlay",
            )
            marker = max(2, 3 * self.scale)
            self.canvas.create_oval(x - marker, y - marker, x + marker, y + marker, fill="#ff3355", outline="", tags="overlay")
            self.canvas.create_text(
                x,
                y,
                text=circle.label or str(index + 1),
                fill="#ff3355",
                font=("TkDefaultFont", max(9, int(13 * min(1.0, self.scale)))),
                tags="overlay",
            )

    def image_to_canvas(self, x: float, y: float) -> tuple[float, float]:
        return self.offset_x + x * self.scale, self.offset_y + y * self.scale

    def canvas_to_image(self, x: float, y: float) -> tuple[float, float]:
        return (x - self.offset_x) / self.scale, (y - self.offset_y) / self.scale

    def find_circle(self, canvas_x: float, canvas_y: float) -> int | None:
        if self.image is None:
            return None
        image_x, image_y = self.canvas_to_image(canvas_x, canvas_y)
        candidates = []
        for index, circle in enumerate(self.circles):
            distance = float(np.hypot(image_x - circle.x, image_y - circle.y))
            if distance <= circle.radius + 12 / max(self.scale, 0.01):
                candidates.append((abs(distance - circle.radius), distance, index))
        if not candidates:
            return None
        inside = [candidate for candidate in candidates if candidate[1] <= self.circles[candidate[2]].radius]
        return min(inside or candidates)[2]

    def on_left_press(self, event: tk.Event) -> None:
        if self.image is None:
            return
        image_x, image_y = self.canvas_to_image(event.x, event.y)
        height, width = self.image.shape[:2]
        if not (0 <= image_x < width and 0 <= image_y < height):
            return
        if self.add_mode:
            default_radius = (
                float(np.median([circle.radius for circle in self.circles]))
                if self.circles
                else float(self.min_radius_var.get())
            )
            self.circles.append(Circle(image_x, image_y, default_radius, f"new{len(self.circles) + 1}"))
            self.ordering_dirty = True
            self.selected_index = len(self.circles) - 1
            self.add_mode = False
            self._draw_overlay()
            self.status_var.set("Added a circle. Re-run Order when ready.")
            return

        index = self.find_circle(event.x, event.y)
        self.selected_index = index
        self.drag_mode = None
        if index is not None:
            circle = self.circles[index]
            distance = float(np.hypot(image_x - circle.x, image_y - circle.y))
            self.drag_mode = "resize" if abs(distance - circle.radius) <= 12 / max(self.scale, 0.01) else "move"
        self._draw_overlay()

    def on_left_drag(self, event: tk.Event) -> None:
        if self.image is None or self.selected_index is None or self.drag_mode is None:
            return
        image_x, image_y = self.canvas_to_image(event.x, event.y)
        circle = self.circles[self.selected_index]
        if self.drag_mode == "move":
            height, width = self.image.shape[:2]
            circle.x = float(np.clip(image_x, 0, width - 1))
            circle.y = float(np.clip(image_y, 0, height - 1))
        else:
            circle.radius = max(3.0, float(np.hypot(image_x - circle.x, image_y - circle.y)))
        self._draw_overlay()

    def on_left_release(self, _event: tk.Event) -> None:
        self.drag_mode = None

    def on_right_press(self, event: tk.Event) -> str:
        index = self.find_circle(event.x, event.y)
        if index is None:
            return "break"
        if self.swap_source_index is None:
            self.swap_source_index = index
            self.status_var.set(f"Swap: right-click the circle that should exchange labels with {self.circles[index].label}.")
        elif self.swap_source_index == index:
            self.swap_source_index = None
            self.status_var.set("Cancelled label swap.")
        else:
            first = self.swap_source_index
            self.circles = swap_circle_identities(self.circles, first, index)
            self.swap_source_index = None
            self.selected_index = index
            self.status_var.set("Swapped the two circle identities.")
        self._draw_overlay()
        return "break"

    def on_mouse_wheel(self, event: tk.Event) -> None:
        self.resize_selected(1 if event.delta > 0 else -1)

    def resize_selected(self, direction: int) -> None:
        if self.selected_index is None:
            return
        self.circles[self.selected_index].radius = max(3.0, self.circles[self.selected_index].radius + direction * 2.0)
        self._draw_overlay()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect and edit Bonsai dish ROI circles.")
    parser.add_argument("media", nargs="?", help="Optional image or video to open at startup")
    parser.add_argument("--detect", action="store_true", help="Run detection immediately after opening startup media")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    root = tk.Tk()
    RoiEditorApp(root, args.media, args.detect)
    root.mainloop()


if __name__ == "__main__":
    main(sys.argv[1:])
