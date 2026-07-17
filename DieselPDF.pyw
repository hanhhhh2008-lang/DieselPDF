import copy
import csv
import ctypes
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
PDF_VENDOR_DIR = os.path.join(APP_DIR, "vendor_pymupdf")
CAD_VENDOR_DIR = os.path.join(APP_DIR, "vendor_cad_py311")
for dependency_dir in [CAD_VENDOR_DIR, PDF_VENDOR_DIR]:
    if os.path.isdir(dependency_dir) and dependency_dir not in sys.path:
        sys.path.insert(0, dependency_dir)
LIBRARY_PATH = os.path.join(APP_DIR, "dieselpdf-library.json")
PAGE_ORIGIN = (60, 46)
DEFAULT_MM_PER_BASE_PX = 1.0 / 3.0

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
    "Snapshot": "\u2317",
    "Duplicate": "\u29c9",
    "Merge": "\u2a01",
    "Split": "\u2702",
    "Replace": "\u21c4",
    "Swap": "\u21c5",
    "Overlay": "\u25a7",
    "Crop": "\u230c",
    "Resize": "\u2922",
    "Watermark": "\u25c8",
    "Image": "\u25a7",
    "Recompress": "\u21e3",
    "Word": "W",
    "Excel": "X",
    "PowerPoint": "P",
    "Prev": "\u2039",
    "Next": "\u203a",
}

DEFAULT_TOOL_SETS = [
    ("Recent Tools", "Recently used", "recent"),
    ("General", "Straight Line", "line"),
    ("General", "Arrow", "arrow"),
    ("General", "Rectangle", "rectangle"),
    ("General", "Circle", "circle"),
    ("General", "Revision Cloud", "cloud"),
    ("General", "Callout", "callout"),
    ("Review", "Approved Stamp", "approved_stamp"),
    ("Review", "Review Required", "review_stamp"),
    ("Review", "Check Mark", "check_mark"),
    ("Review", "Revision Delta", "revision_delta"),
    ("Takeoff", "Distance Sample", "distance_sample"),
    ("Takeoff", "Area Takeoff", "area_box"),
    ("Takeoff", "Count Marker", "count_marker"),
    ("Takeoff", "Scale Bar", "scale_bar"),
    ("Construction", "North Arrow", "north_arrow"),
    ("Construction", "Door Opening", "door_opening"),
    ("Safety", "Warning", "warning"),
    ("Safety", "Fire Point", "fire_point"),
]


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
            "chrome": "#eef1f5",
            "ribbon": "#f8fafc",
            "active": "#e0efff",
            "blue": "#0a67c7",
            "red": "#d94c4c",
            "green": "#268c67",
            "yellow": "#e6a23c",
            "page": "#ffffff",
            "work": "#dfe4ea",
            "text": "#17202a",
            "muted": "#66717f",
            "border": "#cbd2da",
            "card": "#ffffff",
            "sidebar": "#f6f8fa",
            "status": "#edf1f5",
        }

        self.font_title = ("Segoe UI", 19, "bold")
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
        self.snapshot_images = []
        self.pdf_text_selection = []
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
        self.inline_editor = None
        self.inline_window_item = None
        self.inline_edit_data = None
        self.zoom_level = 1.0
        self.rotation = 0
        self.scale_units_per_px = DEFAULT_MM_PER_BASE_PX
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
        self.opacity_var = tk.StringVar(value="100")
        self.object_scale_var = tk.StringVar(value="100")
        self.object_rotation_var = tk.StringVar(value="0")
        self.blend_var = tk.StringVar(value="Normal")
        self.font_family_var = tk.StringVar(value="Arial")
        self.font_size_var = tk.StringVar(value="12")
        self.start_arrow_var = tk.StringVar(value="None")
        self.end_arrow_var = tk.StringVar(value="Closed Arrow")
        self.precision_var = tk.StringVar(value="0.01")
        self.paper_var = tk.StringVar(value="A4")
        self.scale_label_var = tk.StringVar(value="1 px = 0.3333 mm")
        self.unit_var = tk.StringVar(value="mm")
        self.layer_var = tk.StringVar(value="0")
        self.command_var = tk.StringVar()
        self.page_jump_var = tk.StringVar(value="1")
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
            "zoom_level": self.zoom_level,
        }]
        self.doc_buttons = {}
        self.active_tab = "Home"
        self.tab_buttons = {}
        self.recent_tools = []
        self.library_catalog = {}

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
        self.quickbar = tk.Frame(self, bg=self.colors["chrome"], height=66, highlightthickness=0)
        self.quickbar.grid(row=0, column=0, sticky="ew")
        self.quickbar.grid_propagate(False)

        brand = tk.Frame(self.quickbar, bg=self.colors["chrome"])
        brand.pack(side="left", padx=(16, 24), pady=8)
        tk.Label(brand, image=self.app_icon, bg=self.colors["chrome"], width=34, height=34).pack(side="left", padx=(0, 9))
        brand_text = tk.Frame(brand, bg=self.colors["chrome"])
        brand_text.pack(side="left")
        tk.Label(brand_text, text=APP_TITLE, bg=self.colors["chrome"], fg=self.colors["text"], font=self.font_title).pack(anchor="w")
        tk.Label(
            brand_text,
            text="Review  |  Markup  |  Measure  |  Takeoff",
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
            width=max(7, min(12, len(text) + 1)),
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
            highlightbackground="#d8dee6",
        )
        button.pack(side="left", padx=3, pady=6)
        button.bind("<Enter>", lambda _event, label=text: self._set_status(label))
        button.bind("<Enter>", lambda _event, widget=button, label=text: (widget.configure(bg=self.colors["active"]), self._set_status(label)))
        button.bind("<Leave>", lambda _event, widget=button: widget.configure(bg=self.colors["card"]))

    def _icon_for(self, text):
        if text in ICON:
            return ICON[text]
        if "90" in text:
            return "R90"
        return text[:3].upper()

    def _button_text(self, text):
        return f"{self._icon_for(text)}\n{text}"

    def _build_tabs(self):
        self.tabs = tk.Frame(self, bg=self.colors["chrome"], height=40, highlightthickness=1, highlightbackground=self.colors["border"])
        self.tabs.grid(row=1, column=0, sticky="ew")
        self.tabs.grid_propagate(False)
        tk.Frame(self.tabs, bg=self.colors["chrome"], width=14).pack(side="left")
        file_button = tk.Button(
            self.tabs, text="File", bd=0, padx=18, pady=6, bg="#bf3b3b", fg="white",
            activebackground="#a73030", activeforeground="white", font=self.font_body,
            command=self.show_file_menu,
        )
        file_button.pack(side="left", padx=(0, 4), pady=4)
        self.file_button = file_button
        for name in ["Home", "Markup", "Measure", "Properties", "Organize", "Convert", "Studio", "OCR", "Help"]:
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
            self.tab_buttons[name] = btn
            btn.bind("<Enter>", lambda _event, widget=btn, tab=name: widget.configure(fg=self.colors["blue"]) if tab != self.active_tab else None)
            btn.bind("<Leave>", lambda _event, widget=btn, tab=name: widget.configure(fg=self.colors["muted"]) if tab != self.active_tab else None)

    def show_file_menu(self):
        menu = tk.Menu(self, tearoff=False, font=self.font_body)
        menu.add_command(label="New Window", command=self.new_project)
        menu.add_command(label="New Document Tab", command=self.create_document_tab)
        menu.add_separator()
        menu.add_command(label="Open Project...", command=self.open_project)
        menu.add_command(label="Open PDF...", command=self.open_pdf)
        menu.add_separator()
        menu.add_command(label="Save", command=self.save_project)
        menu.add_command(label="Save As...", command=self.save_project_as)
        menu.add_command(label="Export Flattened PDF...", command=self.export_current_page_pdf)
        menu.add_separator()
        menu.add_command(label="Print...", command=self.print_document)
        menu.add_separator()
        menu.add_command(label="Close", command=self.destroy)
        menu.tk_popup(self.file_button.winfo_rootx(), self.file_button.winfo_rooty() + self.file_button.winfo_height())

    def _select_tab(self, name):
        self.active_tab = name
        for tab_name, child in self.tab_buttons.items():
            child.configure(
                bg=self.colors["card"] if tab_name == name else self.colors["chrome"],
                fg=self.colors["blue"] if tab_name == name else self.colors["muted"],
            )
        self._populate_ribbon(name)
        self._set_status(f"{name} tab selected")

    def _bind_shortcuts(self):
        self.bind("<KeyPress-l>", lambda _event: self._shortcut_tool("line"))
        self.bind("<KeyPress-L>", lambda _event: self._shortcut_tool("line"))
        self.bind("<KeyPress-c>", lambda _event: self._shortcut_tool("circle"))
        self.bind("<KeyPress-C>", lambda _event: self._shortcut_tool("circle"))
        self.bind("<KeyPress-r>", lambda _event: self._shortcut_tool("rectangle"))
        self.bind("<KeyPress-R>", lambda _event: self._shortcut_tool("rectangle"))
        self.bind("<KeyPress-p>", lambda _event: self._shortcut_tool("polyline"))
        self.bind("<KeyPress-P>", lambda _event: self._shortcut_tool("polyline"))
        self.bind("<KeyPress-t>", lambda _event: self._shortcut_tool("text_box"))
        self.bind("<KeyPress-T>", lambda _event: self._shortcut_tool("text_box"))
        self.bind("<KeyPress-a>", lambda _event: self._shortcut_tool("arrow"))
        self.bind("<KeyPress-A>", lambda _event: self._shortcut_tool("arrow"))
        self.bind("<KeyPress-h>", lambda _event: self._shortcut_tool("hand"))
        self.bind("<KeyPress-s>", lambda _event: self._shortcut_tool("select"))
        self.bind("<Control-z>", lambda _event: self.undo())
        self.bind("<Control-y>", lambda _event: self.redo())
        self.bind("<Control-p>", lambda _event: self.print_document())
        self.bind("<Prior>", lambda _event: self.previous_page())
        self.bind("<Next>", lambda _event: self.next_page())
        self.bind("<Delete>", lambda _event: self.delete_selected() if self.selected_entries else None)
        self.bind("<Escape>", lambda _event: self._escape_current())

    def _shortcut_tool(self, tool):
        focus = self.focus_get()
        if isinstance(focus, (tk.Entry, tk.Text, ttk.Combobox, ttk.Spinbox)):
            return
        self._set_tool(tool)

    def _escape_current(self):
        if self.inline_editor is not None:
            self.cancel_inline_text()
            return
        self._clear_pending()
        self.drag = None
        self.hide_crosshair()
        self._select_tab("Markup")
        self._set_tool("select")

    def _build_ribbon(self):
        self.ribbon = tk.Frame(self, bg=self.colors["ribbon"], height=142, bd=0, highlightthickness=1, highlightbackground=self.colors["border"])
        self.ribbon.grid(row=2, column=0, sticky="ew")
        self.ribbon.grid_propagate(False)
        self._populate_ribbon("Home")

    def _populate_ribbon(self, tab):
        if not hasattr(self, "ribbon"):
            return
        for child in self.ribbon.winfo_children():
            child.destroy()
        self.tool_buttons = {}
        if tab == "Home":
            files = self._group("Document")
            self._cmd_button(files, "Open PDF", self.open_pdf)
            self._cmd_button(files, "Save", self.save_project)
            self._cmd_button(files, "Print", self.print_document)
            review = self._group("Review")
            self._tool_button(review, "Hand", "hand")
            self._tool_button(review, "Select", "select")
            self._tool_button(review, "Select Text", "select_text", wide=True)
            self._tool_button(review, "Snapshot", "snapshot")
            view = self._group("View")
            self._cmd_button(view, "Zoom -", self.zoom_out)
            self._cmd_button(view, "Zoom +", self.zoom_in)
            self._cmd_button(view, "Rotate Left", lambda: self.rotate_page(-90))
            self._cmd_button(view, "Rotate Right", lambda: self.rotate_page(90))
        elif tab == "Markup":
            draw = self._group("Draw")
            for label, tool in [("Line", "line"), ("Circle", "circle"), ("Cloud", "cloud"), ("Arrow", "arrow"), ("Polyline", "polyline"), ("Rectangle", "rectangle"), ("Polygon", "polygon"), ("Pencil", "pencil"), ("Eraser", "eraser")]:
                self._tool_button(draw, label, tool)
            text = self._group("Text")
            self._tool_button(text, "Text Box", "text_box")
            self._tool_button(text, "Callout", "callout")
            edit = self._group("Edit")
            for label, command in [("Group", self.group_selected), ("Ungroup", self.ungroup_selected), ("Flatten", self.flatten_selected), ("Library", self.save_group_library), ("Delete", self.delete_selected)]:
                self._cmd_button(edit, label, command)
        elif tab == "Measure":
            measure = self._group("Takeoff")
            for label, tool in [("Calibrate", "calibrate"), ("Distance", "distance"), ("Perimeter", "perimeter"), ("Area", "area")]:
                self._tool_button(measure, label, tool)
            self._cmd_button(measure, "Set Scale", self.manual_scale)
        elif tab == "Properties":
            edit = self._group("Selection")
            for label, command in [("Move", self.move_selected), ("Copy", self.copy_selected), ("Offset", self.offset_selected), ("Rotate Left", lambda: self.rotate_selected(-90)), ("Rotate Right", lambda: self.rotate_selected(90)), ("Delete", self.delete_selected)]:
                self._cmd_button(edit, label, command)
        elif tab == "Organize":
            pages = self._group("Pages")
            for label, command in [("Insert", self.insert_page), ("Delete", self.delete_page), ("Extract", self.extract_page), ("Duplicate", self.duplicate_page), ("Merge", self.merge_pdf), ("Split", self.split_pdf), ("Replace", self.replace_page), ("Swap", self.swap_pages)]:
                self._cmd_button(pages, label, command)
            transform = self._group("Transform")
            for label, command in [("Overlay", self.overlay_pdf), ("Rotate Left", lambda: self.rotate_page(-90)), ("Rotate Right", lambda: self.rotate_page(90)), ("Crop", self.crop_page), ("Resize", self.resize_page), ("Watermark", self.add_watermark)]:
                self._cmd_button(transform, label, command)
        elif tab == "Convert":
            create = self._group("Create")
            self._cmd_button(create, "Image", self.import_image_page)
            self._cmd_button(create, "Recompress", self.recompress_pdf)
            cad = self._group("CAD Exchange")
            for label, command in [("CAD to Text", self.cad_to_text), ("Text to CAD", self.show_text_to_cad_editor), ("PDF to CAD", self.pdf_to_cad), ("Export DXF", self.export_current_page_dxf)]:
                self._cmd_button(cad, label, command)
            office = self._group("Export")
            for label, command in [("Image", self.export_pages_to_images), ("Word", lambda: self.export_office_text("Word")), ("Excel", lambda: self.export_office_text("Excel")), ("PowerPoint", lambda: self.export_office_text("PowerPoint"))]:
                self._cmd_button(office, label, command)
        elif tab == "Studio":
            studio = self._group("Collaboration")
            self._cmd_button(studio, "Library", self.save_group_library)
            self._cmd_button(studio, "Save", self.save_project)
        elif tab == "OCR":
            ocr = self._group("Text Recognition")
            self._cmd_button(ocr, "Select Text", lambda: self._set_tool("select_text"))
            self._cmd_button(ocr, "PDF to CAD", self.pdf_to_cad)
        else:
            help_group = self._group("Help")
            self._cmd_button(help_group, "CAD to Text", self._command_help)
        active_button = self.tool_buttons.get(self.current_tool)
        if active_button:
            active_button.configure(bg=self.colors["active"], fg=self.colors["blue"], highlightbackground="#9bc7f5")

    def _group(self, label):
        group = tk.Frame(
            self.ribbon,
            bg=self.colors["ribbon"],
            bd=0,
            padx=6,
            pady=5,
            highlightthickness=0,
        )
        group.pack(side="left", fill="y", padx=(6, 1), pady=8)
        body = tk.Frame(group, bg=self.colors["ribbon"])
        body.pack(side="top", fill="both", expand=True)
        tk.Label(group, text=label.upper(), bg=self.colors["ribbon"], fg=self.colors["muted"], font=self.font_small).pack(side="bottom", pady=(4, 0))
        tk.Frame(self.ribbon, width=1, bg=self.colors["border"]).pack(side="left", fill="y", pady=18)
        return body

    def _tool_button(self, parent, text, tool, wide=False):
        btn = tk.Button(
            parent,
            text=self._button_text(text),
            width=max(9 if wide else 8, min(12, len(text) + 1)),
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
        btn.bind("<Enter>", lambda _event, widget=btn, label=text, mode=tool: (widget.configure(bg=self.colors["active"]), self._set_status(label)) if self.current_tool != mode else self._set_status(label))
        btn.bind("<Leave>", lambda _event, widget=btn, mode=tool: widget.configure(bg=self.colors["chrome"]) if self.current_tool != mode else None)
        self.tool_buttons[tool] = btn
        return btn

    def _cmd_button(self, parent, text, command):
        button = tk.Button(
            parent,
            text=self._button_text(text),
            width=max(8, min(12, len(text) + 1)),
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
        button.bind("<Enter>", lambda _event, widget=button, label=text: (widget.configure(bg=self.colors["active"]), self._set_status(label)))
        button.bind("<Leave>", lambda _event, widget=button: widget.configure(bg=self.colors["chrome"]))

    def _build_doc_strip(self):
        self.doc_tabs = tk.Frame(self, bg=self.colors["chrome"], height=44, highlightthickness=0)
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
            "zoom_level": self.zoom_level,
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
            "scale_units_per_px": DEFAULT_MM_PER_BASE_PX,
            "scale_unit": "mm",
            "scale_label": "1 px = 0.3333 mm",
            "unit": "mm",
            "layers": [{"name": "0", "visible": True, "locked": False}],
            "current_layer": "0",
            "bookmarks": [],
            "undo_stack": [],
            "redo_stack": [],
            "rotation": 0,
            "zoom_level": 1.0,
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
        self.scale_units_per_px = doc.get("scale_units_per_px") or DEFAULT_MM_PER_BASE_PX
        self.scale_unit = doc.get("scale_unit", "mm")
        self.scale_label_var.set(doc.get("scale_label", "1 px = 0.3333 mm"))
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
        self.zoom_level = max(0.4, min(2.5, float(doc.get("zoom_level", 1.0))))
        if hasattr(self, "zoom_label"):
            self.zoom_label.configure(text=f"{int(self.zoom_level * 100)}%")
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
        tk.Label(sidebar, text="Tool Chest", bg=self.colors["sidebar"], fg=self.colors["text"], font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", padx=16, pady=(16, 0))
        tk.Label(sidebar, text="reusable markups, measurements, and saved tools", bg=self.colors["sidebar"], fg=self.colors["muted"], font=self.font_small, anchor="w").pack(fill="x", padx=16, pady=(0, 12))

        self.notebook = ttk.Notebook(sidebar)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.bookmark_frame = tk.Frame(self.notebook, bg=self.colors["card"])
        self.markup_frame = tk.Frame(self.notebook, bg=self.colors["card"])
        self.page_frame = tk.Frame(self.notebook, bg=self.colors["card"])
        self.layer_frame = tk.Frame(self.notebook, bg=self.colors["card"])
        self.library_frame = tk.Frame(self.notebook, bg=self.colors["card"])
        self.notebook.add(self.library_frame, text="Library")
        self.notebook.add(self.bookmark_frame, text="Bookmarks")
        self.notebook.add(self.markup_frame, text="Markups")
        self.notebook.add(self.page_frame, text="Pages")
        self.notebook.add(self.layer_frame, text="Layers")

        self.bookmark_list = self._listbox(self.bookmark_frame)
        self.bookmark_list.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Button(self.bookmark_frame, text="Add Bookmark", command=self.add_bookmark, **self._button_style()).pack(fill="x", padx=10, pady=(0, 10))

        columns = ("type", "page", "layer", "detail")
        self.markup_list = ttk.Treeview(self.markup_frame, columns=columns, show="headings", height=12)
        self.markup_list.heading("type", text="Subject")
        self.markup_list.heading("page", text="Page")
        self.markup_list.heading("layer", text="Layer")
        self.markup_list.heading("detail", text="Detail")
        self.markup_list.column("type", width=88, minwidth=70)
        self.markup_list.column("page", width=42, minwidth=38, anchor="center")
        self.markup_list.column("layer", width=60, minwidth=45)
        self.markup_list.column("detail", width=150, minwidth=90)
        self.markup_list.pack(fill="both", expand=True, padx=10, pady=(10, 6))
        self.markup_list.bind("<<TreeviewSelect>>", self._markup_selected)
        tk.Button(self.markup_frame, text="Export Markups List", command=self.export_markups_csv, **self._button_style()).pack(fill="x", padx=10, pady=(0, 10))

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

        self.library_list = ttk.Treeview(self.library_frame, columns=("description",), show="tree", selectmode="browse")
        self.library_list.column("#0", width=225, minwidth=150)
        self.library_list.pack(fill="both", expand=True, padx=10, pady=(10, 6))
        self.library_list.bind("<Double-Button-1>", self._library_activate)
        self.library_list.bind("<Return>", self._library_activate)
        library_buttons = tk.Frame(self.library_frame, bg=self.colors["card"])
        library_buttons.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(library_buttons, text="Insert Tool", command=self.insert_library_tool, **self._button_style()).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(library_buttons, text="Refresh", command=self.refresh_library, **self._flat_button()).pack(side="left")

        self.main.add(sidebar, width=270)
        self._refresh_layer_list()
        self.refresh_library()
        self.notebook.select(self.library_frame)

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
        self.canvas.bind("<Control-MouseWheel>", self.on_ctrl_mousewheel)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)

        self.main.add(area, stretch="always")
        self._refresh_page_list()
        self._update_page_surface()

    def _build_properties(self):
        panel = tk.Frame(self.main, bg=self.colors["sidebar"], width=330)
        self.properties_panel = panel
        panel.pack_propagate(False)
        heading = tk.Frame(panel, bg=self.colors["sidebar"])
        heading.pack(fill="x", padx=12, pady=(12, 7))
        tk.Label(heading, text="Properties", bg=self.colors["sidebar"], fg=self.colors["text"], font=("Segoe UI", 14, "bold"), anchor="w").pack(side="left")
        tk.Label(heading, text="LIVE", bg="#e4f3ed", fg=self.colors["green"], font=("Segoe UI", 7, "bold"), padx=6, pady=2).pack(side="right")
        property_shell = tk.Frame(panel, bg=self.colors["card"], highlightthickness=1, highlightbackground=self.colors["border"])
        property_shell.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.property_canvas = tk.Canvas(property_shell, bg=self.colors["card"], highlightthickness=0, bd=0)
        property_scroll = ttk.Scrollbar(property_shell, orient="vertical", command=self.property_canvas.yview)
        self.property_canvas.configure(yscrollcommand=property_scroll.set)
        self.property_canvas.pack(side="left", fill="both", expand=True)
        property_scroll.pack(side="right", fill="y")
        self.properties = tk.Frame(self.property_canvas, bg=self.colors["card"])
        self.property_window = self.property_canvas.create_window(0, 0, anchor="nw", window=self.properties)
        self.properties.bind("<Configure>", lambda _event: self.property_canvas.configure(scrollregion=self.property_canvas.bbox("all")))
        self.property_canvas.bind("<Configure>", lambda event: self.property_canvas.itemconfigure(self.property_window, width=event.width))

        self._section("General", [("Keep Selected", "True"), ("Exclusive Mode", "False")])
        self._section("Subject", [("Subject Kind", "Default"), ("Subject", "Dimension Line")])
        self._style_section()
        self._measure_section()
        self._section("Line Endings", [("Start", self.start_arrow_var), ("End", self.end_arrow_var), ("Start Scale", "Auto"), ("End Scale", "Auto")])
        self._section("Leader", [("Leader Length", "5.3 mm"), ("Leader Extension", "1.8 mm"), ("Leader Offset", "0 mm")])
        self._section("Caption", [("Show Caption", "Yes"), ("Inline Caption", "Yes")])
        self._section("Layer", [("Current Layer", self.layer_var)])
        self._update_color_buttons()
        self._bind_property_mousewheel(panel)

        self.main.add(panel, minsize=310, width=330, stretch="never")

    def _bind_property_mousewheel(self, widget):
        widget.bind("<MouseWheel>", self._property_mousewheel, add="+")
        for child in widget.winfo_children():
            self._bind_property_mousewheel(child)

    def _property_mousewheel(self, event):
        units = -1 if event.delta > 0 else 1
        self.property_canvas.yview_scroll(units * 3, "units")
        return "break"

    def _section(self, title, rows):
        tk.Label(self.properties, text=title, bg="#e9edf2", fg=self.colors["text"], anchor="w", padx=7, pady=4, font=self.font_heading).pack(fill="x", pady=(0, 1))
        for label, value in rows:
            self._property_row(label, value)

    def _style_section(self):
        tk.Label(self.properties, text="Style", bg="#e9edf2", fg=self.colors["text"], anchor="w", padx=7, pady=4, font=self.font_heading).pack(fill="x", pady=(0, 1))
        self._color_row("Fill Color", self.fill_color_var, self.choose_fill_color)
        self._color_row("Stroke Color", self.line_color_var, self.choose_line_color)
        self._option_row("Border", self.line_type_var, ["Solid", "Dashed", "Dotted"])
        self._spin_row("Line Thickness", self.width_var, 0.5, 50, 0.5)
        self._spin_row("Opacity", self.opacity_var, 0, 100, 5, suffix="%")
        self._spin_row("Scale", self.object_scale_var, 1, 1000, 5, suffix="%")
        self._spin_row("Rotation", self.object_rotation_var, -360, 360, 5, suffix=" deg")
        self._option_row("Blend Mode", self.blend_var, ["Normal", "Multiply", "Screen"])
        self._option_row("Font", self.font_family_var, ["Arial", "Calibri"])
        self._spin_row("Font Size", self.font_size_var, 4, 144, 1)
        tk.Button(self.properties, text="Apply to Selected", command=self.apply_style_to_selected, **self._flat_button()).pack(fill="x", padx=8, pady=5)

    def _measure_section(self):
        tk.Label(self.properties, text="Measure", bg="#e9edf2", fg=self.colors["text"], anchor="w", padx=7, pady=4, font=self.font_heading).pack(fill="x", pady=(0, 1))
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
        button = tk.Button(row, textvariable=var, command=command, bg=self.colors["card"], relief="flat", bd=0, font=self.font_body, anchor="w")
        button.pack(side="left", fill="x", expand=True)
        if var is self.fill_color_var:
            tk.Button(row, text="x", command=self.clear_fill_color, bg=self.colors["card"], fg=self.colors["muted"], relief="flat", bd=0, width=2, font=self.font_body).pack(side="right")
            self.fill_color_button = button
        else:
            self.line_color_button = button

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
        else:
            menu.bind("<<ComboboxSelected>>", lambda _event: self.apply_style_to_selected())

    def _entry_row(self, label, var):
        row = tk.Frame(self.properties, bg=self.colors["card"], height=25)
        row.pack(fill="x")
        tk.Label(row, text=label, bg=self.colors["card"], fg=self.colors["muted"], width=15, anchor="e", font=self.font_body).pack(side="left", padx=(2, 6))
        entry = tk.Entry(row, textvariable=var, bd=0, highlightthickness=1, highlightbackground=self.colors["border"], font=self.font_body)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        entry.bind("<Return>", lambda _event: self.apply_style_to_selected())
        entry.bind("<FocusOut>", lambda _event: self.apply_style_to_selected())

    def _spin_row(self, label, var, from_value, to_value, increment, suffix=""):
        row = tk.Frame(self.properties, bg=self.colors["card"], height=25)
        row.pack(fill="x")
        tk.Label(row, text=label, bg=self.colors["card"], fg=self.colors["muted"], width=15, anchor="e", font=self.font_body).pack(side="left", padx=(2, 6))
        spin = ttk.Spinbox(row, textvariable=var, from_=from_value, to=to_value, increment=increment, width=12, command=self._schedule_style_apply)
        spin.pack(side="left", fill="x", expand=True, padx=(0, 2))
        if suffix:
            tk.Label(row, text=suffix, bg=self.colors["card"], fg=self.colors["muted"], width=4, anchor="w", font=self.font_small).pack(side="right", padx=(0, 4))
        spin.bind("<Return>", lambda _event: self.apply_style_to_selected())
        spin.bind("<FocusOut>", lambda _event: self.apply_style_to_selected())
        spin.bind("<KeyRelease>", lambda _event: self._schedule_style_apply())

    def _schedule_style_apply(self):
        pending = getattr(self, "_style_apply_job", None)
        if pending:
            self.after_cancel(pending)
        self._style_apply_job = self.after(120, self.apply_style_to_selected)

    def _build_statusbar(self):
        self.status = tk.Frame(self, bg=self.colors["status"], height=30, bd=0, highlightthickness=1, highlightbackground=self.colors["border"])
        self.status.grid(row=5, column=0, sticky="ew")
        self.status.grid_propagate(False)
        self.mode_label = tk.Label(self.status, text="Hand Tool", bg=self.colors["status"], fg=self.colors["text"], width=22, anchor="w", font=self.font_body)
        self.mode_label.pack(side="left", padx=12)
        tk.Button(self.status, text=ICON["Prev"], command=self.previous_page, bg=self.colors["status"], fg=self.colors["blue"], relief="flat", bd=0, width=2, font=self.font_icon_small).pack(side="left")
        self.page_picker = ttk.Combobox(self.status, textvariable=self.page_jump_var, values=["1"], width=5, state="readonly")
        self.page_picker.pack(side="left", padx=2)
        self.page_picker.bind("<<ComboboxSelected>>", self._jump_to_page)
        tk.Button(self.status, text=ICON["Next"], command=self.next_page, bg=self.colors["status"], fg=self.colors["blue"], relief="flat", bd=0, width=2, font=self.font_icon_small).pack(side="left")
        self.page_label = tk.Label(self.status, text="", bg=self.colors["status"], fg=self.colors["muted"], width=12, anchor="w", font=self.font_body)
        self.page_label.pack(side="left", padx=(4, 0))
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

    def _jump_to_page(self, event=None):
        try:
            page_number = int(self.page_jump_var.get())
        except (TypeError, ValueError):
            return
        page_index = page_number - 1
        if 0 <= page_index < len(self.pages) and page_index != self.current_page:
            self.current_page = page_index
            self._show_current_page()

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
        aperture = 18 ** 2
        nearby = [candidate for candidate in candidates if (candidate[0] - x) ** 2 + (candidate[1] - y) ** 2 <= aperture]
        if nearby:
            priority = {
                "Endpoint": 0,
                "Intersection": 1,
                "Apparent Intersection": 2,
                "Midpoint": 3,
                "Center": 4,
                "Quadrant": 5,
                "Insertion": 6,
                "Node": 7,
                "Perpendicular": 8,
                "Tangent": 9,
                "Nearest": 10,
                "Extension": 11,
            }
            best = min(nearby, key=lambda candidate: (priority.get(candidate[2], 20), (candidate[0] - x) ** 2 + (candidate[1] - y) ** 2))
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
        opacity = max(0.0, min(100.0, self._safe_float(str(self.opacity_var.get()).replace("%", ""), 100)))
        base_line_color = self.line_color_var.get() or "#ff0000"
        base_fill_color = "" if fill in {"", "None"} else fill
        return {
            "line_color": self._blend_color(base_line_color, opacity),
            "fill_color": self._blend_color(base_fill_color, opacity) if base_fill_color else "",
            "base_line_color": base_line_color,
            "base_fill_color": base_fill_color,
            "opacity": opacity,
            "width": max(0.5, min(50.0, width)),
            "line_type": self.line_type_var.get(),
            "font_family": self.font_family_var.get(),
            "font_size": max(4, min(144, int(self._safe_float(self.font_size_var.get(), 12)))),
        }

    def _blend_color(self, color, opacity, background="#ffffff"):
        if not color:
            return ""
        try:
            fr, fg, fb = [value / 257 for value in self.winfo_rgb(color)]
            br, bg, bb = [value / 257 for value in self.winfo_rgb(background)]
        except tk.TclError:
            return color
        alpha = max(0.0, min(1.0, opacity / 100.0))
        red = round(fr * alpha + br * (1 - alpha))
        green = round(fg * alpha + bg * (1 - alpha))
        blue = round(fb * alpha + bb * (1 - alpha))
        return f"#{red:02x}{green:02x}{blue:02x}"

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
            self._update_color_buttons()
            self.apply_style_to_selected()

    def choose_fill_color(self):
        initial = self.fill_color_var.get()
        color = colorchooser.askcolor(color=initial if initial not in {"", "None"} else "#ffffff", title="Fill Color")[1]
        if color:
            self.fill_color_var.set(color)
            self._update_color_buttons()
            self.apply_style_to_selected()

    def clear_fill_color(self):
        self.fill_color_var.set("None")
        self._update_color_buttons()
        self.apply_style_to_selected()

    def _update_color_buttons(self):
        for name, var in [("line_color_button", self.line_color_var), ("fill_color_button", self.fill_color_var)]:
            button = getattr(self, name, None)
            if not button:
                continue
            color = var.get()
            if color in {"", "None"}:
                button.configure(bg=self.colors["card"], fg=self.colors["muted"])
                continue
            try:
                red, green, blue = [value / 257 for value in self.winfo_rgb(color)]
                foreground = "#ffffff" if red * 0.299 + green * 0.587 + blue * 0.114 < 145 else "#111111"
                button.configure(bg=color, fg=foreground, activebackground=color)
            except tk.TclError:
                button.configure(bg=self.colors["card"], fg=self.colors["text"])

    def _set_tool(self, tool):
        self.current_tool = tool
        self._clear_pending()
        if tool in {"calibrate", "distance", "perimeter", "area"}:
            self._ensure_measure_snaps()
        elif tool in {"line", "arrow", "polyline", "polygon"}:
            self.snap_vars["Endpoint"].set(True)
            self.update_snap_indicator()
        for name, button in self.tool_buttons.items():
            if name == tool:
                button.configure(bg=self.colors["active"], fg=self.colors["blue"], highlightbackground="#b7d4ff")
            else:
                button.configure(bg=self.colors["chrome"], fg=self.colors["text"], highlightbackground="#ececf0")
        names = {
            "hand": "Hand Tool",
            "select": "Select Linework",
            "select_text": "Select Text",
            "snapshot": "Snapshot",
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
            "cp": "copy",
            "copy": "copy",
            "m": "move",
            "move": "move",
            "o": "offset",
            "offset": "offset",
            "ro": "rotate_selected",
            "rotate": "rotate_selected",
            "sc": "scale_selected",
            "scale": "scale_selected",
            "e": "delete",
            "erase": "delete",
            "delete": "delete",
            "g": "group",
            "group": "group",
            "x": "ungroup",
            "explode": "ungroup",
            "u": "undo",
            "undo": "undo",
            "redo": "redo",
            "z": "zoom",
            "zoom": "zoom",
            "pan": "hand",
            "t": "text",
            "text": "text",
            "tb": "text_box",
            "textbox": "text_box",
            "callout": "callout",
            "ar": "arrow",
            "arrow": "arrow",
            "pg": "polygon",
            "polygon": "polygon",
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
            self.show_text_to_cad_editor()
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
        if first in {"print", "plot"}:
            self.print_document()
            return

        tool = aliases.get(first)
        if "draw" in text and "line" in text:
            tool = "line"
        elif "draw" in text and "rectangle" in text:
            tool = "rectangle"
        elif "draw" in text and "circle" in text:
            tool = "circle"
        elif "calibrate" in text or "set measurement scale" in text:
            if len(numbers) >= 2:
                unit = self.unit_var.get() or "mm"
                self.scale_units_per_px = numbers[0] * self.zoom_level / numbers[1]
                self.scale_unit = unit
                self.scale_label_var.set(f"{numbers[1]:g} px = {numbers[0]:g} {unit}")
                self._set_status(f"AI scale set: {self.scale_label_var.get()}")
                return
            tool = "calibrate"
        elif "layer" in text:
            name = command.split(maxsplit=1)[1] if len(command.split()) > 1 else "Layer"
            self.create_layer_named(name)
            return

        if first in {"draw", "make", "create", "add"}:
            prompt_commands = self._parse_cad_prompt(raw)
            if prompt_commands:
                self._draw_cad_commands_on_canvas(prompt_commands)
                self._set_status(f"Text to CAD drew {len(prompt_commands)} object(s)")
                return

        if tool in {"copy", "move", "offset"}:
            {"copy": self.copy_selected, "move": self.move_selected, "offset": self.offset_selected}[tool]()
            return
        if tool == "delete":
            self.delete_selected()
            return
        if tool == "group":
            self.group_selected()
            return
        if tool == "ungroup":
            self.ungroup_selected()
            return
        if tool == "undo":
            self.undo()
            return
        if tool == "redo":
            self.redo()
            return
        if tool == "rotate_selected":
            if numbers:
                self.object_rotation_var.set(f"{numbers[0]:g}")
                self.apply_style_to_selected()
            else:
                self._set_status("RO needs an angle, for example RO 90")
            return
        if tool == "scale_selected":
            if numbers:
                self.object_scale_var.set(f"{numbers[0]:g}")
                self.apply_style_to_selected()
            else:
                self._set_status("SC needs a percent, for example SC 150")
            return
        if tool == "zoom":
            if numbers:
                value = numbers[0] / 100 if numbers[0] > 3 else numbers[0]
                self._set_zoom(value)
            elif len(tokens) >= 2 and tokens[1].lower() in {"in", "+"}:
                self.zoom_in()
            elif len(tokens) >= 2 and tokens[1].lower() in {"out", "-"}:
                self.zoom_out()
            else:
                self._set_status("Z 150 sets 150%; Z IN and Z OUT also work")
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
        prompt_commands = self._parse_cad_prompt(raw)
        if prompt_commands:
            self._draw_cad_commands_on_canvas(prompt_commands)
            self._set_status(f"Text to CAD drew {len(prompt_commands)} object(s)")
            return
        self._set_status("Unknown command. Try HELP, L 100 100 300 100, REC, PL, RO 90, SC 150, OSNAP END MID, TEXTCAD")

    def _command_help(self):
        self._set_status("AutoCAD aliases: L, PL, REC, C, CO/CP, M, O, RO, SC, E, G, X, Z, PAN, TEXT, OSNAP, ORTHO, PLOT")

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
        if self.current_tool in {"line", "circle", "cloud", "arrow", "polyline", "rectangle", "polygon", "pencil", "eraser", "snapshot", "calibrate", "distance", "perimeter", "area"}:
            self.canvas.configure(cursor="crosshair")
            x, y = self._canvas_xy(event)
            sx, sy, label = self.snap_point(x, y)
            self.show_crosshair(sx, sy, label)
            if self.current_tool in {"polyline", "polygon"} and self.pending_points:
                self.update_pending_preview(sx, sy)
        else:
            self.hide_crosshair()

    def on_press(self, event):
        if self.inline_editor is not None:
            self.commit_inline_text()
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
        if self.current_tool == "select_text":
            self.select_text_at(x, y)
            return
        x, y, _label = self.snap_point(x, y)
        if self.current_tool == "eraser":
            self.erase_at(x, y)
            return
        if self.current_tool in {"polyline", "polygon"}:
            self.add_pending_point(x, y)
            return
        if self.current_tool == "pencil":
            self.drag = {"tool": "pencil", "points": [x, y], "preview": None}
            return
        self.drag = {
            "tool": self.current_tool,
            "x": x,
            "y": y,
            "preview": None,
            "temporary_ortho": bool(event.state & 0x0004),
        }

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
            for entry in self.selected_entries:
                text_items = [item for item in entry.get("items", []) if self.canvas.type(item) == "text"]
                if text_items:
                    entry["font_size"] = self._canvas_font_size(text_items[0])
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
        if (self.ortho_var.get() or self.drag.get("temporary_ortho") or bool(event.state & 0x0004)) and x0 is not None and y0 is not None:
            if abs(x1 - x0) >= abs(y1 - y0):
                y1 = y0
            else:
                x1 = x0
        self.drag = None
        if tool == "snapshot":
            if x0 is not None and abs(x1 - x0) >= 8 and abs(y1 - y0) >= 8:
                self.create_snapshot(x0, y0, x1, y1)
            return
        if tool in {"text_box", "callout"}:
            if x0 is None:
                return
            if tool == "text_box":
                if abs(x1 - x0) < 24 or abs(y1 - y0) < 18:
                    x1, y1 = x0 + 190, y0 + 72
                box = clamp_box(x0, y0, x1, y1)
                self.start_inline_text("Text Box", box)
            else:
                tip = (x0, y0)
                box_x = x1
                box_y = y1 - 36
                if abs(x1 - x0) < 24 and abs(y1 - y0) < 24:
                    box_x, box_y = x0 + 80, y0 - 35
                self.start_inline_text("Callout", (box_x, box_y, box_x + 190, box_y + 72), tip=tip)
            return
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
        menu.add_command(label="Rotate 90 Degrees", command=lambda: self.rotate_selected(90), state="normal" if self.selected_entries else "disabled")
        menu.add_command(label="Rotate 180 Degrees", command=lambda: self.rotate_selected(180), state="normal" if self.selected_entries else "disabled")
        menu.add_command(label="Mirror Horizontal", command=lambda: self.mirror_selected(True), state="normal" if self.selected_entries else "disabled")
        menu.add_command(label="Mirror Vertical", command=lambda: self.mirror_selected(False), state="normal" if self.selected_entries else "disabled")
        menu.add_separator()
        menu.add_command(label="Flatten Selected", command=self.flatten_selected, state="normal" if self.selected_entries else "disabled")
        menu.add_command(label="Flatten Page Markups", command=self.flatten_layer)
        menu.add_command(label="Delete", command=self.delete_selected, state="normal" if self.selected_entries else "disabled")
        menu.tk_popup(event.x_root, event.y_root)

    def _draw_preview(self, x0, y0, x1, y1):
        if self.drag.get("preview"):
            self.canvas.delete(self.drag["preview"])
        tool = self.drag["tool"]
        if (self.ortho_var.get() or self.drag.get("temporary_ortho")) and tool in {"line", "arrow", "distance", "calibrate"}:
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
        elif tool == "text_box":
            self.drag["preview"] = self.canvas.create_rectangle(x0, y0, x1, y1, outline=style["line_color"], width=style["width"], dash=dash)
        elif tool == "callout":
            self.drag["preview"] = self.canvas.create_line(x0, y0, x1, y1, fill=style["line_color"], width=style["width"], arrow=tk.LAST)

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
        if self.pending_points and math.hypot(x - self.pending_points[-2], y - self.pending_points[-1]) < 2:
            return
        self.pending_points.extend([x, y])
        self.update_pending_preview(x, y)
        count = len(self.pending_points) // 2
        self._set_status(f"Polyline vertex {count}; click for next point, double-click or right-click to finish")

    def update_pending_preview(self, x, y):
        if not self.pending_points:
            return
        if self.pending_preview:
            self.canvas.delete(self.pending_preview)
        style = self._style()
        points = self.pending_points[:] + [x, y]
        if self.current_tool == "polygon" and len(self.pending_points) >= 4:
            points.extend(self.pending_points[:2])
        self.pending_preview = self.canvas.create_line(points, fill=style["line_color"], width=style["width"], dash=self._dash())

    def finish_pending_shape(self, event=None):
        minimum = 6 if self.current_tool == "polygon" else 4
        if self.current_tool not in {"polyline", "polygon"} or len(self.pending_points) < minimum:
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

    def start_inline_text(self, kind, box, tip=None):
        self.cancel_inline_text()
        page_x0, page_y0, page_x1, page_y1 = self._page_bbox()
        x0, y0, x1, y1 = box
        width = max(110, min(abs(x1 - x0), page_x1 - page_x0 - 10))
        height = max(48, min(abs(y1 - y0), page_y1 - page_y0 - 10))
        x0 = max(page_x0 + 5, min(x0, page_x1 - width - 5))
        y0 = max(page_y0 + 5, min(y0, page_y1 - height - 5))
        x1, y1 = x0 + width, y0 + height
        editor = tk.Text(self.canvas, wrap="word", bd=1, relief="solid", highlightthickness=2, highlightbackground=self.colors["blue"], font=(self.font_family_var.get(), int(self._safe_float(self.font_size_var.get(), 12))))
        editor.insert("1.0", "")
        window_item = self.canvas.create_window(x0 + 4, y0 + 4, anchor="nw", width=width - 8, height=height - 8, window=editor)
        self.inline_editor = editor
        self.inline_window_item = window_item
        self.inline_edit_data = {"kind": kind, "box": (x0, y0, x1, y1), "tip": tip, "style": self._style()}
        editor.bind("<Control-Return>", self._commit_inline_event)
        editor.bind("<Escape>", self._cancel_inline_event)
        editor.bind("<FocusOut>", lambda _event: self.after(60, self._commit_inline_after_focus))
        editor.focus_set()
        self._set_status("Type on the page; press Ctrl+Enter or click outside to finish")

    def _commit_inline_event(self, event=None):
        self.commit_inline_text()
        return "break"

    def _cancel_inline_event(self, event=None):
        self.cancel_inline_text()
        return "break"

    def _commit_inline_after_focus(self):
        if self.inline_editor is not None and self.focus_get() is not self.inline_editor:
            self.commit_inline_text()

    def commit_inline_text(self):
        editor = self.inline_editor
        data = self.inline_edit_data
        if editor is None or data is None:
            return
        text = editor.get("1.0", "end-1c").strip()
        self._remove_inline_editor()
        if not text:
            self._set_status("Empty text cancelled")
            return
        style = data["style"]
        x0, y0, x1, y1 = data["box"]
        rect = self.canvas.create_rectangle(x0, y0, x1, y1, outline=style["line_color"], fill=style["fill_color"] or "white", width=style["width"], dash=self._dash())
        label = self.canvas.create_text(x0 + 10, y0 + 10, text=text, anchor="nw", width=max(20, x1 - x0 - 20), fill=style["line_color"], font=(style["font_family"], style["font_size"]))
        items = [rect, label]
        if data["kind"] == "Callout":
            tip_x, tip_y = data["tip"] or (x0 - 70, y1 + 35)
            arrow = self.canvas.create_line(x0, (y0 + y1) / 2, tip_x, tip_y, fill=style["line_color"], width=style["width"], arrow=tk.LAST)
            items.append(arrow)
        self._record_entry(data["kind"], text, items)

    def _remove_inline_editor(self):
        editor = self.inline_editor
        window_item = self.inline_window_item
        self.inline_editor = None
        self.inline_window_item = None
        self.inline_edit_data = None
        if window_item:
            self.canvas.delete(window_item)
        if editor is not None:
            try:
                editor.destroy()
            except tk.TclError:
                pass

    def cancel_inline_text(self):
        if self.inline_editor is None:
            return
        self._remove_inline_editor()
        self._set_status("Text entry cancelled")

    def select_text_at(self, x, y):
        self.canvas.delete("pdf_text_selection")
        entry = self._entry_at(x, y)
        if entry:
            text_items = [item for item in entry.get("items", []) if self.canvas.type(item) == "text"]
            if text_items:
                self.clear_selection()
                self.selected_entries = self._entries_in_group(entry)
                self.draw_selection()
                value = " ".join(self._item_option(item, "text") for item in text_items).strip()
                if value:
                    self.clipboard_clear()
                    self.clipboard_append(value)
                self._set_status(f"Selected markup text: {value[:70]}")
                return
        page = self.pages[self.current_page]
        if not self._is_pdf_page(page):
            self._set_status("No text at this point")
            return
        fitz = self._pdf_renderer()
        path = page.get("source_pdf") or self.current_pdf or self.current_file
        if not fitz or not path or not os.path.exists(path):
            self._set_status("PDF text is unavailable")
            return
        scale = self.pdf_render_scale * self.zoom_level
        px = (x - PAGE_ORIGIN[0]) / max(scale, 0.001)
        py = (y - PAGE_ORIGIN[1]) / max(scale, 0.001)
        try:
            doc = fitz.open(path)
            pdf_page = doc.load_page(int(page.get("pdf_index", self.current_page)))
            words = pdf_page.get_text("words")
            doc.close()
        except Exception as exc:
            self._set_status(f"Could not select PDF text: {exc}")
            return
        matches = [word for word in words if word[0] - 2 <= px <= word[2] + 2 and word[1] - 2 <= py <= word[3] + 2]
        if not matches:
            self._set_status("No PDF text at this point")
            return
        word = min(matches, key=lambda item: (item[2] - item[0]) * (item[3] - item[1]))
        x0 = PAGE_ORIGIN[0] + word[0] * scale
        y0 = PAGE_ORIGIN[1] + word[1] * scale
        x1 = PAGE_ORIGIN[0] + word[2] * scale
        y1 = PAGE_ORIGIN[1] + word[3] * scale
        self.canvas.create_rectangle(x0, y0, x1, y1, fill="#b7d7ff", outline=self.colors["blue"], stipple="gray50", tags="pdf_text_selection")
        self.canvas.tag_raise("pdf_text_selection")
        self.clipboard_clear()
        self.clipboard_append(str(word[4]))
        self._set_status(f"Selected PDF text and copied it: {word[4]}")

    def create_snapshot(self, x0, y0, x1, y1):
        page = self.pages[self.current_page]
        if not self._is_pdf_page(page):
            self._set_status("Snapshot needs an open PDF page")
            return
        fitz = self._pdf_renderer()
        path = page.get("source_pdf") or self.current_pdf or self.current_file
        if not fitz or not path or not os.path.exists(path):
            self._set_status("PDF snapshot is unavailable")
            return
        x0, y0, x1, y1 = clamp_box(x0, y0, x1, y1)
        scale = self.pdf_render_scale * self.zoom_level
        clip = fitz.Rect(
            (x0 - PAGE_ORIGIN[0]) / scale,
            (y0 - PAGE_ORIGIN[1]) / scale,
            (x1 - PAGE_ORIGIN[0]) / scale,
            (y1 - PAGE_ORIGIN[1]) / scale,
        )
        snapshot_dir = os.path.join(tempfile.gettempdir(), "DieselPDF", "snapshots")
        os.makedirs(snapshot_dir, exist_ok=True)
        snapshot_path = os.path.join(snapshot_dir, f"snapshot-{os.getpid()}-{self.next_entry_id}.png")
        try:
            doc = fitz.open(path)
            pdf_page = doc.load_page(int(page.get("pdf_index", self.current_page)))
            pix = pdf_page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
            pix.save(snapshot_path)
            doc.close()
            image = tk.PhotoImage(file=snapshot_path)
        except Exception as exc:
            self._set_status(f"Could not create snapshot: {exc}")
            return
        self.snapshot_images.append(image)
        item = self.canvas.create_image(x0, y0, anchor="nw", image=image)
        border = self.canvas.create_rectangle(x0, y0, x0 + image.width(), y0 + image.height(), outline=self.colors["blue"], width=1)
        self._record_entry("Snapshot", os.path.basename(snapshot_path), [item, border])
        self._current_entries()[-1]["asset_path"] = snapshot_path
        self._set_status("Snapshot added as an editable markup")

    def finish_calibration(self, x0, y0, x1, y1):
        pixels = math.hypot(x1 - x0, y1 - y0)
        if pixels <= 0:
            return
        real = simpledialog.askfloat("Calibrate", "Known real distance:", minvalue=0.0001)
        if not real:
            return
        unit = self.unit_var.get() or self.scale_unit
        self.scale_units_per_px = real * self.zoom_level / pixels
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
            value = self._round_to_precision((pixels / self.zoom_level) * self.scale_units_per_px)
            return f"{value:g} {self.scale_unit}"
        return f"{pixels:.0f} px"

    def _perimeter_label(self, width_px, height_px):
        perimeter = 2 * (width_px + height_px)
        return f"P = {self._measure_label(perimeter)}"

    def _area_label(self, width_px, height_px):
        area_px = width_px * height_px
        if self.scale_units_per_px:
            base_area_px = area_px / (self.zoom_level * self.zoom_level)
            value = self._round_to_precision(base_area_px * self.scale_units_per_px * self.scale_units_per_px)
            return f"A = {value:g} {self.scale_unit}^2"
        return f"A = {area_px:.0f} px^2"

    def _record_entry(self, kind, detail, items):
        style = self._style()
        entry = {
            "id": self.next_entry_id,
            "kind": kind,
            "detail": detail,
            "items": items,
            "group": None,
            "flattened": False,
            "layer": self.current_layer,
            "stroke_color": style["base_line_color"],
            "fill_color": style["base_fill_color"],
            "line_width": style["width"],
            "line_type": style["line_type"],
            "opacity": style["opacity"],
            "font_family": style["font_family"],
            "font_size": style["font_size"],
            "scale_percent": 100.0,
            "rotation_deg": 0.0,
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
            self.markup_list.insert(
                "",
                "end",
                iid=iid,
                values=(entry["kind"], self.current_page + 1, entry.get("layer", "0"), entry["detail"]),
            )

    def _markup_selected(self, event=None):
        selected = self.markup_list.selection()
        if not selected:
            return
        try:
            entry_id = int(selected[0])
        except (TypeError, ValueError):
            return
        entry = next((item for item in self._current_entries() if item["id"] == entry_id), None)
        if not entry or entry.get("flattened"):
            return
        self.clear_selection()
        self.selected_entries = [candidate for candidate in self._entries_in_group(entry) if not candidate.get("flattened")]
        self.draw_selection()
        self._load_properties_from_selection()
        self._set_status(f"{len(self.selected_entries)} markup(s) selected from Markups list")

    def export_markups_csv(self):
        path = filedialog.asksaveasfilename(
            title="Export Markups List",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="DieselPDF-Markups.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Page", "Subject", "Detail", "Layer", "Stroke", "Fill", "Thickness", "Opacity"])
            for page_number, page in enumerate(self.pages, start=1):
                for entry in page.get("entries", []):
                    writer.writerow([
                        page_number,
                        entry.get("kind", "Markup"),
                        entry.get("detail", ""),
                        entry.get("layer", "0"),
                        entry.get("stroke_color", ""),
                        entry.get("fill_color", ""),
                        entry.get("line_width", ""),
                        entry.get("opacity", ""),
                    ])
        self._set_status(f"Exported Markups list: {os.path.basename(path)}")

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
        self._load_properties_from_selection()
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
            "text_fonts": {
                item: self._canvas_font_size(item)
                for item in original
                if self.canvas.type(item) == "text"
            },
            "text_widths": {
                item: self._safe_float(self._item_option(item, "width"), 0)
                for item in original
                if self.canvas.type(item) == "text"
            },
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
            if self.canvas.type(item) == "text":
                font_size = max(4, int(self.drag["text_fonts"].get(item, 12) * max(0.15, min(abs(sx), abs(sy)))))
                font_family = self.selected_entries[-1].get("font_family", "Arial") if self.selected_entries else "Arial"
                self.canvas.itemconfigure(item, font=(font_family, font_size))
                original_width = self.drag["text_widths"].get(item, 0)
                if original_width > 0:
                    self.canvas.itemconfigure(item, width=max(20, original_width * abs(sx)))
        self.draw_selection()

    def _canvas_font_size(self, item):
        value = self._item_option(item, "font")
        matches = re.findall(r"-?\d+", str(value))
        return abs(int(matches[-1])) if matches else 12

    def apply_style_to_selected(self):
        style = self._style()
        dash = self._dash()
        self._update_color_buttons()
        if not self.selected_entries:
            self._set_status("Tool defaults updated")
            return
        self._apply_selection_transform()
        for entry in self.selected_entries:
            entry.update({
                "stroke_color": style["base_line_color"],
                "fill_color": style["base_fill_color"],
                "line_width": style["width"],
                "line_type": style["line_type"],
                "opacity": style["opacity"],
                "font_family": style["font_family"],
                "font_size": style["font_size"],
            })
            for item in entry["items"]:
                item_type = self.canvas.type(item)
                if item_type == "line":
                    self.canvas.itemconfigure(item, fill=style["line_color"], width=style["width"], dash=dash)
                elif item_type == "polygon":
                    self.canvas.itemconfigure(item, outline=style["line_color"], fill=style["fill_color"], width=style["width"], dash=dash)
                elif item_type in {"rectangle", "oval"}:
                    self.canvas.itemconfigure(item, outline=style["line_color"], width=style["width"], dash=dash)
                    self.canvas.itemconfigure(item, fill=style["fill_color"])
                elif item_type == "text":
                    self.canvas.itemconfigure(item, fill=style["line_color"], font=(style["font_family"], style["font_size"]))
        self.draw_selection()
        self._set_status("Style applied to selected markups")

    def _load_properties_from_selection(self):
        if not self.selected_entries:
            return
        entry = self.selected_entries[-1]
        first_item = entry["items"][0] if entry.get("items") else None
        if first_item:
            item_type = self.canvas.type(first_item)
            inferred_stroke = self._item_option(first_item, "outline") if item_type in {"rectangle", "oval", "polygon"} else self._item_option(first_item, "fill")
            inferred_fill = self._item_option(first_item, "fill") if item_type in {"rectangle", "oval", "polygon"} else ""
            inferred_width = self._safe_float(self._item_option(first_item, "width"), 2)
        else:
            inferred_stroke, inferred_fill, inferred_width = "#ff0000", "", 2
        self.line_color_var.set(entry.get("stroke_color") or inferred_stroke or "#ff0000")
        self.fill_color_var.set(entry.get("fill_color") or inferred_fill or "None")
        self.width_var.set(f"{self._safe_float(entry.get('line_width'), inferred_width):g}")
        self.line_type_var.set(entry.get("line_type", "Solid"))
        self.opacity_var.set(f"{self._safe_float(entry.get('opacity'), 100):g}")
        self.font_family_var.set(entry.get("font_family", "Arial"))
        self.font_size_var.set(f"{self._safe_float(entry.get('font_size'), 12):g}")
        self.object_scale_var.set(f"{self._safe_float(entry.get('scale_percent'), 100):g}")
        self.object_rotation_var.set(f"{self._safe_float(entry.get('rotation_deg'), 0):g}")
        self._update_color_buttons()

    def _apply_selection_transform(self):
        bbox = self._selection_bbox()
        if not bbox:
            return
        target_scale = max(1.0, min(1000.0, self._safe_float(self.object_scale_var.get(), 100)))
        target_rotation = self._safe_float(self.object_rotation_var.get(), 0) % 360
        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        for entry in self.selected_entries:
            current_scale = max(0.01, self._safe_float(entry.get("scale_percent"), 100))
            scale_factor = target_scale / current_scale
            if abs(scale_factor - 1.0) > 1e-6:
                for item in entry["items"]:
                    self.canvas.scale(item, cx, cy, scale_factor, scale_factor)
                    if self.canvas.type(item) == "text":
                        width = self._safe_float(self._item_option(item, "width"), 0)
                        if width > 0:
                            self.canvas.itemconfigure(item, width=max(1, width * scale_factor))
                        current_font = self._canvas_font_size(item)
                        self.canvas.itemconfigure(item, font=(entry.get("font_family", "Arial"), max(4, int(current_font * scale_factor))))
                    elif self.canvas.type(item) in {"line", "rectangle", "oval", "polygon"}:
                        current_width = self._safe_float(self._item_option(item, "width"), entry.get("line_width", 2))
                        self.canvas.itemconfigure(item, width=max(0.5, min(50, current_width * scale_factor)))
                entry["scale_percent"] = target_scale
                entry["line_width"] = max(0.5, min(50, self._safe_float(entry.get("line_width"), 2) * scale_factor))
                entry["font_size"] = max(4, int(self._safe_float(entry.get("font_size"), 12) * scale_factor))
            current_rotation = self._safe_float(entry.get("rotation_deg"), 0) % 360
            delta = ((target_rotation - current_rotation + 180) % 360) - 180
            if abs(delta) > 1e-6:
                self._rotate_entry(entry, delta, cx, cy)
                entry["rotation_deg"] = target_rotation

    def _rotate_entry(self, entry, degrees, cx, cy):
        for index, item in list(enumerate(entry["items"])):
            item_type = self.canvas.type(item)
            coords = self.canvas.coords(item)
            if item_type in {"line", "polygon"}:
                self.canvas.coords(item, *self._rotate_coords_angle(coords, cx, cy, degrees))
            elif item_type == "rectangle" and len(coords) >= 4:
                corners = [coords[0], coords[1], coords[2], coords[1], coords[2], coords[3], coords[0], coords[3]]
                rotated = self._rotate_coords_angle(corners, cx, cy, degrees)
                new_item = self.canvas.create_polygon(
                    rotated,
                    fill=self._item_option(item, "fill"),
                    outline=self._item_option(item, "outline"),
                    width=self._safe_float(self._item_option(item, "width"), 1),
                    dash=self._parse_dash(self._item_option(item, "dash")),
                    stipple=self._item_option(item, "stipple"),
                )
                for tag in self.canvas.gettags(item):
                    self.canvas.addtag_withtag(tag, new_item)
                self.canvas.itemconfigure(new_item, state=self._item_option(item, "state") or "normal")
                self.canvas.delete(item)
                entry["items"][index] = new_item
            elif item_type == "oval" and len(coords) >= 4:
                center = self._rotate_coords_angle([(coords[0] + coords[2]) / 2, (coords[1] + coords[3]) / 2], cx, cy, degrees)
                half_w, half_h = abs(coords[2] - coords[0]) / 2, abs(coords[3] - coords[1]) / 2
                self.canvas.coords(item, center[0] - half_w, center[1] - half_h, center[0] + half_w, center[1] + half_h)
            elif item_type == "text" and len(coords) >= 2:
                rotated = self._rotate_coords_angle(coords[:2], cx, cy, degrees)
                self.canvas.coords(item, rotated[0], rotated[1])
                try:
                    current_angle = self._safe_float(self._item_option(item, "angle"), 0)
                    self.canvas.itemconfigure(item, angle=(current_angle - degrees) % 360)
                except tk.TclError:
                    pass
            elif item_type == "image" and len(coords) >= 2:
                rotated = self._rotate_coords_angle(coords[:2], cx, cy, degrees)
                self.canvas.coords(item, rotated[0], rotated[1])

    def _rotate_coords_angle(self, coords, cx, cy, degrees):
        radians = math.radians(degrees)
        cosine, sine = math.cos(radians), math.sin(radians)
        rotated = []
        for index in range(0, len(coords), 2):
            dx, dy = coords[index] - cx, coords[index + 1] - cy
            rotated.extend([cx + dx * cosine - dy * sine, cy + dx * sine + dy * cosine])
        return rotated

    def rotate_selected(self, degrees):
        if not self.selected_entries:
            self._set_status("Select markups before rotating")
            return
        bbox = self._selection_bbox()
        if not bbox:
            return
        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        for entry in self.selected_entries:
            self._rotate_entry(entry, degrees, cx, cy)
            entry["rotation_deg"] = (self._safe_float(entry.get("rotation_deg"), 0) + degrees) % 360
        self.draw_selection()
        self._set_status(f"Rotated selection {degrees:g} degrees")

    def mirror_selected(self, horizontal=True):
        if not self.selected_entries:
            self._set_status("Select markups before mirroring")
            return
        bbox = self._selection_bbox()
        if not bbox:
            return
        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        before = {}
        for entry in self.selected_entries:
            for item in entry.get("items", []):
                coords = self.canvas.coords(item)
                before[item] = coords[:]
                mirrored = []
                for index in range(0, len(coords), 2):
                    mx = 2 * cx - coords[index] if horizontal else coords[index]
                    my = coords[index + 1] if horizontal else 2 * cy - coords[index + 1]
                    mirrored.extend([mx, my])
                self.canvas.coords(item, *mirrored)
        after = {item: self.canvas.coords(item)[:] for item in before}
        self._push_undo({"type": "coords", "before": before, "after": after})
        self.draw_selection()
        self._set_status("Mirrored selection horizontally" if horizontal else "Mirrored selection vertically")

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
                copied_entry = self._current_entries()[-1]
                for key in ["stroke_color", "fill_color", "line_width", "line_type", "opacity", "font_family", "font_size", "scale_percent", "rotation_deg"]:
                    copied_entry[key] = entry.get(key, copied_entry.get(key))
                copied_entry["asset_path"] = entry.get("asset_path")
                copies.append(copied_entry)
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
                offset_entry = self._current_entries()[-1]
                for key in ["stroke_color", "fill_color", "line_width", "line_type", "opacity", "font_family", "font_size", "scale_percent", "rotation_deg"]:
                    offset_entry[key] = entry.get(key, offset_entry.get(key))
                offset_entry["asset_path"] = entry.get("asset_path")
                created.append(offset_entry)
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
            options = {"text": self._item_option(item, "text"), "fill": fill, "font": self._item_option(item, "font"), "anchor": "nw", "angle": self._safe_float(self._item_option(item, "angle"), 0)}
            text_width = self._safe_float(self._item_option(item, "width"), 0)
            if text_width:
                options["width"] = text_width
            return self.canvas.create_text(shifted, **options)
        if item_type == "image":
            entry = next((candidate for candidate in self._current_entries() if item in candidate.get("items", [])), None)
            path = entry.get("asset_path") if entry else None
            if path and os.path.exists(path):
                try:
                    image = tk.PhotoImage(file=path)
                    self.snapshot_images.append(image)
                    return self.canvas.create_image(shifted, image=image, anchor="nw")
                except tk.TclError:
                    return None
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

    def flatten_selected(self):
        if not self.selected_entries:
            self._set_status("Select markups before flattening")
            return
        count = len(self.selected_entries)
        for entry in self.selected_entries:
            entry["flattened"] = True
        self.clear_selection()
        self._set_status(f"Flattened and locked {count} selected markup(s)")

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
        if not hasattr(self, "library_list"):
            return
        self.library_list.delete(*self.library_list.get_children())
        self.library_catalog = {}
        category_names = ["Recent Tools", "General", "Review", "Takeoff", "Construction", "Safety", "My Tools"]
        category_nodes = {
            name: self.library_list.insert("", "end", text=name, open=name in {"Recent Tools", "General", "Takeoff", "My Tools"})
            for name in category_names
        }

        if self.recent_tools:
            for index, payload in enumerate(self.recent_tools[:8]):
                iid = f"recent_{index}"
                self.library_list.insert(category_nodes["Recent Tools"], "end", iid=iid, text=payload["name"])
                self.library_catalog[iid] = copy.deepcopy(payload)
        else:
            self.library_list.insert(category_nodes["Recent Tools"], "end", text="No recent tools yet")

        builtin_index = 0
        for category, name, kind in DEFAULT_TOOL_SETS:
            if kind == "recent":
                continue
            iid = f"builtin_{builtin_index}"
            builtin_index += 1
            payload = {"source": "builtin", "name": name, "kind": kind}
            self.library_list.insert(category_nodes[category], "end", iid=iid, text=name)
            self.library_catalog[iid] = payload

        library = []
        if os.path.exists(LIBRARY_PATH):
            try:
                with open(LIBRARY_PATH, "r", encoding="utf-8") as handle:
                    library = json.load(handle)
            except (OSError, json.JSONDecodeError):
                library = []
        if library:
            for index, item in enumerate(library):
                iid = f"custom_{index}"
                payload = {
                    "source": "custom",
                    "name": item.get("name", "Saved Tool"),
                    "entries": item.get("entries", []),
                }
                self.library_list.insert(category_nodes["My Tools"], "end", iid=iid, text=payload["name"])
                self.library_catalog[iid] = payload
        else:
            self.library_list.insert(category_nodes["My Tools"], "end", text="Select markups and use Save to Library")

    def _library_activate(self, event=None):
        self.insert_library_tool()

    def insert_library_tool(self, payload=None):
        if payload is None:
            selection = self.library_list.selection()
            if not selection:
                self._set_status("Choose a Tool Chest item to insert")
                return []
            payload = self.library_catalog.get(selection[0])
        if not payload:
            self._set_status("Choose a Tool Chest item, not a tool set heading")
            return []
        if payload.get("source") == "custom":
            created = self._insert_custom_library_tool(payload)
        else:
            created = self._insert_builtin_library_tool(payload.get("kind"))
        if not created:
            return []
        self.clear_selection()
        self.selected_entries = created
        self.draw_selection()
        recent = copy.deepcopy(payload)
        recent_key = (recent.get("source"), recent.get("kind"), recent.get("name"))
        self.recent_tools = [
            item for item in self.recent_tools
            if (item.get("source"), item.get("kind"), item.get("name")) != recent_key
        ]
        self.recent_tools.insert(0, recent)
        self.recent_tools = self.recent_tools[:8]
        self.refresh_library()
        self._set_status(f"Inserted Tool Chest item: {payload.get('name', 'Tool')}")
        return created

    def _insert_builtin_library_tool(self, kind):
        x0, y0, x1, y1 = self._page_bbox()
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        style = self._style()
        stroke = style["line_color"]
        fill = style["fill_color"]
        width = style["width"]
        dash = self._dash()
        items = []
        entry_kind = "Library Tool"
        detail = kind.replace("_", " ").title() if kind else "Tool"

        if kind == "line":
            items = [self.canvas.create_line(cx - 90, cy, cx + 90, cy, fill=stroke, width=width, dash=dash)]
            entry_kind, detail = "Line", "straight line"
        elif kind == "arrow":
            items = [self.canvas.create_line(cx - 90, cy + 30, cx + 90, cy - 30, fill=stroke, width=width, dash=dash, arrow=tk.LAST)]
            entry_kind, detail = "Arrow", "closed arrow"
        elif kind == "rectangle":
            items = [self.canvas.create_rectangle(cx - 90, cy - 55, cx + 90, cy + 55, outline=stroke, fill=fill, width=width, dash=dash)]
            entry_kind, detail = "Rectangle", "rectangle"
        elif kind == "circle":
            items = [self.canvas.create_oval(cx - 65, cy - 65, cx + 65, cy + 65, outline=stroke, fill=fill, width=width, dash=dash)]
            entry_kind, detail = "Circle", "circle"
        elif kind == "cloud":
            items = [self.canvas.create_oval(cx - 95, cy - 55, cx + 95, cy + 55, outline=stroke, fill=fill, width=max(2, width), dash=(4, 3))]
            entry_kind, detail = "Cloud", "revision cloud"
        elif kind == "callout":
            items = [
                self.canvas.create_rectangle(cx - 80, cy - 70, cx + 100, cy - 10, outline=stroke, fill=fill or "#ffffff", width=width),
                self.canvas.create_text(cx - 68, cy - 58, text="NOTE", anchor="nw", fill=stroke, font=(style["font_family"], style["font_size"]), width=150),
                self.canvas.create_line(cx - 25, cy - 10, cx - 90, cy + 70, fill=stroke, width=width, arrow=tk.LAST),
            ]
            entry_kind, detail = "Callout", "editable note callout"
        elif kind in {"approved_stamp", "review_stamp"}:
            color = "#18864b" if kind == "approved_stamp" else "#c93434"
            text = "APPROVED" if kind == "approved_stamp" else "REVIEW"
            items = [
                self.canvas.create_rectangle(cx - 105, cy - 34, cx + 105, cy + 34, outline=color, width=4),
                self.canvas.create_text(cx, cy, text=text, anchor="center", fill=color, font=("Arial", 19, "bold")),
            ]
            entry_kind, detail = "Stamp", text.title()
        elif kind == "check_mark":
            items = [self.canvas.create_line(cx - 70, cy, cx - 20, cy + 45, cx + 80, cy - 65, fill="#18864b", width=max(5, width), joinstyle=tk.ROUND)]
            entry_kind, detail = "Check Mark", "review complete"
        elif kind == "revision_delta":
            items = [
                self.canvas.create_polygon(cx, cy - 70, cx + 70, cy + 55, cx - 70, cy + 55, outline="#c93434", fill="", width=3),
                self.canvas.create_text(cx, cy + 5, text="1", anchor="center", fill="#c93434", font=("Arial", 18, "bold")),
            ]
            entry_kind, detail = "Revision Delta", "revision 1"
        elif kind == "distance_sample":
            length = min(220, max(90, (x1 - x0) * 0.35))
            label = self._measure_label(length)
            items = [
                self.canvas.create_line(cx - length / 2, cy, cx + length / 2, cy, fill=stroke, width=width, arrow=tk.BOTH),
                self.canvas.create_text(cx, cy - 16, text=label, anchor="s", fill=stroke, font=(style["font_family"], style["font_size"])),
            ]
            entry_kind, detail = "Distance", label
        elif kind == "area_box":
            box = (cx - 90, cy - 55, cx + 90, cy + 55)
            label = self._area_label(180, 110)
            items = [
                self.canvas.create_rectangle(*box, outline=stroke, fill=fill or "#e8f2ff", width=width, dash=dash, stipple="gray50"),
                self.canvas.create_text(cx, cy, text=label, anchor="center", fill=stroke, font=(style["font_family"], style["font_size"], "bold")),
            ]
            entry_kind, detail = "Area", label
        elif kind == "count_marker":
            items = [
                self.canvas.create_oval(cx - 28, cy - 28, cx + 28, cy + 28, outline="#d94c4c", fill="#ffffff", width=3),
                self.canvas.create_text(cx, cy, text="1", anchor="center", fill="#d94c4c", font=("Arial", 16, "bold")),
            ]
            entry_kind, detail = "Count", "count marker"
        elif kind == "scale_bar":
            length = 180
            label = self._measure_label(length)
            items = [
                self.canvas.create_line(cx - 90, cy, cx + 90, cy, fill=stroke, width=3),
                self.canvas.create_line(cx - 90, cy - 12, cx - 90, cy + 12, fill=stroke, width=3),
                self.canvas.create_line(cx, cy - 8, cx, cy + 8, fill=stroke, width=2),
                self.canvas.create_line(cx + 90, cy - 12, cx + 90, cy + 12, fill=stroke, width=3),
                self.canvas.create_text(cx, cy - 16, text=label, anchor="s", fill=stroke, font=(style["font_family"], style["font_size"])),
            ]
            entry_kind, detail = "Scale Bar", label
        elif kind == "north_arrow":
            items = [
                self.canvas.create_line(cx, cy + 70, cx, cy - 65, fill=stroke, width=4, arrow=tk.LAST),
                self.canvas.create_text(cx, cy - 88, text="N", anchor="center", fill=stroke, font=("Arial", 18, "bold")),
            ]
            entry_kind, detail = "North Arrow", "north"
        elif kind == "door_opening":
            items = [
                self.canvas.create_line(cx - 90, cy - 60, cx - 90, cy + 70, fill=stroke, width=5),
                self.canvas.create_line(cx - 90, cy + 70, cx + 45, cy + 70, fill=stroke, width=5),
                self.canvas.create_line(cx - 90, cy - 60, cx + 45, cy + 70, fill=stroke, width=3, dash=(5, 4)),
            ]
            entry_kind, detail = "Door Opening", "door swing detail"
        elif kind == "warning":
            items = [
                self.canvas.create_polygon(cx, cy - 70, cx + 72, cy + 58, cx - 72, cy + 58, outline="#b56a00", fill="#ffd65a", width=3),
                self.canvas.create_text(cx, cy + 12, text="!", anchor="center", fill="#5c3a00", font=("Arial", 30, "bold")),
            ]
            entry_kind, detail = "Warning", "safety warning"
        elif kind == "fire_point":
            items = [
                self.canvas.create_oval(cx - 46, cy - 46, cx + 46, cy + 46, outline="#b81f2d", fill="#e5404f", width=3),
                self.canvas.create_text(cx, cy, text="F", anchor="center", fill="#ffffff", font=("Arial", 27, "bold")),
            ]
            entry_kind, detail = "Fire Point", "fire equipment"
        if not items:
            self._set_status("Tool Chest item is unavailable")
            return []
        self._record_entry(entry_kind, detail, items)
        return [self._current_entries()[-1]]

    def _insert_custom_library_tool(self, payload):
        serialized = copy.deepcopy(payload.get("entries", []))
        coords = []
        for entry_data in serialized:
            for obj in entry_data.get("objects", []):
                values = obj.get("coords", [])
                coords.extend(list(zip(values[0::2], values[1::2])))
        if not coords:
            self._set_status("Saved Tool Chest item has no drawable objects")
            return []
        x0, y0, x1, y1 = self._page_bbox()
        target_x, target_y = (x0 + x1) / 2, (y0 + y1) / 2
        source_x = (min(x for x, _y in coords) + max(x for x, _y in coords)) / 2
        source_y = (min(y for _x, y in coords) + max(y for _x, y in coords)) / 2
        dx, dy = target_x - source_x, target_y - source_y
        group_id = None
        if len(serialized) > 1:
            group_id = f"group_{self.next_group_id}"
            self.next_group_id += 1
        created = []
        page = self.pages[self.current_page]
        for entry_data in serialized:
            entry_data["id"] = self.next_entry_id
            entry_data["flattened"] = False
            entry_data["layer"] = self.current_layer
            entry_data["group"] = group_id
            for obj in entry_data.get("objects", []):
                values = obj.get("coords", [])
                obj["coords"] = [value + (dx if index % 2 == 0 else dy) for index, value in enumerate(values)]
            self._restore_entry(page, entry_data)
            entry = page["entries"][-1]
            created.append(entry)
            self._add_markup_row(entry)
            self._apply_layer_visibility(entry)
        if created:
            self._push_undo({"type": "add", "entries": created})
        return created

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
        new_zoom = max(0.4, min(2.5, float(new_zoom)))
        if abs(new_zoom - self.zoom_level) < 1e-6:
            return
        factor = new_zoom / self.zoom_level
        self.clear_selection()
        self._clear_pending()
        origin_x, origin_y = PAGE_ORIGIN
        for page in self.pages:
            for entry in page.get("entries", []):
                for item in entry.get("items", []):
                    self.canvas.scale(item, origin_x, origin_y, factor, factor)
        self.zoom_level = new_zoom
        self._update_page_surface()
        for entry in self._current_entries():
            for item in entry["items"]:
                if self.canvas.itemcget(item, "state") != "hidden":
                    self.canvas.tag_raise(item)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.zoom_label.configure(text=f"{int(self.zoom_level * 100)}%")
        self._set_status(f"Zoom {int(self.zoom_level * 100)}%")

    def on_ctrl_mousewheel(self, event):
        if event.delta > 0:
            self._set_zoom(self.zoom_level * 1.1)
        elif event.delta < 0:
            self._set_zoom(self.zoom_level / 1.1)
        return "break"

    def on_mousewheel(self, event):
        if event.state & 0x0004:
            return self.on_ctrl_mousewheel(event)
        units = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(units * 3, "units")
        return "break"

    def rotate_page(self, degrees):
        bbox = self._page_bbox()
        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        for entry in self._current_entries():
            self._rotate_entry(entry, degrees, cx, cy)
            entry["rotation_deg"] = (self._safe_float(entry.get("rotation_deg"), 0) + degrees) % 360
        page = self.pages[self.current_page]
        page["rotation"] = (int(page.get("rotation", 0)) + degrees) % 360
        self.rotation = page["rotation"]
        if self._is_pdf_page(page) and abs(degrees) % 180 == 90:
            page["width"], page["height"] = page.get("height", self.page_h), page.get("width", self.page_w)
        elif not self._is_pdf_page(page) and abs(degrees) % 180 == 90:
            page["landscape"] = not page.get("landscape", False)
        self.pdf_render_cache.clear()
        self._update_page_surface()
        self.draw_selection()
        self._set_status(f"Rotated current page to {self.rotation} deg")

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
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
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
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf"), ("DieselPDF page", "*.dieselpdf-page.json")])
        if not path:
            return
        if path.lower().endswith(".pdf"):
            self._create_print_ready_pdf(path, "Original", [self.current_page])
            self._set_status(f"Extracted page {self.current_page + 1} to PDF")
            return
        data = {"page": self._serialize_page(self.pages[self.current_page])}
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        self._set_status(f"Extracted page to {os.path.basename(path)}")

    def duplicate_page(self):
        data = self._serialize_page(self.pages[self.current_page])
        page = {key: copy.deepcopy(value) for key, value in data.items() if key != "entries"}
        page["entries"] = []
        self.pages.insert(self.current_page + 1, page)
        for entry_data in data.get("entries", []):
            clone = copy.deepcopy(entry_data)
            clone["id"] = self.next_entry_id
            self._restore_entry(page, clone)
        self.current_page += 1
        self._show_current_page()
        self._set_status("Duplicated current page")

    def merge_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        new_pages = self._pdf_pages_metadata(path)
        self.pages[self.current_page + 1:self.current_page + 1] = new_pages
        self._refresh_page_list()
        self._set_status(f"Merged {len(new_pages)} page(s) from {os.path.basename(path)}")

    def split_pdf(self):
        folder = filedialog.askdirectory(title="Choose folder for split pages")
        if not folder:
            return
        base = os.path.splitext(os.path.basename(self.current_pdf or "DieselPDF"))[0]
        for index in range(len(self.pages)):
            path = os.path.join(folder, f"{base}-page-{index + 1}.pdf")
            self._create_print_ready_pdf(path, "Original", [index])
        self._set_status(f"Split {len(self.pages)} page(s) into {folder}")

    def replace_page(self):
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        replacements = self._pdf_pages_metadata(path)
        if not replacements:
            return
        old_page = self.pages[self.current_page]
        for entry in old_page.get("entries", []):
            for item in entry.get("items", []):
                self.canvas.delete(item)
        self.pages[self.current_page] = replacements[0]
        self._show_current_page()
        self._set_status(f"Replaced page with {os.path.basename(path)} page 1")

    def swap_pages(self):
        if len(self.pages) < 2:
            self._set_status("At least two pages are needed")
            return
        target = simpledialog.askinteger("Swap Pages", f"Swap page {self.current_page + 1} with page:", minvalue=1, maxvalue=len(self.pages))
        if not target or target - 1 == self.current_page:
            return
        other = target - 1
        original = self.current_page
        self.pages[self.current_page], self.pages[other] = self.pages[other], self.pages[self.current_page]
        self.current_page = other
        self._show_current_page()
        self._set_status(f"Swapped pages {original + 1} and {target}")

    def overlay_pdf(self):
        page = self.pages[self.current_page]
        base_path = page.get("source_pdf") or self.current_pdf or self.current_file
        overlay_path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if not overlay_path or not base_path or not self._is_pdf_page(page):
            self._set_status("Overlay needs a PDF page and another PDF")
            return
        fitz = self._pdf_renderer()
        try:
            base = fitz.open(base_path)
            overlay = fitz.open(overlay_path)
            result = fitz.open()
            source_page = base.load_page(int(page.get("pdf_index", 0)))
            target = result.new_page(width=source_page.rect.width, height=source_page.rect.height)
            target.show_pdf_page(target.rect, base, int(page.get("pdf_index", 0)))
            target.show_pdf_page(target.rect, overlay, 0, overlay=True, keep_proportion=True)
            output = os.path.join(tempfile.gettempdir(), "DieselPDF", f"overlay-{os.getpid()}-{self.current_page}.pdf")
            os.makedirs(os.path.dirname(output), exist_ok=True)
            result.save(output, garbage=4, deflate=True)
            result.close(); overlay.close(); base.close()
            page.update(self._pdf_pages_metadata(output)[0])
            self.pdf_render_cache.clear()
            self._show_current_page()
            self._set_status("Overlay applied to current page")
        except Exception as exc:
            messagebox.showerror("Overlay PDF", str(exc))

    def crop_page(self):
        page = self.pages[self.current_page]
        path = page.get("source_pdf") or self.current_pdf or self.current_file
        if not self._is_pdf_page(page) or not path:
            self._set_status("Crop is available for PDF pages")
            return
        margin = simpledialog.askfloat("Crop Page", "Remove margin from each edge (%):", initialvalue=5, minvalue=0, maxvalue=40)
        if margin is None:
            return
        fitz = self._pdf_renderer()
        try:
            source = fitz.open(path)
            source_page = source.load_page(int(page.get("pdf_index", 0)))
            inset_x = source_page.rect.width * margin / 100
            inset_y = source_page.rect.height * margin / 100
            clip = fitz.Rect(inset_x, inset_y, source_page.rect.width - inset_x, source_page.rect.height - inset_y)
            result = fitz.open()
            target = result.new_page(width=clip.width, height=clip.height)
            target.show_pdf_page(target.rect, source, int(page.get("pdf_index", 0)), clip=clip)
            output = os.path.join(tempfile.gettempdir(), "DieselPDF", f"crop-{os.getpid()}-{self.current_page}.pdf")
            result.save(output, garbage=4, deflate=True)
            result.close(); source.close()
            page.update(self._pdf_pages_metadata(output)[0])
            self.pdf_render_cache.clear()
            self._show_current_page()
            self._set_status(f"Cropped {margin:g}% from each edge")
        except Exception as exc:
            messagebox.showerror("Crop Page", str(exc))

    def resize_page(self):
        paper = self.choose_paper_size("Resize Page")
        if not paper:
            return
        page = self.pages[self.current_page]
        page["display_paper"] = paper
        if not self._is_pdf_page(page):
            page["paper"] = paper
        else:
            page["width"], page["height"] = paper_pixels(paper)
        self._update_page_surface()
        self._refresh_page_list()
        self._set_status(f"Page resized to {paper}")

    def add_watermark(self):
        value = simpledialog.askstring("Watermark", "Watermark text:", initialvalue="DRAFT")
        if not value:
            return
        original_page = self.current_page
        style_color = self.line_color_var.get()
        self.line_color_var.set("#b8bcc6")
        for index in range(len(self.pages)):
            self.current_page = index
            width, height = self._page_pixel_size(self.pages[index])
            item = self.canvas.create_text(PAGE_ORIGIN[0] + width / 2, PAGE_ORIGIN[1] + height / 2, text=value, fill="#d0d3da", font=("Arial", 42, "bold"), angle=35)
            self._record_entry("Watermark", value, [item])
            if index != original_page:
                self.canvas.itemconfigure(item, state="hidden")
        self.line_color_var.set(style_color)
        self.current_page = original_page
        self._show_current_page()
        self._set_status(f"Watermark added to {len(self.pages)} page(s)")

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
        if hasattr(self, "page_picker"):
            values = [str(number) for number in range(1, len(self.pages) + 1)]
            self.page_picker.configure(values=values)
            self.page_jump_var.set(str(self.current_page + 1))
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
            self.canvas.itemconfigure(self.page_title, state="hidden")
            self.canvas.itemconfigure(self.page_subtitle, state="hidden")
            self.canvas.itemconfigure(self.page_divider, state="hidden")
        self.canvas.configure(scrollregion=(0, 0, x1 + 90, y1 + 90))
        self._update_page_label()

    def _page_pixel_size(self, page):
        if self._is_pdf_page(page):
            base_width = int(page.get("width", paper_pixels("A4")[0]))
            base_height = int(page.get("height", paper_pixels("A4")[1]))
        else:
            base_width, base_height = paper_pixels(page.get("paper", "A4"))
            if page.get("landscape"):
                base_width, base_height = base_height, base_width
        return max(1, int(base_width * self.zoom_level)), max(1, int(base_height * self.zoom_level))

    def _is_pdf_page(self, page):
        return page.get("paper") == "PDF" and bool(page.get("source_pdf") or self.current_pdf or self.current_file)

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
        path = page.get("source_pdf") or self.current_pdf or self.current_file
        if not path or not os.path.exists(path):
            self._hide_pdf_image()
            return False
        page_index = int(page.get("pdf_index", self.current_page))
        try:
            stamp = int(os.path.getmtime(path))
        except OSError:
            stamp = 0
        effective_scale = self.pdf_render_scale * self.zoom_level
        page_rotation = int(page.get("rotation", 0)) % 360
        cache_key = (path, page_index, round(effective_scale, 4), page_rotation, stamp)
        render_path = self.pdf_render_cache.get(cache_key)
        if not render_path or not os.path.exists(render_path):
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", os.path.basename(path))
            render_path = os.path.join(self.pdf_render_dir, f"{safe_name}.{page_index}.{stamp}.{int(effective_scale * 1000)}.{page_rotation}.png")
            try:
                doc = fitz.open(path)
                pdf_page = doc.load_page(page_index)
                matrix = fitz.Matrix(effective_scale, effective_scale).prerotate(page_rotation)
                pix = pdf_page.get_pixmap(matrix=matrix, alpha=False)
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
            self.page_label.configure(text=f"of {len(self.pages)}")
        if hasattr(self, "page_picker"):
            self.page_jump_var.set(str(self.current_page + 1))

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
        self.scale_units_per_px = 25.4 / (72.0 * self.pdf_render_scale)
        self.scale_unit = "mm"
        self._updating_unit = True
        try:
            self.unit_var.set("mm")
        finally:
            self._updating_unit = False
        self.scale_label_var.set(f"1 px = {self.scale_units_per_px:.4f} mm")
        self.current_page = 0
        self._set_current_document_title(os.path.basename(path))
        self._refresh_page_list()
        self._show_current_page()
        self._sync_active_document()
        self._set_status(f"Opened PDF: {os.path.basename(path)} ({len(self.pages)} page(s))")

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
                        "source_pdf": path,
                        "width": max(1, int(rect.width * self.pdf_render_scale)),
                        "height": max(1, int(rect.height * self.pdf_render_scale)),
                    })
                doc.close()
                return pages or [{"paper": "PDF", "entries": [], "pdf_index": 0, "source_pdf": path, "width": paper_pixels("A4")[0], "height": paper_pixels("A4")[1]}]
            except Exception as exc:
                messagebox.showerror("Open PDF", f"Could not read PDF pages:\n{exc}")
                return [{"paper": "PDF", "entries": [], "pdf_index": 0, "source_pdf": path, "width": paper_pixels("A4")[0], "height": paper_pixels("A4")[1]}]
        messagebox.showerror("Open PDF", "PDF rendering needs PyMuPDF. DieselPDF will install/use the local renderer package.")
        try:
            with open(path, "rb") as handle:
                data = handle.read()
            matches = re.findall(rb"/Type\s*/Page\b", data)
            count = max(1, len(matches))
        except OSError:
            count = 1
        return [{"paper": "PDF", "entries": [], "pdf_index": index, "source_pdf": path, "width": paper_pixels("A4")[0], "height": paper_pixels("A4")[1]} for index in range(count)]

    def import_image_page(self):
        paths = filedialog.askopenfilenames(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"), ("All files", "*.*")])
        if not paths:
            return
        fitz = self._pdf_renderer()
        output = os.path.join(tempfile.gettempdir(), "DieselPDF", f"images-{os.getpid()}-{len(self.pages)}.pdf")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        try:
            doc = fitz.open()
            for path in paths:
                image_doc = fitz.open(path)
                pdf_bytes = image_doc.convert_to_pdf()
                image_pdf = fitz.open("pdf", pdf_bytes)
                doc.insert_pdf(image_pdf)
                image_pdf.close(); image_doc.close()
            doc.save(output, garbage=4, deflate=True)
            doc.close()
            new_pages = self._pdf_pages_metadata(output)
            self.pages[self.current_page + 1:self.current_page + 1] = new_pages
            self.current_page += 1
            self._show_current_page()
            self._set_status(f"Imported {len(paths)} image page(s)")
        except Exception as exc:
            messagebox.showerror("Import Images", str(exc))

    def recompress_pdf(self):
        source_path = self.current_pdf or self.current_file
        if not source_path or not os.path.exists(source_path):
            self._set_status("Open a PDF before recompressing")
            return
        output = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile=os.path.splitext(os.path.basename(source_path))[0] + "-compressed.pdf")
        if not output:
            return
        fitz = self._pdf_renderer()
        try:
            doc = fitz.open(source_path)
            doc.save(output, garbage=4, clean=True, deflate=True, deflate_images=True, deflate_fonts=True)
            doc.close()
            self._set_status(f"Recompressed PDF saved: {os.path.basename(output)}")
        except Exception as exc:
            messagebox.showerror("Recompress PDF", str(exc))

    def export_pages_to_images(self, folder=None):
        folder = folder or filedialog.askdirectory(title="Export pages as PNG images")
        if not folder:
            return []
        os.makedirs(folder, exist_ok=True)
        exported = []
        fitz = self._pdf_renderer()
        for index, page in enumerate(self.pages):
            temp_pdf = os.path.join(tempfile.gettempdir(), "DieselPDF", f"export-page-{os.getpid()}-{index}.pdf")
            self._create_print_ready_pdf(temp_pdf, "Original", [index])
            doc = fitz.open(temp_pdf)
            pix = doc.load_page(0).get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            path = os.path.join(folder, f"DieselPDF-page-{index + 1}.png")
            pix.save(path)
            doc.close()
            exported.append(path)
        self._set_status(f"Exported {len(exported)} page image(s)")
        return exported

    def _document_text(self):
        lines = []
        fitz = self._pdf_renderer()
        opened = {}
        try:
            for index, page in enumerate(self.pages):
                lines.append(f"Page {index + 1}")
                path = page.get("source_pdf") or self.current_pdf or self.current_file
                if self._is_pdf_page(page) and path and fitz:
                    if path not in opened:
                        opened[path] = fitz.open(path)
                    doc = opened[path]
                    pdf_index = int(page.get("pdf_index", index))
                    if 0 <= pdf_index < len(doc):
                        lines.append(doc.load_page(pdf_index).get_text("text").strip())
                for entry in page.get("entries", []):
                    for item in entry.get("items", []):
                        if self.canvas.type(item) == "text":
                            value = self._item_option(item, "text").strip()
                            if value:
                                lines.append(value)
        finally:
            for doc in opened.values():
                doc.close()
        return "\n".join(line for line in lines if line)

    def export_office_text(self, target):
        text = self._document_text()
        if target == "Word":
            path = filedialog.asksaveasfilename(defaultextension=".rtf", filetypes=[("Word-compatible RTF", "*.rtf")], initialfile="DieselPDF-export.rtf")
            if not path:
                return
            escaped = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\par\n")
            with open(path, "w", encoding="ascii", errors="replace") as handle:
                handle.write("{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Arial;}}\\fs22 " + escaped + "}")
        elif target == "Excel":
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("Excel-compatible CSV", "*.csv")], initialfile="DieselPDF-export.csv")
            if not path:
                return
            with open(path, "w", encoding="utf-8-sig") as handle:
                handle.write("Page,Text\n")
                for index, line in enumerate(text.splitlines(), start=1):
                    handle.write(f'{index},"{line.replace(chr(34), chr(34) * 2)}"\n')
        else:
            path = filedialog.asksaveasfilename(defaultextension=".pptx", filetypes=[("PowerPoint", "*.pptx")], initialfile="DieselPDF-export.pptx")
            if not path:
                return
            image_folder = os.path.join(tempfile.gettempdir(), "DieselPDF", f"slides-{os.getpid()}")
            os.makedirs(image_folder, exist_ok=True)
            images = self.export_pages_to_images(image_folder)
            quoted_images = ",".join("'" + item.replace("'", "''") + "'" for item in images)
            escaped_path = path.replace("'", "''")
            script = (
                "$app=New-Object -ComObject PowerPoint.Application; $p=$app.Presentations.Add(); "
                f"$imgs=@({quoted_images}); foreach($img in $imgs){{$s=$p.Slides.Add($p.Slides.Count+1,12); "
                "$s.Shapes.AddPicture($img,$false,$true,0,0,$p.PageSetup.SlideWidth,$p.PageSetup.SlideHeight)|Out-Null}; "
                f"$p.SaveAs('{escaped_path}'); $p.Close(); $app.Quit()"
            )
            result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                messagebox.showerror("Export PowerPoint", "PowerPoint desktop is required for PPTX export.\n\n" + (result.stderr.strip() or "PowerPoint automation failed."))
                return
        self._set_status(f"Exported {target}-compatible document: {os.path.basename(path)}")

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
        self.scale_units_per_px = data.get("scale_units_per_px") or DEFAULT_MM_PER_BASE_PX
        self.scale_unit = data.get("scale_unit", "mm")
        self.scale_label_var.set(data.get("scale_label", "1 px = 0.3333 mm"))
        self.zoom_level = max(0.4, min(2.5, self._safe_float(data.get("zoom_level"), 1.0)))
        self.zoom_label.configure(text=f"{int(self.zoom_level * 100)}%")
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
                "source_pdf": page_data.get("source_pdf") or data.get("pdf_file"),
                "rotation": page_data.get("rotation", 0),
                "display_paper": page_data.get("display_paper"),
                "landscape": page_data.get("landscape", False),
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
        self.scale_units_per_px = DEFAULT_MM_PER_BASE_PX
        self.scale_unit = "mm"
        self.scale_label_var.set("1 px = 0.3333 mm")
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
        self.zoom_level = 1.0
        self.zoom_label.configure(text="100%")
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
            "zoom_level": self.zoom_level,
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
            "source_pdf": page.get("source_pdf"),
            "rotation": page.get("rotation", 0),
            "display_paper": page.get("display_paper"),
            "landscape": page.get("landscape", False),
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
                "angle": self._item_option(item, "angle"),
                "asset_path": entry.get("asset_path") if self.canvas.type(item) == "image" else None,
            })
        return {
            "id": entry["id"],
            "kind": entry["kind"],
            "detail": entry["detail"],
            "group": entry.get("group"),
            "flattened": entry.get("flattened", False),
            "layer": entry.get("layer", "0"),
            "stroke_color": entry.get("stroke_color", "#ff0000"),
            "fill_color": entry.get("fill_color", ""),
            "line_width": entry.get("line_width", 2),
            "line_type": entry.get("line_type", "Solid"),
            "opacity": entry.get("opacity", 100),
            "font_family": entry.get("font_family", "Arial"),
            "font_size": entry.get("font_size", 12),
            "scale_percent": entry.get("scale_percent", 100),
            "rotation_deg": entry.get("rotation_deg", 0),
            "asset_path": entry.get("asset_path"),
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
                items.append(self.canvas.create_text(obj["coords"], text=obj.get("text", ""), fill=obj.get("fill", "#111"), font=obj.get("font", "Arial 12"), anchor="nw", angle=self._safe_float(obj.get("angle"), 0)))
            elif obj["type"] == "image" and obj.get("asset_path") and os.path.exists(obj["asset_path"]):
                try:
                    image = tk.PhotoImage(file=obj["asset_path"])
                    self.snapshot_images.append(image)
                    items.append(self.canvas.create_image(obj["coords"], image=image, anchor="nw"))
                except tk.TclError:
                    pass
        entry = {
            "id": entry_data.get("id", self.next_entry_id),
            "kind": entry_data.get("kind", "Markup"),
            "detail": entry_data.get("detail", ""),
            "items": items,
            "group": entry_data.get("group"),
            "flattened": entry_data.get("flattened", False),
            "layer": entry_data.get("layer", "0"),
            "stroke_color": entry_data.get("stroke_color", "#ff0000"),
            "fill_color": entry_data.get("fill_color", ""),
            "line_width": entry_data.get("line_width", 2),
            "line_type": entry_data.get("line_type", "Solid"),
            "opacity": entry_data.get("opacity", 100),
            "font_family": entry_data.get("font_family", "Arial"),
            "font_size": entry_data.get("font_size", 12),
            "scale_percent": entry_data.get("scale_percent", 100),
            "rotation_deg": entry_data.get("rotation_deg", 0),
            "asset_path": entry_data.get("asset_path"),
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

    def show_text_to_cad_editor(self):
        dialog = tk.Toplevel(self)
        dialog.title("Text to CAD")
        dialog.transient(self)
        dialog.geometry("660x460")
        dialog.minsize(540, 360)
        dialog.configure(bg=self.colors["chrome"])
        tk.Label(dialog, text="Text to CAD", bg=self.colors["chrome"], fg=self.colors["text"], font=("Segoe UI", 16, "bold"), anchor="w").pack(fill="x", padx=18, pady=(16, 2))
        tk.Label(dialog, text="Use AutoCAD commands or plain English. Geometry is created as editable 2D CAD linework.", bg=self.colors["chrome"], fg=self.colors["muted"], font=self.font_body, anchor="w").pack(fill="x", padx=18, pady=(0, 10))
        editor = tk.Text(dialog, wrap="word", undo=True, font=("Consolas", 10), bd=0, highlightthickness=1, highlightbackground=self.colors["border"])
        editor.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        editor.insert("1.0", "LINE 0 0 100 0\nRECT 10 10 80 45\nCIRCLE 120 30 20\n# Or: draw a 100 mm horizontal line from 20,30")

        def load_script():
            path = filedialog.askopenfilename(parent=dialog, filetypes=[("Text CAD script", "*.txt"), ("All files", "*.*")])
            if not path:
                return
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    value = handle.read()
            except OSError as exc:
                messagebox.showerror("Text to CAD", str(exc), parent=dialog)
                return
            editor.delete("1.0", "end")
            editor.insert("1.0", value)

        def generate(export=False):
            value = editor.get("1.0", "end-1c")
            commands = self._parse_cad_text(value)
            prompt_commands = self._parse_cad_prompt(value)
            if not commands:
                commands = prompt_commands
            elif prompt_commands:
                commands.extend(command for command in prompt_commands if command not in commands)
            if not commands:
                messagebox.showinfo("Text to CAD", "No supported geometry was found. Try LINE, PL, RECT, CIRCLE, POLYGON, or TEXT.", parent=dialog)
                return
            self._draw_cad_commands_on_canvas(commands)
            if export:
                path = filedialog.asksaveasfilename(parent=dialog, defaultextension=".dxf", filetypes=[("DXF CAD", "*.dxf")], initialfile="DieselPDF-text-to-cad.dxf")
                if path:
                    self._write_cad_commands_dxf(commands, path)
            dialog.destroy()
            self._set_status(f"Text to CAD created {len(commands)} editable object(s)")

        buttons = tk.Frame(dialog, bg=self.colors["chrome"])
        buttons.pack(fill="x", padx=18, pady=(0, 16))
        tk.Button(buttons, text="Open Script", command=load_script, bg=self.colors["card"], fg=self.colors["text"], relief="flat", bd=0, padx=14, pady=8, font=self.font_body).pack(side="left")
        tk.Button(buttons, text="Create + Export DXF", command=lambda: generate(True), bg=self.colors["card"], fg=self.colors["blue"], relief="flat", bd=0, padx=14, pady=8, font=self.font_body).pack(side="right", padx=(8, 0))
        tk.Button(buttons, text="Create on Page", command=lambda: generate(False), bg=self.colors["blue"], fg="white", activebackground="#005bb5", activeforeground="white", relief="flat", bd=0, padx=14, pady=8, font=self.font_body).pack(side="right")
        editor.focus_set()

    def _parse_cad_prompt(self, text):
        commands = []
        layer = self.current_layer or "0"
        phrases = [part.strip() for part in re.split(r"[\n;]+|(?<=[.!?])\s+", text) if part.strip()]
        for phrase in phrases:
            clean = phrase.split("#", 1)[0].strip()
            lower = clean.lower()
            if not clean or re.match(r"^(line|l|rect|rectangle|rec|circle|c|polyline|pline|pl|polygon|pg|text|t|layer)\b", lower):
                continue
            numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", lower)]
            at_match = re.search(r"(?:at|from|center(?:ed)? at)\s*\(?\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)", lower)
            at_point = (float(at_match.group(1)), float(at_match.group(2))) if at_match else None
            if "rectangle" in lower or "box" in lower:
                size = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:mm|cm|m)?\s*[xXby]+\s*(-?\d+(?:\.\d+)?)", clean)
                if size:
                    width, height = abs(float(size.group(1))), abs(float(size.group(2)))
                    x, y = at_point or (0.0, 0.0)
                    commands.append({"type": "rect", "points": [(x, y), (x + width, y + height)], "layer": layer})
                elif len(numbers) >= 4:
                    commands.append({"type": "rect", "points": [(numbers[0], numbers[1]), (numbers[2], numbers[3])], "layer": layer})
            elif "circle" in lower:
                radius_match = re.search(r"radius\s*(?:of|=|:)?\s*(-?\d+(?:\.\d+)?)", lower)
                radius = abs(float(radius_match.group(1))) if radius_match else (abs(numbers[0]) if numbers else None)
                center = at_point
                if center is None and len(numbers) >= 3:
                    center = (numbers[-2], numbers[-1])
                if radius is not None and center is not None:
                    commands.append({"type": "circle", "center": center, "radius": radius, "layer": layer})
            elif "polyline" in lower or "polygon" in lower:
                pts = [(numbers[index], numbers[index + 1]) for index in range(0, len(numbers) - 1, 2)]
                minimum = 3 if "polygon" in lower else 2
                if len(pts) >= minimum:
                    commands.append({"type": "polygon" if "polygon" in lower else "polyline", "points": pts, "layer": layer})
            elif "line" in lower:
                length_match = re.search(r"(?:length|long)\s*(?:of|=|:)?\s*(-?\d+(?:\.\d+)?)", lower)
                if not length_match:
                    length_match = re.search(r"(?:draw|make|create|add)?\s*(?:a\s*)?(-?\d+(?:\.\d+)?)\s*(?:mm|cm|m)?\s*(?:long\s*)?(?:horizontal|vertical)?\s*(?:straight\s*)?line", lower)
                if len(numbers) >= 4 and not length_match:
                    commands.append({"type": "line", "points": [(numbers[0], numbers[1]), (numbers[2], numbers[3])], "layer": layer})
                elif length_match:
                    length = abs(float(length_match.group(1)))
                    x, y = at_point or (0.0, 0.0)
                    end = (x, y + length) if "vertical" in lower else (x + length, y)
                    commands.append({"type": "line", "points": [(x, y), end], "layer": layer})
            elif "text" in lower:
                quoted = re.search(r"[\"'](.+?)[\"']", clean)
                if quoted and at_point:
                    commands.append({"type": "text", "point": at_point, "text": quoted.group(1), "height": 12, "layer": layer})
        return commands

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
        if not self._pdf_renderer():
            messagebox.showerror("Print", "Printing needs the bundled PyMuPDF renderer.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Print - DieselPDF")
        dialog.transient(self)
        dialog.grab_set()
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors["chrome"])
        tk.Label(dialog, text="Print", bg=self.colors["chrome"], fg=self.colors["text"], font=("Segoe UI", 17, "bold"), anchor="w").pack(fill="x", padx=22, pady=(18, 4))
        tk.Label(dialog, text=f"{len(self.pages)} page(s), including visible markups and snapshots", bg=self.colors["chrome"], fg=self.colors["muted"], font=self.font_body, anchor="w").pack(fill="x", padx=22, pady=(0, 14))
        form = tk.Frame(dialog, bg=self.colors["card"], highlightthickness=1, highlightbackground=self.colors["border"], padx=14, pady=12)
        form.pack(fill="x", padx=22)
        printers = self._available_printers()
        printer_var = tk.StringVar(value=printers[0] if printers else "Windows default printer")
        copies_var = tk.IntVar(value=1)
        range_var = tk.StringVar(value="All")
        range_text_var = tk.StringVar(value=str(self.current_page + 1))
        paper_var = tk.StringVar(value="Original")
        rows = [("Printer", ttk.Combobox(form, textvariable=printer_var, values=printers or [printer_var.get()], state="readonly", width=38)), ("Copies", ttk.Spinbox(form, textvariable=copies_var, from_=1, to=99, width=8)), ("Paper", ttk.Combobox(form, textvariable=paper_var, values=["Original"] + PAPER_NAMES, state="readonly", width=20))]
        for row_index, (label, control) in enumerate(rows):
            tk.Label(form, text=label, bg=self.colors["card"], fg=self.colors["muted"], width=12, anchor="w", font=self.font_body).grid(row=row_index, column=0, sticky="w", pady=4)
            control.grid(row=row_index, column=1, sticky="w", pady=4)
        range_frame = tk.Frame(form, bg=self.colors["card"])
        range_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
        tk.Label(range_frame, text="Pages", bg=self.colors["card"], fg=self.colors["muted"], width=12, anchor="w", font=self.font_body).pack(side="left")
        for label in ["All", "Current", "Custom"]:
            tk.Radiobutton(range_frame, text=label, value=label, variable=range_var, bg=self.colors["card"], fg=self.colors["text"], font=self.font_body, bd=0).pack(side="left", padx=(0, 7))
        tk.Entry(range_frame, textvariable=range_text_var, width=12, bd=0, highlightthickness=1, highlightbackground=self.colors["border"], font=self.font_body).pack(side="left")
        tk.Label(dialog, text="Custom examples: 1-3, 5. Save PDF creates the same flattened output without sending it to a printer.", bg=self.colors["chrome"], fg=self.colors["muted"], wraplength=520, justify="left", font=self.font_small, anchor="w").pack(fill="x", padx=22, pady=14)

        def selected_pages():
            if range_var.get() == "All":
                return list(range(len(self.pages)))
            if range_var.get() == "Current":
                return [self.current_page]
            return self._parse_page_range(range_text_var.get())

        def build_path(path):
            try:
                indices = selected_pages()
                if not indices:
                    raise ValueError("No valid pages were selected")
                self._create_print_ready_pdf(path, paper_var.get(), indices)
                return True
            except Exception as exc:
                messagebox.showerror("Print", f"Could not create print PDF:\n{exc}", parent=dialog)
                return False

        def save_pdf():
            path = filedialog.asksaveasfilename(parent=dialog, defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="DieselPDF-print.pdf")
            if path and build_path(path):
                dialog.destroy()
                self._set_status(f"Print-ready PDF saved: {os.path.basename(path)}")

        def print_selected():
            path = os.path.join(tempfile.gettempdir(), "DieselPDF", f"DieselPDF-print-{os.getpid()}.pdf")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if not build_path(path):
                return
            try:
                printer = printer_var.get()
                for _copy in range(max(1, int(copies_var.get()))):
                    if printer and printer != "Windows default printer":
                        parameters = f'"{printer}"'
                        result = ctypes.windll.shell32.ShellExecuteW(None, "printto", path, parameters, None, 0)
                        if result <= 32:
                            raise OSError(f"Windows print service returned {result}")
                    else:
                        os.startfile(path, "print")
            except (AttributeError, OSError) as exc:
                messagebox.showerror("Print", f"Windows could not send the PDF to the default printer:\n{exc}", parent=dialog)
                return
            dialog.destroy()
            self._set_status(f"Sent {len(selected_pages())} page(s), {max(1, int(copies_var.get()))} copy/copies, to {printer_var.get()}")

        buttons = tk.Frame(dialog, bg=self.colors["chrome"])
        buttons.pack(fill="x", padx=22, pady=(0, 18))
        tk.Button(buttons, text="Cancel", command=dialog.destroy, bg=self.colors["card"], fg=self.colors["text"], relief="flat", bd=0, padx=14, pady=8, font=self.font_body).pack(side="left")
        tk.Button(buttons, text="Save PDF", command=save_pdf, bg=self.colors["card"], fg=self.colors["blue"], relief="flat", bd=0, padx=14, pady=8, font=self.font_body).pack(side="right", padx=(8, 0))
        tk.Button(buttons, text="Print", command=print_selected, bg=self.colors["blue"], fg="white", activebackground="#005bb5", activeforeground="white", relief="flat", bd=0, padx=18, pady=8, font=self.font_body).pack(side="right")

    def _available_printers(self):
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", "Get-CimInstance Win32_Printer | Sort-Object Default -Descending | Select-Object -ExpandProperty Name"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except (OSError, subprocess.SubprocessError):
            return []

    def _parse_page_range(self, value):
        pages = set()
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                if "-" in part:
                    start, end = [int(item.strip()) for item in part.split("-", 1)]
                    pages.update(range(min(start, end) - 1, max(start, end)))
                else:
                    pages.add(int(part) - 1)
            except ValueError:
                continue
        return sorted(index for index in pages if 0 <= index < len(self.pages))

    def _create_print_ready_pdf(self, path, paper="Original", page_indices=None):
        fitz = self._pdf_renderer()
        if not fitz:
            raise RuntimeError("PyMuPDF renderer is unavailable")
        output = fitz.open()
        sources = {}
        page_indices = list(range(len(self.pages))) if page_indices is None else list(page_indices)
        try:
            for page_index in page_indices:
                page_data = self.pages[page_index]
                source_page = None
                source = None
                source_path = page_data.get("source_pdf") or self.current_pdf or self.current_file
                if self._is_pdf_page(page_data) and source_path and os.path.exists(source_path):
                    if source_path not in sources:
                        sources[source_path] = fitz.open(source_path)
                    source = sources[source_path]
                    pdf_index = int(page_data.get("pdf_index", page_index))
                    if 0 <= pdf_index < len(source):
                        source_page = source.load_page(pdf_index)
                if paper != "Original" and paper in PAPER_MM:
                    width_mm, height_mm = PAPER_MM[paper]
                    target_width, target_height = width_mm * 72 / 25.4, height_mm * 72 / 25.4
                elif source_page is not None:
                    target_width, target_height = source_page.rect.width, source_page.rect.height
                else:
                    width_mm, height_mm = PAPER_MM.get(page_data.get("paper", "A4"), PAPER_MM["A4"])
                    target_width, target_height = width_mm * 72 / 25.4, height_mm * 72 / 25.4
                target = output.new_page(width=target_width, height=target_height)
                destination = fitz.Rect(0, 0, target_width, target_height)
                if source_page is not None:
                    ratio = min(target_width / source_page.rect.width, target_height / source_page.rect.height)
                    fitted_width = source_page.rect.width * ratio
                    fitted_height = source_page.rect.height * ratio
                    left = (target_width - fitted_width) / 2
                    top = (target_height - fitted_height) / 2
                    destination = fitz.Rect(left, top, left + fitted_width, top + fitted_height)
                    target.show_pdf_page(destination, source, int(page_data.get("pdf_index", page_index)), keep_proportion=True, rotate=int(page_data.get("rotation", 0)))
                self._draw_print_markups(fitz, target, page_data, destination)
            output.save(path, garbage=4, deflate=True)
        finally:
            for source in sources.values():
                source.close()
            output.close()
        return path

    def _draw_print_markups(self, fitz, target, page_data, destination):
        display_width, display_height = self._page_pixel_size(page_data)
        scale_x = destination.width / max(1, display_width)
        scale_y = destination.height / max(1, display_height)
        origin_x, origin_y = PAGE_ORIGIN

        def point(x, y):
            return fitz.Point(destination.x0 + (x - origin_x) * scale_x, destination.y0 + (y - origin_y) * scale_y)

        def rect(coords):
            p0 = point(coords[0], coords[1])
            p1 = point(coords[2], coords[3])
            return fitz.Rect(min(p0.x, p1.x), min(p0.y, p1.y), max(p0.x, p1.x), max(p0.y, p1.y))

        for entry in page_data.get("entries", []):
            if not self._layer_visible(entry.get("layer", "0")):
                continue
            opacity = max(0.0, min(1.0, self._safe_float(entry.get("opacity"), 100) / 100))
            for item in entry.get("items", []):
                item_type = self.canvas.type(item)
                coords = self.canvas.coords(item)
                stroke_value = self._item_option(item, "outline") if item_type in {"rectangle", "oval", "polygon"} else self._item_option(item, "fill")
                fill_value = self._item_option(item, "fill") if item_type in {"rectangle", "oval", "polygon"} else ""
                stroke = self._fitz_color(stroke_value) if stroke_value else None
                fill = self._fitz_color(fill_value) if fill_value else None
                width = max(0.25, self._safe_float(self._item_option(item, "width"), 1) * (scale_x + scale_y) / 2)
                if item_type == "line" and len(coords) >= 4:
                    points = [point(coords[index], coords[index + 1]) for index in range(0, len(coords), 2)]
                    for start, end in zip(points, points[1:]):
                        target.draw_line(start, end, color=stroke or (0, 0, 0), width=width, stroke_opacity=opacity)
                elif item_type == "rectangle" and len(coords) >= 4:
                    target.draw_rect(rect(coords), color=stroke, fill=fill, width=width, stroke_opacity=opacity, fill_opacity=opacity)
                elif item_type == "oval" and len(coords) >= 4:
                    target.draw_oval(rect(coords), color=stroke, fill=fill, width=width, stroke_opacity=opacity, fill_opacity=opacity)
                elif item_type == "polygon" and len(coords) >= 6:
                    points = [point(coords[index], coords[index + 1]) for index in range(0, len(coords), 2)]
                    shape = target.new_shape()
                    shape.draw_polyline(points + [points[0]])
                    shape.finish(color=stroke, fill=fill, width=width, stroke_opacity=opacity, fill_opacity=opacity)
                    shape.commit()
                elif item_type == "text" and coords:
                    bbox = self.canvas.bbox(item)
                    if not bbox:
                        continue
                    text_rect = rect(bbox)
                    font_size = max(4, self._safe_float(entry.get("font_size"), 12) * (scale_x + scale_y) / 2)
                    target.insert_textbox(text_rect, self._item_option(item, "text"), fontsize=font_size, fontname="helv", color=stroke or (0, 0, 0), fill_opacity=opacity)
                elif item_type == "image" and entry.get("asset_path") and os.path.exists(entry["asset_path"]):
                    bbox = self.canvas.bbox(item)
                    if bbox:
                        target.insert_image(rect(bbox), filename=entry["asset_path"], overlay=True)

    def _fitz_color(self, color):
        if not color:
            return None
        try:
            red, green, blue = self.winfo_rgb(color)
        except tk.TclError:
            return None
        return red / 65535, green / 65535, blue / 65535


if __name__ == "__main__":
    DieselPDF().mainloop()
