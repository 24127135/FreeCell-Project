"""Tkinter GUI for playable FreeCell with supermove rules and numbered deals."""

# ============================================================
# REGION: Imports & Constants
# ============================================================

import math
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

from game import Card, FreeCell


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

def draw_menu_button(canvas, x, y, w, h, label, on_click):
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
            on_click()

    for target in (hit, label_id, rect):
        canvas.tag_bind(target, "<Enter>", on_enter)
        canvas.tag_bind(target, "<Leave>", on_leave)
        canvas.tag_bind(target, "<Button-1>", on_press)
        canvas.tag_bind(target, "<ButtonRelease-1>", on_release)

    return {"glow1": glow1, "glow2": glow2, "rect": rect, "label": label_id, "hit": hit}


def draw_pill_button(canvas, cx, cy, w, h, label, on_click, *, fill, outline, text_fill):
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

    def __init__(self, canvas, on_play, on_load_test):
        self.canvas = canvas
        self.on_play = on_play
        self.on_load_test = on_load_test

        self._item_ids = []
        self._bg_photo = None
        self._buttons = {}
        self._test_panel_items = []
        self._panel_open = False
        self._panel_animating = False

        self._panel_geometry = None
        self._fade_overlay = None
        self._resize_job = None

    def show(self):
        """Displays the menu screen and binds resize events."""
        self._redraw()
        self.canvas.bind("<Configure>", self._on_canvas_configure, add="+")

    def hide(self):
        """Hides the menu screen and cleans up resources."""
        try:
            self.canvas.unbind("<Configure>")
        except tk.TclError:
            pass
        if self._resize_job is not None:
            try:
                self.canvas.after_cancel(self._resize_job)
            except tk.TclError:
                pass
            self._resize_job = None

        for item_id in self._item_ids:
            try:
                self.canvas.delete(item_id)
            except tk.TclError:
                pass
        self._item_ids.clear()
        self._buttons.clear()
        self._test_panel_items.clear()
        self._bg_photo = None
        self._fade_overlay = None
        self._panel_open = False
        self._panel_animating = False

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

    def _redraw(self):
        """Redraws the entire menu interface."""
        self.canvas.update()
        w = max(1, int(self.canvas.winfo_width()))
        h = max(1, int(self.canvas.winfo_height()))

        self._clear_test_panel()
        for item_id in self._item_ids:
            try:
                self.canvas.delete(item_id)
            except tk.TclError:
                pass
        self._item_ids.clear()
        self._buttons.clear()

        # Background loading logic simplified for brevity
        bg_path = Path(__file__).resolve().parent / "assets" / "Backgrounds" / "background_menu.png"
        if Image is not None and ImageTk is not None and bg_path.exists():
            bg_image = Image.open(bg_path)
            bg_image = bg_image.resize((w, h), Image.LANCZOS)
            self._bg_photo = ImageTk.PhotoImage(bg_image)
            self._item_ids.append(self.canvas.create_image(0, 0, anchor="nw", image=self._bg_photo))
        else:
            self._bg_photo = None
            self._item_ids.append(self.canvas.create_rectangle(0, 0, w, h, fill="#0f4a2b", outline=""))

        self._draw_buttons(w, h)

        if self._panel_open:
            x, y, pw, ph = self._panel_target_geometry()
            self._draw_test_panel(x, y, pw, ph)

    def _draw_buttons(self, canvas_w, canvas_h):
        """Draws the main menu buttons."""
        btn_w, btn_h = 220, 52
        cx = canvas_w / 2
        x = cx - btn_w / 2
        y1 = canvas_h * 0.68 - btn_h / 2
        y2 = y1 + btn_h + 32

        play = draw_menu_button(self.canvas, x, y1, btn_w, btn_h, "Play Now", lambda: self._fade_out(self.on_play))
        tests = draw_menu_button(self.canvas, x, y2, btn_w, btn_h, "Test Cases", self._toggle_test_panel)

        for d in (play, tests):
            for item_id in d.values():
                self._item_ids.append(item_id)

        self._buttons["play"] = {"geom": (x, y1, btn_w, btn_h), "items": play}
        self._buttons["tests"] = {"geom": (x, y2, btn_w, btn_h), "items": tests}

    def _toggle_test_panel(self):
        """Toggles the visibility of the test case selection panel."""
        if self._panel_animating:
            return
        if self._panel_open:
            self._animate_panel_close()
        else:
            self._animate_panel_open()

    def _clear_test_panel(self):
        """Removes all test panel items from the canvas."""
        for item_id in self._test_panel_items:
            try:
                self.canvas.delete(item_id)
            except tk.TclError:
                pass
        self._test_panel_items.clear()

    def _panel_target_geometry(self):
        """Calculates the target geometry for the test panel."""
        (bx, by, bw, bh) = self._buttons["tests"]["geom"]
        panel_w = 260
        panel_x = bx + bw / 2 - panel_w / 2
        panel_y = by + bh + 8
        row_h = 48
        padding_tb = 12
        panel_h = padding_tb + row_h * 2 + padding_tb
        return panel_x, panel_y, panel_w, panel_h

    def _draw_test_panel(self, x, y, w, visible_h):
        """Draws the test panel at the specified location and size."""
        self._clear_test_panel()
        radius = 12

        points = _rounded_rect_points(x, y, w, visible_h, radius)
        panel_rect = self.canvas.create_polygon(
            points, smooth=True, splinesteps=12, fill="#0a2418", outline="#2d7a4f", width=1
        )
        self._test_panel_items.append(panel_rect)
        self._item_ids.append(panel_rect)

        if visible_h <= 4:
            return

        row_h = 48
        top_pad = 12
        content_y0 = y + top_pad

        def add_row(row_idx, label, test_number):
            row_top = content_y0 + row_idx * row_h
            if row_top + row_h > y + visible_h - 6:
                return

            text_id = self.canvas.create_text(
                x + 16, row_top + row_h / 2, anchor="w", text=label, fill="#a8d5b5", font=("Georgia", 12)
            )
            self._test_panel_items.append(text_id)
            self._item_ids.append(text_id)

            btn_w, btn_h = 80, 32
            btn_x = x + w - 16 - btn_w
            btn_y = row_top + (row_h - btn_h) / 2

            def do_load():
                self._fade_out(lambda: self.on_load_test(test_number))

            btn_items = draw_menu_button(self.canvas, btn_x, btn_y, btn_w, btn_h, "Load", do_load)
            for item_id in btn_items.values():
                self._test_panel_items.append(item_id)
                self._item_ids.append(item_id)

        add_row(0, "Test Case 1", 1)
        add_row(1, "Test Case 2", 2)

    def _animate_panel_open(self):
        """Animates the opening of the test panel."""
        self._panel_animating = True
        self._panel_open = True
        x, y, w, full_h = self._panel_target_geometry()
        start = time.time()
        duration = 0.180

        def tick():
            t = (time.time() - start) / duration
            if t >= 1.0:
                self._draw_test_panel(x, y, w, full_h)
                self._panel_animating = False
                return
            eased = _ease_out_cubic(t)
            self._draw_test_panel(x, y, w, full_h * eased)
            self.canvas.after(16, tick)

        tick()

    def _animate_panel_close(self):
        """Animates the closing of the test panel."""
        self._panel_animating = True
        x, y, w, full_h = self._panel_target_geometry()
        start = time.time()
        duration = 0.150

        def tick():
            t = (time.time() - start) / duration
            if t >= 1.0:
                self._clear_test_panel()
                self._panel_open = False
                self._panel_animating = False
                return
            eased = _ease_out_cubic(t)
            self._draw_test_panel(x, y, w, full_h * (1.0 - eased))
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


# ============================================================
# REGION: Main GUI Class
# ============================================================

class FreeCell_GUI:
    """Playable FreeCell GUI backed by the project game logic."""

    SUIT_SYMBOLS = {"H": "♥", "D": "♦", "C": "♣", "S": "♠"}
    FOUNDATION_SLOT_SUITS = ["H", "D", "S", "C"]

    BASE_CARD_WIDTH = 72
    BASE_CARD_HEIGHT = 96
    BASE_STACK_GAP = 30
    BASE_SLOT_GAP = 24
    BASE_TOP_INNER_GAP_DELTA = 6
    BASE_TOP_MIDDLE_EXTRA_GAP = 40
    BASE_LEFT_MARGIN = 20
    BASE_TOP_MARGIN = 20
    BASE_ROW_GAP = 60

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FreeCell - GUI")
        self.root.configure(bg="#1f5b3a")

        self.state = None
        self.initial_state = None
        self.current_deal_number = None
        self.selection = None
        self.history = []
        self.win_announced = False
        self.last_solution_moves = []
        self.last_solver_name = None

        self._init_drag_state()
        self._init_input_state()
        self._init_anim_state()
        self._init_resources()
        self._init_hud_vars()

        self._build_layout()

        self._menu = MenuScreen(
            self.canvas,
            on_play=self._start_new_random_game_from_menu,
            on_load_test=self._load_test_from_menu,
        )
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
        self._press_hold_ms = 120

    def _init_anim_state(self):
        """Initializes animation state variables."""
        self.auto_move_anim = {
            "active": False,
            "tag": "auto_move_card",
            "overlay_images": [],
        }
        self._click_feedback_active = False

    def _init_resources(self):
        """Initializes resource paths and caches."""
        self._assets_root = Path(__file__).resolve().parent / "assets"
        self._cards_root = self._assets_root / "Cards"
        self._backgrounds_root = self._assets_root / "Backgrounds"

        self._card_source_cache = {}
        self._card_photo_cache = {}
        self._drag_photo_cache = {}
        self._foundation_placeholder_cache = {}
        self._background_source_cache = {}
        self._background_photo_cache = {}

        self._background_name_to_path = self._discover_backgrounds()
        self.background_names = list(self._background_name_to_path.keys())
        self.background_var = tk.StringVar(
            value=self.background_names[0] if self.background_names else "Solid Green"
        )

        self._resize_job = None
        self._last_canvas_size = (0, 0)
        self._board_origin_x = 0
        self._board_origin_y = 0
        self._resolution_scale_hint = self._get_resolution_scale_hint()
        self._current_scale = self._resolution_scale_hint
        self._apply_scale_to_layout(self._current_scale)

    def _init_hud_vars(self):
        """Initializes HUD variables."""
        self._hud_ids = []
        self._hud_buttons = {}
        self._hud_status_id = None
        self._hud_stack_id = None
        self._hud_deal_entry = None
        self._hud_deal_window_id = None
        self._hud_deal_button_geom = None

    # ============================================================
    # REGION: Window & Layout
    # ============================================================

    def _build_layout(self):
        """Constructs the main window layout and widgets."""
        self.status_var = tk.StringVar(value="Welcome to FreeCell")
        self.stack_limit_var = tk.StringVar(value="")

        width, height = self._current_board_size()
        main_area = tk.Frame(self.root, bg="#1f5b3a")
        main_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(main_area, width=width, height=height, bg="#0f4a2b", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=0)
        self.canvas.bind("<Configure>", self._on_canvas_resize, add="+")

        algo_panel = tk.Frame(main_area, bg="#174c31", bd=1, relief=tk.FLAT)
        algo_panel.pack(side=tk.RIGHT, fill=tk.Y)

        self.foundation_priority_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            algo_panel, text="Foundation priority", variable=self.foundation_priority_var,
            onvalue=True, offvalue=False, bg="#174c31", fg="white",
            activebackground="#174c31", activeforeground="white", selectcolor="#1f5b3a", anchor="w"
        ).pack(fill=tk.X, padx=10, pady=(10, 6))

        tk.Label(algo_panel, text="Algorithms", bg="#174c31", fg="white", font=("Segoe UI", 10, "bold"), anchor="w").pack(fill=tk.X, padx=10, pady=(0, 6))
        tk.Button(algo_panel, text="BFS", command=self.solve_with_bfs, width=14).pack(fill=tk.X, padx=10, pady=4)
        tk.Button(algo_panel, text="DFS", command=self.solve_with_dfs, width=14).pack(fill=tk.X, padx=10, pady=4)
        tk.Button(algo_panel, text="UCS", command=self.solve_with_ucs, width=14).pack(fill=tk.X, padx=10, pady=4)
        tk.Button(algo_panel, text="A*", command=self.solve_with_astar, width=14).pack(fill=tk.X, padx=10, pady=4)

        tk.Frame(algo_panel, bg="#174c31").pack(fill=tk.BOTH, expand=True)
        tk.Button(algo_panel, text="Export Actions (.txt)", command=self.export_actions_txt, width=18).pack(fill=tk.X, padx=10, pady=(10, 10))

        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        self._setup_canvas_hud()

    def _get_resolution_scale_hint(self):
        """Estimates an initial scale factor based on screen resolution."""
        screen_w = max(1024, self.root.winfo_screenwidth())
        screen_h = max(768, self.root.winfo_screenheight())
        return _clamp(min(screen_w / 1920.0, screen_h / 1080.0), 0.85, 1.35)

    def _apply_scale_to_layout(self, scale):
        """Updates UI constants based on the given scale factor."""
        s = _clamp(scale, 0.58, 1.6)
        self.CARD_WIDTH = max(50, int(round(self.BASE_CARD_WIDTH * s)))
        self.CARD_HEIGHT = max(70, int(round(self.BASE_CARD_HEIGHT * s)))
        self.STACK_GAP = max(14, int(round(self.BASE_STACK_GAP * s)))
        self.SLOT_GAP = max(14, int(round(self.BASE_SLOT_GAP * s)))
        self.TOP_INNER_GAP_DELTA = max(0, int(round(self.BASE_TOP_INNER_GAP_DELTA * s)))
        self.TOP_MIDDLE_EXTRA_GAP = max(0, int(round(self.BASE_TOP_MIDDLE_EXTRA_GAP * s)))
        self.LEFT_MARGIN = max(12, int(round(self.BASE_LEFT_MARGIN * s)))
        self.TOP_MARGIN = max(12, int(round(self.BASE_TOP_MARGIN * s)))
        self.ROW_GAP = max(34, int(round(self.BASE_ROW_GAP * s)))

    def _base_board_size(self):
        """Returns the unscaled dimensions of the game board."""
        w = self.BASE_LEFT_MARGIN * 2 + self.BASE_CARD_WIDTH * 8 + self.BASE_SLOT_GAP * 7
        h = (self.BASE_TOP_MARGIN * 2 + self.BASE_CARD_HEIGHT * 2 + self.BASE_ROW_GAP + 7 * self.BASE_STACK_GAP + 40)
        return w, h

    def _current_board_size(self):
        """Returns the current scaled dimensions of the game board."""
        w = self.LEFT_MARGIN * 2 + self.CARD_WIDTH * 8 + self.SLOT_GAP * 7
        h = (self.TOP_MARGIN * 2 + self.CARD_HEIGHT * 2 + self.ROW_GAP + 7 * self.STACK_GAP + 40)
        return w, h

    def _compute_dynamic_scale(self, canvas_w, canvas_h):
        """Calculates scale factor based on current window size."""
        base_w, base_h = self._base_board_size()
        responsive = min(max(100, canvas_w - 24) / base_w, max(100, canvas_h - 24) / base_h)
        return _clamp((responsive * 0.8) + (self._resolution_scale_hint * 0.2), 0.58, 1.6)

    def _update_board_origin(self):
        """Centers the board content within the canvas."""
        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
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
            self.win_announced = True
            self.status_var.set("You win! All cards moved to foundations.")
            messagebox.showinfo("FreeCell", "Congratulations! You solved this deal.")

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
            self._hud_status_id = self.canvas.create_text(16, 16, anchor="nw", text="", fill="#e0e0e0", font=("Helvetica", 11), tags=("hud",))
            self._hud_ids.append(self._hud_status_id)
            self.status_var.trace_add("write", lambda *a: self.canvas.itemconfigure(self._hud_status_id, text=self.status_var.get()))
            self.canvas.itemconfigure(self._hud_status_id, text=self.status_var.get())

        if self._hud_stack_id is None:
            self._hud_stack_id = self.canvas.create_text(16, 40, anchor="nw", text="", fill="#e0e0e0", font=("Helvetica", 11), tags=("hud",))
            self._hud_ids.append(self._hud_stack_id)
            self.stack_limit_var.trace_add("write", lambda *a: self.canvas.itemconfigure(self._hud_stack_id, text=self.stack_limit_var.get()))
            self.canvas.itemconfigure(self._hud_stack_id, text=self.stack_limit_var.get())

        self._ensure_hud_buttons()
        self._reposition_hud(max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height()))
        self._raise_hud()

    def _ensure_hud_buttons(self):
        """Creates the HUD buttons if they don't exist yet."""
        if self._hud_buttons: return
        base = self._get_background_theme_base()
        fill = _blend_hex(base, "#000000", 0.70)
        outline = _blend_hex(base, "#ffffff", 0.18)
        text_fill = _blend_hex(base, "#ffffff", 0.88)

        cmds = [
            ("Games", self.new_game),
            ("Restart", self.restart_deal),
            ("Undo", self.undo_move),
            ("Deal", self._toggle_deal_entry),
            ("Background", self._cycle_background),
        ]

        for label, cb in cmds:
            w = max(len(label) * 9 + 48, 48)
            items = draw_pill_button(self.canvas, 0, 0, w, 36, label, cb, fill=fill, outline=outline, text_fill=text_fill)
            for item_id in items.values(): self._hud_ids.append(item_id)
            self._hud_buttons[label.lower()] = {"label": label, "items": items}

    def _reposition_hud(self, canvas_w, canvas_h):
        """Updates positions of HUD elements based on canvas size."""
        if self._hud_stack_id: self.canvas.coords(self._hud_stack_id, 16, 40)
        cy = canvas_h - 16 - 18
        x_cursor = 16

        for key in ("games", "restart", "undo", "deal", "background"):
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
            anim.update({"active": False, "overlay_images": []})
            if anim.get("on_complete"):
                anim["on_complete"](anim["origin_state"], anim["next_state"], anim["msg"])
            else:
                self._finalize_auto_move_state(anim["origin_state"], anim["next_state"], anim["msg"])

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

    def animate_solution(self, path):
        """Animates a sequence of solution moves."""
        if not path:
            self.status_var.set("Completed! AI finished solving this game.")
            messagebox.showinfo("Completed", "AI finished solving this game!")
            return

        move = path.pop(0)
        old_state = self.state.copy()
        next_state = self._apply_move_object(old_state, move)
        cards, src_kind, src_idx, target_kind, target_val, moved_count = self._build_ai_move_visual(old_state, move)

        self.status_var.set(f"AI move: {str(move)}")

        if not cards or src_kind is None:
            self.state = next_state
            self.render()
            self.root.after(230, lambda: self.animate_solution(path))
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
            frame["i"] += 1
            t = frame["i"] / 10
            ease = 1 - (1 - t) * (1 - t)
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
            if frame["i"] < 10: self.root.after(16, tick)
            else:
                self.state = next_state
                self.render()
                self.root.after(170, lambda: self.animate_solution(path))

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
        """Handles main canvas resize events."""
        if event.width <= 50 or event.height <= 50: return
        if self._resize_job: self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(70, lambda: self._handle_resize(event.width, event.height))
        self._raise_hud()

    def _handle_resize(self, width, height):
        """Re-scales the board layout to fit new dimensions."""
        self._resize_job = None
        if (width, height) == self._last_canvas_size: return
        
        orig_size = (self.CARD_WIDTH, self.CARD_HEIGHT)
        self._apply_scale_to_layout(self._compute_dynamic_scale(width, height))
        self._last_canvas_size = (width, height)
        
        if (self.CARD_WIDTH, self.CARD_HEIGHT) != orig_size:
            self._card_photo_cache.clear()
            self._foundation_placeholder_cache.clear()
        
        self._background_photo_cache.clear()
        self._update_board_origin()
        if self.state: self.render()
        self._reposition_hud(width, height)
        self._raise_hud()

    def _on_canvas_press(self, event):
        """Handles mouse press events on the canvas."""
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
            
            effect = "foundation_snap" if tkind == "foundation" else None
            steps = 22 if effect else 10 # Slower for effect
            
            self._animate_drag_to(tx, ty, lambda: [self._clear_drag(), self._set_state_if_valid(next_state, msg)], steps=steps, interval_ms=12, effect=effect)
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
        self.current_deal_number = deal_number
        self.state = FreeCell.create_initial_state(deal_number=deal_number)
        self.initial_state = self.state.copy()
        self.selection = None
        self.history = []
        self.win_announced = False
        moved = self._auto_move_to_foundation_internal()
        label = "random" if deal_number is None else str(deal_number)
        msg = f"New game started (deal {label})." + (f" Auto-moved {moved} to foundation." if moved else "")
        self.status_var.set(msg)
        self.render()
        self._setup_canvas_hud()

    def new_game_from_entry(self):
        """Displays the deal entry field to start a specific deal."""
        self._show_deal_entry()

    def restart_deal(self):
        """Restarts the current deal from the initial state."""
        if not self.initial_state: return
        self.state = self.initial_state.copy()
        self.selection = None
        self.history = []
        self.win_announced = False
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
        self.status_var.set("Move undone.")
        self.render()
        # self._animate_state_fade(prev)

    def _cycle_background(self):
        """Rotates through available background themes."""
        if not self.background_names: return
        idx = 0
        try: idx = self.background_names.index(self.background_var.get())
        except ValueError: pass
        
        self.background_var.set(self.background_names[(idx + 1) % len(self.background_names)])
        self._background_photo_cache.clear()
        
        # Reset HUD
        for i in self._hud_ids: self.canvas.delete(i)
        self._hud_ids.clear()
        self._hud_buttons.clear()
        self._hud_status_id = None
        self._hud_stack_id = None
        self._hide_deal_entry()
        self._hud_deal_entry = None
        
        self.render()
        self._setup_canvas_hud()

    def _start_new_random_game_from_menu(self):
        if self._menu:
            self._menu.hide()
            self._menu = None
        self.new_game()
        self._setup_canvas_hud()

    def _load_test_from_menu(self, test_number):
        if self._menu:
            self._menu.hide()
            self._menu = None
        if test_number == 1: self._load_test_1()
        elif test_number == 2: self._load_test_2()
        else: self.new_game()

    def _load_test_1(self):
        # Placeholder for test case 1
        self.new_game()

    def _load_test_2(self):
        # Placeholder for test case 2
        self.new_game()

    def solve_with_bfs(self):
        if getattr(self, "is_solving", False): return
        self.is_solving = True
        self._set_ai_solving_status(sum(self.state.foundations.values()))
        
        def worker():
            try:
                from solvers.bfs_solver import BFSSolver
                solver = BFSSolver(debug=True, debug_every=100000)
                path, metrics = solver.solve(self.state, progress_callback=self._make_ai_progress_callback(), foundation_priority_mode=self.foundation_priority_var.get())
                self.root.after(0, lambda: self._on_solver_complete("BFS", path, metrics))
            except NotImplementedError: self.root.after(0, lambda: self._on_solver_not_implemented("BFS"))
        threading.Thread(target=worker, daemon=True).start()

    def solve_with_dfs(self):
        if getattr(self, "is_solving", False): return
        self.is_solving = True
        self._set_ai_solving_status(sum(self.state.foundations.values()))
        
        def worker():
            try:
                from solvers.dfs_solver import DFSSolver
                solver = DFSSolver(debug=True, debug_every=100000)
                path, metrics = solver.solve(self.state, progress_callback=self._make_ai_progress_callback(), foundation_priority_mode=self.foundation_priority_var.get())
                self.root.after(0, lambda: self._on_solver_complete("DFS", path, metrics))
            except NotImplementedError: self.root.after(0, lambda: self._on_solver_not_implemented("DFS"))
        threading.Thread(target=worker, daemon=True).start()

    def solve_with_astar(self):
        if getattr(self, "is_solving", False): return
        self.is_solving = True
        self._set_ai_solving_status(sum(self.state.foundations.values()))
        
        def worker():
            from solvers.astar_solver import AStarSolver
            solver = AStarSolver(debug=True, debug_every=1000)
            path, metrics = solver.solve(self.state, progress_callback=self._make_ai_progress_callback(), foundation_priority_mode=self.foundation_priority_var.get())
            self.root.after(0, lambda: self._on_solver_complete("A*", path, metrics))
        threading.Thread(target=worker, daemon=True).start()

    def solve_with_ucs(self):
        if getattr(self, "is_solving", False): return
        self.is_solving = True
        self._set_ai_solving_status(sum(self.state.foundations.values()))
        
        def worker():
            from solvers.ucs_solver import UCSSolver
            solver = UCSSolver(debug=True, debug_every=100000)
            path, metrics = solver.solve(self.state, progress_callback=self._make_ai_progress_callback(), foundation_priority_mode=self.foundation_priority_var.get())
            self.root.after(0, lambda: self._on_solver_complete("UCS", path, metrics))
        threading.Thread(target=worker, daemon=True).start()

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

    def _on_solver_not_implemented(self, name):
        self.is_solving = False
        self.status_var.set(f"{name} is not implemented yet.")

    def _on_solver_complete(self, name, path, metrics):
        self.is_solving = False
        if path is not None:
            self.last_solution_moves = list(path)
            self.last_solver_name = name
            elapsed = metrics.get('time_taken', 0.0)
            self.status_var.set(f"{name} solved in {len(path)} moves ({elapsed:.2f}s).")
            self.root.after(500, lambda: self.animate_solution(list(path)))
        else:
            self.status_var.set(f"{name} did not find a solution.")

    def _make_ai_progress_callback(self):
        def cb(data):
            p = data.get("best_foundation_progress", 0)
            self.root.after(0, lambda: self._set_ai_solving_status(p))
        return cb

    def _set_ai_solving_status(self, progress):
        self.status_var.set(f"AI solving: {(progress/52)*100:.1f}% (best foundation progress)")

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
            
            chosen = {"tx": tx, "ty": ty, "next_state": step["next_state"], "msg": base_msg}
            self._start_auto_move_animation(
                [step["card"]], skind, sidx, spos, chosen,
                on_complete=lambda o, n, m: [self._push_history(), setattr(self, 'state', n), run(idx+1)],
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
        path = self._background_name_to_path.get(self.background_var.get())
        if not path: return None
        
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

    def _discover_backgrounds(self):
        """Scans the assets directory for valid background images."""
        found = {}
        if self._backgrounds_root.exists():
            for p in sorted(self._backgrounds_root.iterdir()):
                if p.stem != "background_menu" and p.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                    found[p.stem] = p
        return found

    def _get_background_theme_base(self):
        """Returns the base color hex for the current background theme."""
        name = (self.background_var.get() or "").lower()
        if "cyan" in name or "background_2" in name: return "#0d6f78"
        if "blue" in name or "background_1" in name: return "#0b2a66"
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
            "on_complete": on_complete
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
        self._push_history()
        self.state = n_state
        self.selection = None
        self._apply_auto_foundation_with_animation(msg)
