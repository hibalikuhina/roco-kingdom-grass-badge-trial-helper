"""Tkinter front end: pick a database, match a clipboard icon, grow the database."""
from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from PIL import Image, ImageTk

from . import clipboard, config, imaging
from .database import DEFAULT_ROOT, IconDB, list_dbs

PANEL = 260
CANDIDATES = 10          # rows shown in the Candidates tab after a Ctrl+V check
FONT = "Segoe UI" if sys.platform == "win32" else "TkDefaultFont"

IDLE_HINT = "Copy an icon  —  Ctrl+V to check it,  Ctrl+N to add it"

HELP_TEXT = """Copy an icon to the clipboard (any screenshot crop of one icon,
any resolution), then:

    Ctrl+V   check it against this database  -  answers Y or N and
             shows your input next to the closest icon stored
    Ctrl+N   add it to this database  -  searches first, and if
             something similar is already stored it shows both and
             asks whether to add, replace, or cancel.
             If the pasted image holds a whole grid of icons, they
             are split apart into one row each, and every row where
             something similar is already stored waits for you to
             pick a side: your icon (add it as new) or the stored
             one (skip yours).  Nothing is added or dropped on your
             behalf - the Import button stays disabled until every
             conflict has an answer
    Ctrl+E   edit the database: thumbnails of every icon, with
             rename and multi-select delete
    F5       reload the database from disk
    F1       this help

All three are also buttons at the bottom of the window, and everything
is in the Database and Icon menus.

The verdict shows two numbers.  "similarity" is how close the best stored
icon is; "stand-out" is how far it rises above the rest of the database.
A Y needs both above their thresholds, which you can adjust at the top
right - they are saved per database."""


def _tile_photo(tile: Image.Image | None, size: int = PANEL) -> ImageTk.PhotoImage | None:
    if tile is None:
        return None
    return ImageTk.PhotoImage(imaging.flatten(tile).resize((size, size), Image.LANCZOS))


# --------------------------------------------------------------- dialogs
class DBChooser(tk.Toplevel):
    """Startup dialog: open an existing database or create one by numeric id."""

    def __init__(self, master, root_dir: Path, current: int | None = None):
        super().__init__(master)
        self.title("Select icon database")
        self.root_dir = Path(root_dir)
        self.result: IconDB | None = None
        self.resizable(False, False)
        self.transient(master)

        ttk.Label(self, text="Databases", font=(FONT, 11, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(12, 4))
        ttk.Label(self, text=str(self.root_dir), foreground="#666").grid(
            row=1, column=0, columnspan=3, sticky="w", padx=12)

        self.listbox = tk.Listbox(self, width=42, height=10, font=(FONT, 10),
                                  activestyle="dotbox", exportselection=False)
        self.listbox.grid(row=2, column=0, columnspan=3, padx=12, pady=8)
        self.listbox.bind("<Double-Button-1>", lambda _e: self._open())

        ttk.Label(self, text="New database id:").grid(row=3, column=0, sticky="e", padx=(12, 4))
        self.new_id = ttk.Entry(self, width=8)
        self.new_id.grid(row=3, column=1, sticky="w")
        ttk.Button(self, text="Create", command=self._create).grid(row=3, column=2, sticky="w", padx=(0, 12))

        bar = ttk.Frame(self)
        bar.grid(row=4, column=0, columnspan=3, sticky="ew", padx=12, pady=12)
        ttk.Button(bar, text="Open", command=self._open).pack(side="left")
        ttk.Button(bar, text="Delete", command=self._delete).pack(side="left", padx=6)
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")

        self._refresh(select=current)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Return>", lambda _e: self._open())
        self.bind("<Escape>", lambda _e: self.destroy())

    def _refresh(self, select: int | None = None):
        self.dbs = list_dbs(self.root_dir)
        self.listbox.delete(0, tk.END)
        for db_id, count in self.dbs:
            self.listbox.insert(tk.END, f"DB {db_id:03d}    {count} icon(s)")
        if self.dbs:
            idx = next((i for i, (d, _) in enumerate(self.dbs) if d == select), 0)
            self.listbox.selection_set(idx)
            self.listbox.see(idx)

    def _selected_id(self) -> int | None:
        sel = self.listbox.curselection()
        return self.dbs[sel[0]][0] if sel else None

    def _open(self):
        db_id = self._selected_id()
        if db_id is None:
            messagebox.showinfo("Select a database", "Pick a database, or create one.", parent=self)
            return
        try:
            self.result = IconDB.open(self.root_dir, db_id)
        except Exception as exc:
            messagebox.showerror("Cannot open", str(exc), parent=self)
            return
        self.destroy()

    def _create(self):
        raw = self.new_id.get().strip()
        if not raw.isdigit():
            messagebox.showwarning("Invalid id", "The database id must be a number.", parent=self)
            return
        try:
            self.result = IconDB.create(self.root_dir, int(raw))
        except FileExistsError as exc:
            messagebox.showwarning("Already exists", str(exc), parent=self)
            self._refresh(select=int(raw))
            return
        self.destroy()

    def _delete(self):
        db_id = self._selected_id()
        if db_id is None:
            return
        if messagebox.askyesno(
                "Delete database",
                f"Delete DB {db_id:03d} and every icon in it?\nThis cannot be undone.",
                parent=self, default="no"):
            IconDB(self.root_dir, db_id).destroy()
            self._refresh()


class SimilarIconDialog(tk.Toplevel):
    """Shown when an icon being added looks like one already in the database."""

    def __init__(self, master, new_tile: Image.Image, icon, score: float):
        super().__init__(master)
        self.title("Similar icon already in the database")
        self.result = "cancel"
        self.transient(master)
        self.resizable(False, False)

        ttk.Label(self, text=f"Best existing match scores {score:.3f} "
                             f"({icon.id}  {icon.name}).",
                  font=(FONT, 11, "bold")).pack(padx=14, pady=(14, 2))
        ttk.Label(self, text="Icons are meant to be unique - is the new one really different?",
                  foreground="#555").pack(padx=14)

        row = ttk.Frame(self)
        row.pack(padx=14, pady=12)
        self._photos = []
        for title, tile in (("New (clipboard)", new_tile), (f"Existing {icon.id}", icon.tile)):
            cell = ttk.Frame(row)
            cell.pack(side="left", padx=8)
            ttk.Label(cell, text=title, font=(FONT, 10, "bold")).pack()
            photo = _tile_photo(tile, 220)
            self._photos.append(photo)
            tk.Label(cell, image=photo, bd=1, relief="solid").pack()

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=14, pady=(0, 14))
        ttk.Button(bar, text="Add as new icon", command=lambda: self._done("add")).pack(side="left")
        ttk.Button(bar, text=f"Replace {icon.id}", command=lambda: self._done("replace")).pack(side="left", padx=6)
        ttk.Button(bar, text="Cancel", command=lambda: self._done("cancel")).pack(side="right")
        self.bind("<Escape>", lambda _e: self._done("cancel"))
        self.protocol("WM_DELETE_WINDOW", lambda: self._done("cancel"))

    def _done(self, result: str):
        self.result = result
        self.destroy()


def _modal(dialog: tk.Toplevel):
    dialog.update_idletasks()
    dialog.grab_set()
    dialog.wait_window()


class ScrollFrame(ttk.Frame):
    """A frame that scrolls vertically, with the mouse wheel wired up."""

    def __init__(self, master, height=460, width=760):
        super().__init__(master)
        self.canvas = tk.Canvas(self, height=height, width=width,
                                highlightthickness=0, bg="#fafafa")
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        self.inner = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        for widget in (self.canvas, self.inner):
            widget.bind("<MouseWheel>", self._on_wheel)

    def _on_wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def bind_wheel(self, widget):
        widget.bind("<MouseWheel>", self._on_wheel)


class BatchAddDialog(tk.Toplevel):
    """Resolve a pasted grid icon by icon: add each one, or skip it.

    Every row is a choice between the icon you pasted (left) and whatever the
    database already holds that looks like it (right).  Rows where something
    similar was found start *undecided* - nothing is added or dropped until you
    say which side wins.
    """

    ROW_BG = "#fafafa"
    UNDECIDED_BG = "#fff3d6"

    def __init__(self, master, db, items):
        """items: [(crop, SearchResult), ...] in reading order."""
        super().__init__(master)
        self.title(f"Import {len(items)} icons from the pasted grid")
        self.db = db
        self.items = items
        self.result: list[tuple[int, str]] | None = None   # [(index, name), ...]
        self.single = False                                # "treat as one icon"
        self.transient(master)

        ttk.Label(self, text=f"Found {len(items)} icons in the clipboard image.",
                  font=(FONT, 12, "bold")).pack(anchor="w", padx=14, pady=(14, 0))
        ttk.Label(self, text="Tick the left icon to add it as a new entry, or the right one "
                             "to keep what is already stored and skip yours.",
                  foreground="#555").pack(anchor="w", padx=14, pady=(2, 8))

        scroll = ScrollFrame(self, height=470, width=940)
        scroll.pack(fill="both", expand=True, padx=14)

        self.choices: list[tk.StringVar] = []
        self.rows: list[tk.Frame] = []
        self.conflicts: list[int] = []
        self.names: list[ttk.Entry] = []
        self._photos = []

        next_id = int(db._next_id())
        for index, (_crop, found) in enumerate(items):
            conflict = db.is_duplicate(found)
            if conflict:
                self.conflicts.append(index)
            choice = tk.StringVar(value="" if conflict else "add")
            choice.trace_add("write", lambda *_a, i=index: self._on_choice(i))
            self.choices.append(choice)

            row = tk.Frame(scroll.inner, bg=self.UNDECIDED_BG if conflict else self.ROW_BG,
                           bd=1, relief="solid", padx=6, pady=5)
            row.grid(row=index, column=0, sticky="ew", pady=2)
            self.rows.append(row)
            scroll.bind_wheel(row)

            # ---- left: the icon you pasted
            tk.Radiobutton(row, variable=choice, value="add", bg=row["bg"],
                           text="add as new", compound="right",
                           font=(FONT, 9)).grid(row=0, column=0, rowspan=2, padx=(0, 4))
            photo = _tile_photo(found.tile, 76)
            self._photos.append(photo)
            tk.Label(row, image=photo, bd=1, relief="solid",
                     bg=row["bg"]).grid(row=0, column=1, rowspan=2)
            entry = ttk.Entry(row, width=20)
            entry.insert(0, f"{next_id + index:04d}")
            entry.grid(row=0, column=2, rowspan=2, padx=8)
            self.names.append(entry)

            # ---- middle: why this row is a conflict at all
            if conflict:
                verdict = "already in the database" if db.is_match(found) else "looks similar to"
                scores = (f"similarity {found.similarity:.3f}   "
                          f"stand-out {found.confidence:.3f}")
                tk.Label(row, text=f"{verdict}\n{scores}",
                         bg=row["bg"], fg="#b9770e", justify="center",
                         width=26).grid(row=0, column=3, rowspan=2)
                match_photo = _tile_photo(found.best.tile, 76)
                self._photos.append(match_photo)
                tk.Label(row, image=match_photo, bd=1, relief="solid",
                         bg=row["bg"]).grid(row=0, column=4, rowspan=2, padx=(0, 2))
                right_text = f"skip - keep {found.best.id} {found.best.name}"
            else:
                tk.Label(row, text="nothing similar stored", bg=row["bg"], fg="#1e8449",
                         width=26).grid(row=0, column=3, rowspan=2)
                tk.Label(row, text="", bg=row["bg"], width=11).grid(row=0, column=4, rowspan=2)
                right_text = "skip this icon"

            # ---- right: keep what is stored
            tk.Radiobutton(row, variable=choice, value="skip", bg=row["bg"],
                           text=right_text, font=(FONT, 9)).grid(row=0, column=5,
                                                                 rowspan=2, sticky="w")

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=14, pady=(4, 0))
        self.summary = ttk.Label(bar, text="", font=(FONT, 10, "bold"))
        self.summary.pack(side="left")
        ttk.Button(bar, text="Undecided -> skip",
                   command=lambda: self._resolve_rest("skip")).pack(side="right")
        ttk.Button(bar, text="Undecided -> add as new",
                   command=lambda: self._resolve_rest("add")).pack(side="right", padx=6)

        bar2 = ttk.Frame(self)
        bar2.pack(fill="x", padx=14, pady=12)
        self.add_button = ttk.Button(bar2, text="Import", command=self._confirm)
        self.add_button.pack(side="left")
        ttk.Button(bar2, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(bar2, text="Not a grid - treat as one icon",
                   command=self._as_single).pack(side="right", padx=6)
        self.bind("<Escape>", lambda _e: self.destroy())
        self._refresh_summary()

    # ------------------------------------------------------------- choices
    def _on_choice(self, index: int):
        row = self.rows[index]
        colour = self.ROW_BG if self.choices[index].get() else self.UNDECIDED_BG
        row.configure(bg=colour)
        for child in row.winfo_children():
            if not isinstance(child, ttk.Entry):
                child.configure(bg=colour)
        self._refresh_summary()

    def _resolve_rest(self, value: str):
        for choice in self.choices:
            if not choice.get():
                choice.set(value)

    def _counts(self):
        values = [c.get() for c in self.choices]
        return values.count("add"), values.count("skip"), values.count("")

    def _refresh_summary(self):
        add, skip, undecided = self._counts()
        text = f"{add} to add    {skip} to skip"
        if undecided:
            text += f"    {undecided} still undecided"
        self.summary.config(text=text, foreground="#b9770e" if undecided else "#333")
        self.add_button.config(text=f"Import {add} icon(s)",
                               state="disabled" if undecided else "normal")

    def _as_single(self):
        self.single = True
        self.destroy()

    def _confirm(self):
        self.result = [(i, self.names[i].get().strip())
                       for i, choice in enumerate(self.choices) if choice.get() == "add"]
        self.destroy()


class DBEditor(tk.Toplevel):
    """Browse the database as thumbnails; rename and delete from there."""

    COLUMNS = 5

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.db = app.db
        self.title(f"Edit DB {self.db.id:03d}")
        self.transient(master)
        self.vars: dict[str, tk.BooleanVar] = {}
        self._photos = []

        head = ttk.Frame(self, padding=(14, 12, 14, 6))
        head.pack(fill="x")
        self.heading = ttk.Label(head, text="", font=(FONT, 12, "bold"))
        self.heading.pack(side="left")
        ttk.Label(head, text="filter:").pack(side="left", padx=(16, 4))
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_a: self._populate())
        ttk.Entry(head, textvariable=self.filter_var, width=22).pack(side="left")

        self.scroll = ScrollFrame(self, height=520, width=780)
        self.scroll.pack(fill="both", expand=True, padx=14)

        bar = ttk.Frame(self, padding=(14, 10))
        bar.pack(fill="x")
        ttk.Button(bar, text="Rename...", command=self.rename).pack(side="left")
        ttk.Button(bar, text="Delete ticked", command=self.delete).pack(side="left", padx=6)
        ttk.Button(bar, text="Tick all", command=lambda: self._set_all(True)).pack(side="left")
        ttk.Button(bar, text="Untick all", command=lambda: self._set_all(False)).pack(side="left", padx=6)
        ttk.Button(bar, text="Close", command=self.destroy).pack(side="right")

        self._populate()
        self.bind("<Escape>", lambda _e: self.destroy())

    def _populate(self):
        for child in self.scroll.inner.winfo_children():
            child.destroy()
        self._photos.clear()
        needle = self.filter_var.get().strip().lower()
        icons = [i for i in self.db.icons
                 if not needle or needle in i.name.lower() or needle in i.id.lower()]
        self.vars = {i.id: self.vars.get(i.id, tk.BooleanVar(value=False)) for i in icons}
        self.heading.config(text=f"DB {self.db.id:03d}   -   {len(self.db.icons)} icon(s)"
                                 + (f", {len(icons)} shown" if needle else ""))

        for n, icon in enumerate(icons):
            cell = ttk.Frame(self.scroll.inner, padding=6)
            cell.grid(row=n // self.COLUMNS, column=n % self.COLUMNS)
            photo = _tile_photo(icon.tile, 108)
            self._photos.append(photo)
            button = tk.Checkbutton(
                cell, image=photo, text=f"{icon.id}  {icon.name}", compound="top",
                variable=self.vars[icon.id], indicatoron=False, bd=1, relief="ridge",
                bg="#ffffff", selectcolor="#cfe3ff", font=(FONT, 8), width=118)
            button.pack()
            button.bind("<Double-Button-1>", lambda _e, i=icon: self._rename_icon(i))
            self.scroll.bind_wheel(button)
            self.scroll.bind_wheel(cell)

        if not icons:
            ttk.Label(self.scroll.inner,
                      text="No icons here yet." if not self.db.icons else "Nothing matches the filter.",
                      foreground="#777", padding=20).grid(row=0, column=0)

    def _set_all(self, value: bool):
        for var in self.vars.values():
            var.set(value)

    def _ticked(self):
        return [i for i in self.db.icons if i.id in self.vars and self.vars[i.id].get()]

    def _rename_icon(self, icon):
        name = simpledialog.askstring("Rename", f"New name for {icon.id}:",
                                      initialvalue=icon.name, parent=self)
        if name and name.strip():
            self.db.rename(icon.id, name.strip())
            self._populate()
            self.app.refresh_db_views()
            self.app.set_status(f"Renamed {icon.id} to {name.strip()}.")

    def rename(self):
        ticked = self._ticked()
        if len(ticked) != 1:
            messagebox.showinfo("Rename", "Tick exactly one icon to rename "
                                          "(or double-click it).", parent=self)
            return
        self._rename_icon(ticked[0])

    def delete(self):
        ticked = self._ticked()
        if not ticked:
            messagebox.showinfo("Delete", "Tick the icons you want to delete.", parent=self)
            return
        names = "\n".join(f"  {i.id}  {i.name}" for i in ticked[:12])
        more = f"\n  ... and {len(ticked) - 12} more" if len(ticked) > 12 else ""
        if not messagebox.askyesno("Delete icons",
                                   f"Delete {len(ticked)} icon(s) from DB "
                                   f"{self.db.id:03d}?\n\n{names}{more}\n\nThis cannot be undone.",
                                   parent=self, default="no"):
            return
        for icon in ticked:
            self.db.remove(icon.id)
            self.vars.pop(icon.id, None)
        self._populate()
        self.app.refresh_db_views()
        self.app.set_status(f"Deleted {len(ticked)} icon(s) from DB {self.db.id:03d}.")


# ------------------------------------------------------------------ app
class App:
    def __init__(self, root: tk.Tk, db_root: Path = DEFAULT_ROOT):
        self.root = root
        self.db_root = Path(db_root)
        self.db_root.mkdir(parents=True, exist_ok=True)
        self.db: IconDB | None = None
        self.query_tile: Image.Image | None = None
        self.candidates: list[tuple] = []
        self._photo_in = None
        self._photo_match = None
        self._last_image: Image.Image | None = None

        root.title("Icon Matcher")
        root.minsize(900, 620)
        self._build()
        self._build_menu()
        root.bind("<Control-v>", lambda _e: self.do_match())
        root.bind("<Control-m>", lambda _e: self.do_match())
        root.bind("<Control-n>", lambda _e: self.do_add())
        root.bind("<F5>", lambda _e: self.reload())
        root.bind("<F1>", lambda _e: self.show_help())
        root.bind("<Control-e>", lambda _e: self.edit_db())
        root.after(80, self.choose_db)

    # ------------------------------------------------------------- layout
    def _build(self):
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")

        top = ttk.Frame(self.root, padding=(10, 8))
        top.pack(fill="x")
        self.db_label = ttk.Label(top, text="No database", font=(FONT, 12, "bold"))
        self.db_label.pack(side="left")
        ttk.Button(top, text="Switch DB...", command=self.choose_db).pack(side="left", padx=10)
        ttk.Button(top, text="Open folder", command=self.open_folder).pack(side="left")

        ttk.Label(top, text="stand-out >=").pack(side="right", padx=(2, 10))
        self.rel_var = tk.DoubleVar(value=config.MATCH_REL)
        ttk.Spinbox(top, from_=0.0, to=1.0, increment=0.05, width=5, format="%.2f",
                    textvariable=self.rel_var, command=self._save_thresholds).pack(side="right")
        ttk.Label(top, text="similarity >=").pack(side="right", padx=(12, 10))
        self.sim_var = tk.DoubleVar(value=config.MATCH_SIM)
        ttk.Spinbox(top, from_=0.0, to=1.0, increment=0.01, width=5, format="%.2f",
                    textvariable=self.sim_var, command=self._save_thresholds).pack(side="right")

        self.verdict = tk.Label(self.root, text=IDLE_HINT,
                                font=(FONT, 16, "bold"), bg="#e9e9e9", fg="#333", pady=10)
        self.verdict.pack(fill="x", padx=10)

        # the status bar and the action buttons are packed before the body so
        # that a short window shrinks the panels instead of hiding the buttons
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(self.root, textvariable=self.status, relief="sunken",
                  anchor="w", padding=(6, 3)).pack(fill="x", side="bottom")

        actions = ttk.Frame(self.root, padding=(10, 8, 10, 10))
        actions.pack(fill="x", side="bottom")
        ttk.Button(actions, text="Check clipboard icon  (Ctrl+V)",
                   command=self.do_match).pack(side="left", ipadx=8, ipady=4)
        ttk.Button(actions, text="Add clipboard icon to DB  (Ctrl+N)",
                   command=self.do_add).pack(side="left", padx=8, ipadx=8, ipady=4)
        ttk.Button(actions, text="Edit database  (Ctrl+E)",
                   command=self.edit_db).pack(side="left", ipadx=8, ipady=4)
        ttk.Button(actions, text="Shortcuts  (F1)",
                   command=self.show_help).pack(side="right", ipady=4)

        body = ttk.Frame(self.root, padding=10)
        body.pack(fill="both", expand=True)

        panels = ttk.Frame(body)
        panels.pack(side="left")
        self.in_title = ttk.Label(panels, text="Input (clipboard)", font=(FONT, 10, "bold"))
        self.in_title.grid(row=0, column=0, pady=(0, 4))
        self.match_title = ttk.Label(panels, text="Best match", font=(FONT, 10, "bold"))
        self.match_title.grid(row=0, column=1, pady=(0, 4))
        # a tk.Label with no image sizes width/height in characters and lines,
        # not pixels, which asked for a window taller than the screen and
        # pushed the action row out of sight until the first paste
        self._blank = ImageTk.PhotoImage(Image.new("RGB", (PANEL, PANEL), "#ffffff"))
        self.in_canvas = tk.Label(panels, bd=1, relief="solid", bg="#ffffff",
                                  image=self._blank, width=PANEL, height=PANEL)
        self.in_canvas.grid(row=1, column=0, padx=(0, 10))
        self.match_canvas = tk.Label(panels, bd=1, relief="solid", bg="#ffffff",
                                     image=self._blank, width=PANEL, height=PANEL)
        self.match_canvas.grid(row=1, column=1)
        self.in_sub = ttk.Label(panels, text="-", foreground="#666")
        self.in_sub.grid(row=2, column=0, pady=4)
        self.match_sub = ttk.Label(panels, text="-", foreground="#666")
        self.match_sub.grid(row=2, column=1, pady=4)

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))
        self.tabs = ttk.Notebook(right)
        self.tabs.pack(fill="both", expand=True)
        self.cand_tree = self._make_tree(self.tabs, ("rank", "icon", "score"))
        self.all_tree = self._make_tree(self.tabs, ("id", "name", "added"))
        self.tabs.add(self.cand_tree.master, text="Candidates")
        self.tabs.add(self.all_tree.master, text="All icons")
        self.cand_tree.bind("<<TreeviewSelect>>", self._on_candidate_select)
        self.all_tree.bind("<<TreeviewSelect>>", self._on_all_select)

        tools = ttk.Frame(right)
        tools.pack(fill="x", pady=(8, 0))
        ttk.Button(tools, text="Rename", command=self.rename_selected).pack(side="left")
        ttk.Button(tools, text="Delete", command=self.delete_selected).pack(side="left", padx=6)
        ttk.Button(tools, text="Reload (F5)", command=self.reload).pack(side="left")

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        db_menu = tk.Menu(menubar, tearoff=0)
        db_menu.add_command(label="Switch / create database...", command=self.choose_db)
        db_menu.add_command(label="Edit database (rename / delete icons)...",
                            accelerator="Ctrl+E", command=self.edit_db)
        db_menu.add_command(label="Open database folder", command=self.open_folder)
        db_menu.add_command(label="Reload from disk", accelerator="F5", command=self.reload)
        db_menu.add_separator()
        db_menu.add_command(label="Quit", command=self.root.destroy)
        menubar.add_cascade(label="Database", menu=db_menu)

        icon_menu = tk.Menu(menubar, tearoff=0)
        icon_menu.add_command(label="Check clipboard icon against the database",
                              accelerator="Ctrl+V", command=self.do_match)
        icon_menu.add_command(label="Add clipboard icon to the database",
                              accelerator="Ctrl+N", command=self.do_add)
        icon_menu.add_separator()
        icon_menu.add_command(label="Rename selected", command=self.rename_selected)
        icon_menu.add_command(label="Delete selected", command=self.delete_selected)
        menubar.add_cascade(label="Icon", menu=icon_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Shortcuts and how it works",
                              accelerator="F1", command=self.show_help)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def edit_db(self):
        if self.db:
            _modal(DBEditor(self.root, self))

    def show_help(self):
        messagebox.showinfo("Icon Matcher", HELP_TEXT, parent=self.root)

    def _make_tree(self, parent, columns):
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=12)
        widths = {"rank": 45, "score": 70, "id": 60, "added": 130}
        for c in columns:
            tree.heading(c, text=c.capitalize())
            tree.column(c, width=widths.get(c, 150), anchor="w")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")
        return tree

    # -------------------------------------------------------------- state
    def choose_db(self):
        dlg = DBChooser(self.root, self.db_root, current=self.db.id if self.db else None)
        _modal(dlg)
        if dlg.result is not None:
            self.db = dlg.result
            self.sim_var.set(self.db.threshold("match_sim"))
            self.rel_var.set(self.db.threshold("match_rel"))
            self._clear_results()
            self.refresh_db_views()
            hint = ("Ctrl+N adds the clipboard icon, Ctrl+V checks one."
                    if self.db.icons else
                    "This database is empty - copy an icon and press Ctrl+N to add it.")
            self.set_status(f"Opened DB {self.db.id:03d} "
                            f"({len(self.db.icons)} icons).   {hint}")
        elif self.db is None:
            self.root.destroy()

    def reload(self):
        if self.db:
            self.db.load()
            self.refresh_db_views()
            self.set_status(f"Reloaded DB {self.db.id:03d}.")

    def refresh_db_views(self):
        if not self.db:
            return
        self.db_label.config(text=f"DB {self.db.id:03d}   -   {len(self.db.icons)} icon(s)")
        self.all_tree.delete(*self.all_tree.get_children())
        for icon in self.db.icons:
            self.all_tree.insert("", "end", iid=icon.id,
                                 values=(icon.id, icon.name, icon.added.replace("T", " ")))

    def _save_thresholds(self):
        if self.db:
            self.db.set_thresholds(match_sim=self.sim_var.get(), match_rel=self.rel_var.get())
            self.set_status(f"Verdict now needs similarity >= {self.sim_var.get():.2f} "
                            f"and stand-out >= {self.rel_var.get():.2f}.")

    def set_status(self, text: str):
        self.status.set(text)

    def open_folder(self):
        if not self.db:
            return
        path = str(self.db.dir)
        if sys.platform == "win32":
            os.startfile(path)                      # noqa: S606
        else:
            subprocess.Popen(["xdg-open", path])

    # ------------------------------------------------------------ display
    def _clear_results(self):
        self.query_tile = None
        self.candidates = []
        self._photo_in = self._photo_match = None
        self.in_canvas.config(image=self._blank, width=PANEL, height=PANEL)
        self.match_canvas.config(image=self._blank, width=PANEL, height=PANEL)
        self.in_sub.config(text="-")
        self.match_sub.config(text="-")
        self.cand_tree.delete(*self.cand_tree.get_children())
        self._set_verdict(IDLE_HINT, "#e9e9e9", "#333")

    def _set_verdict(self, text, bg, fg="#ffffff"):
        self.verdict.config(text=text, bg=bg, fg=fg)

    def _show_input(self, tile: Image.Image, note: str):
        self._photo_in = _tile_photo(tile)
        self.in_canvas.config(image=self._photo_in, width=PANEL, height=PANEL)
        self.in_sub.config(text=note)

    def _show_match(self, icon, score: float | None):
        if icon is None:
            self._photo_match = None
            self.match_canvas.config(image=self._blank, width=PANEL, height=PANEL)
            self.match_sub.config(text="-")
            return
        self._photo_match = _tile_photo(icon.tile)
        self.match_canvas.config(image=self._photo_match, width=PANEL, height=PANEL)
        suffix = f"   score {score:.3f}" if score is not None else ""
        self.match_sub.config(text=f"{icon.id}  {icon.name}{suffix}")

    def _fill_candidates(self, results):
        self.candidates = results
        self.cand_tree.delete(*self.cand_tree.get_children())
        for rank, (icon, score) in enumerate(results, 1):
            self.cand_tree.insert("", "end", iid=icon.id,
                                  values=(rank, f"{icon.id}  {icon.name}", f"{score:.3f}"))
        if results:
            self.tabs.select(0)
            self.cand_tree.selection_set(results[0][0].id)

    def _on_candidate_select(self, _event=None):
        sel = self.cand_tree.selection()
        if not sel:
            return
        for icon, score in self.candidates:
            if icon.id == sel[0]:
                self._show_match(icon, score)
                return

    def _on_all_select(self, _event=None):
        sel = self.all_tree.selection()
        if sel and self.db:
            icon = self.db.get(sel[0])
            if icon:
                self._show_match(icon, None)

    def _selected_icon(self):
        tree = self.all_tree if self.tabs.index("current") == 1 else self.cand_tree
        sel = tree.selection()
        return self.db.get(sel[0]) if (sel and self.db) else None

    # ------------------------------------------------------------ actions
    def _grab(self) -> Image.Image | None:
        try:
            self._last_image = clipboard.grab_image()
            return self._last_image
        except clipboard.ClipboardError as exc:
            messagebox.showwarning("No image on the clipboard", str(exc), parent=self.root)
            return None

    def do_match(self):
        if not self.db:
            return
        image = self._grab()
        if image is None:
            return
        self.set_status("Matching...")
        self.root.update_idletasks()
        found = self.db.search(image, top=CANDIDATES)
        self.query_tile = found.tile
        self._show_input(found.tile, f"pasted {image.size[0]}x{image.size[1]}px")
        self._fill_candidates(found.results)

        if not found.results:
            self._show_match(None, None)
            self._set_verdict("N  -  the database is empty."
                              "  Press Ctrl+N to add this icon.", "#c0392b")
            self.set_status("Nothing to compare against yet - "
                            "add icons with Ctrl+N first.")
            return

        icon = found.best
        self._show_match(icon, found.similarity)
        numbers = f"similarity {found.similarity:.3f}   stand-out {found.confidence:.3f}"
        if self.db.is_match(found):
            self._set_verdict(f"Y  -  already in the DB:  {icon.name}      {numbers}", "#1e8449")
        else:
            self._set_verdict(f"N  -  not in the DB.  Ctrl+N adds it.      {numbers}",
                              "#c0392b")
        runner_up = f"   next best {found.results[1][1]:.3f}" if len(found.results) > 1 else ""
        self.set_status(f"Best {icon.id} {icon.name} {found.similarity:.3f}{runner_up}   "
                        f"(DB median {found.median:.3f})")

    def do_add(self):
        if not self.db:
            return
        image = self._grab()
        if image is None:
            return
        self.set_status("Looking for icons...")
        self.root.update_idletasks()
        crops = imaging.split_grid(image)
        if len(crops) >= 2:
            self.do_add_batch(crops)
            return
        self.add_single(image)

    def do_add_batch(self, crops):
        """A pasted grid of icons: review them all, then store the ticked ones."""
        self.set_status(f"Found {len(crops)} icons - checking each against the database...")
        self.root.update_idletasks()
        items = [(crop, self.db.search(crop, top=1)) for crop in crops]

        dlg = BatchAddDialog(self.root, self.db, items)
        _modal(dlg)
        if dlg.single:                       # user says it was really one icon
            self.add_single(self._last_image)
            return
        if dlg.result is None:
            self.set_status("Import cancelled.")
            return

        # every row was decided in the dialog, so nothing is second-guessed here:
        # what you ticked as new gets added, the rest you chose to skip
        chosen = {index for index, _ in dlg.result}
        added = [self.db.add(items[index][0], name, tile=items[index][1].tile)
                 for index, name in dlg.result]
        skipped = [items[i][1].best for i in range(len(items)) if i not in chosen]

        self.refresh_db_views()
        if added:
            self._show_input(added[-1].tile, "last icon added")
            self._show_match(added[-1], None)
        self._set_verdict(f"Imported {len(added)} icon(s) from the grid"
                          + (f", skipped {len(skipped)} by your choice" if skipped else ""),
                          "#1e8449" if added else "#b9770e")
        detail = ""
        if skipped:
            lines = "\n".join(
                f"  kept {icon.id} {icon.name}" if icon else "  skipped (nothing similar stored)"
                for icon in skipped[:12])
            more = f"\n  ... and {len(skipped) - 12} more" if len(skipped) > 12 else ""
            detail = f"\n\nSkipped {len(skipped)} by your choice:\n{lines}{more}"
        messagebox.showinfo("Import",
                            f"Added {len(added)} icon(s) to DB {self.db.id:03d}."
                            f"{detail}", parent=self.root)
        self.set_status(f"DB {self.db.id:03d} now holds {len(self.db.icons)} icons.")

    def add_single(self, image):
        self.set_status("Checking for duplicates...")
        self.root.update_idletasks()
        found = self.db.search(image, top=5)
        tile = found.tile
        self.query_tile = tile
        self._show_input(tile, f"pasted {image.size[0]}x{image.size[1]}px")
        self._fill_candidates(found.results)

        replace_id = None
        if found.results:
            icon = found.best
            self._show_match(icon, found.similarity)
            if self.db.is_duplicate(found):
                self._set_verdict(f"Similar icon found:  {icon.name}   "
                                  f"similarity {found.similarity:.3f}   "
                                  f"stand-out {found.confidence:.3f}", "#b9770e")
                dlg = SimilarIconDialog(self.root, tile, icon, found.similarity)
                _modal(dlg)
                if dlg.result == "cancel":
                    self.set_status("Add cancelled.")
                    return
                if dlg.result == "replace":
                    replace_id = icon.id

        default = self.db.get(replace_id).name if replace_id else self.db._next_id()
        name = simpledialog.askstring("Icon name", "Name for this icon:",
                                      initialvalue=default, parent=self.root)
        if name is None:
            self.set_status("Add cancelled.")
            return

        if replace_id:
            icon = self.db.replace(replace_id, image, name.strip(), tile=tile)
            verb = "Replaced"
        else:
            icon = self.db.add(image, name.strip(), tile=tile)
            verb = "Added"
        self.refresh_db_views()
        self._show_match(icon, None)
        self._set_verdict(f"{verb}  {icon.id}  {icon.name}", "#1e8449")
        self.set_status(f"{verb} {icon.id} in DB {self.db.id:03d} "
                        f"({len(self.db.icons)} icons).")

    def rename_selected(self):
        icon = self._selected_icon()
        if not icon:
            return
        name = simpledialog.askstring("Rename", f"New name for {icon.id}:",
                                      initialvalue=icon.name, parent=self.root)
        if name:
            self.db.rename(icon.id, name.strip())
            self.refresh_db_views()
            self.set_status(f"Renamed {icon.id} to {name.strip()}.")

    def delete_selected(self):
        icon = self._selected_icon()
        if not icon:
            return
        if messagebox.askyesno("Delete icon", f"Remove {icon.id} ({icon.name}) from DB "
                                              f"{self.db.id:03d}?", parent=self.root, default="no"):
            self.db.remove(icon.id)
            self.refresh_db_views()
            self._show_match(None, None)
            self.cand_tree.delete(*[i for i in self.cand_tree.get_children() if i == icon.id])
            self.set_status(f"Deleted {icon.id}.")


def main(db_root: Path = DEFAULT_ROOT):
    root = tk.Tk()
    App(root, db_root)
    root.mainloop()
