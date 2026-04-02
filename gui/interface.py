"""Tkinter GUI for playable FreeCell with supermove rules and numbered deals."""

# ============================================================
# REGION: Imports & Constants
# ============================================================

import math
import json
import random
import re
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import font as tkfont
from pathlib import Path

try:
    import ctypes
except ImportError:
    ctypes = None

try:
    import winsound
except ImportError:
    winsound = None

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

from game import Card, FreeCell, GameState


# ============================================================
# REGION: Utilities (Global)
# ============================================================

def _hex_to_rgb(hex_color):
    """Parses a hex color string into an RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    """Formats an RGB tuple into a hex color string."""
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def _blend_hex(a, b, t):
    """Interpolates between two hex colors by factor t."""
    t = max(0.0, min(1.0, float(t)))
    ar, ag, ab = _hex_to_rgb(a)
    br, bg, bb = _hex_to_rgb(b)
    return _rgb_to_hex(
        (
            int(round(ar + (br - ar) * t)),
            int(round(ag + (bg - ag) * t)),
            int(round(ab + (bb - ab) * t)),
        )
    )


def _ease_out_cubic(t):
    """Calculates cubic ease-out value for animation timing."""
    t = max(0.0, min(1.0, float(t)))
    return 1.0 - (1.0 - t) ** 3


def _ease_out_quad(t):
    """Calculates quadratic ease-out value for animations."""
    t = max(0.0, min(1.0, float(t)))
    return 1 - (1 - t) * (1 - t)


def _ease_in_out_sine(t):
    """Calculates sine ease-in-out for natural acceleration/deceleration."""
    t = max(0.0, min(1.0, float(t)))
    return 0.5 - 0.5 * math.cos(math.pi * t)


def _ease_in_out_sine_intense(t, intensity=1.65):
    """Sharpens sine easing so acceleration/deceleration feels more dramatic."""
    s = _ease_in_out_sine(t)
    power = max(1.0, float(intensity))
    if s < 0.5:
        return 0.5 * ((s * 2.0) ** power)
    return 1.0 - 0.5 * (((1.0 - s) * 2.0) ** power)


def _point_in_rect(px, py, x, y, w, h):
    """Checks if point (px, py) is inside rectangle (x, y, w, h)."""
    return x <= px <= x + w and y <= py <= y + h


def _rounded_rect_points(x, y, w, h, r):
    """Generates polygon coordinates for a rounded rectangle."""
    r = max(2, min(int(r), int(w // 2), int(h // 2)))
    return [
        x + r, y,
        x + w - r, y,
        x + w, y,
        x + w, y + r,
        x + w, y + h - r,
        x + w, y + h,
        x + w - r, y + h,
        x + r, y + h,
        x, y + h,
        x, y + h - r,
        x, y + r,
        x, y,
    ]


def _clamp(value, low, high):
    """Restricts a value to be within the range [low, high]."""
    return max(low, min(high, value))


# ============================================================
# REGION: HUD & Buttons (Global Helpers)
# ============================================================

def draw_menu_button(canvas, x, y, w, h, label, on_click, on_click_sound=None):
    """Draws a styled menu button with hover and press effects."""
    colors = {
        "idle": {"fill": "#0f3320", "outline": "#2d7a4f"},
        "hover": {"fill": "#174d2e", "outline": "#4aab72"},
        "press": {"fill": "#0a2418", "outline": "#2d7a4f"},
    }

    radius = 14
    rect_points = _rounded_rect_points(x, y, w, h, radius)
    glow1_points = _rounded_rect_points(x - 4, y - 4, w + 8, h + 8, radius + 4)
    glow2_points = _rounded_rect_points(x - 8, y - 8, w + 16, h + 16, radius + 6)

    glow1 = canvas.create_polygon(glow1_points, smooth=True, splinesteps=12, fill="", outline="", width=2)
    glow2 = canvas.create_polygon(glow2_points, smooth=True, splinesteps=12, fill="", outline="", width=2)

    rect = canvas.create_polygon(
        rect_points,
        smooth=True,
        splinesteps=12,
        fill=colors["idle"]["fill"],
        outline=colors["idle"]["outline"],
        width=2,
    )

    label_id = canvas.create_text(
        x + w / 2,
        y + h / 2,
        text=label,
        fill="#e8f5e9",
        font=("Georgia", 14, "bold"),
    )

    hit = canvas.create_rectangle(x, y, x + w, y + h, fill="", outline="")
    canvas.tag_raise(glow2)
    canvas.tag_raise(glow1)
    canvas.tag_raise(rect)
    canvas.tag_raise(label_id)
    canvas.tag_raise(hit)

    state = {"mode": "idle", "pressed": False, "inside": False}

    def apply_mode(mode, press_offset=0):
        fill = colors[mode]["fill"]
        outline = colors[mode]["outline"]
        canvas.itemconfig(rect, fill=fill, outline=outline)
        if mode == "hover":
            canvas.itemconfig(glow1, outline="#1e5c38")
            canvas.itemconfig(glow2, outline="#163d26")
        else:
            canvas.itemconfig(glow1, outline="")
            canvas.itemconfig(glow2, outline="")
        canvas.coords(label_id, x + w / 2, y + h / 2 + press_offset)

    def on_enter(_evt=None):
        state["inside"] = True
        if not state["pressed"]:
            state["mode"] = "hover"
            apply_mode("hover", 0)
        canvas.config(cursor="hand2")

    def on_leave(_evt=None):
        state["inside"] = False
        if not state["pressed"]:
            state["mode"] = "idle"
            apply_mode("idle", 0)
        canvas.config(cursor="")

    def on_press(_evt):
        state["pressed"] = True
        state["mode"] = "press"
        apply_mode("press", 2)

    def on_release(evt):
        was_inside = _point_in_rect(evt.x, evt.y, x, y, w, h)
        state["pressed"] = False
        state["mode"] = "hover" if was_inside else "idle"
        apply_mode(state["mode"], 0)
        if was_inside:
            if callable(on_click_sound):
                on_click_sound()
            on_click()

    for target in (hit, label_id, rect):
        canvas.tag_bind(target, "<Enter>", on_enter)
        canvas.tag_bind(target, "<Leave>", on_leave)
        canvas.tag_bind(target, "<Button-1>", on_press)
        canvas.tag_bind(target, "<ButtonRelease-1>", on_release)

    return {"glow1": glow1, "glow2": glow2, "rect": rect, "label": label_id, "hit": hit}


def draw_pill_button(canvas, cx, cy, w, h, label, on_click, on_click_sound=None, *, fill, outline, text_fill):
    """Draws a pill-shaped button on the canvas."""
    h = int(h)
    w = int(w)
    x0 = cx - w / 2
    y0 = cy - h / 2
    x1 = cx + w / 2
    y1 = cy + h / 2

    rx = max(2, int(round(h / 2)))
    points = _rounded_rect_points(x0, y0, w, h, rx)
    bg_id = canvas.create_polygon(
        points,
        smooth=True,
        splinesteps=12,
        fill=fill,
        outline=outline,
        width=1,
        tags=("hud",),
    )

    label_id = canvas.create_text(
        cx,
        cy,
        text=label,
        fill=text_fill,
        font=("Helvetica", 11, "bold"),
        tags=("hud",),
    )

    hit_id = canvas.create_rectangle(x0, y0, x1, y1, fill="", outline="", tags=("hud",))

    canvas.tag_raise(bg_id)
    canvas.tag_raise(label_id)
    canvas.tag_raise(hit_id)

    def _inside(evt):
        try:
            c = canvas.coords(hit_id)
            if not c or len(c) != 4:
                return False
            return c[0] <= evt.x <= c[2] and c[1] <= evt.y <= c[3]
        except tk.TclError:
            return False

    def on_press(_evt=None):
        canvas.config(cursor="hand2")

    def on_release(evt):
        if _inside(evt):
            if callable(on_click_sound):
                on_click_sound()
            on_click()

    for target in (hit_id, label_id, bg_id):
        canvas.tag_bind(target, "<Button-1>", on_press)
        canvas.tag_bind(target, "<ButtonRelease-1>", on_release)

    return {"bg": bg_id, "label": label_id, "hit": hit_id}


# ============================================================
# REGION: Menu Screen
# ============================================================

class MenuScreen:
    """Manages the main menu overlay."""

    CARD_SUITS = ["diamond", "heart", "club", "spade"]
    CARD_RANKS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"]
    CRT_GRID_COLOR = "#1a3d1a"
    CRT_GRID_SPACING = 32
    RAIN_CARD_W = 60
    RAIN_CARD_H = 84
    RAIN_MIN_SCALE = 0.70
    RAIN_MAX_SCALE = 1.35
    RAIN_GRAVITY = 0.035
    RAIN_MAX_SPEED = 2.4
    RAIN_SPIN_SPEED_MIN = 0.03
    RAIN_SPIN_SPEED_MAX = 0.10
    RAIN_SPIN_ACCEL = 0.0012
    RAIN_NUM_CARDS = 14
    RAIN_FALLBACK_CARDS = 8
    RAIN_SLOW_FRAME_SEC = 0.03
    RAIN_FRAME_MS = 20
    RESOLUTION_VISIBLE_ROWS = 4

    def __init__(self, canvas, on_play, on_load_test, on_open_report=None, on_set_resolution=None, get_resolution_options=None, get_current_resolution_label=None, on_show_menu=None, on_hide_menu=None, on_button_click=None):
        self.canvas = canvas
        self.on_play = on_play
        self.on_load_test = on_load_test
        self.on_open_report = on_open_report
        self.on_set_resolution = on_set_resolution
        self.get_resolution_options = get_resolution_options
        self.get_current_resolution_label = get_current_resolution_label
        self.on_show_menu = on_show_menu
        self.on_hide_menu = on_hide_menu
        self.on_button_click = on_button_click

        self._item_ids = []
        self._bg_photo = None
        self._buttons = {}
        self._test_panel_items = []
        self._panel_open = False
        self._panel_animating = False

        self._panel_geometry = None
        self._fade_overlay = None
        self._resize_job = None
        self._blink_job = None
        self._menu_active = False
        self._cursor_visible = True
        self._cursor_id = None
        self._play_text_id = None
        self._test_text_id = None
        self._resolution_text_id = None
        self._report_text_id = None
        self._menu_bind_id = None
        self._wheel_bind_id = None
        self._wheel_up_bind_id = None
        self._wheel_down_bind_id = None
        self._panel_mode = None
        self._resolution_scroll_index = 0
        self._rain_active = False
        self._rain_job = None
        self._falling_cards = []
        self._card_photos = []
        self._font_title = None
        self._font_sub = None
        self._font_menu = None
        self._font_footer = None
        self._font_ascii_title = None
        self._menu_title_text = None
        self._ui_scale = 1.0

        self._load_menu_fonts()
        self._load_menu_title_text()

    def set_ui_scale(self, scale):
        """Updates menu font and hit-area scaling for the active resolution."""
        new_scale = max(0.85, min(2.4, float(scale)))
        if abs(new_scale - self._ui_scale) < 0.01:
            return

        self._ui_scale = new_scale

        if self._font_title is not None:
            self._font_title.configure(size=max(24, int(round(36 * new_scale))))
        if self._font_sub is not None:
            self._font_sub.configure(size=max(9, int(round(11 * new_scale))))
        if self._font_menu is not None:
            self._font_menu.configure(size=max(10, int(round(12 * new_scale))))
        if self._font_footer is not None:
            self._font_footer.configure(size=max(6, int(round(7 * new_scale))))
        if self._font_ascii_title is not None:
            self._font_ascii_title.configure(size=max(8, int(round(9 * new_scale))))

        if self._menu_active and not self._panel_animating and self._fade_overlay is None:
            self._redraw()

    def _load_menu_title_text(self):
        """Loads the menu title art from FREECELL.txt if available."""
        title_path = Path(__file__).resolve().parent / "assets" / "Fonts" / "FREECELL.txt"
        try:
            text = title_path.read_text(encoding="utf-8").strip("\n")
        except OSError:
            text = ""
        self._menu_title_text = text if text else None

    def _load_menu_fonts(self):
        """Loads pixel-style menu fonts with safe fallback when unavailable."""
        font_path = Path(__file__).resolve().parent / "assets" / "fonts" / "PressStart2P-Regular.ttf"
        if ctypes is not None and hasattr(ctypes, "windll") and font_path.exists():
            try:
                ctypes.windll.gdi32.AddFontResourceW(str(font_path))
            except Exception:
                pass

        try:
            self._font_title = tkfont.Font(family="Press Start 2P", size=36)
            self._font_sub = tkfont.Font(family="Press Start 2P", size=11)
            self._font_menu = tkfont.Font(family="Press Start 2P", size=12)
            self._font_footer = tkfont.Font(family="Press Start 2P", size=7)
        except Exception:
            self._font_title = tkfont.Font(family="Courier", size=28, weight="bold")
            self._font_sub = tkfont.Font(family="Courier", size=11, weight="bold")
            self._font_menu = tkfont.Font(family="Courier", size=12, weight="bold")
            self._font_footer = tkfont.Font(family="Courier", size=8)

        self._font_ascii_title = tkfont.Font(family="Consolas", size=9, weight="bold")

    def show(self):
        """Displays the menu screen and binds resize events."""
        self._menu_active = True
        self._cursor_visible = True
        if callable(self.on_show_menu):
            self.on_show_menu()
        try:
            self.canvas.itemconfigure("hud", state="hidden")
        except tk.TclError:
            pass
        self._redraw()
        self._menu_bind_id = self.canvas.bind("<Configure>", self._on_canvas_configure, add="+")
        self._wheel_bind_id = self.canvas.bind("<MouseWheel>", self._on_canvas_mousewheel, add="+")
        self._wheel_up_bind_id = self.canvas.bind("<Button-4>", self._on_canvas_mousewheel_up, add="+")
        self._wheel_down_bind_id = self.canvas.bind("<Button-5>", self._on_canvas_mousewheel_down, add="+")
        self._start_cursor_blink()

    def hide(self):
        """Hides the menu screen and cleans up resources."""
        self._menu_active = False
        self._stop_card_rain()
        if callable(self.on_hide_menu):
            self.on_hide_menu()
        try:
            self.canvas.itemconfigure("hud", state="normal")
        except tk.TclError:
            pass
        if self._blink_job is not None:
            try:
                self.canvas.after_cancel(self._blink_job)
            except tk.TclError:
                pass
            self._blink_job = None
        if self._menu_bind_id is not None:
            try:
                self.canvas.unbind("<Configure>", self._menu_bind_id)
            except tk.TclError:
                pass
            self._menu_bind_id = None
        if self._wheel_bind_id is not None:
            try:
                self.canvas.unbind("<MouseWheel>", self._wheel_bind_id)
            except tk.TclError:
                pass
            self._wheel_bind_id = None
        if self._wheel_up_bind_id is not None:
            try:
                self.canvas.unbind("<Button-4>", self._wheel_up_bind_id)
            except tk.TclError:
                pass
            self._wheel_up_bind_id = None
        if self._wheel_down_bind_id is not None:
            try:
                self.canvas.unbind("<Button-5>", self._wheel_down_bind_id)
            except tk.TclError:
                pass
            self._wheel_down_bind_id = None
        if self._resize_job is not None:
            try:
                self.canvas.after_cancel(self._resize_job)
            except tk.TclError:
                pass
            self._resize_job = None

        try:
            self.canvas.delete("menu")
        except tk.TclError:
            pass
        self._item_ids.clear()
        self._buttons.clear()
        self._test_panel_items.clear()
        self._falling_cards = []
        self._card_photos = []
        self._bg_photo = None
        self._fade_overlay = None
        self._panel_open = False
        self._panel_animating = False
        self._panel_mode = None
        self._resolution_scroll_index = 0
        self._cursor_id = None
        self._play_text_id = None
        self._test_text_id = None
        self._report_text_id = None

    def _on_canvas_configure(self, _evt=None):
        """Handles canvas resize events for the menu."""
        if self._resize_job is not None:
            return

        def run():
            self._resize_job = None
            if self._fade_overlay is not None:
                return
            if self._panel_animating:
                return
            self._redraw()

        self._resize_job = self.canvas.after(60, run)

    def _on_canvas_mousewheel(self, event):
        """Scrolls resolution panel rows with mouse wheel when panel is open."""
        if not self._panel_open or self._panel_mode != "resolution":
            return
        delta = 1 if getattr(event, "delta", 0) < 0 else -1
        self._scroll_resolution(delta)

    def _on_canvas_mousewheel_up(self, _event):
        """Linux wheel-up support for resolution panel scrolling."""
        if self._panel_open and self._panel_mode == "resolution":
            self._scroll_resolution(-1)

    def _on_canvas_mousewheel_down(self, _event):
        """Linux wheel-down support for resolution panel scrolling."""
        if self._panel_open and self._panel_mode == "resolution":
            self._scroll_resolution(1)

    def _redraw(self):
        """Redraws the entire menu interface."""
        self.canvas.update()
        w = max(1, int(self.canvas.winfo_width()))
        h = max(1, int(self.canvas.winfo_height()))

        self._clear_test_panel()
        try:
            self.canvas.delete("menu")
        except tk.TclError:
            pass
        self._item_ids.clear()
        self._buttons.clear()

        self._bg_photo = None
        self.canvas.configure(bg="#0d0f0d")
        self._item_ids.append(self.canvas.create_rectangle(0, 0, w, h, fill="#0d0f0d", outline="", tags=("menu",)))
        self._draw_crt_grid(w, h)

        cx = w / 2
        title_y = h * 0.28
        if self._menu_title_text:
            self._item_ids.append(
                self.canvas.create_text(
                    cx,
                    title_y,
                    text=self._menu_title_text,
                    fill="#00ff41",
                    font=self._font_ascii_title,
                    anchor="center",
                    justify="center",
                    tags=("menu", "menu_ui"),
                )
            )
        else:
            self._item_ids.append(
                self.canvas.create_text(
                    cx,
                    title_y,
                    text="FREECELL",
                    fill="#00ff41",
                    font=self._font_title,
                    anchor="center",
                    tags=("menu", "menu_ui"),
                )
            )
            self._item_ids.append(
                self.canvas.create_text(
                    cx,
                    title_y + 58,
                    text="SOLITAIRE",
                    fill="#00a827",
                    font=self._font_sub,
                    anchor="center",
                    tags=("menu", "menu_ui"),
                )
            )
        self._item_ids.append(
            self.canvas.create_line(
                cx - 120,
                title_y + 82,
                cx + 120,
                title_y + 82,
                fill="#0a2e0a",
                width=2,
                tags=("menu", "menu_ui"),
            )
        )

        self._draw_buttons(w, h)

        if self._panel_open:
            self._draw_active_panel()

        self._start_card_rain(w, h)
        self.canvas.tag_raise("menu_ui")

    def _draw_buttons(self, canvas_w, canvas_h):
        """Draws the main menu buttons."""
        scale = self._ui_scale
        cx = canvas_w / 2
        play_y = canvas_h * 0.55
        row_gap = max(38, int(round(44 * scale)))
        test_y = play_y + row_gap
        report_y = test_y + row_gap
        resolution_y = report_y + row_gap
        hit_w = max(220, int(round(260 * scale)))
        hit_h = max(34, int(round(38 * scale)))

        self._cursor_id = self.canvas.create_text(
            cx - max(70, int(round(90 * scale))),
            play_y,
            text="▶",
            fill="#00ff41",
            font=self._font_menu,
            anchor="center",
            tags=("menu", "menu_ui"),
        )
        self._item_ids.append(self._cursor_id)

        self._play_text_id = self.canvas.create_text(
            cx + max(8, int(round(10 * scale))),
            play_y,
            text="PLAY NOW",
            fill="#00ff41",
            font=self._font_menu,
            anchor="center",
            tags=("menu", "menu_ui"),
        )
        self._item_ids.append(self._play_text_id)

        self._test_text_id = self.canvas.create_text(
            cx + max(8, int(round(10 * scale))),
            test_y,
            text="TEST CASES",
            fill="#00a827",
            font=self._font_menu,
            anchor="center",
            tags=("menu", "menu_ui"),
        )
        self._item_ids.append(self._test_text_id)

        self._report_text_id = self.canvas.create_text(
            cx + max(8, int(round(10 * scale))),
            report_y,
            text="REPORT",
            fill="#00a827",
            font=self._font_menu,
            anchor="center",
            tags=("menu", "menu_ui"),
        )
        self._item_ids.append(self._report_text_id)

        res_label = self.get_current_resolution_label() if callable(self.get_current_resolution_label) else "1280x720"
        self._resolution_text_id = self.canvas.create_text(
            cx + max(8, int(round(10 * scale))),
            resolution_y,
            text="RESOLUTION",
            fill="#00a827",
            font=self._font_menu,
            anchor="center",
            tags=("menu", "menu_ui"),
        )
        self._item_ids.append(self._resolution_text_id)

        play_hit = self.canvas.create_rectangle(
            cx - hit_w / 2,
            play_y - hit_h / 2,
            cx + hit_w / 2,
            play_y + hit_h / 2,
            fill="",
            outline="",
            tags=("menu", "menu_ui"),
        )
        test_hit = self.canvas.create_rectangle(
            cx - hit_w / 2,
            test_y - hit_h / 2,
            cx + hit_w / 2,
            test_y + hit_h / 2,
            fill="",
            outline="",
            tags=("menu", "menu_ui"),
        )
        res_hit = self.canvas.create_rectangle(
            cx - hit_w / 2,
            resolution_y - hit_h / 2,
            cx + hit_w / 2,
            resolution_y + hit_h / 2 + max(20, int(round(28 * scale))),
            fill="",
            outline="",
            tags=("menu", "menu_ui"),
        )
        report_hit = self.canvas.create_rectangle(
            cx - hit_w / 2,
            report_y - hit_h / 2,
            cx + hit_w / 2,
            report_y + hit_h / 2,
            fill="",
            outline="",
            tags=("menu", "menu_ui"),
        )
        self._item_ids.extend([play_hit, test_hit, report_hit, res_hit])

        def _play_enter(_evt=None):
            self.canvas.itemconfig(self._play_text_id, fill="#ffffff")
            self.canvas.config(cursor="hand2")
            self._move_cursor_to(play_y)

        def _play_leave(_evt=None):
            self.canvas.itemconfig(self._play_text_id, fill="#00ff41")
            self.canvas.config(cursor="")

        def _test_enter(_evt=None):
            self.canvas.itemconfig(self._test_text_id, fill="#ffffff")
            self.canvas.config(cursor="hand2")
            self._move_cursor_to(test_y)

        def _test_leave(_evt=None):
            self.canvas.itemconfig(self._test_text_id, fill="#00a827")
            self.canvas.config(cursor="")

        def _res_enter(_evt=None):
            self.canvas.itemconfig(self._resolution_text_id, fill="#ffffff")
            self.canvas.config(cursor="hand2")
            self._move_cursor_to(resolution_y)

        def _res_leave(_evt=None):
            self.canvas.itemconfig(self._resolution_text_id, fill="#00a827")
            self.canvas.config(cursor="")

        def _report_enter(_evt=None):
            self.canvas.itemconfig(self._report_text_id, fill="#ffffff")
            self.canvas.config(cursor="hand2")
            self._move_cursor_to(report_y)

        def _report_leave(_evt=None):
            self.canvas.itemconfig(self._report_text_id, fill="#00a827")
            self.canvas.config(cursor="")

        def _play_release(_evt=None):
            self._play_button_click()
            self._fade_out(self.on_play)

        def _test_release(_evt=None):
            self._play_button_click()
            self._toggle_test_panel()

        def _res_release(_evt=None):
            self._play_button_click()
            self._toggle_resolution_panel()

        def _report_release(_evt=None):
            self._play_button_click()
            if callable(self.on_open_report):
                self.on_open_report()

        for target in (play_hit, self._play_text_id):
            self.canvas.tag_bind(target, "<Enter>", _play_enter)
            self.canvas.tag_bind(target, "<Leave>", _play_leave)
            self.canvas.tag_bind(target, "<ButtonRelease-1>", _play_release)

        for target in (test_hit, self._test_text_id):
            self.canvas.tag_bind(target, "<Enter>", _test_enter)
            self.canvas.tag_bind(target, "<Leave>", _test_leave)
            self.canvas.tag_bind(target, "<ButtonRelease-1>", _test_release)

        for target in (report_hit, self._report_text_id):
            self.canvas.tag_bind(target, "<Enter>", _report_enter)
            self.canvas.tag_bind(target, "<Leave>", _report_leave)
            self.canvas.tag_bind(target, "<ButtonRelease-1>", _report_release)

        for target in (res_hit, self._resolution_text_id):
            self.canvas.tag_bind(target, "<Enter>", _res_enter)
            self.canvas.tag_bind(target, "<Leave>", _res_leave)
            self.canvas.tag_bind(target, "<ButtonRelease-1>", _res_release)

        self._buttons["play"] = {"geom": (cx - hit_w / 2, play_y - hit_h / 2, hit_w, hit_h), "items": {"label": self._play_text_id, "hit": play_hit}}
        self._buttons["tests"] = {"geom": (cx - hit_w / 2, test_y - hit_h / 2, hit_w, hit_h), "items": {"label": self._test_text_id, "hit": test_hit}}
        self._buttons["report"] = {"geom": (cx - hit_w / 2, report_y - hit_h / 2, hit_w, hit_h), "items": {"label": self._report_text_id, "hit": report_hit}}
        self._buttons["resolution"] = {"geom": (cx - hit_w / 2, resolution_y - hit_h / 2, hit_w, hit_h), "items": {"label": self._resolution_text_id, "hit": res_hit}}

    def _play_button_click(self):
        """Plays menu button click feedback via optional callback."""
        if callable(self.on_button_click):
            try:
                self.on_button_click()
            except Exception:
                pass

    def _move_cursor_to(self, y):
        """Moves the menu cursor next to the active menu item."""
        if self._cursor_id is None:
            return
        try:
            x = self.canvas.coords(self._cursor_id)[0]
            self.canvas.coords(self._cursor_id, x, y)
        except tk.TclError:
            pass

    def _start_cursor_blink(self):
        """Starts the blink loop for the active menu cursor."""
        def _blink():
            if not self._menu_active:
                self._blink_job = None
                return
            self._cursor_visible = not self._cursor_visible
            if self._cursor_id is not None:
                try:
                    self.canvas.itemconfig(self._cursor_id, fill="#00ff41" if self._cursor_visible else "#0d0f0d")
                except tk.TclError:
                    pass
            self._blink_job = self.canvas.after(500, _blink)

        if self._blink_job is not None:
            try:
                self.canvas.after_cancel(self._blink_job)
            except tk.TclError:
                pass
        self._blink_job = self.canvas.after(500, _blink)

    def _toggle_test_panel(self):
        """Toggles the visibility of the test case selection panel."""
        self._toggle_panel("tests")

    def _toggle_resolution_panel(self):
        """Toggles the visibility of the resolution dropdown panel."""
        rows = self._resolution_rows()
        current = self.get_current_resolution_label() if callable(self.get_current_resolution_label) else ""
        if current in rows:
            visible = self._resolution_visible_row_count()
            idx = rows.index(current)
            self._resolution_scroll_index = max(0, min(idx, max(0, len(rows) - visible)))
        self._toggle_panel("resolution")

    def _toggle_panel(self, mode):
        """Generic panel toggle logic for tests/resolution panels."""
        if self._panel_animating:
            return
        if self._panel_open and self._panel_mode == mode:
            self._animate_panel_close()
            return
        self._panel_mode = mode
        self._animate_panel_open()

    def _clear_test_panel(self):
        """Removes all test panel items from the canvas."""
        for item_id in self._test_panel_items:
            try:
                self.canvas.delete(item_id)
            except tk.TclError:
                pass
        self._test_panel_items.clear()

    def _panel_target_geometry(self, panel_key, row_count):
        """Calculates panel geometry under a specific menu button."""
        scale = self._ui_scale
        (bx, by, bw, bh) = self._buttons[panel_key]["geom"]
        if panel_key == "tests":
            panel_w = max(340, int(round(380 * scale)))
        else:
            panel_w = max(240, int(round(260 * scale)))
        panel_x = bx + bw / 2 - panel_w / 2
        panel_y = by + bh + max(6, int(round(8 * scale)))
        row_h = max(30, int(round(38 * scale))) if panel_key == "tests" else max(30, int(round(36 * scale)))
        padding_tb = max(8, int(round(12 * scale)))
        panel_h = padding_tb + row_h * row_count + padding_tb
        return panel_x, panel_y, panel_w, panel_h

    def _resolution_rows(self):
        """Returns resolution labels for dropdown rows."""
        options = self.get_resolution_options() if callable(self.get_resolution_options) else []
        return options if options else ["1280x720"]

    def _resolution_visible_row_count(self):
        """Returns how many resolution rows are visible at once in the panel."""
        return max(1, int(self.RESOLUTION_VISIBLE_ROWS))

    def _scroll_resolution(self, delta):
        """Scrolls the resolution list by delta rows and redraws the active panel."""
        rows = self._resolution_rows()
        visible = min(self._resolution_visible_row_count(), len(rows))
        max_start = max(0, len(rows) - visible)
        self._resolution_scroll_index = max(0, min(self._resolution_scroll_index + int(delta), max_start))
        self._draw_active_panel()

    def _draw_active_panel(self, visible_h=None):
        """Draws whichever panel mode is currently active."""
        if self._panel_mode == "resolution":
            rows = self._resolution_rows()
            visible_rows = min(self._resolution_visible_row_count(), len(rows))
            x, y, w, full_h = self._panel_target_geometry("resolution", visible_rows)
            self._draw_resolution_panel(x, y, w, full_h if visible_h is None else visible_h)
            return

        test_rows = self._test_case_rows()
        x, y, w, full_h = self._panel_target_geometry("tests", len(test_rows))
        self._draw_test_panel(x, y, w, full_h if visible_h is None else visible_h)

    def _test_case_rows(self):
        """Returns menu test case labels and keys."""
        return [
            ("Game #1 Start (52)", "1-start"),
            ("Game #1 Mid-Game (44)", "1-mid"),
            ("Game #1 Late (16)", "1-late16"),
            ("Game #1 Late (12)", "1-late12"),
            ("Game #1 Late (10)", "1-late10"),
        ]

    def _draw_test_panel(self, x, y, w, visible_h):
        """Draws the test panel at the specified location and size."""
        self._clear_test_panel()
        radius = 12
        scale = self._ui_scale

        points = _rounded_rect_points(x, y, w, visible_h, radius)
        panel_rect = self.canvas.create_polygon(
            points, smooth=True, splinesteps=12, fill="#0a2418", outline="#2d7a4f", width=1, tags=("menu", "menu_ui")
        )
        self._test_panel_items.append(panel_rect)
        self._item_ids.append(panel_rect)

        if visible_h <= 4:
            return

        rows = self._test_case_rows()
        top_pad = max(8, int(round(12 * scale)))
        available_h = max(1, visible_h - (2 * top_pad))
        row_h = max(28, min(max(30, int(round(38 * scale))), int(available_h / max(1, len(rows)))))
        content_y0 = y + top_pad

        def fit_label(text, font_obj, max_width_px):
            if font_obj.measure(text) <= max_width_px:
                return text
            suffix = "..."
            for keep in range(len(text), 0, -1):
                candidate = text[:keep].rstrip() + suffix
                if font_obj.measure(candidate) <= max_width_px:
                    return candidate
            return suffix

        def add_row(row_idx, label, case_key):
            row_top = content_y0 + row_idx * row_h
            if row_top + row_h > y + visible_h - 6:
                return

            label_font = tkfont.Font(family="Georgia", size=max(9, int(round(11 * scale))))
            label_x = x + max(12, int(round(16 * scale)))

            btn_w = max(74, int(round(80 * scale)))
            btn_h = max(26, int(round(30 * scale)))
            btn_x = x + w - max(12, int(round(16 * scale))) - btn_w
            btn_y = row_top + (row_h - btn_h) / 2

            max_label_w = max(40, int(btn_x - label_x - max(12, int(round(14 * scale)))))
            fitted_label = fit_label(label, label_font, max_label_w)

            text_id = self.canvas.create_text(
                label_x,
                row_top + row_h / 2,
                anchor="w",
                text=fitted_label,
                fill="#a8d5b5",
                font=label_font,
                tags=("menu", "menu_ui"),
            )
            self._test_panel_items.append(text_id)
            self._item_ids.append(text_id)

            def do_load():
                self._fade_out(lambda: self.on_load_test(case_key))

            btn_items = draw_menu_button(
                self.canvas,
                btn_x,
                btn_y,
                btn_w,
                btn_h,
                "Load",
                do_load,
                on_click_sound=self._play_button_click,
            )
            for item_id in btn_items.values():
                self.canvas.itemconfigure(item_id, tags=("menu", "menu_ui"))
                self._test_panel_items.append(item_id)
                self._item_ids.append(item_id)

        for idx, (label, case_key) in enumerate(rows):
            add_row(idx, label, case_key)

    def _draw_resolution_panel(self, x, y, w, visible_h):
        """Draws a styled dropdown panel for resolution selection."""
        self._clear_test_panel()
        radius = 12
        scale = self._ui_scale

        points = _rounded_rect_points(x, y, w, visible_h, radius)
        panel_rect = self.canvas.create_polygon(
            points, smooth=True, splinesteps=12, fill="#0a2418", outline="#2d7a4f", width=1, tags=("menu", "menu_ui")
        )
        self._test_panel_items.append(panel_rect)
        self._item_ids.append(panel_rect)

        if visible_h <= 4:
            return

        rows = self._resolution_rows()
        visible_count = min(self._resolution_visible_row_count(), len(rows))
        max_start = max(0, len(rows) - visible_count)
        self._resolution_scroll_index = max(0, min(self._resolution_scroll_index, max_start))
        start = self._resolution_scroll_index
        end = start + visible_count
        shown_rows = rows[start:end]
        current = self.get_current_resolution_label() if callable(self.get_current_resolution_label) else ""
        row_h = max(30, int(round(36 * scale)))
        top_pad = max(8, int(round(12 * scale)))
        content_y0 = y + top_pad

        for row_idx, label in enumerate(shown_rows):
            row_top = content_y0 + row_idx * row_h
            if row_top + row_h > y + visible_h - 6:
                return

            tint = "#00ff41" if label == current else "#a8d5b5"
            text_id = self.canvas.create_text(
                x + max(12, int(round(16 * scale))),
                row_top + row_h / 2,
                anchor="w",
                text=label,
                fill=tint,
                font=("Georgia", max(9, int(round(11 * scale)))),
                tags=("menu", "menu_ui"),
            )
            self._test_panel_items.append(text_id)
            self._item_ids.append(text_id)

            btn_w = max(66, int(round(72 * scale)))
            btn_h = max(24, int(round(26 * scale)))
            btn_x = x + w - max(12, int(round(16 * scale))) - btn_w
            btn_y = row_top + (row_h - btn_h) / 2

            def do_set(value=label):
                if callable(self.on_set_resolution):
                    self.on_set_resolution(value)
                self._animate_panel_close()
                self._redraw()

            btn_items = draw_menu_button(
                self.canvas,
                btn_x,
                btn_y,
                btn_w,
                btn_h,
                "Set",
                do_set,
                on_click_sound=self._play_button_click,
            )
            for item_id in btn_items.values():
                self.canvas.itemconfigure(item_id, tags=("menu", "menu_ui"))
                self._test_panel_items.append(item_id)
                self._item_ids.append(item_id)

        if len(rows) > visible_count:
            arrow_x = x + w - max(14, int(round(18 * scale)))
            arrow_font = ("Consolas", max(10, int(round(11 * scale))), "bold")
            up_id = self.canvas.create_text(arrow_x, y + max(10, int(round(12 * scale))), text="▲", fill="#00ff41", font=arrow_font, anchor="center", tags=("menu", "menu_ui"))
            dn_id = self.canvas.create_text(arrow_x, y + visible_h - max(10, int(round(12 * scale))), text="▼", fill="#00ff41", font=arrow_font, anchor="center", tags=("menu", "menu_ui"))
            up_hit = self.canvas.create_rectangle(x + w - max(28, int(round(32 * scale))), y + 2, x + w - 4, y + max(18, int(round(22 * scale))), fill="", outline="", tags=("menu", "menu_ui"))
            dn_hit = self.canvas.create_rectangle(x + w - max(28, int(round(32 * scale))), y + visible_h - max(18, int(round(22 * scale))), x + w - 4, y + visible_h - 2, fill="", outline="", tags=("menu", "menu_ui"))

            for item_id in (up_id, dn_id, up_hit, dn_hit):
                self._test_panel_items.append(item_id)
                self._item_ids.append(item_id)

            def _scroll_up(_evt=None):
                self._play_button_click()
                self._scroll_resolution(-1)

            def _scroll_down(_evt=None):
                self._play_button_click()
                self._scroll_resolution(1)

            self.canvas.tag_bind(up_hit, "<ButtonRelease-1>", _scroll_up)
            self.canvas.tag_bind(dn_hit, "<ButtonRelease-1>", _scroll_down)
            self.canvas.tag_bind(up_id, "<ButtonRelease-1>", _scroll_up)
            self.canvas.tag_bind(dn_id, "<ButtonRelease-1>", _scroll_down)



    def _animate_panel_open(self):
        """Animates the opening of the test panel."""
        self._panel_animating = True
        self._panel_open = True
        start = time.time()
        duration = 0.180

        def tick():
            t = (time.time() - start) / duration
            if t >= 1.0:
                self._draw_active_panel()
                self._panel_animating = False
                return
            eased = _ease_out_cubic(t)
            if self._panel_mode == "resolution":
                full_h = self._panel_target_geometry("resolution", min(self._resolution_visible_row_count(), len(self._resolution_rows())))[3]
            else:
                full_h = self._panel_target_geometry("tests", 2)[3]
            self._draw_active_panel(full_h * eased)
            self.canvas.after(16, tick)

        tick()

    def _animate_panel_close(self):
        """Animates the closing of the test panel."""
        self._panel_animating = True
        start = time.time()
        duration = 0.150

        def tick():
            t = (time.time() - start) / duration
            if t >= 1.0:
                self._clear_test_panel()
                self._panel_open = False
                self._panel_animating = False
                self._panel_mode = None
                return
            eased = _ease_out_cubic(t)
            if self._panel_mode == "resolution":
                full_h = self._panel_target_geometry("resolution", min(self._resolution_visible_row_count(), len(self._resolution_rows())))[3]
            else:
                full_h = self._panel_target_geometry("tests", 2)[3]
            self._draw_active_panel(full_h * (1.0 - eased))
            self.canvas.after(16, tick)

        tick()

    def _fade_out(self, callback):
        """Fades out the menu screen before invoking callback."""
        self.canvas.update()
        w = max(1, int(self.canvas.winfo_width()))
        h = max(1, int(self.canvas.winfo_height()))
        if self._fade_overlay is not None:
            return

        self._fade_overlay = self.canvas.create_rectangle(0, 0, w, h, fill="#000000", outline="", stipple="")
        self._item_ids.append(self._fade_overlay)

        steps = ["", "gray75", "gray50", "gray25", "gray12", None]

        def run_step(i):
            if i == 0:
                try:
                    callback()
                except Exception:
                    pass
            if i >= len(steps):
                return
            st = steps[i]
            if st is None:
                self.canvas.itemconfig(self._fade_overlay, stipple="")
            else:
                self.canvas.itemconfig(self._fade_overlay, stipple=st)
            self.canvas.after(60, lambda: run_step(i + 1))

        run_step(0)

    def _draw_crt_grid(self, canvas_w, canvas_h):
        """Draws dim CRT grid lines behind menu UI."""
        for x in range(0, canvas_w, self.CRT_GRID_SPACING):
            item_id = self.canvas.create_line(x, 0, x, canvas_h, fill=self.CRT_GRID_COLOR, width=0.5, tags=("menu",))
            self._item_ids.append(item_id)
        for y in range(0, canvas_h, self.CRT_GRID_SPACING):
            item_id = self.canvas.create_line(0, y, canvas_w, y, fill=self.CRT_GRID_COLOR, width=0.5, tags=("menu",))
            self._item_ids.append(item_id)

    def _get_card_path(self, rank, suit):
        """Builds menu rain card asset path from rank/suit."""
        return Path(__file__).resolve().parent / "assets" / "Cards" / suit / f"{rank}_{suit}.png"

    def _spawn_card(self, canvas_w, canvas_h, delay_frames=0):
        """Creates a falling card descriptor used by the rain loop."""
        suit = random.choice(self.CARD_SUITS)
        rank = random.choice(self.CARD_RANKS)
        path = self._get_card_path(rank, suit)

        scale = random.uniform(self.RAIN_MIN_SCALE, self.RAIN_MAX_SCALE)
        card_w = max(28, int(round(self.RAIN_CARD_W * scale)))
        card_h = max(40, int(round(self.RAIN_CARD_H * scale)))

        if Image is not None:
            try:
                img = Image.open(path).resize((card_w, card_h), Image.LANCZOS)
            except Exception:
                img = Image.new("RGB", (card_w, card_h), "#ffffff")
        else:
            img = None

        # Keep menu rain away from center UI by spawning from side lanes only.
        x_min = card_w
        x_max = max(card_w + 1, canvas_w - card_w)
        usable_w = max(1, x_max - x_min)
        center_gap_ratio = 0.34
        center_gap = int(usable_w * center_gap_ratio)
        center_mid = (x_min + x_max) // 2
        gap_left = center_mid - (center_gap // 2)
        gap_right = center_mid + (center_gap // 2)

        left_lane = (x_min, max(x_min, gap_left))
        right_lane = (min(x_max, gap_right), x_max)
        lane_choices = []
        if left_lane[1] - left_lane[0] >= 6:
            lane_choices.append(left_lane)
        if right_lane[1] - right_lane[0] >= 6:
            lane_choices.append(right_lane)
        if not lane_choices:
            lane_choices.append((x_min, x_max))
        lane_start, lane_end = random.choice(lane_choices)
        spin_dir = random.choice((-1.0, 1.0))
        spin_speed = spin_dir * random.uniform(self.RAIN_SPIN_SPEED_MIN, self.RAIN_SPIN_SPEED_MAX)
        y_low = min(-canvas_h, -card_h)
        y_high = max(-canvas_h, -card_h)
        return {
            "suit": suit,
            "rank": rank,
            "img_base": img,
            "photo": None,
            "canvas_id": None,
            "w": card_w,
            "h": card_h,
            "x": random.randint(lane_start, lane_end),
            "y": random.randint(y_low, y_high),
            "vy": random.uniform(0.01, 0.08),
            "angle": random.uniform(-18.0, 18.0),
            "spin_speed": spin_speed,
            "spin_accel": spin_dir * self.RAIN_SPIN_ACCEL,
            "delay": int(max(0, delay_frames)),
            "active": delay_frames == 0,
        }

    def _start_card_rain(self, canvas_w, canvas_h):
        """Initializes falling cards and starts rain animation loop."""
        self._stop_card_rain()
        self._rain_active = True
        self._falling_cards = []
        self._card_photos = []

        for i in range(self.RAIN_NUM_CARDS):
            card = self._spawn_card(canvas_w, canvas_h, delay_frames=i * 14)
            card["canvas_id"] = self.canvas.create_image(card["x"], card["y"], image=None, anchor="center", tags=("menu",))
            self._item_ids.append(card["canvas_id"])
            self._falling_cards.append(card)

        self._run_card_rain()

    def _stop_card_rain(self):
        """Stops rain loop and releases image references."""
        self._rain_active = False
        if self._rain_job is not None:
            try:
                self.canvas.after_cancel(self._rain_job)
            except tk.TclError:
                pass
            self._rain_job = None
        self._falling_cards = []
        self._card_photos = []

    def _run_card_rain(self):
        """Animates falling cards behind menu UI."""
        if not self._rain_active:
            self._rain_job = None
            return

        frame_start = time.time()
        canvas_w = max(1, int(self.canvas.winfo_width()))
        canvas_h = max(1, int(self.canvas.winfo_height()))

        for idx, card in enumerate(self._falling_cards):
            if card["delay"] > 0:
                card["delay"] -= 1
                continue

            if not card["active"]:
                card["active"] = True

            fall_progress = _clamp(card["y"] / max(1, canvas_h), 0.0, 1.0)
            accel_mult = 1.0 + (0.35 * fall_progress)
            card["vy"] = min(card["vy"] + (self.RAIN_GRAVITY * accel_mult), self.RAIN_MAX_SPEED)
            card["y"] += card["vy"]

            card["spin_speed"] += card["spin_accel"]
            card["angle"] += card["spin_speed"]

            photo = None
            if ImageTk is not None and card["img_base"] is not None:
                try:
                    rotated = card["img_base"].rotate(card["angle"], expand=True, resample=Image.BICUBIC)
                    photo = ImageTk.PhotoImage(rotated)
                except Exception:
                    photo = None

            if photo is not None:
                card["photo"] = photo
                self._card_photos.append(photo)
                if len(self._card_photos) > self.RAIN_NUM_CARDS * 4:
                    self._card_photos = self._card_photos[-(self.RAIN_NUM_CARDS * 2):]
                try:
                    self.canvas.itemconfig(card["canvas_id"], image=photo)
                except tk.TclError:
                    pass

            try:
                self.canvas.coords(card["canvas_id"], card["x"], card["y"])
            except tk.TclError:
                pass

            if card["y"] > canvas_h + card["h"]:
                new_card = self._spawn_card(canvas_w, canvas_h, delay_frames=0)
                new_card["canvas_id"] = card["canvas_id"]
                self._falling_cards[idx] = new_card

        frame_elapsed = time.time() - frame_start
        if frame_elapsed > self.RAIN_SLOW_FRAME_SEC and len(self._falling_cards) > self.RAIN_FALLBACK_CARDS:
            for card in self._falling_cards[self.RAIN_FALLBACK_CARDS:]:
                try:
                    self.canvas.delete(card["canvas_id"])
                except tk.TclError:
                    pass
            self._falling_cards = self._falling_cards[:self.RAIN_FALLBACK_CARDS]

        self.canvas.tag_raise("menu_ui")
        self._rain_job = self.canvas.after(self.RAIN_FRAME_MS, self._run_card_rain)


# ============================================================
# REGION: Main GUI Class
# ============================================================

class FreeCell_GUI:
    """Playable FreeCell GUI backed by the project game logic."""

    SUIT_SYMBOLS = {"H": "♥", "D": "♦", "C": "♣", "S": "♠"}
    FOUNDATION_SLOT_SUITS = ["H", "D", "S", "C"]
    WINDOW_SIZES = (
        (1280, 720),
        (1366, 768),
        (1600, 900),
        (1024, 768),
        (1920, 1080),
        (2560, 1440),
        (3840, 2160),
    )
    AI_PLAYBACK_FRAMES = 7
    AI_PLAYBACK_FRAME_MS = 11
    AI_PLAYBACK_NEXT_MOVE_MS = 90
    AI_PLAYBACK_EASE_INTENSITY = 1.65
    UNDO_LEFT_MARGIN = 22
    UNDO_BOTTOM_MARGIN = 18

    BASE_CARD_WIDTH = 72
    BASE_CARD_HEIGHT = 96
    BASE_STACK_GAP = 30
    BASE_SLOT_GAP = 24
    BASE_TOP_INNER_GAP_DELTA = 6
    BASE_TOP_MIDDLE_EXTRA_GAP = 40
    BASE_LEFT_MARGIN = 20
    BASE_TOP_MARGIN = 20
    BASE_ROW_GAP = 60
    GAME_BACKGROUND_FILE = "background.png"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FreeCell - GUI")
        self.root.configure(bg="#000000")
        self.root.resizable(False, False)
        self._resolution_index = 0

        self.state = None
        self.initial_state = None
        self.current_deal_number = None
        self.selection = None
        self.history = []
        self.win_announced = False
        self.last_solution_moves = []
        self.last_solver_name = None
        self.is_solving = False
        self._solver_cancel_event = threading.Event()
        self._active_solver_name = None

        self._init_drag_state()
        self._init_input_state()
        self._init_anim_state()
        self._init_resources()
        self._init_hud_vars()

        self._build_layout()
        self._apply_selected_resolution(self.WINDOW_SIZES[self._resolution_index], center=True)

        self._menu = MenuScreen(
            self.canvas,
            on_play=self._start_new_random_game_from_menu,
            on_load_test=self._load_test_from_menu,
            on_open_report=self.open_results_report,
            on_set_resolution=self._set_resolution_from_menu,
            get_resolution_options=self._get_resolution_options,
            get_current_resolution_label=self._get_current_resolution_label,
            on_show_menu=self._on_menu_show,
            on_hide_menu=self._on_menu_hide,
            on_button_click=self._play_click_sound,
        )
        mw, mh = self.WINDOW_SIZES[self._resolution_index]
        self._menu.set_ui_scale(self._ui_scale_for_resolution(mw, mh))
        self._menu.show()

    def run(self):
        """Starts the Tkinter main event loop."""
        self.root.mainloop()

    def _init_drag_state(self):
        """Initializes drag-related state variables."""
        self.drag = {
            "active": False,
            "source_kind": None,
            "source_idx": None,
            "source_pos": None,
            "card": None,
            "cards": [],
            "count": 1,
            "tag": None,
            "offset_x": 0, "offset_y": 0,
            "x": 0, "y": 0,
            "target_x": 0, "target_y": 0,
            "origin_x": 0, "origin_y": 0,
            "lifted": False,
            "follow_job": None,
            "follow_active": False,
            "overlay_images": [],
        }

    def _init_input_state(self):
        """Initializes input tracking state variables."""
        self.pointer_input = {
            "active": False,
            "start_x": 0, "start_y": 0,
            "last_x": 0, "last_y": 0,
            "mouse_down_time": 0.0,
            "is_dragging": False,
            "source": None,
            "hold_job": None,
            "press_preview_active": False,
            "press_preview_tag": "press_feedback",
            "press_preview_images": [],
            "press_preview_source": None,
        }
        self._press_hold_ms = 200

    def _init_anim_state(self):
        """Initializes animation state variables."""
        self.auto_move_anim = {
            "active": False,
            "tag": "auto_move_card",
            "overlay_images": [],
        }
        self._click_feedback_active = False
        self._celebration_active = False
        self._celebration_seq = 0
        self._celebration_photo = None
        
        # Win sequence state
        self._win_active = False
        self._rain_active = False
        self._fountain_cards = []
        self._fountain_start = 0
        self._rain_cards = []
        self._win_photos = []
        self._rain_photos = []

        # AI playback state
        self._ai_playback_active = False
        self._ai_playback_seq = 0
        
        # Move counter and timer
        self._move_count = 0
        self._game_start_time = time.time()

    def _init_resources(self):
        """Initializes resource paths and caches."""
        self._assets_root = Path(__file__).resolve().parent / "assets"
        self._cards_root = self._assets_root / "Cards"
        self._backgrounds_root = self._assets_root / "Backgrounds"
        self._fonts_root = self._assets_root / "Fonts"
        self._sound_effects_root = self._assets_root / "Sound effects"
        self._game_background_path = self._backgrounds_root / self.GAME_BACKGROUND_FILE

        self._card_source_cache = {}
        self._card_photo_cache = {}
        self._drag_photo_cache = {}
        self._foundation_placeholder_cache = {}
        self._background_source_cache = {}
        self._background_photo_cache = {}
        self._popup_title_cache = {}
        self.card_images = self._card_photo_cache

        self._resize_timer = None
        self._last_canvas_size = (0, 0)
        self._board_origin_x = 0
        self._board_origin_y = 0

        # Default to half-size layout on startup before first snap event.
        self.CARD_WIDTH = 52
        self.CARD_HEIGHT = 72
        self.X_SPACING = 14
        self.Y_SPACING = 20
        self.BOARD_OFFSET_X = 12
        self.BOARD_OFFSET_Y = 12
        self.SLOT_GAP = self.X_SPACING
        self.STACK_GAP = self.Y_SPACING
        self.LEFT_MARGIN = self.BOARD_OFFSET_X
        self.TOP_MARGIN = self.BOARD_OFFSET_Y
        self.ROW_GAP = 34
        self.TOP_INNER_GAP_DELTA = 4
        self.TOP_MIDDLE_EXTRA_GAP = 24

    def _play_sound_effect(self, filename, fallback_bell=False):
        """Plays a WAV sound effect asynchronously from assets/Sound effects."""
        sound_path = self._sound_effects_root / str(filename)
        played = False

        if winsound is not None and sound_path.exists():
            try:
                winsound.PlaySound(
                    str(sound_path),
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
                played = True
            except RuntimeError:
                played = False

        if fallback_bell and not played:
            try:
                self.root.bell()
            except tk.TclError:
                pass

    def _play_click_sound(self):
        """Plays UI click sound for button interactions."""
        self._play_sound_effect("Click.wav")

    def _play_notification_sound(self):
        """Plays popup notification sound when a dialog appears."""
        self._play_sound_effect("Notification.wav", fallback_bell=True)

    def _init_hud_vars(self):
        """Initializes HUD variables."""
        self._hud_ids = []
        self._hud_buttons = {}
        self._hud_status_id = None
        self._hud_stack_id = None
        self._hud_timer_id = None
        self._hud_status_trace_bound = False
        self._hud_stack_trace_bound = False
        self._hud_timer_job = None
        self._hud_undo_window_id = None
        self._hud_deal_entry = None
        self._hud_deal_window_id = None
        self._hud_deal_button_geom = None
        self._report_mode_active = False
        self.report_panel = None
        self.report_text_box = None
        self.report_text_frame = None
        self.report_graph_frame = None
        self.report_graph_canvas = None
        self.report_graph_data = None
        self.report_case_var = None

    # ============================================================
    # REGION: Window & Layout
    # ============================================================

    def _build_layout(self):
        """Constructs the main window layout and widgets."""
        self.status_var = tk.StringVar(value="Welcome to FreeCell")
        self.stack_limit_var = tk.StringVar(value="")
        self.deal_var = tk.StringVar(value="")
        self.deal_code_var = tk.StringVar(value="DEAL # RANDOM")
        self._load_panel_fonts()

        self.root.configure(bg="#000000")

        width, height = self._current_board_size()
        self.main_frame = tk.Frame(self.root, bg="#00ff41", padx=3, pady=3)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        self.left_panel = tk.Frame(
            self.main_frame,
            bg="#0d0f0d",
            width=220,
            highlightbackground="#00ff41",
            highlightthickness=2,
        )
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.left_panel.pack_propagate(False)

        self.game_frame = tk.Frame(self.main_frame, bg="#0d0f0d")
        self.game_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.game_frame, width=width, height=height, bg="#1a3a1a", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.foundation_priority_var = tk.BooleanVar(value=True)

        def add_divider(parent):
            tk.Frame(parent, bg="#1a3d1a", height=2).pack(fill=tk.X, padx=10, pady=5)

        def add_section_label(parent, text):
            tk.Label(
                parent,
                text=text,
                bg="#0d0f0d",
                fg="#00a827",
                font=self._font_px_label,
                anchor="w",
                padx=10,
                justify="left",
            ).pack(fill=tk.X, pady=(9, 3))

        sidebar_title = self._load_sidebar_title_text()
        sidebar_title_font = self._fit_ascii_font_to_width(sidebar_title, max_width=196)
        tk.Label(
            self.left_panel,
            text=sidebar_title,
            bg="#0d0f0d",
            fg="#00ff41",
            font=sidebar_title_font,
            pady=8,
            padx=8,
            justify="center",
        ).pack(fill=tk.X)
        tk.Label(
            self.left_panel,
            textvariable=self.deal_code_var,
            bg="#0d0f0d",
            fg="#00a827",
            font=self._font_px_small,
            anchor="center",
            justify="center",
            pady=2,
        ).pack(fill=tk.X)
        self._update_deal_code_label()
        add_divider(self.left_panel)

        add_section_label(self.left_panel, "NAVIGATION")
        self._make_panel_btn(self.left_panel, "< BACK TO MENU", self.back_to_menu).pack(fill=tk.X, padx=10, pady=3)
        add_divider(self.left_panel)

        add_section_label(self.left_panel, "GAME")
        self._make_panel_btn(self.left_panel, "NEW GAME", self.new_game).pack(fill=tk.X, padx=10, pady=3)
        self._make_panel_btn(self.left_panel, "RESTART", self.restart_deal).pack(fill=tk.X, padx=10, pady=3)
        add_divider(self.left_panel)

        add_section_label(self.left_panel, "DEAL")
        deal_frame = tk.Frame(self.left_panel, bg="#0d0f0d")
        deal_frame.pack(fill=tk.X, padx=10, pady=3)

        self.deal_entry = tk.Entry(
            deal_frame,
            textvariable=self.deal_var,
            bg="#0d0f0d",
            fg="#00ff41",
            insertbackground="#00ff41",
            font=self._font_px_btn,
            relief="solid",
            bd=1,
            highlightbackground="#00ff41",
            highlightthickness=1,
            width=8,
        )
        self.deal_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        self.deal_entry.bind("<Return>", lambda _evt=None: self._load_deal_from_panel())

        self.load_deal_btn = tk.Button(
            deal_frame,
            text="LOAD",
            command=self._wrap_button_command(self._load_deal_from_panel),
            bg="#00ff41",
            fg="#000000",
            activebackground="#00a827",
            activeforeground="#000000",
            font=self._font_px_btn,
            relief="solid",
            bd=1,
            padx=6,
            pady=7,
            cursor="hand2",
        )
        self.load_deal_btn.pack(side=tk.LEFT, padx=(6, 0))
        add_divider(self.left_panel)

        add_section_label(self.left_panel, "SOLVER")
        self.solver_buttons = {
            "BFS": self._make_panel_btn(self.left_panel, "BFS", self.solve_with_bfs),
            "DFS": self._make_panel_btn(self.left_panel, "DFS", self.solve_with_dfs),
            "UCS": self._make_panel_btn(self.left_panel, "UCS", self.solve_with_ucs),
            "A*": self._make_panel_btn(self.left_panel, "A*", self.solve_with_astar),
        }
        for solver_btn in self.solver_buttons.values():
            solver_btn.pack(fill=tk.X, padx=10, pady=3)

        self.stop_solver_btn = self._make_panel_btn(self.left_panel, "STOP SOLVER", self.stop_current_solver)
        self.stop_solver_btn.configure(
            state=tk.DISABLED,
            bg="#220d0d",
            fg="#ff6666",
            activebackground="#3a1111",
            activeforeground="#ff9999",
        )
        self.stop_solver_btn.pack(fill=tk.X, padx=10, pady=(6, 3))

        fp_frame = tk.Frame(self.left_panel, bg="#0d0f0d")
        fp_frame.pack(fill=tk.X, padx=10, pady=6)
        tk.Checkbutton(
            fp_frame,
            text="FOUNDATION\nPRIORITY",
            variable=self.foundation_priority_var,
            command=self._play_click_sound,
            bg="#0d0f0d",
            fg="#00a827",
            activebackground="#0d0f0d",
            activeforeground="#00ff41",
            selectcolor="#0a2e0a",
            font=self._font_px_label,
            anchor="w",
        ).pack(side=tk.LEFT)
        add_divider(self.left_panel)

        self._make_panel_btn(self.left_panel, "EXPORT .TXT", self.export_actions_txt).pack(fill=tk.X, padx=10, pady=3)

        self.report_panel = tk.Frame(
            self.game_frame,
            bg="#0d0f0d",
            highlightbackground="#00ff41",
            highlightthickness=1,
            bd=0,
        )
        tk.Label(
            self.report_panel,
            text="REPORT VIEWER",
            bg="#0d0f0d",
            fg="#00ff41",
            font=self._font_px_heading,
            anchor="w",
            padx=10,
            pady=8,
        ).pack(fill=tk.X)

        report_btn_row = tk.Frame(self.report_panel, bg="#0d0f0d")
        report_btn_row.pack(fill=tk.X, padx=10, pady=(4, 2))

        tk.Button(
            report_btn_row,
            text="REFRESH",
            command=self._wrap_button_command(self._refresh_report_panel),
            bg="#0d0f0d",
            fg="#00ff41",
            activebackground="#0a2e0a",
            activeforeground="#00ff41",
            relief="solid",
            bd=1,
            highlightbackground="#00ff41",
            highlightthickness=1,
            font=self._font_px_small,
            cursor="hand2",
            padx=8,
            pady=4,
        ).pack(side=tk.LEFT)

        tk.Button(
            report_btn_row,
            text="ERASE ALL",
            command=self._wrap_button_command(self.erase_results_report),
            bg="#3a0000",
            fg="#ff6b6b",
            activebackground="#5a0000",
            activeforeground="#ffb3b3",
            relief="solid",
            bd=1,
            highlightbackground="#ff6b6b",
            highlightthickness=1,
            font=self._font_px_small,
            cursor="hand2",
            padx=8,
            pady=4,
        ).pack(side=tk.LEFT, padx=(6, 0))

        tk.Button(
            report_btn_row,
            text="GENERATE GRAPH",
            command=self._wrap_button_command(self.generate_report_graph),
            bg="#0d0f0d",
            fg="#8ad1ff",
            activebackground="#10263a",
            activeforeground="#bfe8ff",
            relief="solid",
            bd=1,
            highlightbackground="#8ad1ff",
            highlightthickness=1,
            font=self._font_px_small,
            cursor="hand2",
            padx=8,
            pady=4,
        ).pack(side=tk.LEFT, padx=(6, 0))

        tk.Button(
            report_btn_row,
            text="VIEW GRAPH",
            command=self._wrap_button_command(self._show_report_graph),
            bg="#0d0f0d",
            fg="#8ad1ff",
            activebackground="#10263a",
            activeforeground="#bfe8ff",
            relief="solid",
            bd=1,
            highlightbackground="#8ad1ff",
            highlightthickness=1,
            font=self._font_px_small,
            cursor="hand2",
            padx=8,
            pady=4,
        ).pack(side=tk.LEFT, padx=(6, 0))

        tk.Button(
            report_btn_row,
            text="VIEW REPORT",
            command=self._wrap_button_command(self._show_report_text),
            bg="#0d0f0d",
            fg="#00ff41",
            activebackground="#0a2e0a",
            activeforeground="#00ff41",
            relief="solid",
            bd=1,
            highlightbackground="#00ff41",
            highlightthickness=1,
            font=self._font_px_small,
            cursor="hand2",
            padx=8,
            pady=4,
        ).pack(side=tk.LEFT, padx=(6, 0))

        tk.Button(
            report_btn_row,
            text="HIDE",
            command=self._wrap_button_command(self._hide_report_panel),
            bg="#0d0f0d",
            fg="#00a827",
            activebackground="#0a2e0a",
            activeforeground="#00ff41",
            relief="solid",
            bd=1,
            highlightbackground="#00a827",
            highlightthickness=1,
            font=self._font_px_small,
            cursor="hand2",
            padx=8,
            pady=4,
        ).pack(side=tk.RIGHT)

        tk.Button(
            report_btn_row,
            text="BACK TO MENU",
            command=self._wrap_button_command(self._report_back_to_menu),
            bg="#0d0f0d",
            fg="#00ff41",
            activebackground="#0a2e0a",
            activeforeground="#00ff41",
            relief="solid",
            bd=1,
            highlightbackground="#00ff41",
            highlightthickness=1,
            font=self._font_px_small,
            cursor="hand2",
            padx=8,
            pady=4,
        ).pack(side=tk.RIGHT, padx=(0, 6))

        case_row = tk.Frame(self.report_panel, bg="#0d0f0d")
        case_row.pack(fill=tk.X, padx=10, pady=(2, 6))
        tk.Label(
            case_row,
            text="ENTRY #",
            bg="#0d0f0d",
            fg="#00a827",
            font=self._font_px_small,
            anchor="w",
        ).pack(side=tk.LEFT)

        self.report_case_var = tk.StringVar(value="1")
        tk.Entry(
            case_row,
            textvariable=self.report_case_var,
            bg="#0d0f0d",
            fg="#00ff41",
            insertbackground="#00ff41",
            font=self._font_px_small,
            relief="solid",
            bd=1,
            highlightbackground="#00ff41",
            highlightthickness=1,
            width=4,
        ).pack(side=tk.LEFT, padx=(6, 0), ipady=2)

        tk.Button(
            case_row,
            text="ERASE ENTRY",
            command=self._wrap_button_command(self.erase_results_report_case),
            bg="#312000",
            fg="#ffe08a",
            activebackground="#4a3300",
            activeforeground="#fff0b8",
            relief="solid",
            bd=1,
            highlightbackground="#ffe08a",
            highlightthickness=1,
            font=self._font_px_small,
            cursor="hand2",
            padx=8,
            pady=4,
        ).pack(side=tk.LEFT, padx=(8, 0))

        self.report_text_frame = tk.Frame(self.report_panel, bg="#0d0f0d")
        self.report_text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        report_scroll_y = tk.Scrollbar(self.report_text_frame, orient=tk.VERTICAL)
        report_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        report_scroll_x = tk.Scrollbar(self.report_text_frame, orient=tk.HORIZONTAL)
        report_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.report_text_box = tk.Text(
            self.report_text_frame,
            wrap=tk.NONE,
            yscrollcommand=report_scroll_y.set,
            xscrollcommand=report_scroll_x.set,
            bg="#0d0f0d",
            fg="#00ff41",
            insertbackground="#00ff41",
            relief="flat",
            bd=0,
            highlightbackground="#00ff41",
            highlightthickness=0,
            font=("Consolas", 10),
            height=24,
            padx=8,
            pady=6,
            spacing1=1,
            spacing3=1,
        )
        self.report_text_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        report_scroll_y.config(command=self.report_text_box.yview)
        report_scroll_x.config(command=self.report_text_box.xview)

        self.report_graph_frame = tk.Frame(self.report_panel, bg="#0d0f0d")
        self.report_graph_canvas = tk.Canvas(
            self.report_graph_frame,
            bg="#0d0f0d",
            highlightthickness=0,
            bd=0,
        )
        self.report_graph_canvas.pack(fill=tk.BOTH, expand=True)
        self.report_graph_canvas.bind("<Configure>", lambda _evt: self._draw_report_graph())
        self.report_panel.place_forget()

        # Create a frame with white border for the undo button
        self.undo_frame = tk.Frame(self.root, bg="#ffffff", highlightthickness=0)
        self.undo_btn = tk.Button(
            self.undo_frame,
            text="UNDO",
            command=self._wrap_button_command(self.undo_move),
            bg="#0d0f0d",
            fg="#00ff41",
            activebackground="#0a2e0a",
            activeforeground="#00ff41",
            font=self._font_px_btn,
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=22,
            pady=11,
            cursor="hand2",
        )
        self.undo_btn.pack(padx=1, pady=1)  # 1px white border from frame bg

        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        self._setup_canvas_hud()

    def _load_panel_fonts(self):
        """Loads CRT panel fonts with Press Start 2P fallback."""
        font_path = Path(__file__).resolve().parent / "assets" / "fonts" / "PressStart2P-Regular.ttf"
        if ctypes is not None and hasattr(ctypes, "windll") and font_path.exists():
            try:
                ctypes.windll.gdi32.AddFontResourceW(str(font_path))
            except Exception:
                pass
        try:
            self._font_px_heading = tkfont.Font(family="Press Start 2P", size=8)
            self._font_px_btn = tkfont.Font(family="Press Start 2P", size=7)
            self._font_px_small = tkfont.Font(family="Press Start 2P", size=6)
            self._font_px_label = tkfont.Font(family="Press Start 2P", size=6)
        except Exception:
            self._font_px_heading = tkfont.Font(family="Courier", size=10, weight="bold")
            self._font_px_btn = tkfont.Font(family="Courier", size=8, weight="bold")
            self._font_px_small = tkfont.Font(family="Courier", size=7)
            self._font_px_label = tkfont.Font(family="Courier", size=7)
        self._font_popup_ascii = tkfont.Font(family="Consolas", size=9, weight="bold")
        self._font_popup_kv = tkfont.Font(family="Consolas", size=8)

    def _load_sidebar_title_text(self):
        """Loads sidebar title art from FREECELL.txt with fallback text."""
        title_path = self._fonts_root / "FREECELL.txt"
        try:
            text = title_path.read_text(encoding="utf-8").strip("\n")
        except OSError:
            text = ""
        return text if text else "FREECELL"

    def _fit_ascii_font_to_width(self, text, max_width):
        """Creates a monospace font sized to fit the ASCII art within max width."""
        lines = [ln for ln in str(text).splitlines() if ln.strip()]
        longest = max(lines, key=len) if lines else str(text)
        for size in range(9, 2, -1):
            f = tkfont.Font(family="Consolas", size=size, weight="bold")
            if f.measure(longest) <= max_width:
                return f
        return tkfont.Font(family="Consolas", size=3, weight="bold")

    def _update_deal_code_label(self):
        """Updates sidebar deal code line based on current deal seed."""
        if not hasattr(self, "deal_code_var") or self.deal_code_var is None:
            return
        if self.current_deal_number is None:
            self.deal_code_var.set("DEAL # RANDOM")
        else:
            self.deal_code_var.set(f"DEAL # {self.current_deal_number}")

    def _ui_scale_for_resolution(self, width, height):
        """Returns UI scaling factor tuned for locked output resolutions."""
        w = int(width)
        h = int(height)
        if w >= 3840 or h >= 2160:
            return 2.15
        if w >= 2560 or h >= 1440:
            return 1.70
        if w >= 1920 or h >= 1080:
            return 1.35
        if w >= 1600 or h >= 900:
            return 1.18
        if w >= 1366 or h >= 768:
            return 1.06
        if w >= 1280 or h >= 720:
            return 1.00
        return 0.92

    def _apply_ui_scale(self, width, height):
        """Scales sidebar/menu fonts and controls to match active resolution."""
        scale = self._ui_scale_for_resolution(width, height)

        if hasattr(self, "_font_px_heading") and self._font_px_heading is not None:
            self._font_px_heading.configure(size=max(7, int(round(8 * scale))))
        if hasattr(self, "_font_px_btn") and self._font_px_btn is not None:
            self._font_px_btn.configure(size=max(6, int(round(7 * scale))))
        if hasattr(self, "_font_px_small") and self._font_px_small is not None:
            self._font_px_small.configure(size=max(5, int(round(6 * scale))))
        if hasattr(self, "_font_px_label") and self._font_px_label is not None:
            self._font_px_label.configure(size=max(5, int(round(6 * scale))))
        if hasattr(self, "_font_popup_ascii") and self._font_popup_ascii is not None:
            self._font_popup_ascii.configure(size=max(7, int(round(9 * scale))))
        if hasattr(self, "_font_popup_kv") and self._font_popup_kv is not None:
            self._font_popup_kv.configure(size=max(6, int(round(8 * scale))))

        if hasattr(self, "left_panel") and self.left_panel is not None:
            self.left_panel.configure(width=max(220, int(round(220 * scale))))

        if hasattr(self, "deal_entry") and self.deal_entry is not None:
            self.deal_entry.configure(width=max(8, int(round(8 * scale))))
        if hasattr(self, "load_deal_btn") and self.load_deal_btn is not None:
            self.load_deal_btn.configure(
                font=self._font_px_btn,
                padx=max(6, int(round(6 * scale))),
                pady=max(7, int(round(7 * scale))),
            )

        if hasattr(self, "undo_btn") and self.undo_btn is not None:
            self._style_undo_button_like_placeholder()

        if hasattr(self, "_menu") and self._menu is not None:
            self._menu.set_ui_scale(scale)

    def _wrap_button_command(self, command):
        """Wraps a command so button clicks also trigger click audio."""
        if command is None:
            return None

        def _wrapped(*args, **kwargs):
            self._play_click_sound()
            return command(*args, **kwargs)

        return _wrapped

    def _make_panel_btn(self, parent, text, command):
        """Creates a CRT-styled control button for the left panel."""
        return tk.Button(
            parent,
            text=text,
            command=self._wrap_button_command(command),
            bg="#0d0f0d",
            fg="#00ff41",
            activebackground="#0a2e0a",
            activeforeground="#00ff41",
            font=self._font_px_btn,
            relief="solid",
            bd=1,
            highlightbackground="#00ff41",
            highlightthickness=1,
            anchor="w",
            padx=12,
            pady=8,
            cursor="hand2",
        )

    def _on_menu_show(self):
        """Hides gameplay control panels while the menu is visible."""
        self._hide_report_panel(silent=True)
        if hasattr(self, "left_panel") and self.left_panel.winfo_manager():
            self.left_panel.pack_forget()

    def _on_menu_hide(self):
        """Restores gameplay control panels after leaving the menu."""
        if hasattr(self, "left_panel") and not self.left_panel.winfo_manager():
            self.left_panel.pack(side=tk.LEFT, fill=tk.Y, before=self.game_frame)
        # Let geometry settle, then recompute board/hud positions in one pass.
        self.root.after_idle(self._sync_layout_after_menu_exit)

    def _sync_layout_after_menu_exit(self):
        """Re-syncs board origin and HUD positions after menu->game transition."""
        try:
            self.root.update_idletasks()
        except tk.TclError:
            return

        if self.state is not None:
            self.render()

        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
        self._update_board_origin(canvas_w, canvas_h)
        self._reposition_hud(canvas_w, canvas_h)
        self._raise_hud()

    def _is_menu_active(self):
        """Returns True when menu overlay is currently active."""
        return bool(self._menu and getattr(self._menu, "_menu_active", False))

    def _get_current_resolution_label(self):
        """Returns current resolution label for menu display."""
        w, h = self.WINDOW_SIZES[self._resolution_index]
        return f"{w}x{h}"

    def _get_resolution_options(self):
        """Returns fixed resolution labels for dropdown options."""
        return [f"{w}x{h}" for (w, h) in self.WINDOW_SIZES]

    def _current_board_size(self):
        """Returns the current scaled dimensions of the game board."""
        w = self.LEFT_MARGIN * 2 + self.CARD_WIDTH * 8 + self.SLOT_GAP * 7
        h = (self.TOP_MARGIN * 2 + self.CARD_HEIGHT * 2 + self.ROW_GAP + 7 * self.STACK_GAP + 40)
        return w, h

    def _set_resolution_from_menu(self, label):
        """Applies selected resolution from dropdown label."""
        target = str(label).strip()
        for idx, (w, h) in enumerate(self.WINDOW_SIZES):
            if target == f"{w}x{h}":
                self._resolution_index = idx
                self._apply_selected_resolution((w, h), center=True)
                return

    def _center_window_on_screen(self, width, height):
        """Calculates centered window coordinates on current display."""
        screen_w = max(1024, self.root.winfo_screenwidth())
        screen_h = max(768, self.root.winfo_screenheight())
        x = max(0, (screen_w - int(width)) // 2)
        y = max(0, (screen_h - int(height)) // 2)
        return x, y

    def _apply_selected_resolution(self, size, center=False):
        """Applies selected fixed resolution and refreshes layout once."""
        w, h = size
        if center:
            x, y = self._center_window_on_screen(w, h)
        else:
            x, y = self.root.winfo_x(), self.root.winfo_y()
        self.root.geometry(f"{int(w)}x{int(h)}+{x}+{y}")
        self.root.update_idletasks()
        self._apply_fixed_layout(int(w), int(h))

    def _apply_fixed_layout(self, w, h):
        """Applies one of fixed hardcoded board layouts and redraws immediately."""
        profiles = {
            (1024, 768): {
                "card_w": 56,
                "card_h": 76,
                "x_spacing": 14,
                "y_spacing": 24,
                "board_x": 14,
                "board_y": 16,
                "row_gap": 50,
                "top_inner_gap": 4,
                "top_middle_gap": 24,
                "undo": (20, 748),
            },
            (1280, 720): {
                "card_w": 68,
                "card_h": 92,
                "x_spacing": 18,
                "y_spacing": 26,
                "board_x": 18,
                "board_y": 16,
                "row_gap": 54,
                "top_inner_gap": 6,
                "top_middle_gap": 32,
                "undo": (24, 700),
            },
            (1366, 768): {
                "card_w": 72,
                "card_h": 96,
                "x_spacing": 20,
                "y_spacing": 28,
                "board_x": 20,
                "board_y": 18,
                "row_gap": 56,
                "top_inner_gap": 6,
                "top_middle_gap": 36,
                "undo": (24, 748),
            },
            (1600, 900): {
                "card_w": 82,
                "card_h": 110,
                "x_spacing": 24,
                "y_spacing": 32,
                "board_x": 26,
                "board_y": 20,
                "row_gap": 64,
                "top_inner_gap": 7,
                "top_middle_gap": 46,
                "undo": (28, 880),
            },
            (1920, 1080): {
                "card_w": 96,
                "card_h": 128,
                "x_spacing": 30,
                "y_spacing": 38,
                "board_x": 34,
                "board_y": 24,
                "row_gap": 74,
                "top_inner_gap": 8,
                "top_middle_gap": 56,
                "undo": (30, 1060),
            },
            (2560, 1440): {
                "card_w": 124,
                "card_h": 166,
                "x_spacing": 40,
                "y_spacing": 48,
                "board_x": 44,
                "board_y": 26,
                "row_gap": 88,
                "top_inner_gap": 10,
                "top_middle_gap": 70,
                "undo": (36, 1418),
            },
            (3840, 2160): {
                "card_w": 188,
                "card_h": 252,
                "x_spacing": 62,
                "y_spacing": 74,
                "board_x": 68,
                "board_y": 40,
                "row_gap": 128,
                "top_inner_gap": 14,
                "top_middle_gap": 108,
                "undo": (44, 2134),
            },
        }
        p = profiles.get((w, h), profiles[(1280, 720)])

        self.CARD_WIDTH = p["card_w"]
        self.CARD_HEIGHT = p["card_h"]
        self.X_SPACING = p["x_spacing"]
        self.Y_SPACING = p["y_spacing"]
        self.BOARD_OFFSET_X = p["board_x"]
        self.BOARD_OFFSET_Y = p["board_y"]

        self.SLOT_GAP = self.X_SPACING
        self.STACK_GAP = self.Y_SPACING
        self.LEFT_MARGIN = self.BOARD_OFFSET_X
        self.TOP_MARGIN = self.BOARD_OFFSET_Y
        self.ROW_GAP = p["row_gap"]
        self.TOP_INNER_GAP_DELTA = p["top_inner_gap"]
        self.TOP_MIDDLE_EXTRA_GAP = p["top_middle_gap"]

        self._apply_ui_scale(w, h)

        self.card_images.clear()
        self._card_photo_cache.clear()
        self._drag_photo_cache.clear()
        self._foundation_placeholder_cache.clear()
        self._background_photo_cache.clear()

        self._update_board_origin()

        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
        undo_x, undo_y = self._undo_near_cascade1_position(canvas_w, canvas_h)

        if hasattr(self, "_menu") and self._menu and getattr(self._menu, "_menu_active", False):
            try:
                self.canvas.itemconfigure("hud", state="hidden")
            except tk.TclError:
                pass
            self._menu._redraw()
            if hasattr(self, "_hud_undo_window_id") and self._hud_undo_window_id:
                try:
                    self.canvas.coords(self._hud_undo_window_id, undo_x, undo_y)
                except tk.TclError:
                    pass
            return

        if self.state:
            self.render()

        self._reposition_hud(canvas_w, canvas_h)
        self._raise_hud()

    def _update_board_origin(self, canvas_w=None, canvas_h=None):
        """Centers the board content within the canvas."""
        if canvas_w is None:
            canvas_w = self.canvas.winfo_width()
        if canvas_h is None:
            canvas_h = self.canvas.winfo_height()
        canvas_w = max(1, int(canvas_w))
        canvas_h = max(1, int(canvas_h))
        board_w, board_h = self._current_board_size()
        self._board_origin_x = max(0, (canvas_w - board_w) // 2)
        self._board_origin_y = max(0, (canvas_h - board_h) // 2)

    def _slot_x(self, i):
        """Calculates X coordinate for cascade slot i."""
        return self._board_origin_x + self.LEFT_MARGIN + i * (self.CARD_WIDTH + self.SLOT_GAP)

    def _top_slot_x(self, i):
        """Calculates X coordinate for top row slot i (free or foundation)."""
        left = self._board_origin_x + self.LEFT_MARGIN
        gap = max(8, self.SLOT_GAP - self.TOP_INNER_GAP_DELTA)
        if i < 4:
            return left + i * (self.CARD_WIDTH + gap)
        return left + 4 * (self.CARD_WIDTH + gap) + self.TOP_MIDDLE_EXTRA_GAP + (i - 4) * (self.CARD_WIDTH + gap)

    def _top_row_y(self):
        """Returns Y coordinate for the top row (free cells/foundations)."""
        return self._board_origin_y + self.TOP_MARGIN

    def _cascade_row_y(self):
        """Returns base Y coordinate for cascade columns."""
        return self._board_origin_y + self.TOP_MARGIN + self.CARD_HEIGHT + self.ROW_GAP

    def _rect_contains(self, x, y, rx, ry, rw, rh):
        """Checks if board coordinate (x, y) is inside a region."""
        return rx <= x <= rx + rw and ry <= y <= ry + rh

    def _source_card_position(self, kind, idx, state=None):
        """Determine logic-based screen coordinates for a card source."""
        board = self.state if state is None else state
        if kind == "free":
            return self._top_slot_x(idx), self._top_row_y()
        cascade = board.cascades[idx]
        if not cascade:
            return self._slot_x(idx), self._cascade_row_y()
        return self._slot_x(idx), self._cascade_row_y() + (len(cascade) - 1) * self.STACK_GAP

    # ============================================================
    # REGION: Render & Drawing
    # ============================================================

    def render(self):
        """Redraws the entire game state to the canvas."""
        if self.state is None:
            return
        self.canvas.delete("game")
        self._update_board_origin()
        self._draw_background()
        self._update_stack_limit_status()
        self._draw_top_area()
        self._draw_cascades()
        self._draw_selection_marker()
        self._raise_hud()

        if self.state.is_goal_state() and not self.win_announced:
            self.status_var.set("You win! All cards moved to foundations.")
            self._trigger_win_sequence()
            return

    def _draw_background(self):
        """Draws the background image or fallback fill color."""
        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
        bg_photo = self._get_background_photo(canvas_w, canvas_h)
        if bg_photo:
            self.canvas.create_image(0, 0, anchor="nw", image=bg_photo, tags=("game", "bg"))
        else:
            self.canvas.create_rectangle(0, 0, canvas_w, canvas_h, fill="#0f4a2b", outline="", tags=("game", "bg"))

    def _draw_slot_outline(self, x, y, tag, label=None):
        """Draws the visual container for a card slot."""
        self.draw_empty_slot(self.canvas, x, y, self.CARD_WIDTH, self.CARD_HEIGHT, slot_type="freecell", tags=("game", tag))
        if label:
            base_tint = self._get_background_theme_base()
            text_fill = _blend_hex(base_tint, "#ffffff", 0.85)
            self.canvas.create_text(x + self.CARD_WIDTH / 2, y + self.CARD_HEIGHT + 12, text=label, fill=text_fill, font=("Segoe UI", 9), tags=("game", tag))

    def _draw_rounded_rect(self, canvas, x, y, width, height, radius, fill, outline, outline_width, tags, stipple=None):
        """Draws a rounded rectangle polygon on the canvas."""
        points = _rounded_rect_points(x, y, width, height, radius)
        canvas.create_polygon(points, smooth=True, splinesteps=12, fill=fill, outline=outline, width=outline_width, stipple=stipple, tags=tags)

    def draw_empty_slot(self, canvas, x, y, width, height, slot_type, suit=None, tags=()):
        """Draws an empty placeholder for free cells or foundations."""
        base_tint = self._get_background_theme_base()
        radius = max(8, int(round(width * 0.10)))

        if slot_type == "freecell":
            fill = _blend_hex(base_tint, "#ffffff", 0.14)
            border = _blend_hex(base_tint, "#ffffff", 0.30)
            self._draw_rounded_rect(canvas, x, y, width, height, radius=radius, fill=fill, outline=border, outline_width=2, tags=tags, stipple="gray50")
        elif slot_type == "foundation":
            symbol = self.SUIT_SYMBOLS.get(suit, "")
            suit_color = "#dcdcdc"
            fill = _blend_hex(base_tint, "#000000", 0.28)
            dim_suit = _blend_hex(fill, suit_color, 0.48)
            self._draw_rounded_rect(canvas, x, y, width, height, radius=radius, fill=fill, outline=dim_suit, outline_width=3, tags=tags, stipple="gray50")
            canvas.create_text(x + width / 2, y + height / 2, text=symbol, fill=dim_suit, font=("Segoe UI Symbol", max(18, int(height * 0.44)), "bold"), tags=tags)

    def _draw_card(self, x, y, card, tags, lifted=False):
        """Draws a card face or back at the given coordinates."""
        if isinstance(tags, tuple):
            if "game" not in tags: tags = ("game",) + tags
        else:
            tags = ("game",)

        card_photo = self._get_card_photo(card)
        if card_photo:
            offset = 4 if lifted else 2
            stipple = "gray25" if lifted else "gray50"
            self.canvas.create_rectangle(x + offset, y + offset, x + self.CARD_WIDTH + offset, y + self.CARD_HEIGHT + offset, fill="#000000", outline="", stipple=stipple, tags=tags)
            self.canvas.create_image(x, y, anchor="nw", image=card_photo, tags=tags)
            if lifted:
                self.canvas.create_rectangle(x, y, x + self.CARD_WIDTH, y + self.CARD_HEIGHT, outline="#ffd98a", width=3, tags=tags)
            return

        # Fallback procedural drawing
        offset = 4 if lifted else 2
        stipple = "gray25" if lifted else "gray50"
        self.canvas.create_rectangle(x + offset, y + offset, x + self.CARD_WIDTH + offset, y + self.CARD_HEIGHT + offset, fill="#000000", outline="", stipple=stipple, tags=tags)
        
        outline = "#ffd98a" if lifted else "#222222"
        width = 3 if lifted else 2
        face_bg = "#fff8f8" if card.get_color() == "Red" else "#f8f9ff"
        self.canvas.create_rectangle(x, y, x + self.CARD_WIDTH, y + self.CARD_HEIGHT, fill=face_bg, outline=outline, width=width, tags=tags)

        suit_symbol = self.SUIT_SYMBOLS.get(card.suit, card.suit)
        rank_label = Card.RANK_NAMES[card.rank]
        ink = self._card_fill_color(card)
        
        corner = f"{rank_label}{suit_symbol}"
        self.canvas.create_text(x + 9, y + 10, text=corner, fill=ink, anchor="nw", font=("Consolas", 10, "bold"), tags=tags)
        self.canvas.create_text(x + self.CARD_WIDTH - 9, y + self.CARD_HEIGHT - 10, text=corner, fill=ink, anchor="se", font=("Consolas", 10, "bold"), tags=tags)
        self.canvas.create_text(x + self.CARD_WIDTH / 2, y + self.CARD_HEIGHT / 2 - 8, text=suit_symbol, fill=ink, font=("Segoe UI Symbol", 28, "bold"), tags=tags)
        self.canvas.create_text(x + self.CARD_WIDTH / 2, y + self.CARD_HEIGHT / 2 + 17, text=rank_label, fill=ink, font=("Consolas", 13, "bold"), tags=tags)

    def _draw_top_area(self):
        """Draws the free cells and foundation slots area."""
        y = self._top_row_y()
        dragging_free = self.drag["active"] and self.drag["source_kind"] == "free"
        
        press_src = self.pointer_input.get("press_preview_source")
        previewing_free = (press_src and press_src[0] == "free")

        for i in range(4):
            x = self._top_slot_x(i)
            tag = f"free_{i}"
            card = self.state.free_cells[i]
            if card is None:
                self.draw_empty_slot(self.canvas, x, y, self.CARD_WIDTH, self.CARD_HEIGHT, slot_type="freecell", tags=("game", tag))
            
            skip = previewing_free and press_src[1] == i
            if card and not (dragging_free and self.drag["source_idx"] == i) and not skip:
                self._draw_card(x, y, card, tags=(tag, f"card_free_{i}"))

        suits = self.FOUNDATION_SLOT_SUITS
        for i, suit in enumerate(suits):
            x = self._top_slot_x(i + 4)
            tag = f"foundation_{suit}"
            rank = self.state.foundations[suit]
            if rank > 0:
                self._draw_card(x, y, Card(rank, suit), tags=(tag, f"card_foundation_{suit}"))
            else:
                self.draw_empty_slot(self.canvas, x, y, self.CARD_WIDTH, self.CARD_HEIGHT, slot_type="foundation", suit=suit, tags=("game", tag))

    def _draw_cascades(self):
        """Draws all tableau cascades."""
        base_y = self._cascade_row_y()
        drag_casc = self.drag["active"] and self.drag["source_kind"] == "cascade"
        
        press_src = self.pointer_input.get("press_preview_source")
        prev_casc = (press_src and press_src[0] == "cascade")

        for i in range(8):
            x = self._slot_x(i)
            tag = f"cascade_{i}"
            self._draw_slot_outline(x, base_y, tag, f"Cascade {i + 1}")
            cascade = self.state.cascades[i]
            for j, card in enumerate(cascade):
                if drag_casc and self.drag["source_idx"] == i and self.drag["source_pos"] is not None and j >= self.drag["source_pos"]:
                    continue
                if prev_casc and press_src[1] == i and press_src[2] is not None and j >= press_src[2]:
                    continue
                y = base_y + j * self.STACK_GAP
                self._draw_card(x, y, card, tags=(tag, f"card_cascade_{i}_{j}"))

    def _draw_selection_marker(self):
        """Highlights the currently selected card or stack."""
        if not self.selection:
            return
        kind, idx = self.selection
        if kind == "free":
            x, y = self._top_slot_x(idx), self._top_row_y()
        else:
            x = self._slot_x(idx)
            cascade = self.state.cascades[idx]
            y = self._cascade_row_y() if not cascade else self._cascade_row_y() + (len(cascade) - 1) * self.STACK_GAP
        
        self.canvas.create_rectangle(x - 3, y - 3, x + self.CARD_WIDTH + 3, y + self.CARD_HEIGHT + 3, outline="#ffd84d", width=3)

    def _draw_drag_ghost(self, cards, target_x, target_y, alpha):
        """Draws semi-transparent ghosts of dragged cards at dest."""
        for i, card in enumerate(cards):
            y = target_y + i * self.STACK_GAP
            photo = self._get_card_photo_transformed(card, scale=1.0, angle_deg=0.0, opacity=0.30 * alpha)
            if photo:
                self.drag["overlay_images"].append(photo)
                self.canvas.create_image(target_x, y, anchor="nw", image=photo, tags=("drag_overlay",))
            else:
                fill = _blend_hex("#0f4a2b", "#f0f0f0", 0.22 * alpha)
                self.canvas.create_rectangle(target_x, y, target_x + self.CARD_WIDTH, y + self.CARD_HEIGHT, fill=fill, outline="", tags=("drag_overlay",))

    def _draw_target_column_glow(self, cascade_idx, alpha):
        """Draws a glow effect around a potential drop column."""
        if cascade_idx is None: return
        x, y = self._slot_x(cascade_idx), self._cascade_row_y()
        h = self.CARD_HEIGHT + 12 * self.STACK_GAP
        layers = [(2, 0.60), (4, 0.35), (6, 0.15)]
        for pad, strength in layers:
            color = _blend_hex("#0f4a2b", "#f8fff8", strength * alpha)
            self.canvas.create_rectangle(x - pad, y - pad, x + self.CARD_WIDTH + pad, y + h + pad, outline=color, width=2, tags=("drag_overlay",))

    def _draw_drag_frame(self, now):
        """Draws the current frame of the drag animation."""
        if not self.drag["active"]: return

        self.canvas.delete(self.drag["tag"])
        self.canvas.delete("drag_overlay")
        self.drag["overlay_images"] = []

        hover_draw_target = self.drag.get("hover_draw_target")
        if hover_draw_target:
            tkind, tval = hover_draw_target
            if tkind == "cascade":
                next_state = self.drag.get("hover_next_state")
                if next_state and self.drag.get("ghost_alpha", 0.0) > 0.0:
                    gx, gy = self._target_card_position_after_move(next_state, tkind, tval, self.drag["count"])
                    self._draw_drag_ghost(self.drag["cards"], gx, gy, self.drag.get("ghost_alpha", 0.0))

        elapsed = max(0.0, now - self.drag.get("started_at", now))
        x, y = self.drag["x"], self.drag["y"]
        cards = self.drag["cards"]
        cycle = 1.8

        if len(cards) > 1:
            top_scale = 1.0 + 0.08 * _ease_out_quad(min(1.0, elapsed / 0.12))
            shadow_w, shadow_h = self.CARD_WIDTH * top_scale, self.CARD_HEIGHT * top_scale
            self.canvas.create_rectangle(x + 6, y + 6, x + shadow_w + 6, y + shadow_h + 6, fill="#000000", outline="", stipple="gray25", tags=(self.drag["tag"],))

            stack_scale = 1.0 + 0.08 * _ease_out_quad(min(1.0, elapsed / 0.12))
            for i, card in enumerate(cards):
                photo = self._get_card_photo_transformed(card, scale=stack_scale, angle_deg=0.0, opacity=1.0)
                if photo:
                    self.drag["overlay_images"].append(photo)
                    draw_x = x + (self.CARD_WIDTH * stack_scale) / 2.0
                    draw_y = (y + i * self.STACK_GAP) + (self.CARD_HEIGHT * stack_scale) / 2.0
                    self.canvas.create_image(draw_x, draw_y, anchor="center", image=photo, tags=(self.drag["tag"],))
                else:
                    self._draw_card(x, y + i * self.STACK_GAP, card, tags=(self.drag["tag"],), lifted=True)
        else:
            top_card = cards[0]
            
            # Check for manual overrides from foundation animation
            if self.drag.get("anim_scale") is not None:
                top_scale = self.drag["anim_scale"]
            else:
                top_scale = 1.0 + 0.08 * _ease_out_quad(min(1.0, elapsed / 0.12))
                
            if self.drag.get("anim_angle") is not None:
                top_angle = self.drag["anim_angle"]
            else:
                tilt_elapsed = max(0.0, elapsed - 0.12)
                top_angle = 4.0 * math.sin((2.0 * math.pi / cycle) * tilt_elapsed)
            
            shadow = self._get_card_shadow_photo_transformed(top_card, scale=top_scale, angle_deg=top_angle * 0.6, opacity=0.42)
            if shadow:
                self.drag["overlay_images"].append(shadow)
                shadow_x = x + (self.CARD_WIDTH * top_scale) / 2.0 + 6
                shadow_y = y + (self.CARD_HEIGHT * top_scale) / 2.0 + 6
                self.canvas.create_image(shadow_x, shadow_y, anchor="center", image=shadow, tags=(self.drag["tag"],))
            
            top_photo = self._get_card_photo_transformed(top_card, scale=top_scale, angle_deg=top_angle, opacity=1.0)
            if top_photo:
                self.drag["overlay_images"].append(top_photo)
                draw_x = x + (self.CARD_WIDTH * top_scale) / 2.0
                draw_y = y + (self.CARD_HEIGHT * top_scale) / 2.0
                self.canvas.create_image(draw_x, draw_y, anchor="center", image=top_photo, tags=(self.drag["tag"],))
            else:
                self._draw_card(x, y, top_card, tags=(self.drag["tag"],), lifted=True)

        self.canvas.tag_raise(self.drag["tag"])

    def _draw_press_feedback(self, source):
        """Draws visual feedback for a card press action."""
        skind, sidx, spos, cards, sx, sy = source
        tag = self.pointer_input.get("press_preview_tag", "press_feedback")
        self.canvas.delete(tag)
        self.pointer_input["press_preview_images"] = []
        self.pointer_input["press_preview_source"] = source

        press_scale = 0.9
        spacing = self.STACK_GAP if skind != "free" else 0

        for i, card in enumerate(cards):
            y = sy + i * spacing
            photo = self._get_card_photo_transformed(card, scale=press_scale, angle_deg=0.0, opacity=1.0)
            if photo:
                self.pointer_input["press_preview_images"].append(photo)
                draw_x = sx + self.CARD_WIDTH / 2
                draw_y = y + self.CARD_HEIGHT / 2
                self.canvas.create_image(draw_x, draw_y, anchor="center", image=photo, tags=(tag,))
            else:
                self._draw_card(sx, y, card, tags=(tag,), lifted=False)

        self.pointer_input["press_preview_active"] = True
        self.canvas.tag_raise(tag)

    # ============================================================
    # REGION: HUD & Buttons
    # ============================================================

    def _setup_canvas_hud(self):
        """Initializes all HUD elements including status text and buttons."""
        if self._hud_status_id is None:
            status_font = self._font_px_small if hasattr(self, "_font_px_small") else ("Helvetica", 11)
            self._hud_status_id = self.canvas.create_text(16, 16, anchor="nw", text="", fill="#ffffff", font=status_font, tags=("hud",))
            self._hud_ids.append(self._hud_status_id)
            if not self._hud_status_trace_bound:
                self.status_var.trace_add("write", lambda *a: self.canvas.itemconfigure(self._hud_status_id, text=self.status_var.get()))
                self._hud_status_trace_bound = True
            self.canvas.itemconfigure(self._hud_status_id, text=self.status_var.get(), fill="#ffffff", font=status_font)

        if self._hud_stack_id is None:
            stack_font = self._font_px_small if hasattr(self, "_font_px_small") else ("Helvetica", 11)
            self._hud_stack_id = self.canvas.create_text(16, 40, anchor="nw", text="", fill="#00a827", font=stack_font, tags=("hud",))
            self._hud_ids.append(self._hud_stack_id)
            if not self._hud_stack_trace_bound:
                self.stack_limit_var.trace_add("write", lambda *a: self.canvas.itemconfigure(self._hud_stack_id, text=self.stack_limit_var.get()))
                self._hud_stack_trace_bound = True
            self.canvas.itemconfigure(self._hud_stack_id, text=self.stack_limit_var.get(), fill="#00a827", font=stack_font)

        if self._hud_timer_id is None:
            timer_font = self._font_px_small if hasattr(self, "_font_px_small") else ("Helvetica", 10)
            self._hud_timer_id = self.canvas.create_text(0, 0, anchor="se", text="", fill="#ffffff", font=timer_font, tags=("hud",))
            self._hud_ids.append(self._hud_timer_id)
        self._update_hud_timer()
        if self._hud_timer_job is None:
            self._schedule_hud_timer_update()

        if self._hud_undo_window_id is None:
            self._hud_undo_window_id = self.canvas.create_window(16, 16, window=self.undo_frame, anchor="nw", tags=("hud",))
            self._hud_ids.append(self._hud_undo_window_id)
        self._style_undo_button_like_placeholder()

        self._ensure_hud_buttons()
        self._reposition_hud(max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height()))
        self._raise_hud()

    def _ensure_hud_buttons(self):
        """Creates the HUD buttons if they don't exist yet."""
        return

    def _reposition_hud(self, canvas_w, canvas_h):
        """Updates positions of HUD elements based on canvas size."""
        if self._hud_stack_id: self.canvas.coords(self._hud_stack_id, 16, 40)
        if self._hud_timer_id:
            timer_x = self._top_slot_x(7) + self.CARD_WIDTH
            timer_y = self._top_row_y() - 6
            self.canvas.coords(self._hud_timer_id, timer_x, timer_y)
        if hasattr(self, "_hud_undo_window_id") and self._hud_undo_window_id:
            undo_x, undo_y = self._undo_near_cascade1_position(canvas_w, canvas_h)
            self.canvas.coords(self._hud_undo_window_id, undo_x, undo_y)
        cy = canvas_h - 16 - 18
        x_cursor = 16

        for key in ():
            btn = self._hud_buttons.get(key)
            if not btn: continue
            label = btn["label"]
            w = max(len(label) * 9 + 48, 48)
            h = 36
            cx = x_cursor + w / 2
            x0, x1 = cx - w / 2, cx + w / 2
            y0, y1 = cy - h / 2, cy + h / 2
            
            items = btn["items"]
            points = _rounded_rect_points(x0, y0, w, h, int(h / 2))
            self.canvas.coords(items["bg"], *points)
            self.canvas.coords(items["label"], cx, cy)
            self.canvas.coords(items["hit"], x0, y0, x1, y1)

            if key == "deal":
                self._hud_deal_button_geom = (x0, y0, x1, y1)
                if self._hud_deal_window_id:
                    self.canvas.coords(self._hud_deal_window_id, x1 + 50, cy)

            x_cursor += w + 10

    def _schedule_hud_timer_update(self):
        """Schedules periodic timer refresh so clock advances while idle."""
        self._hud_timer_job = self.root.after(250, self._hud_timer_tick)

    def _hud_timer_tick(self):
        """Periodic timer callback."""
        self._hud_timer_job = None
        self._update_hud_timer()
        self._schedule_hud_timer_update()

    def _update_hud_timer(self):
        """Updates HUD timer text and keeps it aligned to foundation edge."""
        if self._hud_timer_id is None or self.state is None:
            return
        try:
            self._update_board_origin()
            timer_x = self._top_slot_x(7) + self.CARD_WIDTH
            timer_y = self._top_row_y() - 6
            self.canvas.coords(self._hud_timer_id, timer_x, timer_y)
            self.canvas.itemconfigure(self._hud_timer_id, text=f"TIME {self._get_elapsed_time()}")
        except tk.TclError:
            pass

    def _style_undo_button_like_placeholder(self):
        """Styles the Undo button to match the empty-slot placeholder look with white border."""
        base_tint = self._get_background_theme_base()
        fill = _blend_hex(base_tint, "#ffffff", 0.14)
        text_fill = _blend_hex(base_tint, "#ffffff", 0.88)
        active_fill = _blend_hex(base_tint, "#ffffff", 0.22)
        self.undo_btn.configure(
            bg=fill,
            fg=text_fill,
            activebackground=active_fill,
            activeforeground=text_fill,
            font=self._font_px_btn,
            state="normal",
            cursor="hand2",
        )

    def _undo_near_cascade1_position(self, canvas_w, canvas_h):
        """Returns Undo button position to the left of Cascade 1 with safe spacing."""
        self.undo_frame.update_idletasks()
        btn_w = max(1, int(self.undo_frame.winfo_reqwidth()))
        btn_h = max(1, int(self.undo_frame.winfo_reqheight()))

        # Position to the left of cascade 1 to avoid overlap with active cards.
        x = int(self._slot_x(0) - btn_w - 20)
        base_y = self._cascade_row_y() + self.CARD_HEIGHT + int(self.STACK_GAP * 10) + 20
        y = int(min(max(8, base_y), max(8, canvas_h - btn_h - 18)))
        return x, y

    def _load_deal_from_panel(self):
        """Loads a specific deal number from the left panel entry."""
        raw = (self.deal_var.get() or "").strip()
        if not raw:
            self.new_game()
            return
        try:
            self.new_game(deal_number=int(raw))
        except ValueError:
            self.status_var.set("Deal number must be an integer.")

    def _highlight_solver(self, active_name):
        """Highlights the currently running solver button in the panel."""
        for name, btn in self.solver_buttons.items():
            if name == active_name:
                btn.configure(bg="#00ff41", fg="#000000")
            else:
                btn.configure(bg="#0d0f0d", fg="#00ff41")

    def _reset_solver_highlight(self):
        """Restores all solver buttons to idle colors."""
        for btn in self.solver_buttons.values():
            btn.configure(bg="#0d0f0d", fg="#00ff41")

    def _raise_hud(self):
        """Brings all HUD elements to the top of the display stack."""
        try:
            self.canvas.tag_raise("hud")
        except tk.TclError:
            pass

    def _toggle_deal_entry(self):
        """Toggles visibility of the deal number entry field."""
        if self._hud_deal_window_id: self._hide_deal_entry()
        else: self._show_deal_entry()

    def _show_deal_entry(self):
        """Displays the deal number entry field."""
        if not self._hud_deal_button_geom: return
        if not self._hud_deal_entry:
            self._hud_deal_entry = tk.Entry(
                self.canvas, font=("Helvetica", 11),
                bg=_blend_hex(self._get_background_theme_base(), "#000000", 0.70),
                fg="#ffffff", insertbackground="#ffffff", relief="flat", highlightthickness=0
            )
            self._hud_deal_entry.bind("<Return>", self._on_deal_entry_return)
            self._hud_deal_entry.bind("<FocusOut>", self._on_deal_entry_focus_out)

        _, _, x1, _ = self._hud_deal_button_geom
        cy = (self._hud_deal_button_geom[1] + self._hud_deal_button_geom[3]) / 2
        
        self._hud_deal_window_id = self.canvas.create_window(x1 + 50, cy, window=self._hud_deal_entry, width=80, height=24, tags=("hud",))
        self._hud_ids.append(self._hud_deal_window_id)
        self._hud_deal_entry.delete(0, tk.END)
        self._hud_deal_entry.focus_set()
        self._raise_hud()

    def _hide_deal_entry(self):
        """Hides the deal number entry field."""
        if self._hud_deal_window_id:
            try: self.canvas.delete(self._hud_deal_window_id)
            except tk.TclError: pass
            self._hud_deal_window_id = None

    def _update_stack_limit_status(self):
        """Recalculates and displays the max movable stack size in the HUD."""
        empty_free = self.state.get_empty_free_cells_count()
        empty_cols = self.state.get_empty_cascades_count()
        c_to_non = (empty_free + 1) * (2 ** empty_cols)
        
        if empty_cols > 0:
            c_to_emp = c_to_non // 2
            self.stack_limit_var.set(f"Max stack: {c_to_non} (to non-empty), {c_to_emp} (to empty)")
        else:
            self.stack_limit_var.set(f"Max stack: {c_to_non} (to non-empty), n/a (to empty)")

    # ============================================================
    # REGION: Animations
    # ============================================================

    def _schedule_drag_follow(self):
        """Schedules the next frame of the drag follow animation."""
        if not self.drag["active"]:
            self.drag["follow_job"] = None
            return

        now = time.time()
        dt = max(0.0, now - self.drag.get("last_frame_at", now))
        self.drag["last_frame_at"] = now

        if self.drag["follow_active"]:
            smoothing = 0.35
            nx = self.drag["x"] + (self.drag["target_x"] - self.drag["x"]) * smoothing
            ny = self.drag["y"] + (self.drag["target_y"] - self.drag["y"]) * smoothing
            self._move_drag_to(nx, ny)

        self._update_drag_hover_state(now, dt)
        self._draw_drag_frame(now)
        self.drag["follow_job"] = self.root.after(16, self._schedule_drag_follow)

    def _tick_auto_move_animation(self):
        """Processes one frame of an auto-move animation."""
        anim = self.auto_move_anim
        if not anim["active"]: return

        now = time.time()
        elapsed = now - anim["start_time"]
        t = _clamp(elapsed / anim["duration"], 0.0, 1.0)
        eased = t * t * (3 - 2 * t)

        nx = anim["start_x"] + (anim["end_x"] - anim["start_x"]) * eased
        ny = anim["start_y"] + (anim["end_y"] - anim["start_y"]) * eased

        # Pulse scale slightly
        ems = elapsed * 1000
        total = anim["duration"] * 1000
        scale = 1.05 if 80 < ems < total - 80 else 1.0 + 0.05 * (ems / 80.0 if ems <= 80 else (total - ems) / 80.0)
        scale = _clamp(scale, 1.0, 1.05)

        self.canvas.delete(anim["tag"])
        anim["overlay_images"].clear()

        cards = anim["cards"]
        if len(cards) == 1:
            photo = self._get_card_photo_transformed(cards[0], scale=scale, angle_deg=0.0, opacity=1.0)
            if photo:
                anim["overlay_images"].append(photo)
                self.canvas.create_image(nx + (self.CARD_WIDTH * scale)/2, ny + (self.CARD_HEIGHT * scale)/2, anchor="center", image=photo, tags=(anim["tag"],))
            else:
                self._draw_card(nx, ny, cards[0], tags=(anim["tag"],), lifted=True)
        else:
            for j, card in enumerate(cards):
                self._draw_card(nx, ny + j * self.STACK_GAP, card, tags=(anim["tag"],), lifted=True)

        self.canvas.tag_raise(anim["tag"])
        if t < 1.0:
            self.root.after(16, self._tick_auto_move_animation)
        else:
            self.canvas.delete(anim["tag"])
            foundation_card = None
            foundation_suit = None
            if anim.get("target_kind") == "foundation" and anim.get("cards"):
                foundation_card = anim["cards"][0]
                foundation_suit = anim.get("target_val")
            anim.update({"active": False, "overlay_images": []})
            if anim.get("on_complete"):
                anim["on_complete"](anim["origin_state"], anim["next_state"], anim["msg"])
            else:
                self._finalize_auto_move_state(anim["origin_state"], anim["next_state"], anim["msg"])
            if foundation_card is not None and foundation_suit is not None:
                fx, fy = self._foundation_slot_center(foundation_suit)
                self._trigger_foundation_celebration(foundation_card, fx, fy)

    def _animate_click_rejection(self, cards, source_kind, source_idx, source_pos):
        """Visualizes a rejected click action (shake effect)."""
        if self._click_feedback_active: return
        self._click_feedback_active = True

        o_state = self.state.copy()
        self.state = self._state_without_moved_source(source_kind, source_idx, source_pos, len(cards))
        self.render()

        sx = self._top_slot_x(source_idx) if source_kind == "free" else self._slot_x(source_idx)
        sy = self._top_row_y() if source_kind == "free" else self._cascade_row_y() + source_pos * self.STACK_GAP

        keyframes = [4, -4, 2, -2, 0]
        frame = {"i": 0}
        tag = "click_reject"
        overlay = []

        def tick():
            i = frame["i"]
            self.canvas.delete(tag)
            overlay.clear()
            
            offset = keyframes[i]
            photo = self._get_card_photo(cards[0])
            if photo:
                overlay.append(photo)
                self.canvas.create_image(sx + offset, sy, anchor="nw", image=photo, tags=(tag,))
            else:
                self._draw_card(sx + offset, sy, cards[0], tags=(tag,), lifted=True)

            if i < len(keyframes) - 1:
                frame["i"] += 1
                self.root.after(60, tick)
            else:
                self.canvas.delete(tag)
                self.state = o_state
                self._click_feedback_active = False
                self.render()

        tick()

    def _animate_drag_to(self, dest_x, dest_y, on_done, steps=10, interval_ms=12, effect=None):
        """Animates the drag ghost returning to a position or snapping to target."""
        self.drag["follow_active"] = False
        sx, sy = self.drag["x"], self.drag["y"]
        dx, dy = dest_x - sx, dest_y - sy
        step = {"i": 0}

        # Clear any overrides initially
        self.drag["anim_scale"] = None
        self.drag["anim_angle"] = None

        def tick():
            step["i"] += 1
            t = step["i"] / steps
            ease = 1 - (1 - t) * (1 - t)
            nx = sx + (dest_x - sx) * ease
            ny = sy + (dest_y - sy) * ease

            if effect == "foundation_snap":
                # Scale: 1.0 -> 1.18 -> 1.0
                # Parabolic curve peaking at 0.5
                parabola = 4 * t * (1 - t)
                self.drag["anim_scale"] = 1.05 + 0.15 * parabola
                
                # Tilt: 0 -> 10 -> 0
                # Sine wave for tilt
                self.drag["anim_angle"] = 10.0 * math.sin(t * math.pi)
                
                # Use standard easing for X but slight overshoot for Y? No, simple move is safer.
            
            self._move_drag_to(nx, ny)
            self._draw_drag_frame(time.time())

            if step["i"] < steps: self.root.after(interval_ms, tick)
            else:
                self.drag["anim_scale"] = None
                self.drag["anim_angle"] = None
                on_done()

        tick()

    def _foundation_slot_center(self, suit):
        """Returns center coordinates of a foundation slot for the given suit."""
        idx = self.FOUNDATION_SLOT_SUITS.index(suit)
        x = self._top_slot_x(idx + 4) + (self.CARD_WIDTH / 2)
        y = self._top_row_y() + (self.CARD_HEIGHT / 2)
        return x, y

    def _draw_celebration_card(self, card, cx, cy, scale, tilt_deg):
        """Draws one frame of celebration card transform at center coordinates."""
        self.canvas.delete("foundation_pop")
        if not (Image and ImageTk):
            return

        path = self._card_asset_path(card)
        if not (path and path.exists()):
            return

        try:
            pkey = str(path)
            if pkey not in self._card_source_cache:
                self._card_source_cache[pkey] = Image.open(path).convert("RGBA")

            base_w = max(24, int(round(self.CARD_WIDTH * scale)))
            base_h = max(32, int(round(self.CARD_HEIGHT * scale)))
            img = self._card_source_cache[pkey].resize((base_w, base_h), Image.LANCZOS)
            rotated = img.rotate(-tilt_deg, expand=True, resample=Image.BICUBIC)
            photo = ImageTk.PhotoImage(rotated)
            self._celebration_photo = photo

            self.canvas.create_image(
                cx,
                cy,
                image=photo,
                anchor="center",
                tags=("game", "foundation_pop"),
            )
            self.canvas.tag_raise("foundation_pop")
            self._raise_hud()
        except Exception:
            self.canvas.delete("foundation_pop")

    def _trigger_foundation_celebration(self, card, cx, cy):
        """Runs pop+tilt landing animation for foundation arrivals."""
        if card is None:
            return

        if self._celebration_active:
            return

        self._celebration_active = True
        self._celebration_seq += 1
        seq = self._celebration_seq

        scale_up = 1.12
        tilt_deg = 8.0
        rise_px = 6.0
        pop_ms = 90.0
        settle_ms = 50.0
        fps_ms = 16
        start_time = time.time()

        def _animate():
            if seq != self._celebration_seq:
                self.canvas.delete("foundation_pop")
                return

            elapsed = (time.time() - start_time) * 1000.0

            if elapsed <= pop_ms:
                t = elapsed / pop_ms
                t = 1 - (1 - t) ** 3
                scale = 1.0 + (scale_up - 1.0) * t
                tilt = tilt_deg * t
                y_off = -rise_px * t
            elif elapsed <= pop_ms + settle_ms:
                t = (elapsed - pop_ms) / settle_ms
                t = t ** 3
                scale = scale_up - (scale_up - 1.0) * t
                tilt = tilt_deg * (1 - t)
                y_off = -rise_px * (1 - t)
            else:
                self.canvas.delete("foundation_pop")
                self._celebration_active = False
                return

            self._draw_celebration_card(card, cx, cy + y_off, scale, tilt)
            self.canvas.after(fps_ms, _animate)

        _animate()

    def _animate_state_fade(self, to_state, duration=0.22):
        """Perform a crossfade animation between current and target state."""
        start = time.time()
        
        def tick():
            now = time.time()
            t = _clamp((now - start) / duration, 0.0, 1.0)
            self.canvas.delete("game")
            self._update_board_origin()
            self._draw_background()
            
            # Simple fade implementation: Draw `to_state` with opacity t
            # Cascades
            for i in range(8):
                x, by = self._slot_x(i), self._cascade_row_y()
                self._draw_slot_outline(x, by, "", f"Cascade {i + 1}")
                for j, card in enumerate(to_state.cascades[i]):
                    y = by + j * self.STACK_GAP
                    photo = self._get_card_photo_transformed(card, scale=1.0, angle_deg=0.0, opacity=t)
                    if photo:
                        self.canvas.create_image(x, y, anchor="nw", image=photo)
                    else:
                        self._draw_card(x, y, card, tags="")

            # Top area
            ty = self._top_row_y()
            for i in range(4):
                x = self._top_slot_x(i)
                card = to_state.free_cells[i]
                if card:
                    photo = self._get_card_photo_transformed(card, scale=1.0, angle_deg=0.0, opacity=t)
                    if photo: self.canvas.create_image(x, ty, anchor="nw", image=photo)
                    else: self._draw_card(x, ty, card, tags="")
                else: 
                    self.draw_empty_slot(self.canvas, x, ty, self.CARD_WIDTH, self.CARD_HEIGHT, slot_type="freecell", tags=())

            for i, suit in enumerate(self.FOUNDATION_SLOT_SUITS):
                x = self._top_slot_x(i + 4)
                rank = to_state.foundations[suit]
                if rank > 0:
                    photo = self._get_card_photo_transformed(Card(rank, suit), scale=1.0, angle_deg=0.0, opacity=t)
                    if photo: self.canvas.create_image(x, ty, anchor="nw", image=photo)
                    else: self._draw_card(x, ty, Card(rank, suit), tags="")
                else:
                    self.draw_empty_slot(self.canvas, x, ty, self.CARD_WIDTH, self.CARD_HEIGHT, slot_type="foundation", suit=suit, tags=())

            if t < 1.0: self.root.after(16, tick)
            else:
                self.state = to_state
                self.render()

        tick()

    def animate_solution(self, path, playback_seq=None):
        """Animates a sequence of solution moves."""
        if playback_seq is None:
            playback_seq = self._ai_playback_seq
        if playback_seq != self._ai_playback_seq:
            return

        if not path:
            # All moves done - win condition should have been triggered already
            if playback_seq == self._ai_playback_seq:
                self._ai_playback_active = False
            return

        move = path.pop(0)
        old_state = self.state.copy()
        try:
            next_state = self._apply_move_object(old_state, move)
        except Exception as exc:
            self._ai_playback_active = False
            self.status_var.set(f"Playback stopped: {exc}")
            return
        cards, src_kind, src_idx, target_kind, target_val, moved_count = self._build_ai_move_visual(old_state, move)

        self.status_var.set(f"AI move: {str(move)}")

        if not cards or src_kind is None:
            self._move_count += 1
            self.state = next_state
            self.render()
            self.root.after(self.AI_PLAYBACK_NEXT_MOVE_MS, lambda: self.animate_solution(path, playback_seq))
            return

        sx, sy = self._source_card_position(src_kind, src_idx, state=old_state)
        if src_kind == 'cascade' and moved_count > 1:
            sy = self._cascade_row_y() + (len(old_state.cascades[src_idx]) - moved_count) * self.STACK_GAP

        tx, ty = self._target_card_position_after_move(next_state, target_kind, target_val, moved_count=moved_count)

        self.state = old_state
        self.render()
        tag = "ai_move_card"
        overlay = []
        frame = {"i": 0}

        def tick():
            if playback_seq != self._ai_playback_seq:
                return
            frame["i"] += 1
            t = frame["i"] / self.AI_PLAYBACK_FRAMES
            ease = _ease_in_out_sine_intense(t, self.AI_PLAYBACK_EASE_INTENSITY)
            nx, ny = sx + (tx - sx) * ease, sy + (ty - sy) * ease

            self.canvas.delete(tag)
            overlay.clear()

            if moved_count == 1:
                mc = cards[0]
                pickup = _clamp(t * 2.2, 0.0, 1.0)
                scale = 1.0 + 0.08 * _ease_out_quad(pickup)
                angle = 4.0 * math.sin(math.pi * t * 1.2)
                
                shadow = self._get_card_shadow_photo_transformed(mc, scale=scale, angle_deg=angle * 0.6, opacity=0.42)
                if shadow:
                    overlay.append(shadow)
                    self.canvas.create_image(nx + 6 + (self.CARD_WIDTH*scale)/2, ny + 6 + (self.CARD_HEIGHT*scale)/2, anchor="center", image=shadow, tags=(tag,))
                
                photo = self._get_card_photo_transformed(mc, scale=scale, angle_deg=angle, opacity=1.0)
                if photo:
                    overlay.append(photo)
                    self.canvas.create_image(nx + (self.CARD_WIDTH*scale)/2, ny + (self.CARD_HEIGHT*scale)/2, anchor="center", image=photo, tags=(tag,))
                else:
                    self._draw_card(nx, ny, mc, tags=(tag,), lifted=True)
            else:
                for j, mc in enumerate(cards):
                    self._draw_card(nx, ny + j * self.STACK_GAP, mc, tags=(tag,), lifted=True)

            self.canvas.tag_raise(tag)
            if frame["i"] < self.AI_PLAYBACK_FRAMES:
                self.root.after(self.AI_PLAYBACK_FRAME_MS, tick)
            else:
                if playback_seq != self._ai_playback_seq:
                    return
                self._move_count += 1
                self.state = next_state
                self.render()
                next_delay = self.AI_PLAYBACK_NEXT_MOVE_MS
                if target_kind == "foundation" and cards:
                    fx, fy = self._foundation_slot_center(target_val)
                    self._trigger_foundation_celebration(cards[0], fx, fy)
                    next_delay = max(next_delay, 220)
                self.root.after(next_delay, lambda: self.animate_solution(path, playback_seq))

        tick()

    def _build_ai_move_visual(self, old_state, move):
        """Prepares metadata for visualizing an AI solver move."""
        moved = 1
        if move.move_type == 'SEQUENCE_CASCADE_TO_CASCADE': moved = move.count
        
        cards = []
        skind = sidx = tkind = tval = None

        if move.move_type in ('CASCADE_TO_CASCADE', 'SEQUENCE_CASCADE_TO_CASCADE'):
            cards = old_state.cascades[move.from_location][-moved:]
            skind, sidx, tkind, tval = 'cascade', move.from_location, 'cascade', move.to_location
        elif move.move_type == 'CASCADE_TO_FREECELL':
            cards = [old_state.cascades[move.from_location][-1]]
            skind, sidx, tkind, tval = 'cascade', move.from_location, 'free', move.to_location
        elif move.move_type == 'FREECELL_TO_CASCADE':
            cards = [old_state.free_cells[move.from_location]]
            skind, sidx, tkind, tval = 'free', move.from_location, 'cascade', move.to_location
        elif move.move_type == 'CASCADE_TO_FOUNDATION':
            cards = [old_state.cascades[move.from_location][-1]]
            skind, sidx, tkind, tval = 'cascade', move.from_location, 'foundation', cards[0].suit
        elif move.move_type == 'FREECELL_TO_FOUNDATION':
            cards = [old_state.free_cells[move.from_location]]
            skind, sidx, tkind, tval = 'free', move.from_location, 'foundation', cards[0].suit

        return cards, skind, sidx, tkind, tval, moved

    # ============================================================
    # REGION: Event Handlers
    # ============================================================

    def _on_canvas_resize(self, event):
        """Legacy hook retained for compatibility; resizing is root-driven."""
        if event.widget is self.canvas:
            self._reposition_hud(max(1, event.width), max(1, event.height))
            self._raise_hud()

    def _handle_resize(self, width, height):
        """Legacy hook retained for compatibility; fixed-layout snapping is root-driven."""
        _ = (width, height)

    def _on_canvas_press(self, event):
        """Handles mouse press events on the canvas."""
        if self._is_menu_active():
            return
        try:
            if self.canvas.find_withtag("current") and "hud" in self.canvas.gettags(self.canvas.find_withtag("current")[0]): return
        except tk.TclError: pass

        if not self.state or self.auto_move_anim["active"] or self.drag["active"] or self._click_feedback_active: return

        src = self._detect_draggable_source(event.x, event.y)
        if not src:
            self.selection = None
            self._reset_pointer_input()
            self.render()
            return

        self.pointer_input.update({
            "active": True, "start_x": event.x, "start_y": event.y, "last_x": event.x, "last_y": event.y,
            "mouse_down_time": time.time(), "is_dragging": False, "source": src, "press_preview_source": src
        })
        self.render()
        self._draw_press_feedback(src)
        self.pointer_input["hold_job"] = self.root.after(self._press_hold_ms, self._on_press_hold_timeout)

    def _on_canvas_drag(self, event):
        """Handles mouse motion events (dragging) on the canvas."""
        if self._is_menu_active():
            return
        if not self.state or self.auto_move_anim["active"] or self._click_feedback_active: return
        
        if self.pointer_input["active"]:
            self.pointer_input["last_x"], self.pointer_input["last_y"] = event.x, event.y
            if not self.pointer_input["is_dragging"]:
                dx, dy = abs(event.x - self.pointer_input["start_x"]), abs(event.y - self.pointer_input["start_y"])
                if dx > 6 or dy > 6: self._begin_pointer_drag(event.x, event.y)

        if self.drag["active"]:
            self.drag["mouse_x"], self.drag["mouse_y"] = event.x, event.y
            self.drag["target_x"], self.drag["target_y"] = event.x - self.drag["offset_x"], event.y - self.drag["offset_y"]

    def _on_canvas_release(self, event):
        """Handles mouse release events on the canvas."""
        if self._is_menu_active():
            return
        try:
            if self.canvas.find_withtag("current") and "hud" in self.canvas.gettags(self.canvas.find_withtag("current")[0]): return
        except tk.TclError: pass

        if not self.state or self.auto_move_anim["active"] or self._click_feedback_active: return

        if self.pointer_input["active"] and not self.pointer_input["is_dragging"]:
            src = self.pointer_input.get("source")
            self._reset_pointer_input()
            if src: self._handle_click_auto_move(src)
            return

        self._reset_pointer_input()
        if not self.drag["active"]: return

        self.drag["follow_active"] = False
        self.drag["mouse_x"], self.drag["mouse_y"] = event.x, event.y
        self._move_drag_to(event.x - self.drag["offset_x"], event.y - self.drag["offset_y"])

        target = self._detect_drop_target(event.x, event.y)
        if not target:
            self._animate_drag_to(self.drag["origin_x"], self.drag["origin_y"], lambda: [self._clear_drag(), self.status_var.set("Invalid drop."), self.render()])
            return

        tkind, tval = target
        # Cancel if dropped on self
        if tkind == self.drag["source_kind"] and tval == self.drag["source_idx"]:
             self._animate_drag_to(self.drag["origin_x"], self.drag["origin_y"], lambda: [self._clear_drag(), self.status_var.set("Move cancelled."), self.render()])
             return

        try:
            next_state, msg = self._apply_drop_move(tkind, tval)
            tx, ty = self._target_card_position_after_move(next_state, tkind, tval, self.drag["count"])
            moved_card = self.drag["card"]
            
            effect = "foundation_snap" if tkind == "foundation" else None
            steps = 22 if effect else 10 # Slower for effect

            def _on_drop_done():
                self._clear_drag()
                self._set_state_if_valid(next_state, msg)
                if tkind == "foundation" and moved_card is not None:
                    fx, fy = self._foundation_slot_center(tval)
                    self._trigger_foundation_celebration(moved_card, fx, fy)

            self._animate_drag_to(tx, ty, _on_drop_done, steps=steps, interval_ms=12, effect=effect)
        except ValueError:
            self._animate_drag_to(self.drag["origin_x"], self.drag["origin_y"], lambda: [self._clear_drag(), self.status_var.set("Invalid move."), self.render()])

    def on_click_cascade(self, idx):
        """Action handler for clicking on a cascade."""
        if self.selection is None:
            if self.state.get_top_card(idx) is None: return
            self.selection = ("cascade", idx)
            self.render()
            return

        skind, sidx = self.selection
        if skind == "cascade" and sidx == idx:
            self.selection = None
            self.render()
            return

        try:
             next_state = FreeCell.move_cascade_to_cascade(self.state, sidx, idx) if skind == "cascade" else FreeCell.move_freecell_to_cascade(self.state, sidx, idx)
             self._set_state_if_valid(next_state, f"Moved to Cascade {idx+1}.")
        except ValueError: self.status_var.set("Invalid move.")

    def on_click_free_cell(self, idx):
        """Action handler for clicking on a free cell."""
        if self.selection is None:
            if self.state.get_free_cell(idx) is None: return
            self.selection = ("free", idx)
            self.render()
            return
        
        skind, sidx = self.selection
        if skind == "free" and sidx == idx:
            self.selection = None
            self.render()
            return

        if skind != "cascade": return
        try:
            next_state = FreeCell.move_cascade_to_freecell(self.state, sidx, idx)
            self._set_state_if_valid(next_state, f"Moved to Free Cell {idx+1}.")
        except ValueError: self.status_var.set("Invalid move.")

    def on_click_foundation(self, suit):
        """Action handler for clicking on a foundation."""
        if not self.selection: return
        skind, sidx = self.selection
        try:
            if skind == "cascade":
                next_state = FreeCell.move_cascade_to_foundation(self.state, sidx)
            else:
                next_state = FreeCell.move_freecell_to_foundation(self.state, sidx)
            self._set_state_if_valid(next_state, f"Moved to Foundation {suit}.")
        except ValueError: self.status_var.set("Invalid move.")

    def _on_deal_entry_focus_out(self, _evt=None):
        """Hides the deal entry when it loses focus."""
        self._hide_deal_entry()

    def _on_deal_entry_return(self, _evt=None):
        """Processes the deal entry input on Enter key."""
        raw = self._hud_deal_entry.get().strip() if self._hud_deal_entry else ""
        self._hide_deal_entry()
        if not raw: return
        try: self.new_game(deal_number=int(raw))
        except ValueError: self.status_var.set("Deal number must be an integer.")

    # ============================================================
    # REGION: Game Actions
    # ============================================================

    def new_game(self, deal_number=None):
        """Starts a new game with the specified deal number or random."""
        self._cancel_ai_playback()
        self._dismiss_win()
        self.canvas.delete("solver_popup")
        effective_deal = deal_number if deal_number is not None else random.randint(1, FreeCell.MICROSOFT_CLASSIC_MAX_DEAL)
        self.current_deal_number = int(effective_deal)
        self._update_deal_code_label()
        self.deal_var.set(str(self.current_deal_number))
        self.state = FreeCell.create_initial_state(deal_number=self.current_deal_number)
        self.initial_state = self.state.copy()
        self.selection = None
        self.history = []
        self.win_announced = False
        self._move_count = 0
        self._game_start_time = time.time()
        moved = self._auto_move_to_foundation_internal()
        label = str(self.current_deal_number)
        msg = f"New game started (deal {label})." + (f" Auto-moved {moved} to foundation." if moved else "")
        self.status_var.set(msg)
        self.render()
        self._setup_canvas_hud()

    def back_to_menu(self):
        """Shows the main menu overlay from the in-game layout."""
        self._cancel_ai_playback()
        self._reset_pointer_input()
        if self.drag.get("active"):
            self._clear_drag()
        try:
            self.canvas.delete("drag_overlay")
            self.canvas.delete("click_reject")
        except tk.TclError:
            pass

        if self._menu is None:
            self._menu = MenuScreen(
                self.canvas,
                on_play=self._start_new_random_game_from_menu,
                on_load_test=self._load_test_from_menu,
                on_open_report=self.open_results_report,
                on_set_resolution=self._set_resolution_from_menu,
                get_resolution_options=self._get_resolution_options,
                get_current_resolution_label=self._get_current_resolution_label,
                on_show_menu=self._on_menu_show,
                on_hide_menu=self._on_menu_hide,
                on_button_click=self._play_click_sound,
            )
            cw, ch = self.WINDOW_SIZES[self._resolution_index]
            self._menu.set_ui_scale(self._ui_scale_for_resolution(cw, ch))
        self._menu.show()

    def new_game_from_entry(self):
        """Displays the deal entry field to start a specific deal."""
        self._show_deal_entry()

    def restart_deal(self):
        """Restarts the current deal from the initial state."""
        if not self.initial_state: return
        self._cancel_ai_playback()
        self._dismiss_win()
        self.canvas.delete("solver_popup")
        self._update_deal_code_label()
        self.state = self.initial_state.copy()
        self.selection = None
        self.history = []
        self.win_announced = False
        self._move_count = 0
        self._game_start_time = time.time()
        moved = self._auto_move_to_foundation_internal()
        self.status_var.set("Deal restarted.")
        self.render()

    def undo_move(self):
        """Reverts the game state to the previous history entry."""
        if not self.history:
            self.status_var.set("Nothing to undo.")
            return
        prev = self.history.pop()
        self.state = prev
        self.selection = None
        self._move_count = max(0, self._move_count - 1)
        self.status_var.set("Move undone.")
        self.render()
        # self._animate_state_fade(prev)

    def _start_new_random_game_from_menu(self):
        if self._menu:
            self._menu.hide()
            self._menu = None
        self.new_game()
        self.root.after_idle(self._sync_layout_after_menu_exit)

    def _load_test_from_menu(self, test_case_key):
        if self._menu:
            self._menu.hide()
            self._menu = None

        state = self._build_menu_test_state(str(test_case_key))
        if state is None:
            self.new_game()
            self.status_var.set("Unknown test case key. Started a new game.")
        else:
            self._apply_loaded_test_state(state, test_case_key)
        self.root.after_idle(self._sync_layout_after_menu_exit)

    def _build_menu_test_state(self, case_key):
        if case_key == "1-start":
            return FreeCell.create_initial_state(deal_number=1)

        if case_key == "1-mid":
            base = FreeCell.create_initial_state(deal_number=1)
            cascades = []
            for cascade in base.cascades:
                cascades.append([card for card in cascade if card.rank > 2])
            foundations = {'S': 2, 'C': 2, 'H': 2, 'D': 2}
            return GameState(cascades=cascades, free_cells=[None, None, None, None], foundations=foundations)

        if case_key == "1-late16":
            foundations = {'C': 9, 'D': 9, 'S': 9, 'H': 9}
            cascades = [
                [Card(10, 'S'), Card(11, 'H'), Card(12, 'S'), Card(13, 'H')],
                [Card(10, 'D'), Card(11, 'S'), Card(12, 'D'), Card(13, 'S')],
                [Card(10, 'C'), Card(11, 'D'), Card(12, 'C'), Card(13, 'D')],
                [Card(10, 'H'), Card(11, 'C'), Card(12, 'H'), Card(13, 'C')],
                [],
                [],
                [],
                [],
            ]
            return GameState(cascades=cascades, free_cells=[None, None, None, None], foundations=foundations)

        if case_key == "1-late12":
            foundations = {'C': 10, 'D': 10, 'S': 10, 'H': 10}
            cascades = [
                [Card(11, 'S'), Card(12, 'H'), Card(13, 'S')],
                [Card(11, 'D'), Card(12, 'S'), Card(13, 'D')],
                [Card(11, 'C'), Card(12, 'D'), Card(13, 'C')],
                [Card(11, 'H'), Card(12, 'C'), Card(13, 'H')],
                [],
                [],
                [],
                [],
            ]
            return GameState(cascades=cascades, free_cells=[None, None, None, None], foundations=foundations)

        if case_key == "1-late10":
            # Layout provided as "10 cards" includes 8 cascade cards; keep provided foundation ranks.
            foundations = {'C': 11, 'D': 11, 'S': 11, 'H': 11}
            cascades = [
                [Card(12, 'S'), Card(13, 'H')],
                [Card(12, 'D'), Card(13, 'S')],
                [Card(12, 'C'), Card(13, 'D')],
                [Card(12, 'H'), Card(13, 'C')],
                [],
                [],
                [],
                [],
            ]
            return GameState(cascades=cascades, free_cells=[None, None, None, None], foundations=foundations)

        return None

    def _apply_loaded_test_state(self, state, case_key):
        self._cancel_ai_playback()
        self._dismiss_win()
        self.canvas.delete("solver_popup")

        self.state = state
        self.initial_state = self.state.copy()
        self.current_deal_number = None
        self._update_deal_code_label()
        self.deal_var.set("")
        self.selection = None
        self.history = []
        self.win_announced = False
        self._move_count = 0
        self._game_start_time = time.time()
        self.status_var.set(f"Loaded Test Case {case_key}.")
        self.render()
        self._setup_canvas_hud()

    # ============================================================
    # REGION: Win Sequence & Popups
    # ============================================================

    def _get_foundation_slot_center(self, suit_idx):
        """Returns the center coordinates of a foundation slot by suit index (0-3)."""
        x = self._top_slot_x(suit_idx + 4)
        y = self._top_row_y()
        return int(x + self.CARD_WIDTH // 2), int(y + self.CARD_HEIGHT // 2)

    def _get_elapsed_time(self):
        """Returns formatted elapsed time string (MM:SS)."""
        s = int(time.time() - self._game_start_time)
        return f"{s//60:02d}:{s%60:02d}"

    def _cancel_ai_playback(self):
        """Invalidates pending AI playback callbacks and clears playback overlay."""
        self._ai_playback_active = False
        self._ai_playback_seq += 1
        try:
            self.canvas.delete("ai_move_card")
        except tk.TclError:
            pass

    def _popup_width_for_cascades(self, canvas_w):
        """Returns popup width matching the full span of 8 cascade slots."""
        cascades_span = self.CARD_WIDTH * 8 + self.SLOT_GAP * 7
        return max(360, min(canvas_w - 24, cascades_span))

    def _popup_spacing(self, canvas_w, canvas_h):
        """Returns resolution-aware spacing metrics for popup layout."""
        scale = self._ui_scale_for_resolution(canvas_w, canvas_h)
        return {
            "edge_margin": max(12, int(round(12 * scale))),
            "top_pad": max(18, int(round(18 * scale))),
            "content_nudge": max(40, int(round(40 * scale))),
            "section_gap": max(14, int(round(14 * scale))),
            "row_gap": max(20, int(round(20 * scale))),
            "row_gap_tight": max(16, int(round(16 * scale))),
            "button_half_h": max(14, int(round(14 * scale))),
            "button_bottom_pad": max(22, int(round(22 * scale))),
        }

    def _popup_safe_button_y(self, y0, y1, content_bottom, spacing):
        """Places popup buttons below content while keeping them inside panel bounds."""
        min_y = y0 + spacing["top_pad"] + spacing["button_half_h"]
        max_y = y1 - spacing["button_bottom_pad"] - spacing["button_half_h"]
        desired = content_bottom + spacing["section_gap"] + spacing["button_half_h"]
        return max(min_y, min(max_y, desired))

    def _draw_centered_colon_row(self, cx, y, label, value, fill, font, tags):
        """Draws a key/value row so the ':' is aligned at the popup center."""
        self.canvas.create_text(cx - 6, y, text=str(label), fill=fill, font=font, anchor="e", tags=tags)
        self.canvas.create_text(cx, y, text=":", fill=fill, font=font, anchor="center", tags=tags)
        self.canvas.create_text(cx + 6, y, text=str(value), fill=fill, font=font, anchor="w", tags=tags)

    def _load_popup_ascii_title(self, filename, fallback_text):
        """Loads ASCII title text from assets/Fonts, with fallback when missing."""
        key = filename.upper()
        if key in self._popup_title_cache:
            return self._popup_title_cache[key]

        title_path = self._fonts_root / filename
        try:
            text = title_path.read_text(encoding="utf-8").strip("\n")
        except OSError:
            text = ""

        final_text = text if text else fallback_text
        self._popup_title_cache[key] = final_text
        return final_text

    def _solver_ascii_filename(self, algorithm, solved):
        """Maps solver labels to popup ASCII title files."""
        algo_key = {"A*": "ASTAR", "BFS": "BFS", "DFS": "DFS", "UCS": "UCS"}.get(algorithm, str(algorithm).upper())
        suffix = "FINISHED" if solved else "FAILED"
        return f"{algo_key}_{suffix}.txt"

    def _trigger_win_sequence(self):
        """Shows the You Win popup first."""
        if self._win_active:
            return
        self._win_active = True
        self.win_announced = True
        self._show_win_popup()

    def _new_game_after_animation(self):
        """Starts a new game after fountain/rain animation completes (~4.5 seconds)."""
        self.root.after(4500, self.new_game)

    def _restart_after_animation(self):
        """Restarts current deal after fountain/rain animation completes (~4.5 seconds)."""
        self.root.after(4500, self.restart_deal)

    def _trigger_fountain_explosion(self):
        """Legacy no-op: win fountain/rain animation has been removed."""
        self._rain_active = False
        self._fountain_cards = []
        self.canvas.delete("fountain")
        self.canvas.delete("win_rain")

    def _run_fountain(self):
        """Animates foundation cards launching upward as a fountain."""
        if not self._win_active:
            return

        W = max(1, self.canvas.winfo_width())
        H = max(1, self.canvas.winfo_height())
        now = (time.time() - self._fountain_start) * 1000
        all_exited = True

        self.canvas.delete("fountain")

        for fc in self._fountain_cards:
            if now < fc["delay"]:
                all_exited = False
                continue

            if fc["exited"]:
                continue

            fc["vy"] += 0.4
            fc["x"] += fc["vx"]
            fc["y"] += fc["vy"]
            fc["tilt"] += fc["tilt_speed"]

            if fc["y"] < -self.CARD_HEIGHT:
                fc["exited"] = True
                continue

            all_exited = False

            try:
                suit_folder = {"H": "heart", "D": "diamond", "C": "club", "S": "spade"}[fc["suit"]]
                path = self._cards_root / suit_folder / f"{fc['rank']}_{suit_folder}.png"
                if not path.exists():
                    continue
                img = Image.open(str(path))
                img = img.resize((self.CARD_WIDTH, self.CARD_HEIGHT), Image.LANCZOS)
                img = img.rotate(fc["tilt"], expand=True, resample=Image.BICUBIC)
                photo = ImageTk.PhotoImage(img)
                self._win_photos.append(photo)
                if len(self._win_photos) > 120:
                    self._win_photos = self._win_photos[-60:]

                self.canvas.create_image(
                    fc["x"], fc["y"],
                    image=photo, anchor="center",
                    tags="fountain"
                )
            except Exception:
                pass

        if all_exited:
            self.canvas.delete("fountain")
            self.root.after(100, self._start_win_card_rain)
            return

        self.canvas.after(16, self._run_fountain)

    def _start_win_card_rain(self):
        """Legacy no-op: win rain animation has been removed."""
        self._rain_active = False
        self._rain_cards = []
        self.canvas.delete("win_rain")

    def _spawn_win_card(self, canvas_w, canvas_h, delay_frames=0):
        """Creates a falling card for win sequence (simpler version of menu's _spawn_card)."""
        CARD_SUITS = ["diamond", "heart", "club", "spade"]
        CARD_RANKS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"]
        
        suit = random.choice(CARD_SUITS)
        rank = random.choice(CARD_RANKS)

        scale = random.uniform(0.70, 1.35)
        card_w = max(28, int(round(60 * scale)))
        card_h = max(40, int(round(84 * scale)))

        path = self._cards_root / suit / f"{rank}_{suit}.png"
        if Image is not None:
            try:
                img = Image.open(str(path)).resize((card_w, card_h), Image.LANCZOS)
            except Exception:
                img = Image.new("RGB", (card_w, card_h), "#ffffff")
        else:
            img = None

        spin_dir = random.choice((-1.0, 1.0))
        return {
            "suit": suit,
            "rank": rank,
            "img_base": img,
            "photo": None,
            "canvas_id": None,
            "w": card_w,
            "h": card_h,
            "x": random.randint(card_w, canvas_w - card_w),
            "y": random.randint(-canvas_h * 2, -card_h),
            "vy": random.uniform(0.1, 0.35),
            "angle": random.uniform(-18.0, 18.0),
            "spin_speed": spin_dir * random.uniform(0.03, 0.10),
            "spin_accel": spin_dir * 0.0012,
            "delay": int(max(0, delay_frames)),
            "active": delay_frames == 0,
        }

    def _run_win_rain(self):
        """Animates falling card rain (reuses menu-style animation)."""
        if not self._rain_active:
            self.canvas.delete("win_rain")
            return

        W = max(1, self.canvas.winfo_width())
        H = max(1, self.canvas.winfo_height())

        for idx, card in enumerate(self._rain_cards):
            if card["delay"] > 0:
                card["delay"] -= 1
                continue

            if not card["active"]:
                card["active"] = True

            # Physics: gravity and terminal velocity
            fall_progress = _clamp(card["y"] / max(1, H), 0.0, 1.0)
            accel_mult = 1.0 + (0.35 * fall_progress)
            card["vy"] = min(card["vy"] + (0.035 * accel_mult), 2.4)
            card["y"] += card["vy"]

            # Rotation
            card["spin_speed"] += card["spin_accel"]
            card["angle"] += card["spin_speed"]

            # Render rotated card
            photo = None
            if ImageTk is not None and card["img_base"] is not None:
                try:
                    rotated = card["img_base"].rotate(card["angle"], expand=True, resample=Image.BICUBIC)
                    photo = ImageTk.PhotoImage(rotated)
                except Exception:
                    pass

            if photo is not None:
                card["photo"] = photo
                self._rain_photos.append(photo)
                if len(self._rain_photos) > 56:
                    self._rain_photos = self._rain_photos[-28:]
                try:
                    self.canvas.itemconfig(card["canvas_id"], image=photo)
                except tk.TclError:
                    pass

            try:
                self.canvas.coords(card["canvas_id"], card["x"], card["y"])
            except tk.TclError:
                pass

            # Respawn at top when exits bottom
            if card["y"] > H + card["h"]:
                new_card = self._spawn_win_card(W, H, delay_frames=0)
                new_card["canvas_id"] = card["canvas_id"]
                self._rain_cards[idx] = new_card

        self.canvas.tag_raise("win_popup")
        self.canvas.after(20, self._run_win_rain)

    def _show_win_popup(self):
        """Draws the You Win popup panel over the card rain."""
        self._play_notification_sound()
        W = max(1, self.canvas.winfo_width())
        H = max(1, self.canvas.winfo_height())
        spacing = self._popup_spacing(W, H)
        cx, cy = W // 2, H // 2

        title_text = self._load_popup_ascii_title("YOUWIN.txt", "YOU WIN!")
        title_lines = max(1, title_text.count("\n") + 1)
        try:
            line_h = max(12, int(self._font_popup_ascii.metrics("linespace")))
        except Exception:
            line_h = 14
        try:
            kv_line_h = max(12, int(self._font_popup_kv.metrics("linespace")))
        except Exception:
            kv_line_h = 14
        try:
            label_line_h = max(12, int(self._font_px_label.metrics("linespace")))
        except Exception:
            label_line_h = 14
        title_h = line_h * title_lines

        PW = self._popup_width_for_cascades(W)
        required_h = (
            spacing["top_pad"] + spacing["content_nudge"] + title_h + spacing["section_gap"]
            + (kv_line_h * 2) + spacing["row_gap"]
            + label_line_h + spacing["section_gap"]
            + (spacing["button_half_h"] * 2)
            + spacing["button_bottom_pad"] + spacing["top_pad"]
        )
        PH = min(H - (spacing["edge_margin"] * 2), max(360, required_h))
        x0, y0 = cx - PW // 2, cy - PH // 2
        x1, y1 = cx + PW // 2, cy + PH // 2

        self.canvas.create_rectangle(0, 0, W, H,
            fill="#000000", stipple="gray50",
            tags="win_popup"
        )

        self.canvas.create_rectangle(x0, y0, x1, y1,
            fill="#0d0f0d", outline="#00ff41",
            width=3, tags="win_popup"
        )

        title_y = y0 + spacing["top_pad"] + spacing["content_nudge"]
        title_id = self.canvas.create_text(cx, title_y,
            text=title_text,
            fill="#00ff41", font=self._font_popup_ascii,
            anchor="n", justify="center", tags="win_popup"
        )

        moves = self._move_count
        elapsed = self._get_elapsed_time()
        title_box = self.canvas.bbox(title_id)
        title_bottom = title_box[3] if title_box else (title_y + title_h)
        stats_y = title_bottom + spacing["section_gap"]
        self._draw_centered_colon_row(
            cx, stats_y, "MOVES", moves, "#00a827", self._font_popup_kv, "win_popup"
        )
        self._draw_centered_colon_row(
            cx, stats_y + spacing["row_gap"], "TIME", elapsed, "#00a827", self._font_popup_kv, "win_popup"
        )

        prompt_y = stats_y + (spacing["row_gap"] * 2)
        self.canvas.create_text(cx, prompt_y,
            text="Choose what to do next:",
            fill="#00a827", font=self._font_px_label,
            anchor="center", tags="win_popup"
        )

        content_bottom = prompt_y + (label_line_h // 2)
        btn_y = self._popup_safe_button_y(y0, y1, content_bottom, spacing)

        btn_half_h = spacing["button_half_h"]
        btn_w = max(96, int(round(112 * self._ui_scale_for_resolution(W, H))))
        btn_gap = max(20, int(round(20 * self._ui_scale_for_resolution(W, H))))

        ng_x0, ng_x1 = cx - btn_gap - btn_w, cx - btn_gap
        ng_rect = self.canvas.create_rectangle(
            ng_x0, btn_y - btn_half_h, ng_x1, btn_y + btn_half_h,
            fill="#0d0f0d", outline="#00ff41",
            width=2, tags="win_popup"
        )
        ng_text = self.canvas.create_text(
            (ng_x0 + ng_x1) // 2, btn_y,
            text="RESTART",
            fill="#00ff41", font=self._font_px_btn,
            anchor="center", tags="win_popup"
        )

        mn_x0, mn_x1 = cx + btn_gap, cx + btn_gap + btn_w
        mn_rect = self.canvas.create_rectangle(
            mn_x0, btn_y - btn_half_h, mn_x1, btn_y + btn_half_h,
            fill="#00ff41", outline="#00ff41",
            width=2, tags="win_popup"
        )
        mn_text = self.canvas.create_text(
            (mn_x0 + mn_x1) // 2, btn_y,
            text="NEW GAME",
            fill="#000000", font=self._font_px_btn,
            anchor="center", tags="win_popup"
        )

        def _restart():
            self._play_click_sound()
            self._dismiss_win()
            self.restart_deal()

        def _new_game():
            self._play_click_sound()
            self._dismiss_win()
            self.new_game()

        for item in [ng_rect, ng_text]:
            self.canvas.tag_bind(item, "<ButtonRelease-1>", lambda e: _restart())
            self.canvas.tag_bind(item, "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
            self.canvas.tag_bind(item, "<Leave>", lambda e: self.canvas.config(cursor=""))

        for item in [mn_rect, mn_text]:
            self.canvas.tag_bind(item, "<ButtonRelease-1>", lambda e: _new_game())
            self.canvas.tag_bind(item, "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
            self.canvas.tag_bind(item, "<Leave>", lambda e: self.canvas.config(cursor=""))

    def _dismiss_win(self):
        """Cleans up win sequence and popups."""
        self._win_active = False
        self._rain_active = False
        self._win_photos = []
        self._rain_photos = []
        self.canvas.delete("win_popup")
        self.canvas.delete("win_rain")
        self.canvas.delete("fountain")

    def show_no_solution_popup(self, algorithm, nodes_explored, time_taken):
        """Shows a red error popup when solver finds no solution."""
        self._play_notification_sound()
        W = max(1, self.canvas.winfo_width())
        H = max(1, self.canvas.winfo_height())
        spacing = self._popup_spacing(W, H)

        title_text = self._load_popup_ascii_title(
            self._solver_ascii_filename(algorithm, solved=False),
            f"{algorithm} FAILED",
        )
        title_lines = max(1, title_text.count("\n") + 1)
        try:
            line_h = max(12, int(self._font_popup_ascii.metrics("linespace")))
        except Exception:
            line_h = 14
        try:
            kv_line_h = max(12, int(self._font_popup_kv.metrics("linespace")))
        except Exception:
            kv_line_h = 14
        try:
            label_line_h = max(12, int(self._font_px_label.metrics("linespace")))
        except Exception:
            label_line_h = 14
        title_h = line_h * title_lines

        PW = self._popup_width_for_cascades(W)
        required_h = (
            spacing["top_pad"] + spacing["content_nudge"] + title_h + spacing["section_gap"]
            + label_line_h + spacing["row_gap_tight"]
            + (kv_line_h * 2) + spacing["section_gap"]
            + (spacing["button_half_h"] * 2)
            + spacing["button_bottom_pad"] + spacing["top_pad"]
        )
        PH = min(H - (spacing["edge_margin"] * 2), max(340, required_h))
        x0 = W // 2 - PW // 2
        y0 = H // 2 - PH // 2
        x1, y1 = x0 + PW, y0 + PH
        cx = (x0 + x1) // 2

        self.canvas.create_rectangle(x0, y0, x1, y1,
            fill="#0d0f0d", outline="#ff3300",
            width=3, tags="solver_popup"
        )
        title_y = y0 + spacing["top_pad"] + spacing["content_nudge"]
        title_id = self.canvas.create_text(cx, title_y,
            text=title_text,
            fill="#ff3300", font=self._font_popup_ascii,
            anchor="n", justify="center", tags="solver_popup"
        )
        title_box = self.canvas.bbox(title_id)
        title_bottom = title_box[3] if title_box else (title_y + title_h)
        body_y = title_bottom + spacing["section_gap"]
        self.canvas.create_text(cx, body_y,
            text=f"{algorithm} found no path",
            fill="#cc2200", font=self._font_px_label,
            anchor="center", tags="solver_popup"
        )
        self._draw_centered_colon_row(
            cx, body_y + spacing["row_gap_tight"], "NODES", f"{nodes_explored:,}", "#cc2200", self._font_popup_kv, "solver_popup"
        )
        self._draw_centered_colon_row(
            cx, body_y + spacing["row_gap_tight"] * 2, "TIME", f"{time_taken:.2f}s", "#cc2200", self._font_popup_kv, "solver_popup"
        )

        content_bottom = body_y + (spacing["row_gap_tight"] * 2) + (kv_line_h // 2)
        btn_y = self._popup_safe_button_y(y0, y1, content_bottom, spacing)
        btn = self.canvas.create_rectangle(
            cx - 70, btn_y - spacing["button_half_h"], cx + 70, btn_y + spacing["button_half_h"],
            fill="#ff3300", outline="#ff3300",
            width=2, tags="solver_popup"
        )
        btn_t = self.canvas.create_text(cx, btn_y,
            text="DISMISS",
            fill="#000000", font=self._font_px_label,
            anchor="center", tags="solver_popup"
        )

        def _dismiss_solver_popup(_evt=None):
            self._play_click_sound()
            self.canvas.delete("solver_popup")

        for item in [btn, btn_t]:
            self.canvas.tag_bind(item, "<ButtonRelease-1>",
                _dismiss_solver_popup)
            self.canvas.tag_bind(item, "<Enter>",
                lambda e: self.canvas.config(cursor="hand2"))
            self.canvas.tag_bind(item, "<Leave>",
                lambda e: self.canvas.config(cursor=""))

        self.canvas.tag_raise("solver_popup")

    def show_solver_stats_popup(self, algorithm, moves, time_taken, nodes_explored):
        """Shows solver stats panel during/after AI playback."""
        self._play_notification_sound()
        W = max(1, self.canvas.winfo_width())
        H = max(1, self.canvas.winfo_height())
        spacing = self._popup_spacing(W, H)

        title_text = self._load_popup_ascii_title(
            self._solver_ascii_filename(algorithm, solved=True),
            f"{algorithm} FINISHED",
        )
        title_lines = max(1, title_text.count("\n") + 1)
        try:
            line_h = max(12, int(self._font_popup_ascii.metrics("linespace")))
        except Exception:
            line_h = 14
        try:
            kv_line_h = max(12, int(self._font_popup_kv.metrics("linespace")))
        except Exception:
            kv_line_h = 14
        title_h = line_h * title_lines

        PW = self._popup_width_for_cascades(W)
        required_h = (
            spacing["top_pad"] + spacing["content_nudge"] + title_h + spacing["section_gap"]
            + kv_line_h + (spacing["row_gap_tight"] * 3) + spacing["section_gap"]
            + (spacing["button_half_h"] * 2)
            + spacing["button_bottom_pad"] + spacing["top_pad"]
        )
        PH = min(H - (spacing["edge_margin"] * 2), max(360, required_h))
        x0 = W // 2 - PW // 2
        y0 = H // 2 - PH // 2
        x1, y1 = x0 + PW, y0 + PH
        cx = (x0 + x1) // 2

        self.canvas.create_rectangle(x0, y0, x1, y1,
            fill="#0d0f0d", outline="#ffee00",
            width=3, tags="solver_popup"
        )
        title_y = y0 + spacing["top_pad"] + spacing["content_nudge"]
        title_id = self.canvas.create_text(cx, title_y,
            text=title_text,
            fill="#ffee00", font=self._font_popup_ascii,
            anchor="n", justify="center", tags="solver_popup"
        )

        title_box = self.canvas.bbox(title_id)
        title_bottom = title_box[3] if title_box else (title_y + title_h)
        stats_y = title_bottom + spacing["section_gap"]
        self._draw_centered_colon_row(
            cx, stats_y, "ALGORITHM", algorithm, "#ba7517", self._font_popup_kv, "solver_popup"
        )
        self._draw_centered_colon_row(
            cx, stats_y + spacing["row_gap_tight"], "MOVES", moves, "#ba7517", self._font_popup_kv, "solver_popup"
        )
        self._draw_centered_colon_row(
            cx, stats_y + spacing["row_gap_tight"] * 2, "TIME", f"{time_taken:.2f}s", "#ba7517", self._font_popup_kv, "solver_popup"
        )
        self._draw_centered_colon_row(
            cx, stats_y + spacing["row_gap_tight"] * 3, "NODES", f"{nodes_explored:,}", "#ba7517", self._font_popup_kv, "solver_popup"
        )

        content_bottom = stats_y + (spacing["row_gap_tight"] * 3) + (kv_line_h // 2)
        btn_y = self._popup_safe_button_y(y0, y1, content_bottom, spacing)
        btn = self.canvas.create_rectangle(
            cx - 50, btn_y - spacing["button_half_h"], cx + 50, btn_y + spacing["button_half_h"],
            fill="#ffee00", outline="#ffee00",
            width=2, tags="solver_popup"
        )
        btn_t = self.canvas.create_text(cx, btn_y,
            text="OK",
            fill="#000000", font=self._font_px_label,
            anchor="center", tags="solver_popup"
        )
        def _on_solver_ok():
            self._play_click_sound()
            if self._ai_playback_active:
                return
            self.canvas.delete("solver_popup")
            self._ai_playback_active = True
            self._ai_playback_seq += 1
            seq = self._ai_playback_seq
            self.animate_solution(list(self.last_solution_moves), seq)

        for item in [btn, btn_t]:
            self.canvas.tag_bind(item, "<ButtonRelease-1>",
                lambda e: _on_solver_ok())
            self.canvas.tag_bind(item, "<Enter>",
                lambda e: self.canvas.config(cursor="hand2"))
            self.canvas.tag_bind(item, "<Leave>",
                lambda e: self.canvas.config(cursor=""))

        self.canvas.tag_raise("solver_popup")

    def solve_with_bfs(self):
        from solvers.bfs_solver import BFSSolver

        self._start_solver_thread("BFS", lambda: BFSSolver(debug=True, debug_every=100000))

    def solve_with_dfs(self):
        from solvers.dfs_solver import DFSSolver

        self._start_solver_thread("DFS", lambda: DFSSolver(debug=True, debug_every=100000))

    def solve_with_astar(self):
        from solvers.astar_solver import AStarSolver

        self._start_solver_thread("A*", lambda: AStarSolver(debug=True, debug_every=1000))

    def solve_with_ucs(self):
        from solvers.ucs_solver import UCSSolver

        self._start_solver_thread("UCS", lambda: UCSSolver(debug=True, debug_every=100000))

    def _start_solver_thread(self, name, solver_builder):
        if getattr(self, "is_solving", False):
            return

        self.is_solving = True
        self._active_solver_name = name
        self._solver_cancel_event.clear()
        self._highlight_solver(name)
        self._set_ai_solving_status(name, sum(self.state.foundations.values()))
        if hasattr(self, "stop_solver_btn") and self.stop_solver_btn is not None:
            self.stop_solver_btn.configure(state=tk.NORMAL)

        def worker():
            try:
                solver = solver_builder()
                path, metrics = solver.solve(
                    self.state,
                    progress_callback=self._make_ai_progress_callback(name),
                    foundation_priority_mode=self.foundation_priority_var.get(),
                    should_stop=self._solver_cancel_event.is_set,
                )
                self.root.after(0, lambda: self._on_solver_complete(name, path, metrics))
            except NotImplementedError:
                self.root.after(0, lambda: self._on_solver_not_implemented(name))

        threading.Thread(target=worker, daemon=True).start()

    def stop_current_solver(self):
        if not getattr(self, "is_solving", False):
            self.status_var.set("No solver is currently running.")
            return
        self._solver_cancel_event.set()
        active = self._active_solver_name or "Solver"
        self.status_var.set(f"Stopping {active}... Please wait.")
        if hasattr(self, "stop_solver_btn") and self.stop_solver_btn is not None:
            self.stop_solver_btn.configure(state=tk.DISABLED)

    def show_hint(self):
        successors = FreeCell.get_successors(self.state)
        if successors:
            self.status_var.set(f"Hint: {successors[0][1]}")
        else:
            self.status_var.set("No legal moves available.")

    def export_actions_txt(self):
        if not self.last_solution_moves:
            self.status_var.set("No action list available. Run a solver first.")
            return

        name = f"freecell_actions_{(self.last_solver_name or 'solver').lower()}.txt"
        path = filedialog.asksaveasfilename(title="Export Actions", defaultextension=".txt", initialfile=name)
        if not path: return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("FreeCell Action List\n")
                f.write(f"Solver: {self.last_solver_name or 'Unknown'}\n")
                f.write(f"Total actions: {len(self.last_solution_moves)}\n\n")
                for i, m in enumerate(self.last_solution_moves, 1): f.write(f"{i}. {m}\n")
            self.status_var.set(f"Exported: {path}")
        except Exception as e: self.status_var.set(f"Export failed: {e}")

    def open_results_report(self):
        if self._menu and getattr(self._menu, "_menu_active", False):
            self._menu.hide()
        self._show_report_panel()
        self._refresh_report_panel()

    def erase_results_report(self):
        report_path = self._results_report_path()
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("UI TESTER RESULTS REPORT\n")
                f.write("=" * 40 + "\n\n")
        except OSError as exc:
            self.status_var.set(f"Report erase failed: {exc}")
            return False

        self.status_var.set("Report erased.")
        self._refresh_report_panel()
        return True

    def erase_results_report_case(self):
        if self.report_case_var is None:
            return False

        try:
            selection = int((self.report_case_var.get() or "").strip())
        except ValueError:
            self.status_var.set("Invalid entry number for report erase.")
            return False

        report_path = self._results_report_path()
        content = self._read_results_report_text()
        entries = self._parse_results_report_entries(content)
        if not entries:
            self.status_var.set("No report entries to erase.")
            return False

        idx = selection - 1
        if idx < 0 or idx >= len(entries):
            self.status_var.set(f"Entry number out of range (1-{len(entries)}).")
            return False

        chosen_header = entries[idx][0]
        kept_entries = [body for i, (_header, body) in enumerate(entries) if i != idx]
        rebuilt = "UI TESTER RESULTS REPORT\n" + ("=" * 40) + "\n\n"
        if kept_entries:
            rebuilt += "\n\n".join(kept_entries) + "\n\n"

        try:
            report_path.write_text(rebuilt, encoding="utf-8")
        except OSError as exc:
            self.status_var.set(f"Failed to erase report entry: {exc}")
            return False

        self.status_var.set(f"Erased report entry: {chosen_header}")
        self._refresh_report_panel()
        return True

    def _results_report_path(self):
        return Path(__file__).resolve().parent.parent / "results_ui.txt"

    def _show_report_panel(self):
        self._enter_report_mode()
        if self.report_panel is not None and not self.report_panel.winfo_ismapped():
            self.report_panel.place(relx=0.02, rely=0.03, relwidth=0.96, relheight=0.94)
            self.report_panel.lift()

    def _hide_report_panel(self, silent=False):
        if self.report_panel is not None and self.report_panel.winfo_ismapped():
            self.report_panel.place_forget()
        self._exit_report_mode()
        if not silent:
            self.status_var.set("Report viewer hidden.")

    def _report_back_to_menu(self):
        self._hide_report_panel(silent=True)
        self.back_to_menu()

    def _enter_report_mode(self):
        self._report_mode_active = True
        if hasattr(self, "left_panel") and self.left_panel.winfo_manager():
            self.left_panel.pack_forget()
        try:
            self.canvas.itemconfigure("hud", state="hidden")
        except tk.TclError:
            pass

    def _exit_report_mode(self):
        self._report_mode_active = False
        menu_active = bool(self._menu and getattr(self._menu, "_menu_active", False))
        if not menu_active and hasattr(self, "left_panel") and not self.left_panel.winfo_manager():
            self.left_panel.pack(side=tk.LEFT, fill=tk.Y, before=self.game_frame)
        if not menu_active:
            try:
                self.canvas.itemconfigure("hud", state="normal")
            except tk.TclError:
                pass
            self._raise_hud()

    def _read_results_report_text(self):
        report_path = self._results_report_path()
        if not report_path.exists():
            return "UI TESTER RESULTS REPORT\n" + ("=" * 40) + "\n\n"
        try:
            return report_path.read_text(encoding="utf-8")
        except OSError:
            return "UI TESTER RESULTS REPORT\n" + ("=" * 40) + "\n\n"

    def _set_report_text(self, text):
        if self.report_text_box is None:
            return
        self.report_text_box.configure(state=tk.NORMAL)
        self.report_text_box.delete("1.0", tk.END)
        self.report_text_box.insert("1.0", text)
        self.report_text_box.configure(state=tk.DISABLED)

    def _show_report_text(self):
        if self.report_graph_frame is not None and self.report_graph_frame.winfo_ismapped():
            self.report_graph_frame.pack_forget()
        if self.report_text_frame is not None and not self.report_text_frame.winfo_ismapped():
            self.report_text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

    def _show_report_graph(self):
        if self.report_graph_data is None:
            if not self.generate_report_graph():
                return
        if self.report_text_frame is not None and self.report_text_frame.winfo_ismapped():
            self.report_text_frame.pack_forget()
        if self.report_graph_frame is not None and not self.report_graph_frame.winfo_ismapped():
            self.report_graph_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        self._draw_report_graph()

    def generate_report_graph(self):
        content = self._read_results_report_text()
        graph_data = self._build_report_graph_data(content)
        if not graph_data.get("algorithms"):
            self.status_var.set("No report data available to graph.")
            self.report_graph_data = None
            return False

        self.report_graph_data = graph_data
        try:
            output_path = Path(__file__).resolve().parent.parent / "results_graph.json"
            output_path.write_text(json.dumps(graph_data, indent=2), encoding="utf-8")
        except OSError:
            pass

        self.status_var.set(f"Graph generated for {len(graph_data['algorithms'])} algorithm(s).")
        return True

    def _build_report_graph_data(self, content):
        algo_stats = {}
        current_algo = None

        for raw_line in content.splitlines():
            line = raw_line.strip()

            algo_match = re.match(r"^---\s+(.+?)\s+\[[^\]]+\]\s+---$", line)
            if algo_match:
                label = algo_match.group(1).strip()
                if label.upper().startswith("A*"):
                    label = "A*"
                current_algo = label
                if current_algo not in algo_stats:
                    algo_stats[current_algo] = {"times": [], "nodes": []}
                continue

            if current_algo is None:
                continue

            t_match = re.search(r"Search time:\s*([0-9]+(?:\.[0-9]+)?)", line, re.IGNORECASE)
            if t_match:
                algo_stats[current_algo]["times"].append(float(t_match.group(1)))
                continue

            n_match = re.search(r"Expanded nodes:\s*([0-9]+)", line, re.IGNORECASE)
            if n_match:
                algo_stats[current_algo]["nodes"].append(int(n_match.group(1)))

        rows = []
        for algo, values in algo_stats.items():
            time_vals = values["times"]
            node_vals = values["nodes"]
            if not time_vals and not node_vals:
                continue
            avg_time = sum(time_vals) / len(time_vals) if time_vals else 0.0
            avg_nodes = sum(node_vals) / len(node_vals) if node_vals else 0.0
            runs = max(len(time_vals), len(node_vals))
            rows.append(
                {
                    "algorithm": algo,
                    "runs": runs,
                    "avg_time": avg_time,
                    "avg_nodes": avg_nodes,
                }
            )

        rows.sort(key=lambda x: x["algorithm"])
        return {"algorithms": rows}

    def _draw_report_graph(self):
        canvas = self.report_graph_canvas
        data = self.report_graph_data
        if canvas is None or not canvas.winfo_exists():
            return

        canvas.delete("all")
        w = max(1, int(canvas.winfo_width()))
        h = max(1, int(canvas.winfo_height()))
        if data is None or not data.get("algorithms"):
            canvas.create_text(w // 2, h // 2, text="No graph data. Click GENERATE GRAPH.", fill="#8ad1ff", font=("Consolas", 12, "bold"))
            return

        rows = data["algorithms"]
        margin = 36
        panel_gap = 24
        panel_h = max(120, (h - margin * 2 - panel_gap) // 2)
        top_y0 = margin
        top_y1 = top_y0 + panel_h
        bot_y0 = top_y1 + panel_gap
        bot_y1 = min(h - margin, bot_y0 + panel_h)

        def draw_panel(y0, y1, metric_key, title, color):
            canvas.create_rectangle(margin, y0, w - margin, y1, outline="#00ff41", width=1)
            canvas.create_text(margin + 8, y0 + 14, text=title, anchor="w", fill="#00ff41", font=("Consolas", 11, "bold"))

            values = [max(0.0, float(row[metric_key])) for row in rows]
            vmax = max(values) if values else 1.0
            vmax = vmax if vmax > 0 else 1.0

            plot_x0 = margin + 10
            plot_x1 = w - margin - 10
            plot_y0 = y0 + 28
            plot_y1 = y1 - 26
            plot_w = max(1, plot_x1 - plot_x0)
            plot_h = max(1, plot_y1 - plot_y0)

            count = len(rows)
            slot_w = plot_w / max(1, count)
            bar_w = max(18, int(slot_w * 0.55))

            for i, row in enumerate(rows):
                val = max(0.0, float(row[metric_key]))
                frac = val / vmax
                bh = max(1, int(plot_h * frac))
                cx = int(plot_x0 + (i + 0.5) * slot_w)
                x0 = cx - bar_w // 2
                x1 = cx + bar_w // 2
                yb = plot_y1
                yt = yb - bh
                canvas.create_rectangle(x0, yt, x1, yb, fill=color, outline=color)
                canvas.create_text(cx, yb + 12, text=row["algorithm"], fill="#00ff41", font=("Consolas", 9, "bold"))
                if metric_key == "avg_time":
                    val_label = f"{val:.3f}s"
                else:
                    val_label = f"{int(round(val)):,}"
                canvas.create_text(cx, yt - 8, text=val_label, fill="#8ad1ff", font=("Consolas", 8, "bold"))

            canvas.create_text(plot_x1, y0 + 14, text=f"max={vmax:.3f}" if metric_key == "avg_time" else f"max={int(round(vmax)):,}", anchor="e", fill="#8ad1ff", font=("Consolas", 9))

        draw_panel(top_y0, top_y1, "avg_time", "Average Search Time", "#00c8ff")
        draw_panel(bot_y0, bot_y1, "avg_nodes", "Average Expanded Nodes", "#00ff7a")

    def _parse_results_report_entries(self, content):
        lines = content.splitlines(keepends=True)
        starts = [i for i, line in enumerate(lines) if line.startswith("[Test case ")]
        entries = []
        for idx, start in enumerate(starts):
            end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
            header = lines[start].strip()
            body = "".join(lines[start:end]).rstrip("\n")
            entries.append((header, body))
        return entries

    def _refresh_report_panel(self):
        content = self._read_results_report_text()
        self._set_report_text(content)
        self.report_graph_data = self._build_report_graph_data(content)
        entries = self._parse_results_report_entries(content)
        if self.report_case_var is not None:
            current = 1
            try:
                current = int((self.report_case_var.get() or "1").strip())
            except ValueError:
                current = 1
            if not entries:
                self.report_case_var.set("1")
            else:
                self.report_case_var.set(str(max(1, min(current, len(entries)))))
        if self.report_graph_frame is not None and self.report_graph_frame.winfo_ismapped():
            self._draw_report_graph()
        self.status_var.set(f"Report loaded ({len(entries)} entr{'y' if len(entries) == 1 else 'ies'}).")

    def _on_solver_not_implemented(self, name):
        self.is_solving = False
        self._active_solver_name = None
        self._reset_solver_highlight()
        if hasattr(self, "stop_solver_btn") and self.stop_solver_btn is not None:
            self.stop_solver_btn.configure(state=tk.DISABLED)
        self.status_var.set(f"{name} is not implemented yet.")

    def _on_solver_complete(self, name, path, metrics):
        self.is_solving = False
        self._active_solver_name = None
        self._reset_solver_highlight()
        if hasattr(self, "stop_solver_btn") and self.stop_solver_btn is not None:
            self.stop_solver_btn.configure(state=tk.DISABLED)
        self._cancel_ai_playback()
        nodes = metrics.get('expanded_nodes', metrics.get('nodes_explored', 0))
        termination = metrics.get('terminated_by') if isinstance(metrics, dict) else None
        elapsed = metrics.get('time_taken', 0.0) if isinstance(metrics, dict) else 0.0

        if termination == 'cancelled':
            self.status_var.set(f"{name} stopped by user ({elapsed:.2f}s, {nodes} nodes).")
            return

        if path is not None:
            self.last_solution_moves = list(path)
            self.last_solver_name = name
            self.status_var.set(f"{name} solved in {len(path)} moves ({elapsed:.2f}s).")
            self.show_solver_stats_popup(name, len(path), elapsed, nodes)
        else:
            self.status_var.set(f"{name} did not find a solution.")
            self.show_no_solution_popup(name, nodes, elapsed)

    def _make_ai_progress_callback(self, algorithm):
        def cb(data):
            p = data.get("best_foundation_progress", 0)
            self.root.after(0, lambda: self._set_ai_solving_status(algorithm, p))
        return cb

    def _set_ai_solving_status(self, algorithm, progress):
        total = 52
        current = max(0, min(total, int(progress)))
        bar_slots = 20
        filled = int(round((current / total) * bar_slots))
        bar = ("█" * filled) + ("▒" * (bar_slots - filled))
        self.status_var.set(f"{algorithm} finding progress: [ {bar} ] {current}/{total}")

    def _apply_move_object(self, state, move):
        return FreeCell.apply_move(state, move) if hasattr(FreeCell, 'apply_move') else self._apply_move_fallback(state, move)

    def _apply_move_fallback(self, state, move):
        # Fallback to granular methods if apply_move isn't centralized (which it isn't based on old file)
        if move.move_type == 'CASCADE_TO_CASCADE': return FreeCell.move_cascade_to_cascade(state, move.from_location, move.to_location)
        if move.move_type == 'SEQUENCE_CASCADE_TO_CASCADE': return FreeCell.move_sequence_cascade_to_cascade(state, move.from_location, move.to_location, move.count)
        if move.move_type == 'CASCADE_TO_FREECELL': return FreeCell.move_cascade_to_freecell(state, move.from_location, move.to_location)
        if move.move_type == 'FREECELL_TO_CASCADE': return FreeCell.move_freecell_to_cascade(state, move.from_location, move.to_location)
        if move.move_type == 'CASCADE_TO_FOUNDATION': return FreeCell.move_cascade_to_foundation(state, move.from_location)
        if move.move_type == 'FREECELL_TO_FOUNDATION': return FreeCell.move_freecell_to_foundation(state, move.from_location)
        raise ValueError(f"Unknown move type: {move.move_type}")

    def _auto_move_to_foundation_internal(self):
        steps = self._collect_auto_foundation_steps(self.state)
        for s in steps:
            self._push_history()
            self.state = s["next_state"]
        return len(steps)

    def _collect_auto_foundation_steps(self, start_state):
        if not self.foundation_priority_var.get(): return []
        steps = []
        state = start_state.copy()
        
        while True:
            done = False
            # Check cascades
            for c in range(8):
                if FreeCell.can_move_cascade_to_foundation(state, c):
                    nxt = FreeCell.move_cascade_to_foundation(state, c)
                    steps.append({"source_kind": "cascade", "source_idx": c, "card": state.get_top_card(c), "next_state": nxt})
                    state = nxt
                    done = True
                    break
            if done: continue
            
            # Check freecells
            for f in range(4):
                if FreeCell.can_move_freecell_to_foundation(state, f):
                    nxt = FreeCell.move_freecell_to_foundation(state, f)
                    steps.append({"source_kind": "free", "source_idx": f, "card": state.get_free_cell(f), "next_state": nxt})
                    state = nxt
                    done = True
                    break
            if not done: break
        return steps

    def _apply_auto_foundation_with_animation(self, base_msg):
        steps = self._collect_auto_foundation_steps(self.state)
        if not steps:
            self.status_var.set(base_msg)
            self.render()
            return

        def run(idx=0):
            if idx >= len(steps):
                self.selection = None
                self.status_var.set(f"{base_msg} Auto-moved {len(steps)} to foundation.")
                self.render()
                return

            step = steps[idx]
            sidx = step["source_idx"]
            skind = step["source_kind"]
            spos = len(self.state.cascades[sidx]) - 1 if skind == "cascade" else 0
            
            tx, ty = self._target_card_position_after_move(step["next_state"], "foundation", step["card"].suit, 1)
            
            chosen = {
                "tx": tx,
                "ty": ty,
                "next_state": step["next_state"],
                "msg": base_msg,
                "target_kind": "foundation",
                "target_val": step["card"].suit,
            }

            def _on_auto_step_complete(o, n, _m):
                self._move_count += 1
                self.history.append(o.copy())
                self.state = n
                run(idx + 1)

            self._start_auto_move_animation(
                [step["card"]], skind, sidx, spos, chosen,
                on_complete=_on_auto_step_complete,
                duration=0.16
            )
        run(0)

    # ============================================================
    # REGION: Utilities (Internal)
    # ============================================================

    def _card_asset_path(self, card):
        """Resolves the file path for a card image asset."""
        folder = {"H": "heart", "D": "diamond", "C": "club", "S": "spade"}.get(card.suit)
        return self._cards_root / folder / f"{card.rank}_{folder}.png" if folder else None

    def _get_card_photo(self, card):
        """Loads or retrieves a cached PhotoImage for a card."""
        if not (Image and ImageTk): return None
        path = self._card_asset_path(card)
        if not (path and path.exists()): return None

        key = (card.rank, card.suit, self.CARD_WIDTH, self.CARD_HEIGHT)
        if key in self._card_photo_cache: return self._card_photo_cache[key]

        pkey = str(path)
        if pkey not in self._card_source_cache:
            try: self._card_source_cache[pkey] = Image.open(path).convert("RGBA")
            except OSError: return None
        
        img = self._card_source_cache[pkey].resize((self.CARD_WIDTH, self.CARD_HEIGHT), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self._card_photo_cache[key] = photo
        return photo

    def _get_foundation_placeholder_photo(self, suit):
        """Generates a faded placeholder image for foundation slots."""
        return None # Simplified to return None as draw_empty_slot handles fallback well

    def _get_background_photo(self, w, h):
        """Retrieves or loads the current background image sized to canvas."""
        if not (Image and ImageTk): return None
        path = self._game_background_path
        if not path: return None
        if not path.exists(): return None
        
        key = (str(path), w, h)
        if key in self._background_photo_cache: return self._background_photo_cache[key]
        
        pkey = str(path)
        if pkey not in self._background_source_cache:
            try: self._background_source_cache[pkey] = Image.open(path).convert("RGB")
            except OSError: return None
            
        img = self._background_source_cache[pkey].resize((w, h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self._background_photo_cache[key] = photo
        return photo

    def _get_background_theme_base(self):
        """Returns the base color hex for the current background theme."""
        return "#1f5b3a"

    def _card_fill_color(self, card):
        """Determines font color (black/red) based on card suit."""
        return "#d62e2e" if card.get_color() == "Red" else "#111111"

    def _get_card_photo_transformed(self, card, scale=1.0, angle_deg=0.0, opacity=1.0):
        """Generates a transformed card image (scaled, rotated, transparent)."""
        if not (Image and ImageTk): return None
        path = self._card_asset_path(card)
        if not (path and path.exists()): return None

        w, h = max(24, int(round(self.CARD_WIDTH * scale))), max(32, int(round(self.CARD_HEIGHT * scale)))
        akey, okey = int(round(angle_deg * 10)), int(round(_clamp(opacity, 0.0, 1.0) * 100))
        key = (card.rank, card.suit, w, h, akey, okey)
        
        if key in self._drag_photo_cache: return self._drag_photo_cache[key]

        pkey = str(path)
        if pkey not in self._card_source_cache:
            try: self._card_source_cache[pkey] = Image.open(path).convert("RGBA")
            except OSError: return None
            
        img = self._card_source_cache[pkey].resize((w, h), Image.LANCZOS)
        if okey < 100:
            alpha = img.split()[-1].point(lambda p: int(p * (okey / 100.0)))
            img.putalpha(alpha)
            
        if abs(angle_deg) > 0.01:
            img = img.rotate(angle_deg, resample=Image.BICUBIC, expand=True, center=(w/2, h))
            
        photo = ImageTk.PhotoImage(img)
        self._drag_photo_cache[key] = photo
        return photo

    def _get_card_shadow_photo_transformed(self, card, scale=1.0, angle_deg=0.0, opacity=1.0):
        """Generates a drop shadow for a transformed card."""
        if not (Image and ImageTk): return None
        path = self._card_asset_path(card)
        if not (path and path.exists()): return None

        w, h = max(24, int(round(self.CARD_WIDTH * scale))), max(32, int(round(self.CARD_HEIGHT * scale)))
        akey, okey = int(round(angle_deg * 10)), int(round(_clamp(opacity, 0.0, 1.0) * 100))
        key = ("shadow", card.rank, card.suit, w, h, akey, okey)
        
        if key in self._drag_photo_cache: return self._drag_photo_cache[key]

        pkey = str(path)
        if pkey not in self._card_source_cache:
            try: self._card_source_cache[pkey] = Image.open(path).convert("RGBA")
            except OSError: return None

        img = self._card_source_cache[pkey].resize((w, h), Image.LANCZOS)
        alpha = img.split()[-1].point(lambda p: int(p * (okey / 100.0)))
        shadow = Image.new("RGBA", (w, h), (0,0,0,0))
        shadow.putalpha(alpha)

        if abs(angle_deg) > 0.01:
            shadow = shadow.rotate(angle_deg, resample=Image.BICUBIC, expand=True, center=(w/2, h))

        photo = ImageTk.PhotoImage(shadow)
        self._drag_photo_cache[key] = photo
        return photo

    def _detect_draggable_source(self, x, y):
        """Identifies a valid card or stack under the mouse pointer."""
        for i in range(4):
            sx, sy = self._top_slot_x(i), self._top_row_y()
            if self._rect_contains(x, y, sx, sy, self.CARD_WIDTH, self.CARD_HEIGHT):
                c = self.state.get_free_cell(i)
                return ("free", i, 0, [c], sx, sy) if c else None

        for i in range(8):
            sx, by = self._slot_x(i), self._cascade_row_y()
            casc = self.state.cascades[i]
            if not casc: continue
            
            ty = by + (len(casc) - 1) * self.STACK_GAP
            if not self._rect_contains(x, y, sx, by, self.CARD_WIDTH, (ty - by) + self.CARD_HEIGHT): continue
            
            cpos = len(casc) - 1 if y >= ty else min(max(0, int((y - by) // self.STACK_GAP)), len(casc) - 1)
            cards = casc[cpos:]
            
            if FreeCell.is_valid_tableau_sequence(cards):
                # Check valid pickup
                if len(cards) > 1:
                    allowed = FreeCell.get_movable_sequence_length(self.state, i)
                    if len(cards) > allowed: continue
                return ("cascade", i, cpos, cards, sx, by + cpos * self.STACK_GAP)
        return None

    def _detect_drop_target(self, x, y):
        """Identifies the game slot under the mouse pointer."""
        for i in range(4):
            if self._rect_contains(x, y, self._top_slot_x(i), self._top_row_y(), self.CARD_WIDTH, self.CARD_HEIGHT): return ("free", i)
        
        for i, s in enumerate(self.FOUNDATION_SLOT_SUITS):
            if self._rect_contains(x, y, self._top_slot_x(i+4), self._top_row_y(), self.CARD_WIDTH, self.CARD_HEIGHT): return ("foundation", s)
        
        by = self._cascade_row_y()
        h = self.CARD_HEIGHT + 12 * self.STACK_GAP
        for i in range(8):
            if self._rect_contains(x, y, self._slot_x(i), by, self.CARD_WIDTH, h): return ("cascade", i)
            
        return None

    def _start_drag(self, skind, sidx, spos, cards, sx, sy, mx, my):
        """Initializes drag state for a set of cards."""
        now = time.time()
        self.drag.update({
            "active": True, "source_kind": skind, "source_idx": sidx, "source_pos": spos,
            "card": cards[0], "cards": list(cards), "count": len(cards), "tag": "drag_card",
            "offset_x": mx - sx, "offset_y": my - sy,
            "x": sx, "y": sy - 4, "target_x": sx, "target_y": sy - 4,
            "origin_x": sx, "origin_y": sy, "lifted": True, "follow_active": True,
            "mouse_x": mx, "mouse_y": my, "started_at": now, "last_frame_at": now,
            "hover_candidate": None, "hover_target": None, "ghost_alpha": 0.0, "highlight_alpha": 0.0
        })
        self.render()
        self._draw_drag_frame(now)
        self._schedule_drag_follow()

    def _update_drag_hover_state(self, now, dt):
        """Updates hover states and drag preview transparency."""
        target = self._detect_drop_target(self.drag.get("mouse_x", 0), self.drag.get("mouse_y", 0))
        valid_next = None
        
        if target:
            tkind, tval = target
            if tkind == "cascade":
                try: valid_next, _ = self._apply_drop_move(tkind, tval)
                except ValueError: target = None

        if target != self.drag["hover_candidate"]:
            self.drag["hover_candidate"] = target
            self.drag["hover_candidate_since"] = now

        if target and (now - self.drag.get("hover_candidate_since", now)) >= 0.08:
            self.drag["hover_target"] = target
            self.drag["hover_draw_target"] = target
            self.drag["hover_next_state"] = valid_next
        elif not target:
            self.drag["hover_target"] = None
            self.drag["hover_next_state"] = None

        da = dt / (0.08 if self.drag["hover_target"] else 0.10)
        sign = 1 if self.drag["hover_target"] else -1
        self.drag["ghost_alpha"] = _clamp(self.drag["ghost_alpha"] + sign * da, 0.0, 1.0)
        self.drag["highlight_alpha"] = _clamp(self.drag["highlight_alpha"] + sign * da, 0.0, 1.0)
        
        if self.drag["ghost_alpha"] <= 0 and self.drag["highlight_alpha"] <= 0:
            self.drag["hover_draw_target"] = None

    def _clear_drag(self):
        """Resets all drag-related state."""
        if self.drag["follow_job"]:
            try: self.root.after_cancel(self.drag["follow_job"])
            except tk.TclError: pass
        
        if self.drag["tag"]: self.canvas.delete(self.drag["tag"])
        self.drag.update({
            "active": False, "source_kind": None, "source_idx": None, "cards": [], "count": 1,
            "tag": None, "hover_target": None, "ghost_alpha": 0.0
        })
        # self._drag_photo_cache.clear()

    def _reset_pointer_input(self):
        """Clears current mouse/touch input state."""
        self._cancel_pointer_hold_timer()
        self._clear_press_feedback()
        self.pointer_input.update({
            "active": False, "is_dragging": False, "source": None, "hold_job": None,
            "press_preview_active": False, "press_preview_source": None
        })

    def _cancel_pointer_hold_timer(self):
        """Cancels any pending long-press timers."""
        if self.pointer_input["hold_job"]:
            try: self.root.after_cancel(self.pointer_input["hold_job"])
            except tk.TclError: pass
            self.pointer_input["hold_job"] = None

    def _clear_press_feedback(self):
        """Removes the visual press indicator."""
        tag = self.pointer_input.get("press_preview_tag", "press_feedback")
        self.canvas.delete(tag)
        self.pointer_input["press_preview_active"] = False
        self.pointer_input["press_preview_source"] = None

    def _begin_pointer_drag(self, mx, my):
        """Transitions from a press/hold to an active drag state."""
        if not self.pointer_input["active"] or self.pointer_input["is_dragging"]: return False
        src = self.pointer_input.get("source")
        if not src:
            self._reset_pointer_input()
            return False
            
        self._cancel_pointer_hold_timer()
        self._clear_press_feedback()
        self.selection = None
        skind, sidx, spos, cards, sx, sy = src
        self._start_drag(skind, sidx, spos, cards, sx, sy, mx, my)
        self.pointer_input["is_dragging"] = True
        return True

    def _on_press_hold_timeout(self):
        """Handles long-press (hold) events to initiate drag."""
        if not self.pointer_input["active"] or self.pointer_input["is_dragging"]: return
        self.pointer_input["hold_job"] = None
        self._begin_pointer_drag(self.pointer_input["last_x"], self.pointer_input["last_y"])

    def _collect_click_move_candidates(self, skind, sidx, spos, cards):
        """Finds all valid moves for a clicked card/stack."""
        candidates = []
        count = len(cards)
        card = cards[0]

        def try_add(tkind, tval, move_func, desc):
            try:
                nxt = move_func()
                tx, ty = self._target_card_position_after_move(nxt, tkind, tval, count)
                candidates.append({"target_kind": tkind, "target_val": tval, "next_state": nxt, "msg": desc, "tx": tx, "ty": ty})
            except ValueError: pass

        if skind == "cascade":
            if count == 1:
                try_add("foundation", card.suit, lambda: FreeCell.move_cascade_to_foundation(self.state, sidx), f"Moved to Foundation {card.suit}.")
                for f in range(4): try_add("free", f, lambda: FreeCell.move_cascade_to_freecell(self.state, sidx, f), f"Moved to Free Cell {f+1}.")

            for c in range(8):
                if c == sidx: continue
                if count == 1: try_add("cascade", c, lambda: FreeCell.move_cascade_to_cascade(self.state, sidx, c), f"Moved to Cascade {c+1}.")
                else: try_add("cascade", c, lambda: FreeCell.move_sequence_cascade_to_cascade(self.state, sidx, c, count), f"Supermoved {count} to Cascade {c+1}.")
        
        elif skind == "free":
            try_add("foundation", card.suit, lambda: FreeCell.move_freecell_to_foundation(self.state, sidx), f"Moved to Foundation {card.suit}.")
            for c in range(8): try_add("cascade", c, lambda: FreeCell.move_freecell_to_cascade(self.state, sidx, c), f"Moved to Cascade {c+1}.")

        return candidates

    def _pick_click_move_candidate(self, candidates, cx, cy):
        """Selects the best destination from multiple candidates."""
        # Priority: Foundation > Cascade > FreeCell
        for k in ("foundation", "cascade", "free"):
            subset = [c for c in candidates if c["target_kind"] == k]
            if subset: return min(subset, key=lambda c: (c["tx"]+self.CARD_WIDTH/2 - cx)**2 + (c["ty"]+self.CARD_HEIGHT/2 - cy)**2)
        return candidates[0] if candidates else None

    def _state_without_moved_source(self, skind, sidx, spos, count):
        """Returns a preview state with the moving cards temporarily removed."""
        p = self.state.copy()
        if skind == "free": p.free_cells[sidx] = None
        elif skind == "cascade": p.cascades[sidx] = p.cascades[sidx][:spos]
        return p

    def _finalize_auto_move_state(self, o_state, n_state, msg):
        """Commits the final state after an auto-move animation completes."""
        self._move_count += 1
        self.history.append(o_state)
        self.state = n_state
        self.selection = None
        self._apply_auto_foundation_with_animation(msg)

    def _start_auto_move_animation(self, cards, skind, sidx, spos, chosen, on_complete=None, duration=0.22):
        """Initiates an automatic card movement animation."""
        o_state = self.state.copy()
        self.state = self._state_without_moved_source(skind, sidx, spos, len(cards))
        self.render()

        sx = self._top_slot_x(sidx) if skind == "free" else self._slot_x(sidx)
        sy = self._top_row_y() if skind == "free" else self._cascade_row_y() + spos * self.STACK_GAP

        self.auto_move_anim.update({
            "active": True, "tag": "auto_move_card", "overlay_images": [],
            "cards": list(cards), "start_x": sx, "start_y": sy,
            "end_x": chosen["tx"], "end_y": chosen["ty"],
            "start_time": time.time(), "duration": duration,
            "origin_state": o_state, "next_state": chosen["next_state"], "msg": chosen["msg"],
            "on_complete": on_complete,
            "target_kind": chosen.get("target_kind"),
            "target_val": chosen.get("target_val"),
        })
        self._tick_auto_move_animation()

    def _handle_click_auto_move(self, source):
        """Processes a click event to automatically move a card."""
        skind, sidx, spos, cards, sx, sy = source
        candidates = self._collect_click_move_candidates(skind, sidx, spos, cards)
        if not candidates:
            if len(cards) == 1:
                self._animate_click_rejection(cards, skind, sidx, spos)
            else:
                self.status_var.set("No valid moves available for this stack.")
                self.render()
            return

        cx, cy = sx + self.CARD_WIDTH / 2, sy + self.CARD_HEIGHT / 2
        chosen = self._pick_click_move_candidate(candidates, cx, cy)
        self._start_auto_move_animation(cards, skind, sidx, spos, chosen)

    def _move_drag_to(self, x, y):
        """Updates internal drag coordinates."""
        self.drag["x"], self.drag["y"] = x, y

    def _apply_drop_move(self, tkind, tval):
        """Executes logic for dropping cards onto a target."""
        skind, sidx, count, card = self.drag["source_kind"], self.drag["source_idx"], self.drag["count"], self.drag["card"]

        if skind == "cascade" and tkind == "cascade":
            if count > 1: return FreeCell.move_sequence_cascade_to_cascade(self.state, sidx, tval, count), f"Supermoved {count} to Cascade {tval+1}."
            return FreeCell.move_cascade_to_cascade(self.state, sidx, tval), f"Moved to Cascade {tval+1}."
        
        if skind == "cascade" and tkind == "free":
            if count != 1: raise ValueError("Only one card to free cell")
            return FreeCell.move_cascade_to_freecell(self.state, sidx, tval), f"Moved to Free Cell {tval+1}."
        
        if skind == "cascade" and tkind == "foundation":
            if count != 1 or card.suit != tval: raise ValueError("Invalid foundation")
            return FreeCell.move_cascade_to_foundation(self.state, sidx), f"Moved to Foundation {tval}."
        
        if skind == "free" and tkind == "cascade":
            return FreeCell.move_freecell_to_cascade(self.state, sidx, tval), f"Moved to Cascade {tval+1}."
        
        if skind == "free" and tkind == "foundation":
            if card.suit != tval: raise ValueError("Invalid foundation")
            return FreeCell.move_freecell_to_foundation(self.state, sidx), f"Moved to Foundation {tval}."

        raise ValueError("Unsupported drop move")

    def _target_card_position_after_move(self, n_state, tkind, tval, moved_count=1):
        """Calculates destination coordinates based on the future state."""
        if tkind == "free": return self._top_slot_x(tval), self._top_row_y()
        if tkind == "foundation":
            smap = {s: i+4 for i, s in enumerate(self.FOUNDATION_SLOT_SUITS)}
            return self._top_slot_x(smap[tval]), self._top_row_y()
        
        x = self._slot_x(tval)
        y = self._cascade_row_y() + (len(n_state.cascades[tval]) - moved_count) * self.STACK_GAP
        return x, y

    def _push_history(self):
        """Saves current state to history stack."""
        self.history.append(self.state.copy())

    def _set_state_if_valid(self, n_state, msg):
        """Updates game state and UI if the move was valid."""
        self._move_count += 1
        self._push_history()
        self.state = n_state
        self.selection = None
        self._apply_auto_foundation_with_animation(msg)
