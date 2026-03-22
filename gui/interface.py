"""Tkinter GUI for playable FreeCell with supermove rules and numbered deals."""

import tkinter as tk
from tkinter import messagebox
import threading
from game import Card, FreeCell


class FreeCell_GUI:
    """Playable FreeCell GUI backed by the project game logic."""

    SUIT_SYMBOLS = {"H": "♥", "D": "♦", "C": "♣", "S": "♠"}

    CARD_WIDTH = 72
    CARD_HEIGHT = 96
    STACK_GAP = 22
    SLOT_GAP = 24
    LEFT_MARGIN = 20
    TOP_MARGIN = 20
    ROW_GAP = 60

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FreeCell - GUI")
        self.root.configure(bg="#1f5b3a")

        self.state = None
        self.initial_state = None
        self.current_deal_number = None
        self.selection = None  # ("cascade"|"free", index)
        self.history = []
        self.win_announced = False

        self.drag = {
            "active": False,
            "source_kind": None,
            "source_idx": None,
            "source_pos": None,
            "card": None,
            "cards": [],
            "count": 1,
            "tag": None,
            "offset_x": 0,
            "offset_y": 0,
            "x": 0,
            "y": 0,
            "target_x": 0,
            "target_y": 0,
            "origin_x": 0,
            "origin_y": 0,
            "lifted": False,
            "follow_job": None,
            "follow_active": False,
        }

        self._build_layout()
        self.new_game()

    def _build_layout(self):
        toolbar = tk.Frame(self.root, bg="#1f5b3a")
        toolbar.pack(fill=tk.X, padx=10, pady=(10, 6))

        tk.Button(toolbar, text="New Random", command=self.new_game, width=12).pack(side=tk.LEFT, padx=4)
        tk.Label(toolbar, text="Deal #", bg="#1f5b3a", fg="white", font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT,
            padx=(12, 4),
        )
        self.deal_entry = tk.Entry(toolbar, width=10)
        self.deal_entry.pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Load Deal", command=self.new_game_from_entry, width=12).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Restart Deal", command=self.restart_deal, width=12).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Undo", command=self.undo_move, width=10).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Hint", command=self.show_hint, width=10).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Solve A*", command=self.solve_with_astar, bg="#4CAF50", fg="white", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(10, 4))
        tk.Button(toolbar, text="Solve UCS", command=self.solve_with_ucs, bg="#2196F3", fg="white", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=4)
        self.status_var = tk.StringVar(value="Welcome to FreeCell")
        self.status_label = tk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            bg="#1f5b3a",
            fg="white",
            font=("Segoe UI", 10, "bold"),
        )
        self.status_label.pack(fill=tk.X, padx=12, pady=(0, 6))

        width = self.LEFT_MARGIN * 2 + self.CARD_WIDTH * 8 + self.SLOT_GAP * 7
        height = self.TOP_MARGIN * 2 + self.CARD_HEIGHT + self.ROW_GAP + self.CARD_HEIGHT + 7 * self.STACK_GAP + 40

        self.canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg="#0f4a2b",
            highlightthickness=0,
        )
        self.canvas.pack(padx=10, pady=(0, 10))

        # Drag interactions for smooth card movement and snap behavior.
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

    def new_game(self, deal_number=None):
        self.current_deal_number = deal_number
        self.state = FreeCell.create_initial_state(deal_number=deal_number)
        self.initial_state = self.state.copy()
        self.selection = None
        self.history = []
        self.win_announced = False
        moved = self._auto_move_to_foundation_internal()
        deal_label = "random" if deal_number is None else str(deal_number)
        if moved:
            self.status_var.set(
                f"New game started (deal {deal_label}). Auto-moved {moved} card(s) to foundation."
            )
        else:
            self.status_var.set(f"New game started (deal {deal_label}). Select a top card to move.")
        self.render()

    def new_game_from_entry(self):
        raw = self.deal_entry.get().strip()
        if not raw:
            self.status_var.set("Enter a deal number to load a numbered deal.")
            return

        try:
            deal_number = int(raw)
        except ValueError:
            self.status_var.set("Deal number must be an integer.")
            return

        self.new_game(deal_number=deal_number)

    def restart_deal(self):
        if self.initial_state is None:
            return
        self.state = self.initial_state.copy()
        self.selection = None
        self.history = []
        self.win_announced = False
        moved = self._auto_move_to_foundation_internal()
        deal_label = "random" if self.current_deal_number is None else str(self.current_deal_number)
        if moved:
            self.status_var.set(f"Deal {deal_label} restarted. Auto-moved {moved} card(s) to foundation.")
        else:
            self.status_var.set(f"Deal {deal_label} restarted.")
        self.render()

    def undo_move(self):
        if not self.history:
            self.status_var.set("Nothing to undo.")
            return
        self.state = self.history.pop()
        self.selection = None
        self.status_var.set("Move undone.")
        self.render()

    def _card_fill_color(self, card):
        return "#d62e2e" if card.get_color() == "Red" else "#111111"

    def _slot_x(self, i):
        return self.LEFT_MARGIN + i * (self.CARD_WIDTH + self.SLOT_GAP)

    def _top_row_y(self):
        return self.TOP_MARGIN

    def _cascade_row_y(self):
        return self.TOP_MARGIN + self.CARD_HEIGHT + self.ROW_GAP

    def render(self):
        self.canvas.delete("all")
        self._draw_top_area()
        self._draw_cascades()
        self._draw_selection_marker()

        if self.state.is_goal_state() and not self.win_announced:
            self.win_announced = True
            self.status_var.set("You win! All cards moved to foundations.")
            messagebox.showinfo("FreeCell", "Congratulations! You solved this deal.")

    def _draw_slot_outline(self, x, y, tag, label):
        self.canvas.create_rectangle(
            x,
            y,
            x + self.CARD_WIDTH,
            y + self.CARD_HEIGHT,
            outline="#b8d8c7",
            width=2,
            dash=(4, 3),
            tags=(tag,),
        )
        self.canvas.create_text(
            x + self.CARD_WIDTH / 2,
            y + self.CARD_HEIGHT + 12,
            text=label,
            fill="#d9eee2",
            font=("Segoe UI", 9),
            tags=(tag,),
        )

    def _draw_card(self, x, y, card, tags, lifted=False):
        # Stronger shadow and brighter border while dragging for a held-card feel.
        shadow_offset = 4 if lifted else 2
        shadow_stipple = "gray25" if lifted else "gray50"
        outline = "#ffd98a" if lifted else "#222222"
        border_width = 3 if lifted else 2

        self.canvas.create_rectangle(
            x + shadow_offset,
            y + shadow_offset,
            x + self.CARD_WIDTH + shadow_offset,
            y + self.CARD_HEIGHT + shadow_offset,
            fill="#000000",
            outline="",
            stipple=shadow_stipple,
            tags=tags,
        )

        suit_symbol = self.SUIT_SYMBOLS.get(card.suit, card.suit)
        rank_label = Card.RANK_NAMES[card.rank]
        ink_color = self._card_fill_color(card)
        face_bg = "#fff8f8" if card.get_color() == "Red" else "#f8f9ff"

        self.canvas.create_rectangle(
            x,
            y,
            x + self.CARD_WIDTH,
            y + self.CARD_HEIGHT,
            fill=face_bg,
            outline=outline,
            width=border_width,
            tags=tags,
        )

        corner_text = f"{rank_label}{suit_symbol}"
        self.canvas.create_text(
            x + 9,
            y + 10,
            text=corner_text,
            fill=ink_color,
            anchor="nw",
            font=("Consolas", 10, "bold"),
            tags=tags,
        )

        self.canvas.create_text(
            x + self.CARD_WIDTH - 9,
            y + self.CARD_HEIGHT - 10,
            text=corner_text,
            fill=ink_color,
            anchor="se",
            font=("Consolas", 10, "bold"),
            tags=tags,
        )

        self.canvas.create_text(
            x + self.CARD_WIDTH / 2,
            y + self.CARD_HEIGHT / 2 - 8,
            text=suit_symbol,
            fill=ink_color,
            font=("Segoe UI Symbol", 28, "bold"),
            tags=tags,
        )

        self.canvas.create_text(
            x + self.CARD_WIDTH / 2,
            y + self.CARD_HEIGHT / 2 + 17,
            text=rank_label,
            fill=ink_color,
            font=("Consolas", 13, "bold"),
            tags=tags,
        )

    def _draw_top_area(self):
        y = self._top_row_y()
        dragging_free = self.drag["active"] and self.drag["source_kind"] == "free"

        # Free cells at slots 0..3
        for i in range(4):
            x = self._slot_x(i)
            tag = f"free_{i}"
            self._draw_slot_outline(x, y, tag, f"Free {i + 1}")
            card = self.state.free_cells[i]
            if card is not None and not (dragging_free and self.drag["source_idx"] == i):
                self._draw_card(x, y, card, tags=(tag, f"card_free_{i}"))

        # Foundations at slots 4..7 (H D C S)
        suits = ["H", "D", "C", "S"]
        for i, suit in enumerate(suits):
            x = self._slot_x(i + 4)
            tag = f"foundation_{suit}"
            self._draw_slot_outline(x, y, tag, f"Foundation {suit}")

            rank = self.state.foundations[suit]
            if rank > 0:
                card = Card(rank, suit)
                self._draw_card(x, y, card, tags=(tag, f"card_foundation_{suit}"))

    def _draw_cascades(self):
        base_y = self._cascade_row_y()
        dragging_cascade = self.drag["active"] and self.drag["source_kind"] == "cascade"
        for i in range(8):
            x = self._slot_x(i)
            tag = f"cascade_{i}"
            self._draw_slot_outline(x, base_y, tag, f"Cascade {i + 1}")

            cascade = self.state.cascades[i]
            for j, card in enumerate(cascade):
                if (
                    dragging_cascade
                    and self.drag["source_idx"] == i
                    and self.drag["source_pos"] is not None
                    and j >= self.drag["source_pos"]
                ):
                    continue
                y = base_y + j * self.STACK_GAP
                self._draw_card(x, y, card, tags=(tag, f"card_cascade_{i}_{j}"))

    def _rect_contains(self, x, y, rx, ry, rw, rh):
        return rx <= x <= rx + rw and ry <= y <= ry + rh

    def _source_card_position(self, kind, idx, state=None):
        board = self.state if state is None else state
        if kind == "free":
            return self._slot_x(idx), self._top_row_y()

        cascade = board.cascades[idx]
        if not cascade:
            return self._slot_x(idx), self._cascade_row_y()
        return self._slot_x(idx), self._cascade_row_y() + (len(cascade) - 1) * self.STACK_GAP

    def _detect_draggable_source(self, x, y):
        # Free cells first
        for i in range(4):
            sx, sy = self._slot_x(i), self._top_row_y()
            if self._rect_contains(x, y, sx, sy, self.CARD_WIDTH, self.CARD_HEIGHT):
                card = self.state.get_free_cell(i)
                if card is not None:
                    return "free", i, 0, [card], sx, sy
                return None

        # Any card in a valid top sequence in each cascade.
        for i in range(8):
            cascade = self.state.cascades[i]
            if not cascade:
                continue
            sx = self._slot_x(i)
            base_y = self._cascade_row_y()
            top_y = base_y + (len(cascade) - 1) * self.STACK_GAP
            if not self._rect_contains(x, y, sx, base_y, self.CARD_WIDTH, (top_y - base_y) + self.CARD_HEIGHT):
                continue

            if y >= top_y:
                card_pos = len(cascade) - 1
            else:
                card_pos = int((y - base_y) // self.STACK_GAP)
                card_pos = max(0, min(card_pos, len(cascade) - 1))

            cards = cascade[card_pos:]
            if FreeCell.is_valid_tableau_sequence(cards):
                return "cascade", i, card_pos, cards, sx, base_y + card_pos * self.STACK_GAP

        return None

    def _detect_drop_target(self, x, y):
        # Free cells
        for i in range(4):
            sx, sy = self._slot_x(i), self._top_row_y()
            if self._rect_contains(x, y, sx, sy, self.CARD_WIDTH, self.CARD_HEIGHT):
                return "free", i

        # Foundations
        suits = ["H", "D", "C", "S"]
        for i, suit in enumerate(suits):
            sx, sy = self._slot_x(i + 4), self._top_row_y()
            if self._rect_contains(x, y, sx, sy, self.CARD_WIDTH, self.CARD_HEIGHT):
                return "foundation", suit

        # Cascades
        base_y = self._cascade_row_y()
        stack_h = self.CARD_HEIGHT + 12 * self.STACK_GAP
        for i in range(8):
            sx = self._slot_x(i)
            if self._rect_contains(x, y, sx, base_y, self.CARD_WIDTH, stack_h):
                return "cascade", i

        return None

    def _start_drag(self, source_kind, source_idx, source_pos, cards, sx, sy, mouse_x, mouse_y):
        count = len(cards)
        card = cards[0]
        self.drag["active"] = True
        self.drag["source_kind"] = source_kind
        self.drag["source_idx"] = source_idx
        self.drag["source_pos"] = source_pos
        self.drag["card"] = card
        self.drag["cards"] = list(cards)
        self.drag["count"] = count
        self.drag["tag"] = "drag_card"
        self.drag["offset_x"] = mouse_x - sx
        self.drag["offset_y"] = mouse_y - sy
        hold_x = sx
        hold_y = sy - 4
        self.drag["x"] = hold_x
        self.drag["y"] = hold_y
        self.drag["target_x"] = hold_x
        self.drag["target_y"] = hold_y
        self.drag["origin_x"] = sx
        self.drag["origin_y"] = sy
        self.drag["lifted"] = True
        self.drag["follow_active"] = True
        self.drag["follow_job"] = None

        # Redraw board with drag state so source card is temporarily hidden.
        self.render()
        if count == 1:
            self._draw_card(hold_x, hold_y, card, tags=(self.drag["tag"],), lifted=True)
        else:
            for j, moving_card in enumerate(cards):
                self._draw_card(
                    hold_x,
                    hold_y + j * self.STACK_GAP,
                    moving_card,
                    tags=(self.drag["tag"],),
                    lifted=True,
                )
        self.canvas.tag_raise(self.drag["tag"])
        self._schedule_drag_follow()

    def _schedule_drag_follow(self):
        if not self.drag["active"] or not self.drag["follow_active"]:
            self.drag["follow_job"] = None
            return

        # Smoothly approach cursor target to avoid choppy B1-Motion jumps.
        smoothing = 0.35
        nx = self.drag["x"] + (self.drag["target_x"] - self.drag["x"]) * smoothing
        ny = self.drag["y"] + (self.drag["target_y"] - self.drag["y"]) * smoothing
        self._move_drag_to(nx, ny)
        self.drag["follow_job"] = self.root.after(12, self._schedule_drag_follow)

    def _clear_drag(self):
        follow_job = self.drag.get("follow_job")
        if follow_job is not None:
            try:
                self.root.after_cancel(follow_job)
            except tk.TclError:
                pass

        tag = self.drag.get("tag")
        if tag:
            self.canvas.delete(tag)
        self.drag.update(
            {
                "active": False,
                "source_kind": None,
                "source_idx": None,
                "source_pos": None,
                "card": None,
                "cards": [],
                "count": 1,
                "tag": None,
                "offset_x": 0,
                "offset_y": 0,
                "x": 0,
                "y": 0,
                "target_x": 0,
                "target_y": 0,
                "origin_x": 0,
                "origin_y": 0,
                "lifted": False,
                "follow_job": None,
                "follow_active": False,
            }
        )

    def _move_drag_to(self, new_x, new_y):
        dx = new_x - self.drag["x"]
        dy = new_y - self.drag["y"]
        self.canvas.move(self.drag["tag"], dx, dy)
        self.drag["x"] = new_x
        self.drag["y"] = new_y

    def _animate_drag_to(self, dest_x, dest_y, on_done, steps=10, interval_ms=12):
        self.drag["follow_active"] = False
        start_x = self.drag["x"]
        start_y = self.drag["y"]
        step = {"i": 0}

        def tick():
            i = step["i"] + 1
            step["i"] = i
            t = i / steps
            # Ease-out interpolation for smooth snap.
            ease = 1 - (1 - t) * (1 - t)
            nx = start_x + (dest_x - start_x) * ease
            ny = start_y + (dest_y - start_y) * ease
            self._move_drag_to(nx, ny)

            if i < steps:
                self.root.after(interval_ms, tick)
            else:
                on_done()

        tick()

    def _apply_drop_move(self, target_kind, target_val):
        src_kind = self.drag["source_kind"]
        src_idx = self.drag["source_idx"]
        card = self.drag["card"]
        move_count = self.drag["count"]

        next_state = None
        msg = None

        if src_kind == "cascade" and target_kind == "cascade":
            if move_count > 1:
                next_state = FreeCell.move_sequence_cascade_to_cascade(self.state, src_idx, target_val, move_count)
                msg = f"Supermoved {move_count} cards to Cascade {target_val + 1}."
            else:
                next_state = FreeCell.move_cascade_to_cascade(self.state, src_idx, target_val)
                msg = f"Moved to Cascade {target_val + 1}."
        elif src_kind == "cascade" and target_kind == "free":
            if move_count != 1:
                raise ValueError("Only one card can move to a free cell")
            next_state = FreeCell.move_cascade_to_freecell(self.state, src_idx, target_val)
            msg = f"Moved to Free Cell {target_val + 1}."
        elif src_kind == "cascade" and target_kind == "foundation":
            if move_count != 1:
                raise ValueError("Only one card can move to foundation")
            if card.suit != target_val:
                raise ValueError("Invalid foundation target")
            next_state = FreeCell.move_cascade_to_foundation(self.state, src_idx)
            msg = f"Moved {card} to Foundation {target_val}."
        elif src_kind == "free" and target_kind == "cascade":
            next_state = FreeCell.move_freecell_to_cascade(self.state, src_idx, target_val)
            msg = f"Moved to Cascade {target_val + 1}."
        elif src_kind == "free" and target_kind == "foundation":
            if card.suit != target_val:
                raise ValueError("Invalid foundation target")
            next_state = FreeCell.move_freecell_to_foundation(self.state, src_idx)
            msg = f"Moved {card} to Foundation {target_val}."
        else:
            raise ValueError("Unsupported drop move")

        return next_state, msg

    def _target_card_position_after_move(self, next_state, target_kind, target_val, moved_count=1):
        if target_kind == "free":
            return self._slot_x(target_val), self._top_row_y()
        if target_kind == "foundation":
            suit_to_slot = {"H": 4, "D": 5, "C": 6, "S": 7}
            return self._slot_x(suit_to_slot[target_val]), self._top_row_y()
        # cascade: align dragged sequence base with destination base position.
        x = self._slot_x(target_val)
        y = self._cascade_row_y() + (len(next_state.cascades[target_val]) - moved_count) * self.STACK_GAP
        return x, y

    def _on_canvas_press(self, event):
        if self.drag["active"]:
            return

        source = self._detect_draggable_source(event.x, event.y)
        if source is None:
            self.selection = None
            self.render()
            return

        source_kind, source_idx, source_pos, cards, sx, sy = source
        self.selection = None
        self._start_drag(source_kind, source_idx, source_pos, cards, sx, sy, event.x, event.y)
        if len(cards) > 1:
            self.status_var.set(f"Dragging sequence ({len(cards)} cards)...")
        else:
            self.status_var.set(f"Dragging {cards[0]}...")

    def _on_canvas_drag(self, event):
        if not self.drag["active"]:
            return
        nx = event.x - self.drag["offset_x"]
        ny = event.y - self.drag["offset_y"]
        self.drag["target_x"] = nx
        self.drag["target_y"] = ny

    def _on_canvas_release(self, event):
        if not self.drag["active"]:
            return

        self.drag["follow_active"] = False

        # Pull one final target update before drop evaluation.
        release_x = event.x - self.drag["offset_x"]
        release_y = event.y - self.drag["offset_y"]
        self._move_drag_to(release_x, release_y)

        target = self._detect_drop_target(event.x, event.y)
        if target is None:
            ox, oy = self.drag["origin_x"], self.drag["origin_y"]

            def done_back():
                self._clear_drag()
                self.status_var.set("Invalid drop.")
                self.render()

            self._animate_drag_to(ox, oy, done_back)
            return

        target_kind, target_val = target

        # Click-and-release on source acts like a hold/cancel, not an invalid move.
        if target_kind == self.drag["source_kind"] and target_val == self.drag["source_idx"]:
            ox, oy = self.drag["origin_x"], self.drag["origin_y"]

            def done_same_source():
                self._clear_drag()
                self.status_var.set("Move cancelled.")
                self.render()

            self._animate_drag_to(ox, oy, done_same_source)
            return

        try:
            next_state, msg = self._apply_drop_move(target_kind, target_val)
            tx, ty = self._target_card_position_after_move(
                next_state,
                target_kind,
                target_val,
                moved_count=self.drag["count"],
            )

            def done_ok():
                self._clear_drag()
                self._set_state_if_valid(next_state, msg)

            self._animate_drag_to(tx, ty, done_ok)
        except ValueError:
            ox, oy = self.drag["origin_x"], self.drag["origin_y"]

            def done_fail():
                self._clear_drag()
                self.status_var.set("Invalid move.")
                self.render()

            self._animate_drag_to(ox, oy, done_fail)

    def _draw_selection_marker(self):
        if self.selection is None:
            return
        kind, idx = self.selection
        if kind == "free":
            x = self._slot_x(idx)
            y = self._top_row_y()
        else:
            x = self._slot_x(idx)
            cascade = self.state.cascades[idx]
            y = self._cascade_row_y() if not cascade else self._cascade_row_y() + (len(cascade) - 1) * self.STACK_GAP

        self.canvas.create_rectangle(
            x - 3,
            y - 3,
            x + self.CARD_WIDTH + 3,
            y + self.CARD_HEIGHT + 3,
            outline="#ffd84d",
            width=3,
        )

    def _push_history(self):
        self.history.append(self.state.copy())

    def _set_state_if_valid(self, next_state, ok_message):
        self._push_history()
        self.state = next_state
        self._auto_move_to_foundation_internal()
        self.selection = None
        self.status_var.set(ok_message)
        self.render()

    def on_click_cascade(self, idx):
        if self.selection is None:
            if self.state.get_top_card(idx) is None:
                self.status_var.set("That cascade is empty.")
                return
            self.selection = ("cascade", idx)
            self.status_var.set(f"Selected top card from Cascade {idx + 1}.")
            self.render()
            return

        src_kind, src_idx = self.selection
        if src_kind == "cascade" and src_idx == idx:
            self.selection = None
            self.status_var.set("Selection cleared.")
            self.render()
            return

        try:
            if src_kind == "cascade":
                next_state = FreeCell.move_cascade_to_cascade(self.state, src_idx, idx)
                self._set_state_if_valid(next_state, f"Moved to Cascade {idx + 1}.")
            else:
                next_state = FreeCell.move_freecell_to_cascade(self.state, src_idx, idx)
                self._set_state_if_valid(next_state, f"Moved to Cascade {idx + 1}.")
        except ValueError:
            self.status_var.set("Invalid move.")

    def on_click_free_cell(self, idx):
        if self.selection is None:
            card = self.state.get_free_cell(idx)
            if card is None:
                self.status_var.set("That free cell is empty.")
                return
            self.selection = ("free", idx)
            self.status_var.set(f"Selected card from Free Cell {idx + 1}.")
            self.render()
            return

        src_kind, src_idx = self.selection
        if src_kind == "free" and src_idx == idx:
            self.selection = None
            self.status_var.set("Selection cleared.")
            self.render()
            return

        if not (src_kind == "cascade"):
            self.status_var.set("You can only move from a cascade into a free cell.")
            return

        try:
            next_state = FreeCell.move_cascade_to_freecell(self.state, src_idx, idx)
            self._set_state_if_valid(next_state, f"Moved to Free Cell {idx + 1}.")
        except ValueError:
            self.status_var.set("Invalid move.")

    def on_click_foundation(self, suit):
        if self.selection is None:
            self.status_var.set("Select a source card first.")
            return

        src_kind, src_idx = self.selection
        try:
            if src_kind == "cascade":
                card = self.state.get_top_card(src_idx)
                if card is None or card.suit != suit:
                    self.status_var.set("Invalid foundation target for selected card.")
                    return
                next_state = FreeCell.move_cascade_to_foundation(self.state, src_idx)
                self._set_state_if_valid(next_state, f"Moved {card} to Foundation {suit}.")
            else:
                card = self.state.get_free_cell(src_idx)
                if card is None or card.suit != suit:
                    self.status_var.set("Invalid foundation target for selected card.")
                    return
                next_state = FreeCell.move_freecell_to_foundation(self.state, src_idx)
                self._set_state_if_valid(next_state, f"Moved {card} to Foundation {suit}.")
        except ValueError:
            self.status_var.set("Invalid move to foundation.")

    def _auto_move_to_foundation_internal(self):
        moved = 0
        while True:
            step_done = False

            for c in range(8):
                if FreeCell.can_move_cascade_to_foundation(self.state, c):
                    self._push_history()
                    self.state = FreeCell.move_cascade_to_foundation(self.state, c)
                    moved += 1
                    step_done = True
                    break
            if step_done:
                continue

            for f in range(4):
                if FreeCell.can_move_freecell_to_foundation(self.state, f):
                    self._push_history()
                    self.state = FreeCell.move_freecell_to_foundation(self.state, f)
                    moved += 1
                    step_done = True
                    break

            if not step_done:
                break

        return moved

    def show_hint(self):
        successors = FreeCell.get_successors(self.state)
        if not successors:
            self.status_var.set("No legal moves available.")
            return
        _next_state, move = successors[0]
        self.status_var.set(f"Hint: {move}")

    def run(self):
        self.root.mainloop()

    def solve_with_astar(self):
        if getattr(self, "is_solving", False):
            return

        self.is_solving = True
        self.status_var.set("AI đang suy nghĩ...")
        self.root.update()

        def worker_thread():
            from solvers.astar_solver import AStarSolver
            solver = AStarSolver()
            path, metrics = solver.solve(self.state)
            self.root.after(0, lambda: self._on_solve_complete(path, metrics))

        threading.Thread(target=worker_thread, daemon=True).start()

    def _on_astar_complete(self, path, metrics):
        self.is_solving = False

        if path:
            self.status_var.set(
                f"Giải trong {metrics['solution_length']} bước ({metrics['time_taken']:.2f}s).")
            self.root.after(500, lambda: self.animate_solution(path))
        else:
            self.status_var.set("AI không tìm thấy đường giải!")

    def solve_with_ucs(self):
        if getattr(self, "is_solving", False): return
        self.is_solving = True
        self.status_var.set("UCS đang chạy... ")
        self.root.update()

        import threading
        def worker():
            from solvers.ucs_solver import UCSSolver
            solver = UCSSolver()
            path, metrics = solver.solve(self.state)
            self.root.after(0, lambda: self._on_ucs_complete(path, metrics))

        threading.Thread(target=worker, daemon=True).start()

    def _on_ucs_complete(self, path, metrics):
        self.is_solving = False
        if path:
            self.status_var.set(f"UCS chạy thành công! {metrics['solution_length']} bước ({metrics['time_taken']:.2f}s).")
            self.animate_solution(path)
        else:
            self.status_var.set("UCS không tìm thấy đường giải!")
    def animate_solution(self, path):

        if not path:
            from tkinter import messagebox
            self.status_var.set("Hoàn thành! AI đã giải xong ván bài.")
            messagebox.showinfo("Hoàn thành", "AI đã giải xong ván bài!")
            return

        move = path.pop(0)

        from game.freecell import FreeCell

        if move.move_type == 'CASCADE_TO_CASCADE':
            self.state = FreeCell.move_cascade_to_cascade(self.state, move.from_location, move.to_location)
        elif move.move_type == 'SEQUENCE_CASCADE_TO_CASCADE':
            self.state = FreeCell.move_sequence_cascade_to_cascade(self.state, move.from_location, move.to_location,
                                                                   move.count)
        elif move.move_type == 'CASCADE_TO_FREECELL':
            self.state = FreeCell.move_cascade_to_freecell(self.state, move.from_location, move.to_location)
        elif move.move_type == 'FREECELL_TO_CASCADE':
            self.state = FreeCell.move_freecell_to_cascade(self.state, move.from_location, move.to_location)
        elif move.move_type == 'CASCADE_TO_FOUNDATION':
            self.state = FreeCell.move_cascade_to_foundation(self.state, move.from_location)
        elif move.move_type == 'FREECELL_TO_FOUNDATION':
            self.state = FreeCell.move_freecell_to_foundation(self.state, move.from_location)

        self.status_var.set(f"AI đang đi: {str(move)}")
        self.render()
        self.root.update()
        self.root.after(300, lambda: self.animate_solution(path))
