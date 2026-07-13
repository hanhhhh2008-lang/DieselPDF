import copy
import json
import math
import os
import re
import shlex
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk


APP_TITLE = "DieselPDF"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
VENDOR_DIR = os.path.join(APP_DIR, "vendor")
PDF_VENDOR_DIR = os.path.join(APP_DIR, "vendor_pymupdf")
CAD_VENDOR_DIR = os.path.join(APP_DIR, "vendor_cad_py311")
for dependency_dir in [CAD_VENDOR_DIR, PDF_VENDOR_DIR, VENDOR_DIR]:
    if os.path.isdir(dependency_dir) and dependency_dir not in sys.path:
        sys.path.insert(0, dependency_dir)
LIBRARY_PATH = os.path.join(APP_DIR, "dieselpdf-library.json")
PAGE_ORIGIN = (60, 46)

PAPER_MM = {
    "A0": (841, 1189),
    "A1": (594, 841),
    "A2": (420, 594),
    "A3": (297, 420),
    "A4": (210, 297),
    "A5": (148, 210),
    "Letter": (216, 279),
    "Legal": (216, 356),
}

PAPER_NAMES = list(PAPER_MM.keys())
MEASURE_UNITS = ["mm", "cm", "m"]
UNIT_TO_MM = {"mm": 1.0, "cm": 10.0, "m": 1000.0}

SNAP_MODES = [
    "Endpoint",
    "Midpoint",
    "Intersection",
    "Apparent Intersection",
    "Extension",
    "Geometric Center",
    "Center",
    "Tangent",
    "Quadrant",
    "Perpendicular",
    "Node",
    "Nearest",
    "Parallel",
    "Insertion",
]

ICON = {
    "New": "\u2795",
    "Open": "\u25f0",
    "Open PDF": "\u25f1",
    "Save": "\u25a3",
    "Save As": "\u25a7",
    "Print": "\u2399",
    "Undo": "\u21b6",
    "Redo": "\u21b7",
    "Zoom -": "\u2296",
    "Zoom +": "\u2295",
    "Rotate Left": "\u27f2",
    "Rotate Right": "\u27f3",
    "Hand": "\u270b",
    "Select": "\u25c7",
    "Select Text": "\u25a4",
    "Line": "\u2501",
    "Circle": "\u25cb",
    "Cloud": "\u2601",
    "Arrow": "\u2197",
    "Polyline": "\u2571",
    "Rectangle": "\u25ad",
    "Polygon": "\u2b20",
    "Pencil": "\u270e",
    "Eraser": "\u232b",
    "Calibrate": "\u2699",
    "Distance": "\u2194",
    "Perimeter": "\u25a1",
    "Area": "\u25a3",
    "Set Scale": "\u2696",
    "Text Box": "\u25a4",
    "Callout": "\u21f1",
    "Group": "\u25f0",
    "Ungroup": "\u25cc",
    "Flatten": "\u25ac",
    "Library": "\u25a6",
    "Move": "\u2725",
    "Copy": "\u29c9",
    "Offset": "\u22d4",
    "CAD to Text": "\u25a4",
    "Text to CAD": "\u270e",
    "PDF to CAD": "\u21f2",
    "Export DXF": "\u21e7",
    "Delete": "\u2715",
    "Insert": "\u229e",
    "Extract": "\u21e5",
    "Prev": "\u2039",
    "Next": "\u203a",
}


def paper_pixels(name):
    width_mm, height_mm = PAPER_MM.get(name, PAPER_MM["A4"])
    factor = 3.0
    return int(width_mm * factor), int(height_mm * factor)


def clamp_box(x0, y0, x1, y1):
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


class DieselPDF(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1440x900")
        self.minsize(1180, 760)

        self.colors = {
            "chrome": "#f5f5f7",
            "ribbon": "#fbfbfd",
            "active": "#e8f0ff",
            "blue": "#0071e3",
            "red": "#ff3b30",
            "green": "#34c759",
            "yellow": "#ffd60a",
            "page": "#ffffff",
            "work": "#e8eaee",
            "text": "#1d1d1f",
            "muted": "#6e6e73",
            "border": "#d2d2d7",
            "card": "#ffffff",
            "sidebar": "#fbfbfd",
            "status": "#f5f5f7",
        }

        self.font_title = ("Segoe UI", 18, "bold")
        self.font_heading = ("Segoe UI", 10, "bold")
        self.font_body = ("Segoe UI", 9)
        self.font_small = ("Segoe UI", 8)
        self.font_icon = ("Segoe UI Symbol", 15)
        self.font_icon_small = ("Segoe UI Symbol", 13)

        self.configure(bg=self.colors["chrome"])
        self._apply_style()
        self._set_app_icon()

        self.current_tool = "hand"
        self.current_file = None
        self.current_pdf = None
        self.pdf_render_scale = 1.35
        self.pdf_render_cache = {}
        self.pdf_page_image = None
        self.pdf_page_item = None
        self.pdf_render_dir = os.path.join(tempfile.gettempdir(), "DieselPDF", "rendered-pages")
        os.makedirs(self.pdf_render_dir, exist_ok=True)
        self.project_file = None
        self.current_page = 0
        self.pages = [{"paper": "A4", "entries": []}]
        self.page_w, self.page_h = paper_pixels("A4")
        self.next_entry_id = 1
        self.next_group_id = 1
        self.selected_entries = []
        self.selection_boxes = []
        self.resize_handles = []
        self.undo_stack = []
        self.redo_stack = []
        self.drag = None
        self.pending_points = []
        self.pending_preview = None
        self.zoom_level = 1.0
        self.rotation = 0
        self.scale_units_per_px = None
        self.scale_unit = "mm"
        self.tool_buttons = {}
        self.cursor_items = []
        self.snap_marker = None
        self.snap_candidate = None
        self.layers = [{"name": "0", "visible": True, "locked": False}]
        self.current_layer = "0"
        self.active_command = ""

        self.line_color_var = tk.StringVar(value="#ff0000")
        self.fill_color_var = tk.StringVar(value="None")
        self.width_var = tk.StringVar(value="2")
        self.line_type_var = tk.StringVar(value="Solid")
        self.opacity_var = tk.StringVar(value="100%")
        self.blend_var = tk.StringVar(value="Normal")
        self.font_family_var = tk.StringVar(value="Arial")
        self.font_size_var = tk.StringVar(value="12")
        self.start_arrow_var = tk.StringVar(value="None")
        self.end_arrow_var = tk.StringVar(value="Closed Arrow")
        self.precision_var = tk.StringVar(value="0.01")
        self.paper_var = tk.StringVar(value="A4")
        self.scale_label_var = tk.StringVar(value="Not calibrated")
        self.unit_var = tk.StringVar(value="mm")
        self.layer_var = tk.StringVar(value="0")
        self.command_var = tk.StringVar()
        self.snap_indicator_var = tk.StringVar(value="OSNAP")
        self.snap_vars = {name: tk.BooleanVar(value=name in {"Endpoint", "Midpoint", "Intersection", "Extension", "Center", "Nearest"}) for name in SNAP_MODES}
        self.unit_var.trace_add("write", self._unit_changed)
        self.next_document_id = 2
        self.active_document_id = "doc_1"
        self.documents = [{
            "id": "doc_1",
            "title": "New Document*",
            "project_file": self.project_file,
            "current_file": self.current_file,
            "current_pdf": self.current_pdf,
            "pages": self.pages,
            "current_page": self.current_page,
            "scale_units_per_px": self.scale_units_per_px,
            "scale_unit": self.scale_unit,
            "scale_label": self.scale_label_var.get(),
            "unit": self.unit_var.get(),
            "layers": self.layers,
            "current_layer": self.current_layer,
            "bookmarks": [],
            "undo_stack": self.undo_stack,
            "redo_stack": self.redo_stack,
            "rotation": self.rotation,
        }]
        self.doc_buttons = {}

        self._build_ui()
        self._bind_shortcuts()
        self._set_tool("hand")
        self._set_status("Ready")

    def _apply_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=self.colors["sidebar"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=self.colors["sidebar"],
            foreground=self.colors["muted"],
            padding=(12, 7),
            borderwidth=0,
            font=self.font_body,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.colors["card"])],
            foreground=[("selected", self.colors["text"])],
        )
        style.configure(
            "Treeview",
            background=self.colors["card"],
            fieldbackground=self.colors["card"],
            foreground=self.colors["text"],
            borderwidth=0,
            rowheight=25,
            font=self.font_body,
        )
        style.configure(
            "Treeview.Heading",
            background=self.colors["sidebar"],
            foreground=self.colors["muted"],
            relief="flat",
            font=self.font_small,
        )

    def _set_app_icon(self):
        icon = tk.PhotoImage(width=32, height=32)
        icon.put("#f5f5f7", to=(0, 0, 32, 32))
        icon.put("#1d1d1f", to=(6, 7, 24, 25))
        icon.put("#4f5d75", to=(8, 9, 22, 23))
        icon.put("#8ecae6", to=(10, 11, 20, 15))
        icon.put("#ffb703", to=(10, 17, 20, 22))
        icon.put("#1d1d1f", to=(13, 5, 19, 8))
        icon.put("#0071e3", to=(22, 12, 25, 24))
        icon.put("#0071e3", to=(24, 21, 28, 24))
        icon.put("#ff3b30", to=(27, 24, 30, 29))
        self.app_icon = icon
        self.iconphoto(False, self.app_icon)

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        self._build_header()
        self._build_tabs()
        self._build_ribbon()
        self._build_doc_strip()
        self._build_workspace()
        self._build_statusbar()

    def _build_header(self):
        self.quickbar = tk.Frame(self, bg=self.colors["chrome"], height=58)
        self.quickbar.grid(row=0, column=0, sticky="ew")
        self.quickbar.grid_propagate(False)

        brand = tk.Frame(self.quickbar, bg=self.colors["chrome"])
        brand.pack(side="left", padx=(18, 26), pady=7)
        tk.Label(brand, text=APP_TITLE, bg=self.colors["chrome"], fg=self.colors["text"], font=self.font_title).pack(anchor="w")
        tk.Label(
            brand,
            text="native review, markup, measure, and takeoff",
            bg=self.colors["chrome"],
            fg=self.colors["muted"],
            font=self.font_small,
        ).pack(anchor="w")

        actions = [
            ("New", self.new_project),
            ("Open", self.open_project),
            ("Open PDF", self.open_pdf),
            ("Save", self.save_project),
            ("Save As", self.save_project_as),
            ("Print", self.print_document),
            ("Undo", self.undo),
            ("Redo", self.redo),
            ("Zoom -", self.zoom_out),
            ("Zoom +", self.zoom_in),
            ("Rotate Left", lambda: self.rotate_page(-90)),
            ("Rotate Right", lambda: self.rotate_page(90)),
        ]
        for text, command in actions:
            self._quick_button(text, command)

        self.window_title = tk.Label(
            self.quickbar,
            text="New Document* - DieselPDF",
            bg=self.colors["chrome"],
            fg=self.colors["muted"],
            font=self.font_body,
        )
        self.window_title.pack(side="right", padx=18)

    def _quick_button(self, text, command):
        button = tk.Button(
            self.quickbar,
            text=self._button_text(text),
            width=7,
            height=2,
            command=command,
            bg=self.colors["card"],
            fg=self.colors["text"],
            activebackground=self.colors["active"],
            activeforeground=self.colors["text"],
            relief="flat",
            bd=0,
            padx=8,
            pady=5,
            font=self.font_small,
            justify="center",
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )
        button.pack(side="left", padx=3, pady=6)
        button.bind("<Enter>", lambda _event, label=text: self._set_status(label))

    def _icon_for(self, text):
        if text in ICON:
            return ICON[text]
        if "90" in text:
            return "R90"
        return text[:3].upper()

    def _button_text(self, text):
        return f"{self._icon_for(text)}\n{text}"

    def _build_tabs(self):
        self.tabs = tk.Frame(self, bg=self.colors["chrome"], height=38)
        self.tabs.grid(row=1, column=0, sticky="ew")
        self.tabs.grid_propagate(False)
        tk.Frame(self.tabs, bg=self.colors["chrome"], width=14).pack(side="left")
        for name in ["Home", "Markup", "Measure", "Properties", "Pages", "Studio", "OCR", "Help"]:
            btn = tk.Button(
                self.tabs,
                text=name,
                bd=0,
                padx=14,
                pady=6,
                bg=self.colors["card"] if name == "Home" else self.colors["chrome"],
                fg=self.colors["blue"] if name == "Home" else self.colors["muted"],
                activebackground=self.colors["active"],
                activeforeground=self.colors["blue"],
                font=self.font_body,
                command=lambda n=name: self._select_tab(n),
            )
            btn.pack(side="left", padx=2, pady=4)

    def _select_tab(self, name):
        for child in self.tabs.winfo_children():
            if isinstance(child, tk.Button):
                child.configure(bg=self.colors["chrome"], fg=self.colors["muted"])
                if child.cget("text") == name:
                    child.configure(bg=self.colors["card"], fg=self.colors["blue"])
        self._set_status(f"{name} tab selected")

    def _bind_shortcuts(self):
        self.bind("<KeyPress-l>", lambda _event: self._shortcut_tool("line"))
        self.bind("<KeyPress-L>", lambda _event: self._shortcut_tool("line"))
        self.bind("<KeyPress-h>", lambda _event: self._shortcut_tool("hand"))
        self.bind("<KeyPress-s>", lambda _event: self._shortcut_tool("select"))
        self.bind("<Control-z>", lambda _event: self.undo())
        self.bind("<Control-y>", lambda _event: self.redo())
        self.bind("<Escape>", lambda _event: self._escape_current())

    def _shortcut_tool(self, tool):
        if self.focus_get() == getattr(self, "command_entry", None):
            return
        self._set_tool(tool)

    def _escape_current(self):
        self._clear_pending()
        self.drag = None
        self.hide_crosshair()
        self._set_tool("hand")

    def _build_ribbon(self):
        self.ribbon = tk.Frame(self, bg=self.colors["ribbon"], height=148, bd=0, highlightthickness=1, highlightbackground=self.colors["border"])
        self.ribbon.grid(row=2, column=0, sticky="ew")
        self.ribbon.grid_propagate(False)

        home = self._group("Home")
        self._cmd_button(home, "Open PDF", self.open_pdf)

        review = self._group("Review")
        self._tool_button(review, "Hand", "hand")
        self._tool_button(review, "Select", "select")
        self._tool_button(review, "Select Text", "select_text", wide=True)

        draw = self._group("Draw")
        for label, tool in [
            ("Line", "line"),
            ("Circle", "circle"),
            ("Cloud", "cloud"),
            ("Arrow", "arrow"),
            ("Polyline", "polyline"),
            ("Rectangle", "rectangle"),
            ("Polygon", "polygon"),
            ("Pencil", "pencil"),
            ("Eraser", "eraser"),
        ]:
            self._tool_button(draw, label, tool)

        measure = self._group("Measure")
        for label, tool in [("Calibrate", "calibrate"), ("Distance", "distance"), ("Perimeter", "perimeter"), ("Area", "area")]:
            self._tool_button(measure, label, tool)
        self._cmd_button(measure, "Set Scale", self.manual_scale)

        text = self._group("Text")
        self._tool_button(text, "Text Box", "text_box")
        self._tool_button(text, "Callout", "callout")

        organize = self._group("Organize")
        self._cmd_button(organize, "Group", self.group_selected)
        self._cmd_button(organize, "Ungroup", self.ungroup_selected)
        self._cmd_button(organize, "Flatten", self.flatten_layer)
        self._cmd_button(organize, "Library", self.save_group_library)

        cad = self._group("CAD")
        self._cmd_button(cad, "Move", self.move_selected)
        self._cmd_button(cad, "Copy", self.copy_selected)
        self._cmd_button(cad, "Offset", self.offset_selected)
        self._cmd_button(cad, "CAD to Text", self.cad_to_text)
        self._cmd_button(cad, "Text to CAD", self.text_to_cad_pdf)
        self._cmd_button(cad, "PDF to CAD", self.pdf_to_cad)
        self._cmd_button(cad, "Export DXF", self.export_current_page_dxf)
        self._cmd_button(cad, "Delete", self.delete_selected)

        pages = self._group("Pages")
        self._cmd_button(pages, "Insert", self.insert_page)
        self._cmd_button(pages, "Delete", self.delete_page)
        self._cmd_button(pages, "Extract", self.extract_page)
        self._cmd_button(pages, "Prev", self.previous_page)
        self._cmd_button(pages, "Next", self.next_page)

    def _group(self, label):
        group = tk.Frame(
            self.ribbon,
            bg=self.colors["card"],
            bd=0,
            padx=7,
            pady=7,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )
        group.pack(side="left", fill="y", padx=5, pady=10)
        body = tk.Frame(group, bg=self.colors["card"])
        body.pack(side="top", fill="both", expand=True)
        tk.Label(group, text=label.upper(), bg=self.colors["card"], fg=self.colors["muted"], font=self.font_small).pack(side="bottom", pady=(4, 0))
        return body

    def _tool_button(self, parent, text, tool, wide=False):
        btn = tk.Button(
            parent,
            text=self._button_text(text),
            width=9 if wide else 8,
            height=3,
            command=lambda: self._set_tool(tool),
            bg=self.colors["chrome"],
            fg=self.colors["text"],
            activebackground=self.colors["active"],
            activeforeground=self.colors["blue"],
            relief="flat",
            bd=0,
            font=self.font_small,
            justify="center",
            highlightthickness=1,
            highlightbackground="#ececf0",
        )
        btn.pack(side="left", padx=2, pady=2)
        btn.bind("<Enter>", lambda _event, label=text: self._set_status(label))
        self.tool_buttons[tool] = btn
        return btn

    def _cmd_button(self, parent, text, command):
        button = tk.Button(
            parent,
            text=self._button_text(text),
            width=8,
            height=3,
            command=command,
            bg=self.colors["chrome"],
            fg=self.colors["text"],
            activebackground=self.colors["active"],
            activeforeground=self.colors["blue"],
            relief="flat",
            bd=0,
            font=self.font_small,
            justify="center",
            highlightthickness=1,
            highlightbackground="#ececf0",
        )
        button.pack(side="left", padx=2, pady=2)
        button.bind("<Enter>", lambda _event, label=text: self._set_status(label))

    def _build_doc_strip(self):
        self.doc_tabs = tk.Frame(self, bg=self.colors["chrome"], height=42)
        self.doc_tabs.grid(row=3, column=0, sticky="ew")
        self.doc_tabs.grid_propagate(False)
        self.doc_tab_bar = tk.Frame(self.doc_tabs, bg=self.colors["chrome"])
        self.doc_tab_bar.pack(side="left", padx=(14, 0), pady=7, fill="y")
        self._render_document_tabs()
        tk.Button(
            self.doc_tabs,
            text=ICON["New"],
            width=3,
            command=self.create_document_tab,
            bg=self.colors["card"],
            fg=self.colors["blue"],
            activebackground=self.colors["active"],
            relief="flat",
            bd=0,
            font=self.font_icon_small,
        ).pack(side="left", padx=(6, 0), pady=7, fill="y")
        tk.Frame(self.doc_tabs, bg=self.colors["chrome"]).pack(side="left", fill="both", expand=True)

    def _render_document_tabs(self):
        if not hasattr(self, "doc_tab_bar"):
            return
        for child in self.doc_tab_bar.winfo_children():
            child.destroy()
        self.doc_buttons = {}
        for doc in self.documents:
            active = doc["id"] == self.active_document_id
            button = tk.Button(
                self.doc_tab_bar,
                text=doc["title"],
                command=lambda doc_id=doc["id"]: self.switch_document(doc_id),
                bg=self.colors["card"] if active else self.colors["chrome"],
                fg=self.colors["text"] if active else self.colors["muted"],
                activebackground=self.colors["active"],
                activeforeground=self.colors["blue"],
                relief="flat",
                bd=0,
                padx=16,
                pady=8,
                font=self.font_body,
                highlightthickness=1,
                highlightbackground=self.colors["border"] if active else self.colors["chrome"],
            )
            button.pack(side="left", fill="y", padx=(0, 3))
            button.bind("<Enter>", lambda _event, title=doc["title"]: self._set_status(title))
            self.doc_buttons[doc["id"]] = button

    def _set_current_document_title(self, title):
        doc = self._active_document()
        if doc:
            doc["title"] = title
        self.window_title.configure(text=f"{title} - DieselPDF")
        self._render_document_tabs()

    def _active_document(self):
        return next((doc for doc in self.documents if doc["id"] == self.active_document_id), None)

    def _bookmark_values(self):
        if hasattr(self, "bookmark_list"):
            return list(self.bookmark_list.get(0, "end"))
        doc = self._active_document()
        return doc.get("bookmarks", []) if doc else []

    def _sync_active_document(self):
        doc = self._active_document()
        if not doc:
            return
        doc.update({
            "project_file": self.project_file,
            "current_file": self.current_file,
            "current_pdf": self.current_pdf,
            "pages": self.pages,
            "current_page": self.current_page,
            "scale_units_per_px": self.scale_units_per_px,
            "scale_unit": self.scale_unit,
            "scale_label": self.scale_label_var.get(),
            "unit": self.unit_var.get(),
            "layers": self.layers,
            "current_layer": self.current_layer,
            "bookmarks": self._bookmark_values(),
            "undo_stack": self.undo_stack,
            "redo_stack": self.redo_stack,
            "rotation": self.rotation,
        })

    def _hide_document_entries(self, doc):
        for page in doc.get("pages", []):
            for entry in page.get("entries", []):
                for item in entry.get("items", []):
                    self.canvas.itemconfigure(item, state="hidden")

    def _new_document_record(self, title=None):
        doc_id = f"doc_{self.next_document_id}"
        self.next_document_id += 1
        return {
            "id": doc_id,
            "title": title or f"New Document {self.next_document_id - 1}*",
            "project_file": None,
            "current_file": None,
            "current_pdf": None,
            "pages": [{"paper": "A4", "entries": []}],
            "current_page": 0,
            "scale_units_per_px": None,
            "scale_unit": "mm",
            "scale_label": "Not calibrated",
            "unit": "mm",
            "layers": [{"name": "0", "visible": True, "locked": False}],
            "current_layer": "0",
            "bookmarks": [],
            "undo_stack": [],
            "redo_stack": [],
            "rotation": 0,
        }

    def create_document_tab(self):
        self._sync_active_document()
        current = self._active_document()
        if current:
            self._hide_document_entries(current)
        doc = self._new_document_record()
        self.documents.append(doc)
        self.active_document_id = doc["id"]
        self._load_document(doc)
        self._set_status(f"Created {doc['title']} tab")

    def switch_document(self, doc_id):
        if doc_id == self.active_document_id:
            return
        self._sync_active_document()
        current = self._active_document()
        if current:
            self._hide_document_entries(current)
        target = next((doc for doc in self.documents if doc["id"] == doc_id), None)
        if not target:
            return
        self.active_document_id = doc_id
        self._load_document(target)
        self._set_status(f"Switched to {target['title']}")

    def _load_document(self, doc):
        self.project_file = doc.get("project_file")
        self.current_file = doc.get("current_file")
        self.current_pdf = doc.get("current_pdf") or (self.current_file if self._is_pdf_path(self.current_file) else None)
        self.pages = doc.get("pages", [{"paper": "A4", "entries": []}])
        self.current_page = min(doc.get("current_page", 0), max(0, len(self.pages) - 1))
        self.scale_units_per_px = doc.get("scale_units_per_px")
        self.scale_unit = doc.get("scale_unit", "mm")
        self.scale_label_var.set(doc.get("scale_label", "Not calibrated"))
        self._updating_unit = True
        try:
            self.unit_var.set(doc.get("unit", self.scale_unit))
        finally:
            self._updating_unit = False
        self.layers = doc.get("layers", [{"name": "0", "visible": True, "locked": False}])
        self.current_layer = doc.get("current_layer", self.layers[0]["name"] if self.layers else "0")
        self.layer_var.set(self.current_layer)
        self.undo_stack = doc.get("undo_stack", [])
        self.redo_stack = doc.get("redo_stack", [])
        self.rotation = doc.get("rotation", 0)
        self.bookmark_list.delete(0, "end")
        for bookmark in doc.get("bookmarks", []):
            self.bookmark_list.insert("end", bookmark)
        self.window_title.configure(text=f"{doc['title']} - DieselPDF")
        self._refresh_layer_list()
        self._refresh_page_list()
        self._show_current_page()
        self._render_document_tabs()

    def _build_workspace(self):
        self.main = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=8, bg=self.colors["border"], bd=0)
        self.main.grid(row=4, column=0, sticky="nsew")
        self._build_left_panel()
        self._build_canvas()
        self._build_properties()

    def _build_left_panel(self):
        sidebar = tk.Frame(self.main, bg=self.colors["sidebar"], width=270)
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="Workspace", bg=self.colors["sidebar"], fg=self.colors["text"], font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", padx=16, pady=(16, 0))
        tk.Label(sidebar, text="bookmarks, markups, pages, review", bg=self.colors["sidebar"], fg=self.colors["muted"], font=self.font_small, anchor="w").pack(fill="x", padx=16, pady=(0, 12))

        self.notebook = ttk.Notebook(sidebar)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.bookmark_frame = tk.Frame(self.notebook, bg=self.colors["card"])
        self.markup_frame = tk.Frame(self.notebook, bg=self.colors["card"])
        self.page_frame = tk.Frame(self.notebook, bg=self.colors["card"])
        self.layer_frame = tk.Frame(self.notebook, bg=self.colors["card"])
        self.library_frame = tk.Frame(self.notebook, bg=self.colors["card"])
        self.notebook.add(self.bookmark_frame, text="Bookmarks")
        self.notebook.add(self.markup_frame, text="Markups")
        self.notebook.add(self.page_frame, text="Pages")
        self.notebook.add(self.layer_frame, text="Layers")
        self.notebook.add(self.library_frame, text="Library")

        self.bookmark_list = self._listbox(self.bookmark_frame)
        self.bookmark_list.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Button(self.bookmark_frame, text="Add Bookmark", command=self.add_bookmark, **self._button_style()).pack(fill="x", padx=10, pady=(0, 10))

        columns = ("type", "detail")
        self.markup_list = ttk.Treeview(self.markup_frame, columns=columns, show="headings", height=12)
        self.markup_list.heading("type", text="Type")
        self.markup_list.heading("detail", text="Detail")
        self.markup_list.column("type", width=80)
        self.markup_list.column("detail", width=145)
        self.markup_list.pack(fill="both", expand=True, padx=10, pady=10)

        self.page_list = self._listbox(self.page_frame)
        self.page_list.pack(fill="both", expand=True, padx=10, pady=10)
        self.page_list.bind("<<ListboxSelect>>", self._page_selected)

        self.layer_list = self._listbox(self.layer_frame)
        self.layer_list.pack(fill="both", expand=True, padx=10, pady=10)
        self.layer_list.bind("<<ListboxSelect>>", self._layer_selected)
        layer_buttons = tk.Frame(self.layer_frame, bg=self.colors["card"])
        layer_buttons.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(layer_buttons, text="+", command=self.add_layer, **self._button_style()).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(layer_buttons, text="V", command=self.toggle_layer_visibility, **self._button_style()).pack(side="left", fill="x", expand=True)

        self.library_list = self._listbox(self.library_frame)
        self.library_list.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Button(self.library_frame, text="Refresh Library", command=self.refresh_library, **self._button_style()).pack(fill="x", padx=10, pady=(0, 10))

        self.main.add(sidebar, width=270)
        self._refresh_layer_list()

    def _button_style(self):
        return {
            "bg": self.colors["blue"],
            "fg": "white",
            "activebackground": "#005bb5",
            "activeforeground": "white",
            "relief": "flat",
            "bd": 0,
            "pady": 7,
            "font": self.font_body,
        }

    def _listbox(self, parent):
        return tk.Listbox(
            parent,
            bg=self.colors["card"],
            fg=self.colors["text"],
            selectbackground=self.colors["active"],
            selectforeground=self.colors["blue"],
            bd=0,
            highlightthickness=0,
            font=self.font_body,
        )

    def _build_canvas(self):
        area = tk.Frame(self.main, bg=self.colors["work"])
        area.rowconfigure(0, weight=1)
        area.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(area, bg=self.colors["work"], highlightthickness=0, cursor="hand2")
        self.vbar = ttk.Scrollbar(area, orient=tk.VERTICAL, command=self.canvas.yview)
        self.hbar = ttk.Scrollbar(area, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vbar.set, xscrollcommand=self.hbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="ew")

        self.shadow1 = self.canvas.create_rectangle(68, 54, 68 + self.page_w, 54 + self.page_h, fill="#d9dce3", outline="")
        self.shadow2 = self.canvas.create_rectangle(64, 50, 64 + self.page_w, 50 + self.page_h, fill="#eef0f5", outline="")
        self.page_rect = self.canvas.create_rectangle(PAGE_ORIGIN[0], PAGE_ORIGIN[1], PAGE_ORIGIN[0] + self.page_w, PAGE_ORIGIN[1] + self.page_h, fill=self.colors["page"], outline="#e1e1e6")
        self.page_title = self.canvas.create_text(90, 82, text="DieselPDF", anchor="nw", fill=self.colors["text"], font=("Segoe UI", 24, "bold"))
        self.page_subtitle = self.canvas.create_text(92, 120, text="Default mode is Hand. Select a tool, then draw on the page.", anchor="nw", fill=self.colors["muted"], font=("Segoe UI", 12))
        self.page_divider = self.canvas.create_line(90, 160, PAGE_ORIGIN[0] + self.page_w - 80, 160, fill="#eeeeef")

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.finish_pending_shape)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_motion)

        self.main.add(area, stretch="always")
        self._refresh_page_list()
        self._update_page_surface()

    def _build_properties(self):
        panel = tk.Frame(self.main, bg=self.colors["sidebar"], width=330)
        panel.pack_propagate(False)
        tk.Label(panel, text="Tool Properties", bg=self.colors["sidebar"], fg=self.colors["text"], font=("Segoe UI", 14, "bold"), anchor="w").pack(fill="x", padx=12, pady=(12, 6))
        self.properties = tk.Frame(panel, bg=self.colors["card"], highlightthickness=1, highlightbackground=self.colors["border"])
        self.properties.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._section("General", [("Keep Selected", "True"), ("Exclusive Mode", "False")])
        self._section("Subject", [("Subject Kind", "Default"), ("Subject", "Dimension Line")])
        self._style_section()
        self._section("Line Endings", [("Start", self.start_arrow_var), ("End", self.end_arrow_var), ("Start Scale", "Auto"), ("End Scale", "Auto")])
        self._section("Leader", [("Leader Length", "5.3 mm"), ("Leader Extension", "1.8 mm"), ("Leader Offset", "0 mm")])
        self._section("Caption", [("Show Caption", "Yes"), ("Inline Caption", "Yes")])
        self._measure_section()
        self._section("Layer", [("Current Layer", self.layer_var)])

        self.main.add(panel, minsize=310, width=330, stretch="never")

    def _section(self, title, rows):
        tk.Label(self.properties, text=f"v {title}", bg="#f0f0f2", fg=self.colors["text"], anchor="w", font=self.font_heading).pack(fill="x", pady=(0, 1))
        for label, value in rows:
            self._property_row(label, value)

    def _style_section(self):
        tk.Label(self.properties, text="v Style", bg="#f0f0f2", fg=self.colors["text"], anchor="w", font=self.font_heading).pack(fill="x", pady=(0, 1))
        self._color_row("Fill Color", self.fill_color_var, self.choose_fill_color)
        self._color_row("Stroke Color", self.line_color_var, self.choose_line_color)
        self._option_row("Border", self.line_type_var, ["Solid", "Dashed", "Dotted"])
        self._entry_row("Width", self.width_var)
        self._option_row("Opacity", self.opacity_var, ["100%", "75%", "50%", "25%"])
        self._option_row("Blend Mode", self.blend_var, ["Normal", "Multiply", "Screen"])
        self._option_row("Font", self.font_family_var, ["Arial", "Calibri"])
        self._entry_row("Font Size", self.font_size_var)
        tk.Button(self.properties, text="Apply to Selected", command=self.apply_style_to_selected, **self._flat_button()).pack(fill="x", padx=8, pady=5)

    def _measure_section(self):
        tk.Label(self.properties, text="v Measure", bg="#f0f0f2", fg=self.colors["text"], anchor="w", font=self.font_heading).pack(fill="x", pady=(0, 1))
        self._property_row("Label", "<Not Set>")
        self._property_row("Scale", self.scale_label_var)
        self._option_row("Unit", self.unit_var, MEASURE_UNITS)
        self._option_row("Paper Size", self.paper_var, PAPER_NAMES)
        self._entry_row("Precision", self.precision_var)
        tk.Button(self.properties, text="Manual Scale", command=self.manual_scale, **self._flat_button()).pack(fill="x", padx=8, pady=5)

    def _flat_button(self):
        return {
            "bg": self.colors["chrome"],
            "fg": self.colors["text"],
            "activebackground": self.colors["active"],
            "relief": "flat",
            "bd": 0,
            "font": self.font_body,
        }

    def _property_row(self, label, value):
        row = tk.Frame(self.properties, bg=self.colors["card"], height=25)
        row.pack(fill="x")
        tk.Label(row, text=label, bg=self.colors["card"], fg=self.colors["muted"], width=15, anchor="e", font=self.font_body).pack(side="left", padx=(2, 6))
        if isinstance(value, tk.StringVar):
            tk.Label(row, textvariable=value, bg=self.colors["card"], fg=self.colors["text"], anchor="w", font=self.font_body).pack(side="left", fill="x", expand=True)
        else:
            tk.Label(row, text=value, bg=self.colors["card"], fg=self.colors["text"], anchor="w", font=self.font_body).pack(side="left", fill="x", expand=True)

    def _color_row(self, label, var, command):
        row = tk.Frame(self.properties, bg=self.colors["card"], height=25)
        row.pack(fill="x")
        tk.Label(row, text=label, bg=self.colors["card"], fg=self.colors["muted"], width=15, anchor="e", font=self.font_body).pack(side="left", padx=(2, 6))
        tk.Button(row, textvariable=var, command=command, bg=self.colors["card"], relief="flat", bd=0, font=self.font_body).pack(side="left", fill="x", expand=True)

    def _option_row(self, label, var, values):
        row = tk.Frame(self.properties, bg=self.colors["card"], height=25)
        row.pack(fill="x")
        tk.Label(row, text=label, bg=self.colors["card"], fg=self.colors["muted"], width=15, anchor="e", font=self.font_body).pack(side="left", padx=(2, 6))
        menu = ttk.Combobox(row, textvariable=var, values=values, width=15, state="readonly")
        menu.pack(side="left", fill="x", expand=True, padx=(0, 5))
        if var is self.paper_var:
            menu.bind("<<ComboboxSelected>>", lambda _event: self.apply_current_paper_size())
        elif var is self.unit_var:
            menu.bind("<<ComboboxSelected>>", lambda _event: self._set_measure_unit(self.unit_var.get()))

    def _entry_row(self, label, var):
        row = tk.Frame(self.properties, bg=self.colors["card"], height=25)
        row.pack(fill="x")
        tk.Label(row, text=label, bg=self.colors["card"], fg=self.colors["muted"], width=15, anchor="e", font=self.font_body).pack(side="left", padx=(2, 6))
        tk.Entry(row, textvariable=var, bd=0, highlightthickness=1, highlightbackground=self.colors["border"], font=self.font_body).pack(side="left", fill="x", expand=True, padx=(0, 5))

    def _build_statusbar(self):
        self.status = tk.Frame(self, bg=self.colors["status"], height=30, bd=0, highlightthickness=1, highlightbackground=self.colors["border"])
        self.status.grid(row=5, column=0, sticky="ew")
        self.status.grid_propagate(False)
        self.mode_label = tk.Label(self.status, text="Hand Tool", bg=self.colors["status"], fg=self.colors["text"], width=22, anchor="w", font=self.font_body)
        self.mode_label.pack(side="left", padx=12)
        self.page_label = tk.Label(self.status, text="", bg=self.colors["status"], fg=self.colors["muted"], width=20, anchor="w", font=self.font_body)
        self.page_label.pack(side="left")
        self.zoom_label = tk.Label(self.status, text="100%", bg=self.colors["status"], fg=self.colors["muted"], width=8, anchor="w", font=self.font_body)
        self.zoom_label.pack(side="left")
        self.osnap_button = tk.Button(self.status, textvariable=self.snap_indicator_var, command=self.show_osnap_menu, bg=self.colors["card"], fg=self.colors["blue"], relief="flat", bd=0, font=self.font_body)
        self.osnap_button.pack(side="left", padx=(0, 8))
        self.ortho_var = tk.BooleanVar(value=False)
        self.otrack_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.status, text="OTRACK", variable=self.otrack_var, bg=self.colors["status"], fg=self.colors["muted"], font=self.font_small, bd=0).pack(side="left")
        tk.Checkbutton(self.status, text="ORTHO", variable=self.ortho_var, bg=self.colors["status"], fg=self.colors["muted"], font=self.font_small, bd=0).pack(side="left")
        tk.Label(self.status, text="Command", bg=self.colors["status"], fg=self.colors["muted"], font=self.font_small).pack(side="left", padx=(8, 3))
        self.command_entry = tk.Entry(self.status, textvariable=self.command_var, width=38, bd=0, highlightthickness=1, highlightbackground=self.colors["border"], font=self.font_body)
        self.command_entry.pack(side="left", padx=(0, 8))
        self.command_entry.bind("<Return>", self.run_command_from_entry)
        self.status_label = tk.Label(self.status, text="", bg=self.colors["status"], fg=self.colors["muted"], anchor="w", font=self.font_body)
        self.status_label.pack(side="left", fill="x", expand=True)
        self._update_page_label()

    def show_osnap_menu(self):
        menu = tk.Menu(self, tearoff=False, bg="#4d596c", fg="white", activebackground="#667287", activeforeground="white")
        for mode in SNAP_MODES:
            menu.add_checkbutton(label=mode, variable=self.snap_vars[mode], command=self.update_snap_indicator)
        menu.add_separator()
        menu.add_command(label="Settings", command=lambda: self._set_status("OSNAP settings updated from status menu"))
        menu.tk_popup(self.osnap_button.winfo_rootx(), self.osnap_button.winfo_rooty() - 360)

    def update_snap_indicator(self):
        active = [name for name, var in self.snap_vars.items() if var.get()]
        self.snap_indicator_var.set("OSNAP" if active else "OSNAP OFF")

    def show_crosshair(self, x, y, snap_label=""):
        self.hide_crosshair()
        size = 5
        self.cursor_items = [
            self.canvas.create_line(x - 18, y, x - size, y, fill="#111827", width=1),
            self.canvas.create_line(x + size, y, x + 18, y, fill="#111827", width=1),
            self.canvas.create_line(x, y - 18, x, y - size, fill="#111827", width=1),
            self.canvas.create_line(x, y + size, x, y + 18, fill="#111827", width=1),
            self.canvas.create_rectangle(x - size, y - size, x + size, y + size, outline=self.colors["blue"], width=2),
        ]
        if snap_label:
            self.cursor_items.append(self.canvas.create_text(x + 12, y - 14, text=snap_label, fill=self.colors["blue"], anchor="nw", font=self.font_small))

    def hide_crosshair(self):
        for item in self.cursor_items:
            self.canvas.delete(item)
        self.cursor_items = []

    def snap_point(self, x, y):
        candidates = []
        active = {name for name, var in self.snap_vars.items() if var.get()}
        if not active:
            return x, y, ""

        for entry in self._current_entries():
            if not self._layer_visible(entry.get("layer", "0")):
                continue
            for item in entry["items"]:
                if self.canvas.itemcget(item, "state") == "hidden":
                    continue
                item_type = self.canvas.type(item)
                coords = self.canvas.coords(item)
                if item_type == "line" and len(coords) >= 4:
                    pts = list(zip(coords[0::2], coords[1::2]))
                    if "Endpoint" in active:
                        candidates.extend((px, py, "Endpoint") for px, py in (pts[0], pts[-1]))
                    if "Midpoint" in active:
                        candidates.append(((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2, "Midpoint"))
                    if "Nearest" in active:
                        candidates.append((*self._nearest_on_segment(x, y, pts[0], pts[-1]), "Nearest"))
                    if "Extension" in active:
                        candidates.append((*self._nearest_on_infinite_line(x, y, pts[0], pts[-1]), "Extension"))
                elif item_type in {"rectangle", "oval", "polygon"}:
                    bbox = self.canvas.bbox(item)
                    if not bbox:
                        continue
                    x0, y0, x1, y1 = bbox
                    center = ((x0 + x1) / 2, (y0 + y1) / 2)
                    if "Center" in active or "Geometric Center" in active:
                        candidates.append((center[0], center[1], "Center"))
                    if "Quadrant" in active:
                        candidates.extend([(center[0], y0, "Quadrant"), (x1, center[1], "Quadrant"), (center[0], y1, "Quadrant"), (x0, center[1], "Quadrant")])
                    if "Endpoint" in active or "Node" in active:
                        candidates.extend([(x0, y0, "Endpoint"), (x1, y0, "Endpoint"), (x1, y1, "Endpoint"), (x0, y1, "Endpoint")])
                elif item_type == "text":
                    bbox = self.canvas.bbox(item)
                    if bbox and "Insertion" in active:
                        candidates.append((bbox[0], bbox[1], "Insertion"))

        if "Intersection" in active or "Apparent Intersection" in active:
            candidates.extend(self._line_intersections(active))

        if not candidates:
            return x, y, ""
        best = min(candidates, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
        if (best[0] - x) ** 2 + (best[1] - y) ** 2 <= 18 ** 2:
            return best
        return x, y, ""

    def _nearest_on_segment(self, x, y, a, b):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        length2 = dx * dx + dy * dy
        if length2 == 0:
            return ax, ay
        t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / length2))
        return ax + t * dx, ay + t * dy

    def _nearest_on_infinite_line(self, x, y, a, b):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        length2 = dx * dx + dy * dy
        if length2 == 0:
            return ax, ay
        t = ((x - ax) * dx + (y - ay) * dy) / length2
        return ax + t * dx, ay + t * dy

    def _line_intersections(self, active):
        lines = []
        for entry in self._current_entries():
            for item in entry["items"]:
                if self.canvas.type(item) == "line":
                    coords = self.canvas.coords(item)
                    if len(coords) >= 4:
                        lines.append((coords[0], coords[1], coords[-2], coords[-1]))
        intersections = []
        for i, first in enumerate(lines):
            for second in lines[i + 1:]:
                point = self._segment_intersection(first, second)
                if point:
                    label = "Intersection" if "Intersection" in active else "Apparent Intersection"
                    intersections.append((point[0], point[1], label))
        return intersections

    def _segment_intersection(self, a, b):
        x1, y1, x2, y2 = a
        x3, y3, x4, y4 = b
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-9:
            return None
        px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom
        return px, py

    def _style(self):
        width = self._safe_float(self.width_var.get(), 2)
        fill = self.fill_color_var.get()
        return {
            "line_color": self.line_color_var.get(),
            "fill_color": "" if fill == "None" else fill,
            "width": max(1, width),
            "line_type": self.line_type_var.get(),
            "font_family": self.font_family_var.get(),
            "font_size": int(self._safe_float(self.font_size_var.get(), 12)),
        }

    def _dash(self):
        line_type = self.line_type_var.get()
        if line_type == "Dashed":
            return (8, 5)
        if line_type == "Dotted":
            return (2, 4)
        return None

    def _safe_float(self, value, fallback):
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def choose_line_color(self):
        color = colorchooser.askcolor(color=self.line_color_var.get(), title="Line Color")[1]
        if color:
            self.line_color_var.set(color)
            self.apply_style_to_selected()

    def choose_fill_color(self):
        color = colorchooser.askcolor(title="Fill Color")[1]
        if color:
            self.fill_color_var.set(color)
            self.apply_style_to_selected()

    def _set_tool(self, tool):
        self.current_tool = tool
        self._clear_pending()
        if tool in {"calibrate", "distance", "perimeter", "area"}:
            self._ensure_measure_snaps()
        for name, button in self.tool_buttons.items():
            if name == tool:
                button.configure(bg=self.colors["active"], fg=self.colors["blue"], highlightbackground="#b7d4ff")
            else:
                button.configure(bg=self.colors["chrome"], fg=self.colors["text"], highlightbackground="#ececf0")
        names = {
            "hand": "Hand Tool",
            "select": "Select Linework",
            "select_text": "Select Text",
            "line": "Straight Line",
            "circle": "Circle",
            "cloud": "Cloud",
            "arrow": "Arrow",
            "polyline": "Polyline",
            "rectangle": "Rectangle",
            "polygon": "Polygon",
            "pencil": "Pencil",
            "eraser": "Eraser",
            "calibrate": "Calibrate",
            "distance": "Distance",
            "perimeter": "Perimeter",
            "area": "Area",
            "text_box": "Text Box",
            "callout": "Callout",
        }
        self.mode_label.configure(text=names.get(tool, tool))
        self.canvas.configure(cursor="hand2" if tool == "hand" else "crosshair")
        self._set_status(f"{names.get(tool, tool)} selected")

    def _ensure_measure_snaps(self):
        for name in ["Endpoint", "Midpoint", "Intersection", "Nearest"]:
            self.snap_vars[name].set(True)
        self.update_snap_indicator()

    def _set_status(self, text):
        self.status_label.configure(text=text)

    def run_command_from_entry(self, event=None):
        command = self.command_var.get().strip()
        self.command_var.set("")
        if command:
            self.run_ai_command(command)

    def run_ai_command(self, command):
        raw = command.strip()
        text = raw.lower()
        try:
            tokens = shlex.split(raw)
        except ValueError:
            tokens = raw.split()
        first = tokens[0].lower() if tokens else ""
        numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", text)]
        aliases = {
            "l": "line",
            "line": "line",
            "pl": "polyline",
            "pline": "polyline",
            "polyline": "polyline",
            "rec": "rectangle",
            "rect": "rectangle",
            "rectangle": "rectangle",
            "c": "circle",
            "circle": "circle",
            "a": "area",
            "di": "distance",
            "distance": "distance",
            "co": "copy",
            "copy": "copy",
            "m": "move",
            "move": "move",
            "o": "offset",
            "offset": "offset",
            "t": "text",
            "text": "text",
            "tb": "text_box",
            "textbox": "text_box",
            "callout": "callout",
            "help": "help",
            "?": "help",
        }

        if first in {"help", "?"}:
            self._command_help()
            return
        if first in {"osnap", "snap"}:
            self._run_snap_command(tokens)
            return
        if first in {"otrack", "ot"}:
            self._run_bool_command(self.otrack_var, "OTRACK", tokens)
            return
        if first in {"ortho", "or"}:
            self._run_bool_command(self.ortho_var, "ORTHO", tokens)
            return
        if first in {"cadtext", "cad2text", "dxftext", "cad-to-text"}:
            self.cad_to_text()
            return
        if first in {"textcad", "text2cad", "text-to-cad", "textpdf", "text2pdf"}:
            self.text_to_cad_pdf()
            return
        if first in {"pdfcad", "pdf2cad", "pdf-to-cad"}:
            self.pdf_to_cad()
            return
        if first in {"exportdxf", "savedxf", "dxf"}:
            self.export_current_page_dxf()
            return
        if first in {"exportpdf", "savepdf"}:
            self.export_current_page_pdf()
            return
        if first in {"openpdf", "pdfopen"}:
            self.open_pdf()
            return
        if first in {"save", "qsave"}:
            self.save_project()
            return

        tool = aliases.get(first)
        if "draw" in text and "line" in text:
            tool = "line"
        elif "draw" in text and "rectangle" in text:
            tool = "rectangle"
        elif "draw" in text and "circle" in text:
            tool = "circle"
        elif "calibrate" in text or "scale" in text:
            if len(numbers) >= 2:
                unit = self.unit_var.get() or "mm"
                self.scale_units_per_px = numbers[0] / numbers[1]
                self.scale_unit = unit
                self.scale_label_var.set(f"{numbers[1]:g} px = {numbers[0]:g} {unit}")
                self._set_status(f"AI scale set: {self.scale_label_var.get()}")
                return
            tool = "calibrate"
        elif "layer" in text:
            name = command.split(maxsplit=1)[1] if len(command.split()) > 1 else "Layer"
            self.create_layer_named(name)
            return

        if tool in {"copy", "move", "offset"}:
            {"copy": self.copy_selected, "move": self.move_selected, "offset": self.offset_selected}[tool]()
            return
        if tool == "circle" and len(numbers) >= 3:
            x, y, radius = numbers[:3]
            self.create_shape("circle", x - radius, y - radius, x + radius, y + radius)
            self._set_status("Command drew circle")
            return
        if tool in {"line", "arrow", "rectangle", "distance", "perimeter", "area"} and len(numbers) >= 4:
            self.create_shape(tool, numbers[0], numbers[1], numbers[2], numbers[3])
            self._set_status(f"Command drew {tool}")
            return
        if tool == "polyline" and len(numbers) >= 4:
            self._create_polyline_from_coords(numbers)
            return
        if tool == "polygon" and len(numbers) >= 6:
            self._create_polygon_from_coords(numbers)
            return
        if tool == "text" and len(numbers) >= 2:
            self._create_command_text(raw, numbers[0], numbers[1])
            return
        if tool:
            self._set_tool(tool)
            return
        self._set_status("Unknown command. Try HELP, L 100 100 300 100, OSNAP END MID, PDFCAD, CADTEXT, TEXTCAD")

    def _command_help(self):
        self._set_status("Commands: L/LINE, REC, CIRCLE x y r, PL/PLINE, TEXT x y words, OSNAP, ORTHO, OTRACK, CADTEXT, TEXTCAD, PDFCAD, EXPORTDXF")

    def _run_bool_command(self, variable, label, tokens):
        value = not variable.get()
        if len(tokens) >= 2:
            value = tokens[1].lower() in {"1", "on", "yes", "true", "enable", "enabled"}
        variable.set(value)
        self._set_status(f"{label} {'ON' if value else 'OFF'}")

    def _run_snap_command(self, tokens):
        if len(tokens) == 1:
            active = [name for name, var in self.snap_vars.items() if var.get()]
            self._set_status("OSNAP active: " + (", ".join(active) if active else "OFF"))
            return
        snap_aliases = {
            "end": "Endpoint",
            "endpoint": "Endpoint",
            "mid": "Midpoint",
            "midpoint": "Midpoint",
            "int": "Intersection",
            "intersection": "Intersection",
            "app": "Apparent Intersection",
            "apparent": "Apparent Intersection",
            "ext": "Extension",
            "extension": "Extension",
            "cen": "Center",
            "center": "Center",
            "geo": "Geometric Center",
            "geometric": "Geometric Center",
            "tan": "Tangent",
            "tangent": "Tangent",
            "qua": "Quadrant",
            "quadrant": "Quadrant",
            "per": "Perpendicular",
            "perpendicular": "Perpendicular",
            "nod": "Node",
            "node": "Node",
            "nea": "Nearest",
            "nearest": "Nearest",
            "par": "Parallel",
            "parallel": "Parallel",
            "ins": "Insertion",
            "insertion": "Insertion",
        }
        requested = [token.lower() for token in tokens[1:]]
        if requested[0] in {"off", "0", "false"}:
            for var in self.snap_vars.values():
                var.set(False)
            self.update_snap_indicator()
            self._set_status("OSNAP OFF")
            return
        if requested[0] in {"on", "1", "true"}:
            for name in ["Endpoint", "Midpoint", "Intersection", "Nearest"]:
                self.snap_vars[name].set(True)
            self.update_snap_indicator()
            self._set_status("OSNAP ON")
            return
        if requested[0] == "all":
            for var in self.snap_vars.values():
                var.set(True)
            self.update_snap_indicator()
            self._set_status("OSNAP ALL")
            return
        for var in self.snap_vars.values():
            var.set(False)
        enabled = []
        for token in requested:
            name = snap_aliases.get(token)
            if name and name in self.snap_vars:
                self.snap_vars[name].set(True)
                enabled.append(name)
        self.update_snap_indicator()
        self._set_status("OSNAP set: " + (", ".join(enabled) if enabled else "OFF"))

    def _create_polyline_from_coords(self, numbers):
        coords = numbers[:len(numbers) - (len(numbers) % 2)]
        if len(coords) < 4:
            self._set_status("Polyline needs at least two points")
            return
        style = self._style()
        item = self.canvas.create_line(coords, fill=style["line_color"], width=style["width"], dash=self._dash())
        self._record_entry("Polyline", "command polyline", [item])

    def _create_polygon_from_coords(self, numbers):
        coords = numbers[:len(numbers) - (len(numbers) % 2)]
        if len(coords) < 6:
            self._set_status("Polygon needs at least three points")
            return
        style = self._style()
        item = self.canvas.create_polygon(coords, outline=style["line_color"], fill=style["fill_color"], width=style["width"], dash=self._dash())
        self._record_entry("Polygon", "command polygon", [item])

    def _create_command_text(self, raw, x, y):
        parts = raw.split()
        words = []
        numbers_seen = 0
        for part in parts[1:]:
            if numbers_seen < 2:
                try:
                    float(part)
                    numbers_seen += 1
                    continue
                except ValueError:
                    pass
            words.append(part)
        text = " ".join(words).strip() or "Text"
        style = self._style()
        item = self.canvas.create_text(x, y, text=text, anchor="nw", fill=style["line_color"], font=(style["font_family"], style["font_size"]))
        self._record_entry("Text", text, [item])

    def _current_entries(self):
        return self.pages[self.current_page]["entries"]

    def _entry_by_tag(self, tag):
        if not tag.startswith("entry_"):
            return None
        entry_id = int(tag.split("_", 1)[1])
        for page in self.pages:
            for entry in page["entries"]:
                if entry["id"] == entry_id:
                    return entry
        return None

    def _canvas_xy(self, event):
        return self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

    def _page_bbox(self):
        return self.canvas.coords(self.page_rect)

    def _inside_page(self, x, y):
        x0, y0, x1, y1 = self._page_bbox()
        return x0 <= x <= x1 and y0 <= y <= y1

    def on_motion(self, event):
        if self.current_tool in {"line", "circle", "cloud", "arrow", "polyline", "rectangle", "polygon", "pencil", "eraser", "calibrate", "distance", "perimeter", "area"}:
            self.canvas.configure(cursor="crosshair")
            x, y = self._canvas_xy(event)
            sx, sy, label = self.snap_point(x, y)
            self.show_crosshair(sx, sy, label)
        else:
            self.hide_crosshair()

    def on_press(self, event):
        x, y = self._canvas_xy(event)
        if self.current_tool == "hand":
            self.drag = {"pan": True, "x": event.x, "y": event.y}
            self.canvas.scan_mark(event.x, event.y)
            return
        if self.current_tool == "select":
            handle = self._resize_handle_at(x, y)
            if handle:
                self._begin_resize(handle, x, y)
                return
            if not self._inside_page(x, y):
                return
            self.select_at(x, y, event)
            return
        if not self._inside_page(x, y):
            return
        x, y, _label = self.snap_point(x, y)
        if self.current_tool == "select_text":
            self._set_status("Select Text mode: click text markups with Select to edit the markup list.")
            return
        if self.current_tool == "eraser":
            self.erase_at(x, y)
            return
        if self.current_tool in {"text_box", "callout"}:
            self.place_text_tool(x, y)
            return
        if self.current_tool in {"polyline", "polygon"}:
            self.add_pending_point(x, y)
            return
        if self.current_tool == "pencil":
            self.drag = {"tool": "pencil", "points": [x, y], "preview": None}
            return
        self.drag = {"tool": self.current_tool, "x": x, "y": y, "preview": None}

    def on_drag(self, event):
        if not self.drag:
            return
        if self.drag.get("pan"):
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            return
        if self.drag.get("resize"):
            x, y = self._canvas_xy(event)
            self._resize_selected_to(x, y)
            return
        x, y = self._canvas_xy(event)
        x, y, label = self.snap_point(x, y)
        self.show_crosshair(x, y, label)
        if self.drag.get("tool") == "pencil":
            self.drag["points"].extend([x, y])
            if self.drag.get("preview"):
                self.canvas.delete(self.drag["preview"])
            self.drag["preview"] = self.canvas.create_line(self.drag["points"], fill=self.line_color_var.get(), width=self._style()["width"], smooth=True)
            return
        self._draw_preview(self.drag["x"], self.drag["y"], x, y)

    def on_release(self, event):
        if not self.drag:
            return
        if self.drag.get("pan"):
            self.drag = None
            return
        if self.drag.get("resize"):
            before = self.drag["before"]
            after = {item: self.canvas.coords(item) for item in before}
            self.drag = None
            self._push_undo({"type": "coords", "before": before, "after": after})
            self.draw_selection()
            self._set_status("Selection resized")
            return
        tool = self.drag.get("tool")
        preview = self.drag.get("preview")
        if preview:
            self.canvas.delete(preview)
        if tool == "pencil":
            points = self.drag["points"]
            self.drag = None
            if len(points) >= 4:
                item = self.canvas.create_line(points, fill=self.line_color_var.get(), width=self._style()["width"], smooth=True, capstyle=tk.ROUND, joinstyle=tk.ROUND)
                self._record_entry("Pencil", "freehand stroke", [item])
            return
        x0 = self.drag.get("x")
        y0 = self.drag.get("y")
        x1, y1 = self._canvas_xy(event)
        x1, y1, _label = self.snap_point(x1, y1)
        if self.ortho_var.get() and x0 is not None and y0 is not None:
            if abs(x1 - x0) >= abs(y1 - y0):
                y1 = y0
            else:
                x1 = x0
        self.drag = None
        if x0 is None or abs(x1 - x0) < 4 and abs(y1 - y0) < 4:
            return
        self.create_shape(tool, x0, y0, x1, y1)

    def on_right_click(self, event):
        if self.current_tool in {"polyline", "polygon"} and self.pending_points:
            self.finish_pending_shape(event)
            return
        x, y = self._canvas_xy(event)
        entry = self._entry_at(x, y)
        if entry and entry not in self.selected_entries:
            fake_event = type("Event", (), {"state": 0})()
            self.select_at(x, y, fake_event)
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label="Group Selected", command=self.group_selected, state="normal" if len(self.selected_entries) >= 2 else "disabled")
        menu.add_command(label="Ungroup Selected", command=self.ungroup_selected, state="normal" if any(entry.get("group") for entry in self.selected_entries) else "disabled")
        menu.add_separator()
        menu.add_command(label="Apply Style", command=self.apply_style_to_selected, state="normal" if self.selected_entries else "disabled")
        menu.add_command(label="Delete", command=self.delete_selected, state="normal" if self.selected_entries else "disabled")
        menu.tk_popup(event.x_root, event.y_root)

    def _draw_preview(self, x0, y0, x1, y1):
        if self.drag.get("preview"):
            self.canvas.delete(self.drag["preview"])
        tool = self.drag["tool"]
        if self.ortho_var.get() and tool in {"line", "arrow", "distance", "calibrate"}:
            if abs(x1 - x0) >= abs(y1 - y0):
                y1 = y0
            else:
                x1 = x0
        style = self._style()
        dash = self._dash()
        if tool in {"line", "distance", "calibrate"}:
            self.drag["preview"] = self.canvas.create_line(x0, y0, x1, y1, fill=style["line_color"], width=style["width"], dash=dash)
        elif tool == "arrow":
            self.drag["preview"] = self.canvas.create_line(x0, y0, x1, y1, fill=style["line_color"], width=style["width"], dash=dash, arrow=tk.LAST)
        elif tool in {"rectangle", "perimeter", "area"}:
            fill = style["fill_color"] if tool == "area" else ""
            self.drag["preview"] = self.canvas.create_rectangle(x0, y0, x1, y1, outline=style["line_color"], fill=fill, width=style["width"], dash=dash)
        elif tool == "circle":
            self.drag["preview"] = self.canvas.create_oval(x0, y0, x1, y1, outline=style["line_color"], fill=style["fill_color"], width=style["width"], dash=dash)
        elif tool == "cloud":
            points = self._cloud_points(x0, y0, x1, y1)
            self.drag["preview"] = self.canvas.create_line(points, fill=style["line_color"], width=style["width"], smooth=True)

    def create_shape(self, tool, x0, y0, x1, y1):
        style = self._style()
        dash = self._dash()
        items = []
        detail = tool
        if tool == "line":
            items.append(self.canvas.create_line(x0, y0, x1, y1, fill=style["line_color"], width=style["width"], dash=dash))
            self._record_entry("Line", "straight line", items)
        elif tool == "arrow":
            items.append(self.canvas.create_line(x0, y0, x1, y1, fill=style["line_color"], width=style["width"], dash=dash, arrow=tk.LAST))
            self._record_entry("Arrow", "closed arrow", items)
        elif tool == "rectangle":
            items.append(self.canvas.create_rectangle(x0, y0, x1, y1, outline=style["line_color"], fill=style["fill_color"], width=style["width"], dash=dash))
            self._record_entry("Rectangle", "rectangle", items)
        elif tool == "circle":
            items.append(self.canvas.create_oval(x0, y0, x1, y1, outline=style["line_color"], fill=style["fill_color"], width=style["width"], dash=dash))
            self._record_entry("Circle", "ellipse/circle", items)
        elif tool == "cloud":
            items.append(self.canvas.create_line(self._cloud_points(x0, y0, x1, y1), fill=style["line_color"], width=style["width"], smooth=True))
            self._record_entry("Cloud", "cloud markup", items)
        elif tool == "distance":
            line = self.canvas.create_line(x0, y0, x1, y1, fill=style["line_color"], width=style["width"], dash=dash, arrow=tk.BOTH)
            label = self._measure_label(math.hypot(x1 - x0, y1 - y0))
            text = self.canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2 - 14, text=label, fill=style["line_color"], font=(style["font_family"], style["font_size"], "bold"))
            self._record_entry("Distance", label, [line, text])
        elif tool == "perimeter":
            x0, y0, x1, y1 = clamp_box(x0, y0, x1, y1)
            rect = self.canvas.create_rectangle(x0, y0, x1, y1, outline=style["line_color"], width=style["width"], dash=dash)
            label = self._perimeter_label(abs(x1 - x0), abs(y1 - y0))
            text = self.canvas.create_text((x0 + x1) / 2, y0 - 12, text=label, fill=style["line_color"], font=(style["font_family"], style["font_size"], "bold"))
            self._record_entry("Perimeter", label, [rect, text])
        elif tool == "area":
            x0, y0, x1, y1 = clamp_box(x0, y0, x1, y1)
            rect = self.canvas.create_rectangle(x0, y0, x1, y1, outline=style["line_color"], fill=style["fill_color"] or "#dcecff", width=style["width"], dash=dash, stipple="gray25")
            label = self._area_label(abs(x1 - x0), abs(y1 - y0))
            text = self.canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=label, fill=style["line_color"], font=(style["font_family"], style["font_size"], "bold"))
            self._record_entry("Area", label, [rect, text])
        elif tool == "calibrate":
            self.finish_calibration(x0, y0, x1, y1)

    def _cloud_points(self, x0, y0, x1, y1):
        x0, y0, x1, y1 = clamp_box(x0, y0, x1, y1)
        step = max(12, min(abs(x1 - x0), abs(y1 - y0)) / 6)
        points = []
        x = x0
        while x <= x1:
            points.extend([x, y0 - (6 if int((x - x0) / step) % 2 else 0)])
            x += step
        y = y0
        while y <= y1:
            points.extend([x1 + (6 if int((y - y0) / step) % 2 else 0), y])
            y += step
        x = x1
        while x >= x0:
            points.extend([x, y1 + (6 if int((x1 - x) / step) % 2 else 0)])
            x -= step
        y = y1
        while y >= y0:
            points.extend([x0 - (6 if int((y1 - y) / step) % 2 else 0), y])
            y -= step
        points.extend(points[:2])
        return points

    def add_pending_point(self, x, y):
        x, y, label = self.snap_point(x, y)
        self.show_crosshair(x, y, label)
        self.pending_points.extend([x, y])
        if self.pending_preview:
            self.canvas.delete(self.pending_preview)
        style = self._style()
        if len(self.pending_points) >= 4:
            points = self.pending_points[:]
            if self.current_tool == "polygon" and len(points) >= 6:
                points.extend(points[:2])
            self.pending_preview = self.canvas.create_line(points, fill=style["line_color"], width=style["width"], dash=self._dash())
        self._set_status("Add vertices; double-click or right-click to finish.")

    def finish_pending_shape(self, event=None):
        if self.current_tool not in {"polyline", "polygon"} or len(self.pending_points) < 4:
            return
        style = self._style()
        dash = self._dash()
        if self.pending_preview:
            self.canvas.delete(self.pending_preview)
            self.pending_preview = None
        if self.current_tool == "polyline":
            item = self.canvas.create_line(self.pending_points, fill=style["line_color"], width=style["width"], dash=dash)
            self._record_entry("Polyline", "polyline", [item])
        else:
            item = self.canvas.create_polygon(self.pending_points, outline=style["line_color"], fill=style["fill_color"], width=style["width"], dash=dash)
            self._record_entry("Polygon", "polygon", [item])
        self.pending_points = []

    def _clear_pending(self):
        if self.pending_preview:
            self.canvas.delete(self.pending_preview)
            self.pending_preview = None
        self.pending_points = []

    def place_text_tool(self, x, y):
        text = simpledialog.askstring("Text", "Enter text:", initialvalue="Text")
        if not text:
            return
        style = self._style()
        w, h = 170, 58
        rect = self.canvas.create_rectangle(x, y, x + w, y + h, outline=style["line_color"], fill=style["fill_color"] or "white", width=style["width"], dash=self._dash())
        label = self.canvas.create_text(x + 10, y + 10, text=text, anchor="nw", width=w - 20, fill=style["line_color"], font=(style["font_family"], style["font_size"]))
        items = [rect, label]
        if self.current_tool == "callout":
            arrow = self.canvas.create_line(x - 70, y + h + 35, x, y + h / 2, fill=style["line_color"], width=style["width"], arrow=tk.LAST)
            items.append(arrow)
            self._record_entry("Callout", text, items)
        else:
            self._record_entry("Text Box", text, items)

    def finish_calibration(self, x0, y0, x1, y1):
        pixels = math.hypot(x1 - x0, y1 - y0)
        if pixels <= 0:
            return
        real = simpledialog.askfloat("Calibrate", "Known real distance:", minvalue=0.0001)
        if not real:
            return
        unit = self.unit_var.get() or self.scale_unit
        self.scale_units_per_px = real / pixels
        self.scale_unit = unit
        self.scale_label_var.set(f"1 px = {self.scale_units_per_px:.4f} {unit}")
        style = self._style()
        line = self.canvas.create_line(x0, y0, x1, y1, fill=self.colors["blue"], width=max(2, style["width"]), arrow=tk.BOTH)
        label = self.canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2 - 14, text=f"Scale: {real:g} {unit}", fill=self.colors["blue"], font=(style["font_family"], style["font_size"], "bold"))
        self._record_entry("Calibration", f"{real:g} {unit}", [line, label])

    def manual_scale(self):
        value = simpledialog.askfloat("Manual Scale", "Real units per 100 pixels:", minvalue=0.0001)
        if not value:
            return
        unit = self.unit_var.get() or self.scale_unit
        self.scale_units_per_px = value / 100
        self.scale_unit = unit
        self.scale_label_var.set(f"100 px = {value:g} {unit}")
        self._set_status(f"Manual scale set: 100 px = {value:g} {unit}")

    def _unit_changed(self, *_args):
        if getattr(self, "_updating_unit", False):
            return
        self._set_measure_unit(self.unit_var.get())

    def _set_measure_unit(self, unit):
        if unit not in UNIT_TO_MM or unit == self.scale_unit:
            return
        previous = self.scale_unit if self.scale_unit in UNIT_TO_MM else "mm"
        if self.scale_units_per_px:
            millimeters_per_px = self.scale_units_per_px * UNIT_TO_MM[previous]
            self.scale_units_per_px = millimeters_per_px / UNIT_TO_MM[unit]
            self.scale_label_var.set(f"1 px = {self.scale_units_per_px:.4f} {unit}")
        self.scale_unit = unit
        self._updating_unit = True
        try:
            self.unit_var.set(unit)
        finally:
            self._updating_unit = False
        self._set_status(f"Measure unit set to {unit}")

    def _precision(self):
        return max(0.000001, self._safe_float(self.precision_var.get(), 0.01))

    def _round_to_precision(self, value):
        precision = self._precision()
        return round(value / precision) * precision

    def _measure_label(self, pixels):
        if self.scale_units_per_px:
            value = self._round_to_precision(pixels * self.scale_units_per_px)
            return f"{value:g} {self.scale_unit}"
        return f"{pixels:.0f} px"

    def _perimeter_label(self, width_px, height_px):
        perimeter = 2 * (width_px + height_px)
        return f"P = {self._measure_label(perimeter)}"

    def _area_label(self, width_px, height_px):
        area_px = width_px * height_px
        if self.scale_units_per_px:
            value = self._round_to_precision(area_px * self.scale_units_per_px * self.scale_units_per_px)
            return f"A = {value:g} {self.scale_unit}^2"
        return f"A = {area_px:.0f} px^2"

    def _record_entry(self, kind, detail, items):
        entry = {
            "id": self.next_entry_id,
            "kind": kind,
            "detail": detail,
            "items": items,
            "group": None,
            "flattened": False,
            "layer": self.current_layer,
        }
        self.next_entry_id += 1
        tag = f"entry_{entry['id']}"
        for item in items:
            self.canvas.addtag_withtag(tag, item)
        self._current_entries().append(entry)
        self._push_undo({"type": "add", "entries": [entry]})
        self._add_markup_row(entry)
        self._apply_layer_visibility(entry)
        self._set_status(f"{kind} added")

    def _layer_visible(self, name):
        layer = next((layer for layer in self.layers if layer["name"] == name), None)
        return True if layer is None else layer.get("visible", True)

    def _apply_layer_visibility(self, entry):
        if not self._layer_visible(entry.get("layer", "0")):
            for item in entry["items"]:
                self.canvas.itemconfigure(item, state="hidden")
            self._remove_markup_row(entry)

    def _push_undo(self, action):
        self.undo_stack.append(action)
        self.undo_stack = self.undo_stack[-10:]
        self.redo_stack.clear()

    def _add_markup_row(self, entry):
        iid = str(entry["id"])
        if not self.markup_list.exists(iid):
            self.markup_list.insert("", "end", iid=iid, values=(entry["kind"], entry["detail"]))

    def _remove_markup_row(self, entry):
        iid = str(entry["id"])
        if self.markup_list.exists(iid):
            self.markup_list.delete(iid)

    def _set_entry_visible(self, entry, visible):
        state = "normal" if visible else "hidden"
        for item in entry["items"]:
            self.canvas.itemconfigure(item, state=state)
        if visible:
            self._add_markup_row(entry)
        else:
            self._remove_markup_row(entry)

    def undo(self):
        if not self.undo_stack:
            self._set_status("Nothing to undo")
            return
        action = self.undo_stack.pop()
        if action["type"] == "add":
            for entry in action["entries"]:
                self._set_entry_visible(entry, False)
        elif action["type"] == "delete":
            for entry in action["entries"]:
                self._set_entry_visible(entry, True)
        elif action["type"] == "coords":
            for item, coords in action["before"].items():
                self.canvas.coords(item, *coords)
            self.draw_selection()
        self.redo_stack.append(action)
        self.redo_stack = self.redo_stack[-10:]
        self._set_status("Undo")

    def redo(self):
        if not self.redo_stack:
            self._set_status("Nothing to redo")
            return
        action = self.redo_stack.pop()
        if action["type"] == "add":
            for entry in action["entries"]:
                self._set_entry_visible(entry, True)
        elif action["type"] == "delete":
            for entry in action["entries"]:
                self._set_entry_visible(entry, False)
        elif action["type"] == "coords":
            for item, coords in action["after"].items():
                self.canvas.coords(item, *coords)
            self.draw_selection()
        self.undo_stack.append(action)
        self.undo_stack = self.undo_stack[-10:]
        self._set_status("Redo")

    def erase_at(self, x, y):
        entry = self._entry_at(x, y)
        if not entry:
            self._set_status("Nothing under eraser")
            return
        if entry.get("flattened"):
            self._set_status("Flattened markup is locked")
            return
        self._set_entry_visible(entry, False)
        self._push_undo({"type": "delete", "entries": [entry]})
        self._set_status(f"Erased {entry['kind']}")

    def _entry_at(self, x, y):
        found = self.canvas.find_overlapping(x - 8, y - 8, x + 8, y + 8)
        for item in reversed(found):
            tags = self.canvas.gettags(item)
            for tag in tags:
                entry = self._entry_by_tag(tag)
                if entry:
                    return entry
        candidates = []
        for entry in self._current_entries():
            if not self._layer_visible(entry.get("layer", "0")):
                continue
            for item in entry["items"]:
                if self.canvas.itemcget(item, "state") == "hidden":
                    continue
                distance = self._distance_to_item(item, x, y)
                if distance <= 10:
                    candidates.append((distance, entry))
        if candidates:
            return min(candidates, key=lambda value: value[0])[1]
        return None

    def _distance_to_item(self, item, x, y):
        item_type = self.canvas.type(item)
        coords = self.canvas.coords(item)
        if item_type == "line" and len(coords) >= 4:
            points = list(zip(coords[0::2], coords[1::2]))
            return min(math.hypot(x - nx, y - ny) for nx, ny in (self._nearest_on_segment(x, y, points[i], points[i + 1]) for i in range(len(points) - 1)))
        bbox = self.canvas.bbox(item)
        if not bbox:
            return float("inf")
        x0, y0, x1, y1 = bbox
        if x0 <= x <= x1 and y0 <= y <= y1:
            return 0
        dx = max(x0 - x, 0, x - x1)
        dy = max(y0 - y, 0, y - y1)
        return math.hypot(dx, dy)

    def _entries_in_group(self, entry):
        group = entry.get("group")
        if not group:
            return [entry]
        return [candidate for candidate in self._current_entries() if candidate.get("group") == group]

    def select_at(self, x, y, event):
        entry = self._entry_at(x, y)
        ctrl = bool(event.state & 0x0004)
        if not ctrl:
            self.clear_selection()
        if not entry:
            self._set_status("No markup selected")
            return
        if entry.get("flattened"):
            self._set_status("Flattened markup is locked")
            return
        group_entries = [candidate for candidate in self._entries_in_group(entry) if not candidate.get("flattened")]
        selected = all(candidate in self.selected_entries for candidate in group_entries)
        if selected:
            for candidate in group_entries:
                if candidate in self.selected_entries:
                    self.selected_entries.remove(candidate)
        else:
            for candidate in group_entries:
                if candidate not in self.selected_entries:
                    self.selected_entries.append(candidate)
        self.draw_selection()
        self._set_status(f"{len(self.selected_entries)} markup(s) selected")

    def clear_selection(self):
        for box in self.selection_boxes:
            self.canvas.delete(box)
        self.selection_boxes = []
        self.resize_handles = []
        self.selected_entries = []

    def draw_selection(self):
        for box in self.selection_boxes:
            self.canvas.delete(box)
        self.selection_boxes = []
        self.resize_handles = []
        for entry in self.selected_entries:
            bbox = self._entry_bbox(entry)
            if bbox:
                x0, y0, x1, y1 = bbox
                self.selection_boxes.append(self.canvas.create_rectangle(x0 - 5, y0 - 5, x1 + 5, y1 + 5, outline=self.colors["blue"], width=2, dash=(4, 3)))
        bbox = self._selection_bbox()
        if bbox:
            self._draw_resize_handles(bbox)

    def _entry_bbox(self, entry):
        boxes = [self.canvas.bbox(item) for item in entry["items"] if self.canvas.itemcget(item, "state") != "hidden"]
        boxes = [box for box in boxes if box]
        if not boxes:
            return None
        return min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)

    def _selection_bbox(self):
        boxes = [self._entry_bbox(entry) for entry in self.selected_entries]
        boxes = [box for box in boxes if box]
        if not boxes:
            return None
        return min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)

    def _draw_resize_handles(self, bbox):
        x0, y0, x1, y1 = bbox
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        points = {
            "nw": (x0, y0),
            "n": (cx, y0),
            "ne": (x1, y0),
            "e": (x1, cy),
            "se": (x1, y1),
            "s": (cx, y1),
            "sw": (x0, y1),
            "w": (x0, cy),
        }
        for anchor, (hx, hy) in points.items():
            item = self.canvas.create_rectangle(hx - 4, hy - 4, hx + 4, hy + 4, fill=self.colors["card"], outline=self.colors["blue"], width=2)
            self.selection_boxes.append(item)
            self.resize_handles.append({"item": item, "anchor": anchor})
            self.canvas.tag_raise(item)

    def _resize_handle_at(self, x, y):
        for handle in reversed(self.resize_handles):
            coords = self.canvas.coords(handle["item"])
            if coords and coords[0] - 3 <= x <= coords[2] + 3 and coords[1] - 3 <= y <= coords[3] + 3:
                return handle
        return None

    def _begin_resize(self, handle, x, y):
        bbox = self._selection_bbox()
        if not bbox:
            return
        original = {}
        for entry in self.selected_entries:
            if entry.get("flattened"):
                continue
            for item in entry["items"]:
                original[item] = self.canvas.coords(item)
        if not original:
            return
        self.drag = {
            "resize": True,
            "anchor": handle["anchor"],
            "bbox": bbox,
            "before": {item: coords[:] for item, coords in original.items()},
            "original": original,
        }
        self._set_status("Drag resize handle to scale selection")

    def _resize_selected_to(self, x, y):
        x0, y0, x1, y1 = self.drag["bbox"]
        nx0, ny0, nx1, ny1 = x0, y0, x1, y1
        anchor = self.drag["anchor"]
        if "w" in anchor:
            nx0 = x
        if "e" in anchor:
            nx1 = x
        if "n" in anchor:
            ny0 = y
        if "s" in anchor:
            ny1 = y
        if anchor == "n":
            nx0, nx1 = x0, x1
        elif anchor == "s":
            nx0, nx1 = x0, x1
        elif anchor == "e":
            ny0, ny1 = y0, y1
        elif anchor == "w":
            ny0, ny1 = y0, y1
        min_size = 8
        if nx1 - nx0 < min_size:
            if "w" in anchor:
                nx0 = nx1 - min_size
            else:
                nx1 = nx0 + min_size
        if ny1 - ny0 < min_size:
            if "n" in anchor:
                ny0 = ny1 - min_size
            else:
                ny1 = ny0 + min_size
        width = max(1, x1 - x0)
        height = max(1, y1 - y0)
        sx = (nx1 - nx0) / width
        sy = (ny1 - ny0) / height
        for item, coords in self.drag["original"].items():
            new_coords = []
            for index, value in enumerate(coords):
                if index % 2 == 0:
                    new_coords.append(nx0 + (value - x0) * sx)
                else:
                    new_coords.append(ny0 + (value - y0) * sy)
            self.canvas.coords(item, *new_coords)
        self.draw_selection()

    def apply_style_to_selected(self):
        style = self._style()
        dash = self._dash()
        for entry in self.selected_entries:
            for item in entry["items"]:
                item_type = self.canvas.type(item)
                if item_type in {"line", "polygon"}:
                    self.canvas.itemconfigure(item, fill=style["line_color"], width=style["width"], dash=dash)
                    if item_type == "polygon":
                        self.canvas.itemconfigure(item, outline=style["line_color"])
                        if style["fill_color"]:
                            self.canvas.itemconfigure(item, fill=style["fill_color"])
                elif item_type in {"rectangle", "oval"}:
                    self.canvas.itemconfigure(item, outline=style["line_color"], width=style["width"], dash=dash)
                    self.canvas.itemconfigure(item, fill=style["fill_color"])
                elif item_type == "text":
                    self.canvas.itemconfigure(item, fill=style["line_color"], font=(style["font_family"], style["font_size"]))
        self.draw_selection()
        self._set_status("Style applied to selected markups")

    def move_selected(self):
        if not self.selected_entries:
            self._set_status("Select markups before Move")
            return
        dx = simpledialog.askfloat("Move", "Move X:", initialvalue=10.0)
        if dx is None:
            return
        dy = simpledialog.askfloat("Move", "Move Y:", initialvalue=10.0)
        if dy is None:
            return
        for entry in self.selected_entries:
            if entry.get("flattened"):
                continue
            for item in entry["items"]:
                self.canvas.move(item, dx, dy)
        self.draw_selection()
        self._set_status(f"Moved selection by {dx:g}, {dy:g}")

    def copy_selected(self):
        if not self.selected_entries:
            self._set_status("Select markups before Copy")
            return
        copies = []
        for entry in self.selected_entries:
            new_items = [self._clone_canvas_item(item, 20, 20) for item in entry["items"]]
            new_items = [item for item in new_items if item]
            if new_items:
                self._record_entry(f"{entry['kind']} Copy", entry["detail"], new_items)
                copies.append(self._current_entries()[-1])
        self.clear_selection()
        self.selected_entries = copies
        self.draw_selection()
        self._set_status(f"Copied {len(copies)} markup(s)")

    def offset_selected(self):
        if not self.selected_entries:
            self._set_status("Select markups before Offset")
            return
        distance = simpledialog.askfloat("Offset", "Offset distance:", initialvalue=20.0)
        if distance is None:
            return
        created = []
        for entry in self.selected_entries:
            new_items = [self._clone_canvas_item(item, distance, distance) for item in entry["items"]]
            new_items = [item for item in new_items if item]
            if new_items:
                self._record_entry(f"{entry['kind']} Offset", f"offset {distance:g}", new_items)
                created.append(self._current_entries()[-1])
        self.clear_selection()
        self.selected_entries = created
        self.draw_selection()
        self._set_status(f"Offset {len(created)} markup(s)")

    def delete_selected(self):
        if not self.selected_entries:
            self._set_status("Select markups before Delete")
            return
        deleted = list(self.selected_entries)
        for entry in deleted:
            if entry.get("flattened"):
                continue
            self._set_entry_visible(entry, False)
        self._push_undo({"type": "delete", "entries": deleted})
        self.clear_selection()
        self._set_status(f"Deleted {len(deleted)} selected markup(s)")

    def _clone_canvas_item(self, item, dx, dy):
        item_type = self.canvas.type(item)
        coords = self.canvas.coords(item)
        shifted = [value + (dx if index % 2 == 0 else dy) for index, value in enumerate(coords)]
        fill = self._item_option(item, "fill")
        outline = self._item_option(item, "outline")
        width = self._safe_float(self._item_option(item, "width"), 1)
        dash = self._parse_dash(self._item_option(item, "dash"))
        if item_type == "line":
            return self.canvas.create_line(shifted, fill=fill, width=width, dash=dash, arrow=self._item_option(item, "arrow") or None)
        if item_type == "rectangle":
            return self.canvas.create_rectangle(shifted, outline=outline, fill=fill, width=width, dash=dash, stipple=self._item_option(item, "stipple"))
        if item_type == "oval":
            return self.canvas.create_oval(shifted, outline=outline, fill=fill, width=width, dash=dash)
        if item_type == "polygon":
            return self.canvas.create_polygon(shifted, outline=outline, fill=fill, width=width, dash=dash, stipple=self._item_option(item, "stipple"))
        if item_type == "text":
            options = {"text": self._item_option(item, "text"), "fill": fill, "font": self._item_option(item, "font"), "anchor": "nw"}
            text_width = self._safe_float(self._item_option(item, "width"), 0)
            if text_width:
                options["width"] = text_width
            return self.canvas.create_text(shifted, **options)
        return None

    def group_selected(self):
        if len(self.selected_entries) < 2:
            self._set_status("Select at least two markups to group")
            return
        group_id = f"group_{self.next_group_id}"
        self.next_group_id += 1
        for entry in self.selected_entries:
            entry["group"] = group_id
        self.selected_entries = [entry for entry in self._current_entries() if entry.get("group") == group_id]
        self.draw_selection()
        self._set_status(f"Grouped {len(self.selected_entries)} markups as {group_id}")

    def ungroup_selected(self):
        groups = {entry.get("group") for entry in self.selected_entries if entry.get("group")}
        if not groups:
            self._set_status("No grouped markups selected")
            return
        count = 0
        for entry in self._current_entries():
            if entry.get("group") in groups:
                entry["group"] = None
                count += 1
        self.draw_selection()
        self._set_status(f"Ungrouped {count} markup(s)")

    def flatten_layer(self):
        targets = self.selected_entries or self._current_entries()
        if not targets:
            self._set_status("No markups to flatten")
            return
        for entry in targets:
            entry["flattened"] = True
        self.clear_selection()
        self._set_status(f"Flattened {len(targets)} markup(s)")

    def save_group_library(self):
        targets = self.selected_entries
        if not targets:
            self._set_status("Select a group or markups before saving to library")
            return
        name = simpledialog.askstring("Save Group", "Library item name:", initialvalue="Saved Detail")
        if not name:
            return
        library = []
        if os.path.exists(LIBRARY_PATH):
            try:
                with open(LIBRARY_PATH, "r", encoding="utf-8") as handle:
                    library = json.load(handle)
            except (OSError, json.JSONDecodeError):
                library = []
        library.append({"name": name, "entries": [self._serialize_entry(entry) for entry in targets]})
        with open(LIBRARY_PATH, "w", encoding="utf-8") as handle:
            json.dump(library, handle, indent=2)
        self.refresh_library()
        self._set_status(f"Saved {name} to library")

    def refresh_library(self):
        self.library_list.delete(0, "end")
        if not os.path.exists(LIBRARY_PATH):
            return
        try:
            with open(LIBRARY_PATH, "r", encoding="utf-8") as handle:
                library = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return
        for item in library:
            self.library_list.insert("end", item.get("name", "Library Item"))

    def add_bookmark(self):
        name = simpledialog.askstring("Bookmark", "Bookmark name:", initialvalue=f"Page {self.current_page + 1}")
        if not name:
            return
        self.bookmark_list.insert("end", f"{name} - Page {self.current_page + 1}")
        self._set_status("Bookmark added")

    def _refresh_layer_list(self):
        if not hasattr(self, "layer_list"):
            return
        self.layer_list.delete(0, "end")
        for layer in self.layers:
            marker = "on" if layer.get("visible", True) else "off"
            current = "*" if layer["name"] == self.current_layer else " "
            self.layer_list.insert("end", f"{current} {marker}  {layer['name']}")
        index = next((i for i, layer in enumerate(self.layers) if layer["name"] == self.current_layer), 0)
        self.layer_list.selection_clear(0, "end")
        self.layer_list.selection_set(index)

    def add_layer(self):
        name = simpledialog.askstring("New Layer", "Layer name:", initialvalue=f"Layer {len(self.layers)}")
        if not name:
            return
        self.create_layer_named(name)

    def create_layer_named(self, name):
        if any(layer["name"] == name for layer in self.layers):
            self.current_layer = name
            self.layer_var.set(name)
            self._refresh_layer_list()
            self._set_status(f"Current layer: {name}")
            return
        self.layers.append({"name": name, "visible": True, "locked": False})
        self.current_layer = name
        self.layer_var.set(name)
        self._refresh_layer_list()
        self._set_status(f"Layer {name} created")

    def _layer_selected(self, event=None):
        selection = self.layer_list.curselection()
        if not selection:
            return
        self.current_layer = self.layers[selection[0]]["name"]
        self.layer_var.set(self.current_layer)
        self._refresh_layer_list()
        self._set_status(f"Current layer: {self.current_layer}")

    def toggle_layer_visibility(self):
        selection = self.layer_list.curselection()
        if not selection:
            return
        layer = self.layers[selection[0]]
        layer["visible"] = not layer.get("visible", True)
        for page in self.pages:
            for entry in page["entries"]:
                if entry.get("layer", "0") == layer["name"]:
                    self._set_entry_visible(entry, layer["visible"])
        self._refresh_layer_list()
        self._set_status(f"Layer {layer['name']} visibility: {layer['visible']}")

    def zoom_in(self):
        self._set_zoom(min(2.5, self.zoom_level + 0.1))

    def zoom_out(self):
        self._set_zoom(max(0.4, self.zoom_level - 0.1))

    def _set_zoom(self, new_zoom):
        factor = new_zoom / self.zoom_level
        self.zoom_level = new_zoom
        self.canvas.scale("all", 0, 0, factor, factor)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.zoom_label.configure(text=f"{int(self.zoom_level * 100)}%")
        self.draw_selection()
        self._set_status(f"Zoom {int(self.zoom_level * 100)}%")

    def rotate_page(self, degrees):
        bbox = self._page_bbox()
        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        clockwise = degrees > 0
        for entry in self._current_entries():
            for item in entry["items"]:
                item_type = self.canvas.type(item)
                coords = self.canvas.coords(item)
                if item_type in {"line", "polygon"}:
                    self.canvas.coords(item, *self._rotate_coords(coords, cx, cy, clockwise))
                elif item_type in {"rectangle", "oval"}:
                    rotated = self._rotate_coords([coords[0], coords[1], coords[2], coords[1], coords[2], coords[3], coords[0], coords[3]], cx, cy, clockwise)
                    xs = rotated[0::2]
                    ys = rotated[1::2]
                    self.canvas.coords(item, min(xs), min(ys), max(xs), max(ys))
                elif item_type == "text":
                    rotated = self._rotate_coords(coords[:2], cx, cy, clockwise)
                    self.canvas.coords(item, rotated[0], rotated[1])
        self.rotation = (self.rotation + degrees) % 360
        self.draw_selection()
        self._set_status(f"Rotated current page content to {self.rotation} deg")

    def _rotate_coords(self, coords, cx, cy, clockwise):
        rotated = []
        for i in range(0, len(coords), 2):
            x, y = coords[i], coords[i + 1]
            dx, dy = x - cx, y - cy
            if clockwise:
                rx, ry = cx + dy, cy - dx
            else:
                rx, ry = cx - dy, cy + dx
            rotated.extend([rx, ry])
        return rotated

    def insert_page(self):
        paper = self.choose_paper_size("Insert Page")
        if not paper:
            return
        self.pages.insert(self.current_page + 1, {"paper": paper, "entries": []})
        self.current_page += 1
        self.paper_var.set(paper)
        self._refresh_page_list()
        self._show_current_page()
        self._set_status(f"Inserted {paper} page")

    def choose_paper_size(self, title):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(bg=self.colors["chrome"])
        dialog.resizable(False, False)
        tk.Label(dialog, text="Paper size", bg=self.colors["chrome"], fg=self.colors["text"], font=self.font_heading).pack(anchor="w", padx=18, pady=(16, 6))
        choice = tk.StringVar(value=self.paper_var.get() if self.paper_var.get() in PAPER_MM else "A4")
        combo = ttk.Combobox(dialog, textvariable=choice, values=PAPER_NAMES, state="readonly", width=24)
        combo.pack(padx=18, pady=(0, 14))
        result = {"value": None}

        def accept():
            result["value"] = choice.get()
            dialog.destroy()

        buttons = tk.Frame(dialog, bg=self.colors["chrome"])
        buttons.pack(fill="x", padx=18, pady=(0, 16))
        tk.Button(buttons, text="OK", command=accept, **self._button_style()).pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Button(buttons, text="Cancel", command=dialog.destroy, bg=self.colors["card"], fg=self.colors["text"], relief="flat", bd=0, pady=7, font=self.font_body).pack(side="left", fill="x", expand=True)
        combo.focus_set()
        self.wait_window(dialog)
        return result["value"]

    def delete_page(self):
        if len(self.pages) == 1:
            self._set_status("Cannot delete the only page")
            return
        page = self.pages.pop(self.current_page)
        for entry in page["entries"]:
            for item in entry["items"]:
                self.canvas.delete(item)
        self.current_page = max(0, self.current_page - 1)
        self._refresh_page_list()
        self._show_current_page()
        self._set_status("Deleted page")

    def extract_page(self):
        path = filedialog.asksaveasfilename(defaultextension=".dieselpdf-page.json", filetypes=[("DieselPDF page", "*.dieselpdf-page.json")])
        if not path:
            return
        data = {"page": self._serialize_page(self.pages[self.current_page])}
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        self._set_status(f"Extracted page to {os.path.basename(path)}")

    def previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._show_current_page()

    def next_page(self):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self._show_current_page()

    def _page_selected(self, event=None):
        selection = self.page_list.curselection()
        if not selection:
            return
        self.current_page = selection[0]
        self._show_current_page()

    def _refresh_page_list(self):
        if not hasattr(self, "page_list"):
            return
        self.page_list.delete(0, "end")
        for idx, page in enumerate(self.pages, start=1):
            self.page_list.insert("end", f"Page {idx} - {page['paper']}")
        self.page_list.selection_clear(0, "end")
        self.page_list.selection_set(self.current_page)
        self._update_page_label()

    def _show_current_page(self):
        self.clear_selection()
        for page in self.pages:
            for entry in page["entries"]:
                for item in entry["items"]:
                    self.canvas.itemconfigure(item, state="hidden")
        for entry in self._current_entries():
            for item in entry["items"]:
                self.canvas.itemconfigure(item, state="normal" if self._layer_visible(entry.get("layer", "0")) else "hidden")
        self.paper_var.set(self.pages[self.current_page]["paper"])
        self._update_page_surface()
        for entry in self._current_entries():
            for item in entry["items"]:
                if self.canvas.itemcget(item, "state") != "hidden":
                    self.canvas.tag_raise(item)
        self._rebuild_markup_list()
        self._refresh_page_list()
        self._set_status(f"Showing page {self.current_page + 1}")

    def _update_page_surface(self):
        page = self.pages[self.current_page]
        self.page_w, self.page_h = self._page_pixel_size(page)
        x0, y0 = PAGE_ORIGIN
        x1, y1 = x0 + self.page_w, y0 + self.page_h
        self.canvas.coords(self.shadow1, x0 + 8, y0 + 8, x1 + 8, y1 + 8)
        self.canvas.coords(self.shadow2, x0 + 4, y0 + 4, x1 + 4, y1 + 4)
        self.canvas.coords(self.page_rect, x0, y0, x1, y1)
        self.canvas.coords(self.page_title, x0 + 30, y0 + 34)
        self.canvas.coords(self.page_subtitle, x0 + 32, y0 + 72)
        self.canvas.coords(self.page_divider, x0 + 30, y0 + 114, x1 - 80, y0 + 114)
        if self._is_pdf_page(page):
            rendered = self._render_pdf_page(page, x0, y0)
            state = "hidden" if rendered else "normal"
            self.canvas.itemconfigure(self.page_title, state=state, text=os.path.basename(self.current_pdf or self.current_file or "PDF"))
            self.canvas.itemconfigure(self.page_subtitle, state=state, text="PDF renderer not available. Install PyMuPDF to show pages.")
            self.canvas.itemconfigure(self.page_divider, state=state)
        else:
            self._hide_pdf_image()
            self.canvas.itemconfigure(self.page_title, state="normal", text="DieselPDF")
            self.canvas.itemconfigure(self.page_subtitle, state="normal", text="Default mode is Hand. Select a tool, then draw on the page.")
            self.canvas.itemconfigure(self.page_divider, state="normal")
        self.canvas.configure(scrollregion=(0, 0, x1 + 90, y1 + 90))
        self._update_page_label()

    def _page_pixel_size(self, page):
        if self._is_pdf_page(page):
            return int(page.get("width", paper_pixels("A4")[0])), int(page.get("height", paper_pixels("A4")[1]))
        return paper_pixels(page.get("paper", "A4"))

    def _is_pdf_page(self, page):
        return page.get("paper") == "PDF" and bool(self.current_pdf or self.current_file)

    def _is_pdf_path(self, path):
        return bool(path) and str(path).lower().endswith(".pdf")

    def _hide_pdf_image(self):
        if self.pdf_page_item:
            self.canvas.itemconfigure(self.pdf_page_item, state="hidden")

    def _pdf_renderer(self):
        try:
            import fitz
            return fitz
        except Exception:
            return None

    def _render_pdf_page(self, page, x0, y0):
        fitz = self._pdf_renderer()
        if not fitz:
            self._hide_pdf_image()
            return False
        path = self.current_pdf or self.current_file
        if not path or not os.path.exists(path):
            self._hide_pdf_image()
            return False
        page_index = int(page.get("pdf_index", self.current_page))
        try:
            stamp = int(os.path.getmtime(path))
        except OSError:
            stamp = 0
        cache_key = (path, page_index, self.pdf_render_scale, stamp)
        render_path = self.pdf_render_cache.get(cache_key)
        if not render_path or not os.path.exists(render_path):
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", os.path.basename(path))
            render_path = os.path.join(self.pdf_render_dir, f"{safe_name}.{page_index}.{stamp}.{int(self.pdf_render_scale * 100)}.png")
            try:
                doc = fitz.open(path)
                pdf_page = doc.load_page(page_index)
                pix = pdf_page.get_pixmap(matrix=fitz.Matrix(self.pdf_render_scale, self.pdf_render_scale), alpha=False)
                pix.save(render_path)
                doc.close()
            except Exception as exc:
                self._hide_pdf_image()
                self._set_status(f"Could not render PDF page: {exc}")
                return False
            self.pdf_render_cache[cache_key] = render_path
        try:
            self.pdf_page_image = tk.PhotoImage(file=render_path)
        except tk.TclError as exc:
            self._hide_pdf_image()
            self._set_status(f"Could not load rendered PDF image: {exc}")
            return False
        if not self.pdf_page_item:
            self.pdf_page_item = self.canvas.create_image(x0, y0, anchor="nw", image=self.pdf_page_image)
        else:
            self.canvas.itemconfigure(self.pdf_page_item, image=self.pdf_page_image, state="normal")
            self.canvas.coords(self.pdf_page_item, x0, y0)
        self.canvas.tag_raise(self.pdf_page_item, self.page_rect)
        return True

    def apply_current_paper_size(self):
        paper = self.paper_var.get()
        if paper not in PAPER_MM:
            return
        self.pages[self.current_page]["paper"] = paper
        self._update_page_surface()
        self._refresh_page_list()
        self._set_status(f"Current page set to {paper}")

    def _update_page_label(self):
        if hasattr(self, "page_label"):
            self.page_label.configure(text=f"Page {self.current_page + 1} of {len(self.pages)}")

    def _rebuild_markup_list(self):
        self.markup_list.delete(*self.markup_list.get_children())
        for entry in self._current_entries():
            if self.canvas.itemcget(entry["items"][0], "state") != "hidden":
                self._add_markup_row(entry)

    def new_project(self):
        subprocess.Popen([sys.executable, os.path.abspath(__file__)], close_fds=True)
        self._set_status("Opened a new DieselPDF window")

    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if not path:
            return
        self.new_project_without_prompt()
        self.current_file = path
        self.current_pdf = path
        self.pages = self._pdf_pages_metadata(path)
        self.current_page = 0
        self._set_current_document_title(os.path.basename(path))
        self._refresh_page_list()
        self._show_current_page()
        self._sync_active_document()
        self._set_status(f"Opened PDF: {os.path.basename(path)} ({len(self.pages)} page(s))")

    def _pdf_page_count(self, path):
        return len(self._pdf_pages_metadata(path))

    def _pdf_pages_metadata(self, path):
        fitz = self._pdf_renderer()
        if fitz:
            try:
                doc = fitz.open(path)
                pages = []
                for index, pdf_page in enumerate(doc):
                    rect = pdf_page.rect
                    pages.append({
                        "paper": "PDF",
                        "entries": [],
                        "pdf_index": index,
                        "width": max(1, int(rect.width * self.pdf_render_scale)),
                        "height": max(1, int(rect.height * self.pdf_render_scale)),
                    })
                doc.close()
                return pages or [{"paper": "PDF", "entries": [], "pdf_index": 0, "width": paper_pixels("A4")[0], "height": paper_pixels("A4")[1]}]
            except Exception as exc:
                messagebox.showerror("Open PDF", f"Could not read PDF pages:\n{exc}")
                return [{"paper": "PDF", "entries": [], "pdf_index": 0, "width": paper_pixels("A4")[0], "height": paper_pixels("A4")[1]}]
        messagebox.showerror("Open PDF", "PDF rendering needs PyMuPDF. DieselPDF will install/use the local renderer package.")
        try:
            with open(path, "rb") as handle:
                data = handle.read()
            matches = re.findall(rb"/Type\s*/Page\b", data)
            count = max(1, len(matches))
        except OSError:
            count = 1
        return [{"paper": "PDF", "entries": [], "pdf_index": index, "width": paper_pixels("A4")[0], "height": paper_pixels("A4")[1]} for index in range(count)]

    def open_project(self):
        path = filedialog.askopenfilename(filetypes=[("DieselPDF project", "*.dieselpdf.json"), ("JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("Open", str(exc))
            return
        self.new_project_without_prompt()
        self.project_file = path
        self.current_file = data.get("source_file")
        self.current_pdf = data.get("pdf_file") or (self.current_file if self._is_pdf_path(self.current_file) else None)
        self.scale_units_per_px = data.get("scale_units_per_px")
        self.scale_unit = data.get("scale_unit", "mm")
        self.scale_label_var.set(data.get("scale_label", "Not calibrated"))
        self._updating_unit = True
        try:
            self.unit_var.set(data.get("unit", self.scale_unit))
        finally:
            self._updating_unit = False
        self.layers = data.get("layers", [{"name": "0", "visible": True, "locked": False}])
        self.current_layer = data.get("current_layer", self.layers[0]["name"])
        self.layer_var.set(self.current_layer)
        self.pages = []
        for page_data in data.get("pages", [{"paper": "A4", "entries": []}]):
            page = {
                "paper": page_data.get("paper", "A4"),
                "entries": [],
                "pdf_index": page_data.get("pdf_index"),
                "width": page_data.get("width"),
                "height": page_data.get("height"),
            }
            self.pages.append(page)
            for entry_data in page_data.get("entries", []):
                self._restore_entry(page, entry_data)
        self.current_page = 0
        for bookmark in data.get("bookmarks", []):
            self.bookmark_list.insert("end", bookmark)
        self._set_current_document_title(os.path.basename(path))
        self._refresh_page_list()
        self._refresh_layer_list()
        self._show_current_page()
        self._sync_active_document()
        self._set_status("Project opened")

    def new_project_without_prompt(self):
        for page in self.pages:
            for entry in page["entries"]:
                for item in entry["items"]:
                    self.canvas.delete(item)
        self.project_file = None
        self.current_file = None
        self.current_pdf = None
        self._hide_pdf_image()
        self.pages = [{"paper": "A4", "entries": []}]
        self.current_page = 0
        self.scale_units_per_px = None
        self.scale_unit = "mm"
        self.scale_label_var.set("Not calibrated")
        self._updating_unit = True
        try:
            self.unit_var.set("mm")
        finally:
            self._updating_unit = False
        self.layers = [{"name": "0", "visible": True, "locked": False}]
        self.current_layer = "0"
        self.layer_var.set("0")
        self.paper_var.set("A4")
        self.rotation = 0
        self.clear_selection()
        self.bookmark_list.delete(0, "end")
        self.markup_list.delete(*self.markup_list.get_children())
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._set_current_document_title("New Document*")
        self._sync_active_document()

    def save_project(self):
        if not self.project_file:
            return self.save_project_as()
        self._write_project(self.project_file)

    def save_project_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".dieselpdf.json", filetypes=[("DieselPDF project", "*.dieselpdf.json"), ("JSON", "*.json")])
        if not path:
            return
        self.project_file = path
        self._write_project(path)

    def _write_project(self, path):
        data = {
            "app": APP_TITLE,
            "source_file": self.current_file,
            "pdf_file": self.current_pdf,
            "scale_units_per_px": self.scale_units_per_px,
            "scale_unit": self.scale_unit,
            "scale_label": self.scale_label_var.get(),
            "unit": self.unit_var.get(),
            "layers": self.layers,
            "current_layer": self.current_layer,
            "bookmarks": list(self.bookmark_list.get(0, "end")),
            "pages": [self._serialize_page(page) for page in self.pages],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        self._set_current_document_title(os.path.basename(path))
        self._sync_active_document()
        self._set_status(f"Saved {os.path.basename(path)}")

    def _serialize_page(self, page):
        return {
            "paper": page["paper"],
            "pdf_index": page.get("pdf_index"),
            "width": page.get("width"),
            "height": page.get("height"),
            "entries": [self._serialize_entry(entry) for entry in page["entries"]],
        }

    def _serialize_entry(self, entry):
        objects = []
        for item in entry["items"]:
            objects.append({
                "type": self.canvas.type(item),
                "coords": self.canvas.coords(item),
                "fill": self._item_option(item, "fill"),
                "outline": self._item_option(item, "outline"),
                "width": self._item_option(item, "width"),
                "dash": self._item_option(item, "dash"),
                "arrow": self._item_option(item, "arrow"),
                "text": self._item_option(item, "text"),
                "font": self._item_option(item, "font"),
                "stipple": self._item_option(item, "stipple"),
            })
        return {
            "id": entry["id"],
            "kind": entry["kind"],
            "detail": entry["detail"],
            "group": entry.get("group"),
            "flattened": entry.get("flattened", False),
            "layer": entry.get("layer", "0"),
            "objects": objects,
        }

    def _item_option(self, item, option):
        try:
            return self.canvas.itemcget(item, option)
        except tk.TclError:
            return ""

    def _restore_entry(self, page, entry_data):
        items = []
        for obj in entry_data.get("objects", []):
            kwargs = {"fill": obj.get("fill", "")}
            if obj["type"] == "line":
                kwargs.update(width=self._safe_float(obj.get("width"), 1), dash=self._parse_dash(obj.get("dash")), arrow=obj.get("arrow") or None)
                items.append(self.canvas.create_line(obj["coords"], **kwargs))
            elif obj["type"] == "rectangle":
                kwargs.update(outline=obj.get("outline", ""), width=self._safe_float(obj.get("width"), 1), dash=self._parse_dash(obj.get("dash")), stipple=obj.get("stipple", ""))
                items.append(self.canvas.create_rectangle(obj["coords"], **kwargs))
            elif obj["type"] == "oval":
                kwargs.update(outline=obj.get("outline", ""), width=self._safe_float(obj.get("width"), 1), dash=self._parse_dash(obj.get("dash")))
                items.append(self.canvas.create_oval(obj["coords"], **kwargs))
            elif obj["type"] == "polygon":
                kwargs.update(outline=obj.get("outline", ""), width=self._safe_float(obj.get("width"), 1), dash=self._parse_dash(obj.get("dash")), stipple=obj.get("stipple", ""))
                items.append(self.canvas.create_polygon(obj["coords"], **kwargs))
            elif obj["type"] == "text":
                items.append(self.canvas.create_text(obj["coords"], text=obj.get("text", ""), fill=obj.get("fill", "#111"), font=obj.get("font", "Arial 12"), anchor="nw"))
        entry = {
            "id": entry_data.get("id", self.next_entry_id),
            "kind": entry_data.get("kind", "Markup"),
            "detail": entry_data.get("detail", ""),
            "items": items,
            "group": entry_data.get("group"),
            "flattened": entry_data.get("flattened", False),
            "layer": entry_data.get("layer", "0"),
        }
        self.next_entry_id = max(self.next_entry_id, entry["id"] + 1)
        for item in items:
            self.canvas.addtag_withtag(f"entry_{entry['id']}", item)
        page["entries"].append(entry)

    def _parse_dash(self, dash):
        if not dash:
            return None
        try:
            return tuple(int(float(part)) for part in str(dash).split())
        except ValueError:
            return None

    def _cad_backend(self):
        try:
            import ezdxf
            return ezdxf
        except Exception as exc:
            messagebox.showerror("CAD module", f"CAD module needs ezdxf in vendor_cad_py311.\n\n{exc}")
            return None

    def _cad_scale(self):
        return self.scale_units_per_px if self.scale_units_per_px else 1.0

    def _canvas_to_cad(self, x, y):
        x0, y0, _x1, _y1 = self._page_bbox()
        scale = self._cad_scale()
        return (x - x0) * scale, (self.page_h - (y - y0)) * scale

    def _cad_to_canvas(self, x, y):
        x0, y0, _x1, _y1 = self._page_bbox()
        scale = self._cad_scale() or 1.0
        return x0 + (x / scale), y0 + self.page_h - (y / scale)

    def _cad_layer_name(self, name):
        clean = re.sub(r"[^A-Za-z0-9_$ -]+", "_", str(name or "0")).strip()
        return clean[:250] or "0"

    def _cad_units_code(self):
        return {"mm": 4, "cm": 5, "m": 6}.get(self.scale_unit or self.unit_var.get(), 4)

    def _entries_to_cad_commands(self, entries):
        commands = []
        for entry in entries:
            if not self._layer_visible(entry.get("layer", "0")):
                continue
            layer = self._cad_layer_name(entry.get("layer", "0"))
            for item in entry["items"]:
                if self.canvas.itemcget(item, "state") == "hidden":
                    continue
                item_type = self.canvas.type(item)
                coords = self.canvas.coords(item)
                if item_type == "line" and len(coords) >= 4:
                    points = [self._canvas_to_cad(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]
                    if len(points) == 2:
                        commands.append({"type": "line", "points": points, "layer": layer})
                    else:
                        commands.append({"type": "polyline", "points": points, "layer": layer})
                elif item_type == "rectangle" and len(coords) >= 4:
                    x0, y0, x1, y1 = coords[:4]
                    p1 = self._canvas_to_cad(x0, y0)
                    p2 = self._canvas_to_cad(x1, y1)
                    commands.append({"type": "rect", "points": [p1, p2], "layer": layer})
                elif item_type == "oval" and len(coords) >= 4:
                    x0, y0, x1, y1 = coords[:4]
                    cx, cy = self._canvas_to_cad((x0 + x1) / 2, (y0 + y1) / 2)
                    rx = abs(x1 - x0) * self._cad_scale() / 2
                    ry = abs(y1 - y0) * self._cad_scale() / 2
                    commands.append({"type": "ellipse", "center": (cx, cy), "rx": rx, "ry": ry, "layer": layer})
                elif item_type == "polygon" and len(coords) >= 6:
                    points = [self._canvas_to_cad(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]
                    commands.append({"type": "polygon", "points": points, "layer": layer})
                elif item_type == "text" and len(coords) >= 2:
                    x, y = self._canvas_to_cad(coords[0], coords[1])
                    commands.append({
                        "type": "text",
                        "point": (x, y),
                        "text": self._item_option(item, "text") or "",
                        "height": self._text_height(item),
                        "layer": layer,
                    })
        return commands

    def _text_height(self, item):
        font = self._item_option(item, "font")
        match = re.search(r"\b(\d+)\b", str(font))
        return max(1.0, float(match.group(1)) if match else self._safe_float(self.font_size_var.get(), 12))

    def _write_cad_commands_dxf(self, commands, path):
        ezdxf = self._cad_backend()
        if not ezdxf:
            return False
        doc = ezdxf.new(dxfversion="R2010")
        doc.header["$INSUNITS"] = self._cad_units_code()
        for layer in {self._cad_layer_name(cmd.get("layer", "0")) for cmd in commands} | {self._cad_layer_name(layer["name"]) for layer in self.layers}:
            try:
                if layer not in doc.layers:
                    doc.layers.add(layer)
            except Exception:
                pass
        msp = doc.modelspace()
        for cmd in commands:
            layer = self._cad_layer_name(cmd.get("layer", "0"))
            attribs = {"layer": layer}
            kind = cmd.get("type")
            if kind == "line":
                p1, p2 = cmd["points"][:2]
                msp.add_line(p1, p2, dxfattribs=attribs)
            elif kind == "polyline":
                msp.add_lwpolyline(cmd["points"], dxfattribs=attribs)
            elif kind == "polygon":
                msp.add_lwpolyline(cmd["points"], close=True, dxfattribs=attribs)
            elif kind == "rect":
                (x0, y0), (x1, y1) = cmd["points"][:2]
                msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs=attribs)
            elif kind == "circle":
                msp.add_circle(cmd["center"], cmd["radius"], dxfattribs=attribs)
            elif kind == "ellipse":
                rx = max(0.001, float(cmd.get("rx", 1)))
                ry = max(0.001, float(cmd.get("ry", rx)))
                if abs(rx - ry) < 0.001:
                    msp.add_circle(cmd["center"], rx, dxfattribs=attribs)
                else:
                    major = max(rx, ry)
                    minor = min(rx, ry)
                    major_axis = (major if rx >= ry else 0, major if ry > rx else 0)
                    msp.add_ellipse(cmd["center"], major_axis=major_axis, ratio=minor / major, dxfattribs=attribs)
            elif kind == "text":
                text = msp.add_text(str(cmd.get("text", "")), dxfattribs={**attribs, "height": max(1.0, float(cmd.get("height", 12)))})
                text.dxf.insert = cmd.get("point", (0, 0))
        doc.saveas(path)
        return True

    def export_current_page_dxf(self, path=None):
        if path is None:
            path = filedialog.asksaveasfilename(defaultextension=".dxf", filetypes=[("DXF CAD", "*.dxf")], initialfile="DieselPDF-page.dxf")
        if not path:
            return False
        commands = self._entries_to_cad_commands(self._current_entries())
        if not commands:
            self._set_status("No markups to export as DXF")
            return False
        if self._write_cad_commands_dxf(commands, path):
            self._set_status(f"Exported DXF: {os.path.basename(path)}")
            return True
        return False

    def _write_cad_commands_pdf(self, commands, path):
        fitz = self._pdf_renderer()
        if not fitz:
            messagebox.showerror("Text to PDF", "PDF export needs PyMuPDF.")
            return False
        points = []
        for cmd in commands:
            if "points" in cmd:
                points.extend(cmd["points"])
            if "center" in cmd:
                cx, cy = cmd["center"]
                radius = max(cmd.get("radius", 0), cmd.get("rx", 0), cmd.get("ry", 0))
                points.extend([(cx - radius, cy - radius), (cx + radius, cy + radius)])
            if "point" in cmd:
                points.append(cmd["point"])
        if not points:
            return False
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)
        margin = 36
        width = max(300, max_x - min_x + margin * 2)
        height = max(300, max_y - min_y + margin * 2)

        def pt(point):
            x, y = point
            return fitz.Point(margin + x - min_x, margin + max_y - y)

        doc = fitz.open()
        page = doc.new_page(width=width, height=height)
        black = (0, 0, 0)
        for cmd in commands:
            kind = cmd.get("type")
            if kind == "line":
                page.draw_line(pt(cmd["points"][0]), pt(cmd["points"][1]), color=black, width=1)
            elif kind == "polyline":
                pts = [pt(point) for point in cmd["points"]]
                for start, end in zip(pts, pts[1:]):
                    page.draw_line(start, end, color=black, width=1)
            elif kind == "polygon":
                pts = [pt(point) for point in cmd["points"]]
                for start, end in zip(pts, pts[1:] + pts[:1]):
                    page.draw_line(start, end, color=black, width=1)
            elif kind == "rect":
                p0, p1 = pt(cmd["points"][0]), pt(cmd["points"][1])
                page.draw_rect(fitz.Rect(p0, p1), color=black, width=1)
            elif kind == "circle":
                page.draw_circle(pt(cmd["center"]), cmd["radius"], color=black, width=1)
            elif kind == "ellipse":
                cx, cy = cmd["center"]
                rx = cmd.get("rx", 1)
                ry = cmd.get("ry", rx)
                p0 = pt((cx - rx, cy + ry))
                p1 = pt((cx + rx, cy - ry))
                page.draw_oval(fitz.Rect(p0, p1), color=black, width=1)
            elif kind == "text":
                page.insert_text(pt(cmd.get("point", (0, 0))), str(cmd.get("text", "")), fontsize=max(6, float(cmd.get("height", 12))), color=black)
        doc.save(path)
        doc.close()
        return True

    def export_current_page_pdf(self, path=None):
        if path is None:
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="DieselPDF-page.pdf")
        if not path:
            return False
        commands = self._entries_to_cad_commands(self._current_entries())
        if not commands:
            self._set_status("No markups to export as PDF")
            return False
        if self._write_cad_commands_pdf(commands, path):
            self._set_status(f"Exported PDF: {os.path.basename(path)}")
            return True
        return False

    def cad_to_text(self, cad_path=None, text_path=None):
        ezdxf = self._cad_backend()
        if not ezdxf:
            return False
        if cad_path is None:
            cad_path = filedialog.askopenfilename(filetypes=[("DXF CAD", "*.dxf"), ("All files", "*.*")])
        if not cad_path:
            return False
        try:
            doc = ezdxf.readfile(cad_path)
            lines = self._dxf_to_text_lines(doc, cad_path)
        except Exception as exc:
            messagebox.showerror("CAD to Text", str(exc))
            return False
        if text_path is None:
            base = os.path.splitext(os.path.basename(cad_path))[0] + ".txt"
            text_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")], initialfile=base)
        if not text_path:
            return False
        with open(text_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        self._set_status(f"CAD text exported: {os.path.basename(text_path)}")
        return True

    def _dxf_to_text_lines(self, doc, source_path):
        lines = [f"CAD TEXT REPORT: {os.path.basename(source_path)}", f"Units: {doc.header.get('$INSUNITS', 'not set')}", ""]
        counts = {}
        for entity in doc.modelspace():
            kind = entity.dxftype()
            counts[kind] = counts.get(kind, 0) + 1
            layer = getattr(entity.dxf, "layer", "0")
            try:
                if kind == "LINE":
                    lines.append(f"LINE layer={layer} start={tuple(entity.dxf.start)} end={tuple(entity.dxf.end)}")
                elif kind == "LWPOLYLINE":
                    pts = [(round(p[0], 4), round(p[1], 4)) for p in entity.get_points("xy")]
                    lines.append(f"LWPOLYLINE layer={layer} points={pts}")
                elif kind == "CIRCLE":
                    lines.append(f"CIRCLE layer={layer} center={tuple(entity.dxf.center)} radius={entity.dxf.radius}")
                elif kind == "ARC":
                    lines.append(f"ARC layer={layer} center={tuple(entity.dxf.center)} radius={entity.dxf.radius} start={entity.dxf.start_angle} end={entity.dxf.end_angle}")
                elif kind == "TEXT":
                    lines.append(f"TEXT layer={layer} at={tuple(entity.dxf.insert)} text={entity.dxf.text}")
                elif kind == "MTEXT":
                    lines.append(f"MTEXT layer={layer} at={tuple(entity.dxf.insert)} text={entity.plain_text()}")
                elif kind == "INSERT":
                    lines.append(f"INSERT layer={layer} block={entity.dxf.name} at={tuple(entity.dxf.insert)}")
                else:
                    lines.append(f"{kind} layer={layer}")
            except Exception:
                lines.append(f"{kind} layer={layer}")
        lines.insert(2, "Entity counts: " + ", ".join(f"{name}={count}" for name, count in sorted(counts.items())))
        return lines

    def text_to_cad_pdf(self, text_path=None, dxf_path=None, pdf_path=None):
        if text_path is None:
            text_path = filedialog.askopenfilename(filetypes=[("Text CAD script", "*.txt"), ("All files", "*.*")])
        if not text_path:
            return False
        try:
            with open(text_path, "r", encoding="utf-8") as handle:
                commands = self._parse_cad_text(handle.read())
        except OSError as exc:
            messagebox.showerror("Text to CAD", str(exc))
            return False
        if not commands:
            self._set_status("No CAD commands found in text file")
            return False
        if dxf_path is None:
            base = os.path.splitext(os.path.basename(text_path))[0] + ".dxf"
            dxf_path = filedialog.asksaveasfilename(defaultextension=".dxf", filetypes=[("DXF CAD", "*.dxf")], initialfile=base)
        wrote_dxf = False
        if dxf_path:
            wrote_dxf = self._write_cad_commands_dxf(commands, dxf_path)
        if pdf_path is None and messagebox.askyesno("Text to CAD/PDF", "Also create a PDF preview from this text CAD script?"):
            base = os.path.splitext(os.path.basename(text_path))[0] + ".pdf"
            pdf_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile=base)
        wrote_pdf = False
        if pdf_path:
            wrote_pdf = self._write_cad_commands_pdf(commands, pdf_path)
        self._draw_cad_commands_on_canvas(commands)
        self._set_status(f"Text CAD imported: {len(commands)} command(s), DXF={wrote_dxf}, PDF={wrote_pdf}")
        return wrote_dxf or wrote_pdf

    def _parse_cad_text(self, text):
        commands = []
        layer = self.current_layer or "0"
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].split(";", 1)[0].strip()
            if not line:
                continue
            try:
                tokens = shlex.split(line)
            except ValueError:
                tokens = line.split()
            if not tokens:
                continue
            op = tokens[0].lower()
            if op in {"layer", "-layer"} and len(tokens) >= 2:
                layer = self._cad_layer_name(" ".join(tokens[1:]))
                continue
            nums = []
            for token in tokens[1:]:
                try:
                    nums.append(float(token))
                except ValueError:
                    pass
            if op in {"line", "l"} and len(nums) >= 4:
                commands.append({"type": "line", "points": [(nums[0], nums[1]), (nums[2], nums[3])], "layer": layer})
            elif op in {"rect", "rectangle", "rec"} and len(nums) >= 4:
                commands.append({"type": "rect", "points": [(nums[0], nums[1]), (nums[2], nums[3])], "layer": layer})
            elif op in {"circle", "c"} and len(nums) >= 3:
                commands.append({"type": "circle", "center": (nums[0], nums[1]), "radius": abs(nums[2]), "layer": layer})
            elif op in {"polyline", "pline", "pl"} and len(nums) >= 4:
                pts = [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
                commands.append({"type": "polyline", "points": pts, "layer": layer})
            elif op in {"polygon", "pg"} and len(nums) >= 6:
                pts = [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
                commands.append({"type": "polygon", "points": pts, "layer": layer})
            elif op in {"text", "t"} and len(tokens) >= 4:
                try:
                    x, y = float(tokens[1]), float(tokens[2])
                except ValueError:
                    continue
                commands.append({"type": "text", "point": (x, y), "text": " ".join(tokens[3:]), "height": 12, "layer": layer})
        return commands

    def _draw_cad_commands_on_canvas(self, commands):
        created = []
        for cmd in commands:
            kind = cmd.get("type")
            if kind == "line":
                p0 = self._cad_to_canvas(*cmd["points"][0])
                p1 = self._cad_to_canvas(*cmd["points"][1])
                self.create_shape("line", p0[0], p0[1], p1[0], p1[1])
                created.append(self._current_entries()[-1])
            elif kind == "rect":
                p0 = self._cad_to_canvas(*cmd["points"][0])
                p1 = self._cad_to_canvas(*cmd["points"][1])
                self.create_shape("rectangle", p0[0], p0[1], p1[0], p1[1])
                created.append(self._current_entries()[-1])
            elif kind == "circle":
                cx, cy = self._cad_to_canvas(*cmd["center"])
                radius = cmd["radius"] / (self._cad_scale() or 1.0)
                self.create_shape("circle", cx - radius, cy - radius, cx + radius, cy + radius)
                created.append(self._current_entries()[-1])
            elif kind in {"polyline", "polygon"}:
                coords = []
                for point in cmd["points"]:
                    coords.extend(self._cad_to_canvas(*point))
                if kind == "polyline":
                    self._create_polyline_from_coords(coords)
                else:
                    self._create_polygon_from_coords(coords)
                created.append(self._current_entries()[-1])
            elif kind == "text":
                x, y = self._cad_to_canvas(*cmd["point"])
                style = self._style()
                item = self.canvas.create_text(x, y, text=cmd.get("text", ""), anchor="nw", fill=style["line_color"], font=(style["font_family"], style["font_size"]))
                self._record_entry("Text", cmd.get("text", ""), [item])
                created.append(self._current_entries()[-1])
        if created:
            self.clear_selection()
            self.selected_entries = created
            self.draw_selection()

    def pdf_to_cad(self, pdf_path=None, dxf_path=None):
        if pdf_path is None:
            pdf_path = self.current_pdf if self.current_pdf and os.path.exists(self.current_pdf) else None
        if pdf_path is None:
            pdf_path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf"), ("All files", "*.*")])
        if not pdf_path:
            return False
        if dxf_path is None:
            base = os.path.splitext(os.path.basename(pdf_path))[0] + ".dxf"
            dxf_path = filedialog.asksaveasfilename(defaultextension=".dxf", filetypes=[("DXF CAD", "*.dxf")], initialfile=base)
        if not dxf_path:
            return False
        commands = self._extract_pdf_cad_commands(pdf_path)
        if not commands:
            self._set_status("No vector/text PDF content found for CAD export")
            return False
        if self._write_cad_commands_dxf(commands, dxf_path):
            self._set_status(f"PDF to CAD exported {len(commands)} entities: {os.path.basename(dxf_path)}")
            return True
        return False

    def _extract_pdf_cad_commands(self, pdf_path):
        fitz = self._pdf_renderer()
        if not fitz:
            messagebox.showerror("PDF to CAD", "PDF to CAD needs PyMuPDF.")
            return []
        commands = []
        try:
            doc = fitz.open(pdf_path)
        except Exception as exc:
            messagebox.showerror("PDF to CAD", str(exc))
            return []
        y_offset = 0
        for page_index, page in enumerate(doc):
            height = float(page.rect.height)
            layer = f"PDF_PAGE_{page_index + 1}"
            try:
                drawings = page.get_drawings()
            except Exception:
                drawings = []
            for drawing in drawings:
                for item in drawing.get("items", []):
                    op = item[0]
                    if op == "l":
                        p1, p2 = item[1], item[2]
                        commands.append({"type": "line", "points": [(p1.x, y_offset + height - p1.y), (p2.x, y_offset + height - p2.y)], "layer": layer})
                    elif op == "re":
                        rect = item[1]
                        commands.append({"type": "rect", "points": [(rect.x0, y_offset + height - rect.y0), (rect.x1, y_offset + height - rect.y1)], "layer": layer})
                    elif op == "c":
                        pts = [(point.x, y_offset + height - point.y) for point in item[1:]]
                        if len(pts) >= 2:
                            commands.append({"type": "polyline", "points": pts, "layer": layer})
            try:
                text_dict = page.get_text("dict")
            except Exception:
                text_dict = {"blocks": []}
            for block in text_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        value = span.get("text", "").strip()
                        if not value:
                            continue
                        bbox = span.get("bbox", [0, 0, 0, 0])
                        commands.append({"type": "text", "point": (bbox[0], y_offset + height - bbox[1]), "text": value, "height": max(4, span.get("size", 10)), "layer": layer})
            y_offset += height + 80
        doc.close()
        return commands

    def print_document(self):
        paper = self.choose_paper_size("Print")
        if not paper:
            return
        path = filedialog.asksaveasfilename(defaultextension=".ps", filetypes=[("PostScript", "*.ps")], initialfile=f"DieselPDF-{paper}.ps")
        if not path:
            return
        self.canvas.postscript(file=path, colormode="color")
        self._set_status(f"Print snapshot saved for {paper}: {os.path.basename(path)}")


if __name__ == "__main__":
    DieselPDF().mainloop()
