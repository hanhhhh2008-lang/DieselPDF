import importlib.machinery
import importlib.util
import os
import tempfile
import time


APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PATH = os.path.join(APP_DIR, "DieselPDF.pyw")
loader = importlib.machinery.SourceFileLoader("dieselpdf_app", APP_PATH)
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)

app = module.DieselPDF()
app.withdraw()
app.update_idletasks()

assert app.active_tab == "Home"
assert app.current_tool == "hand"
assert app.canvas.itemcget(app.page_title, "state") == "hidden"
assert app.scale_unit == "mm"
assert app._measure_label(300) == "100 mm"

app.unit_var.set("cm")
app.update_idletasks()
assert app._measure_label(300) == "10 cm"
app.unit_var.set("m")
app.update_idletasks()
assert app._measure_label(300) == "0.1 m"
app.unit_var.set("mm")
app.update_idletasks()

tabs = ["Home", "Markup", "Measure", "Properties", "Organize", "Convert", "Studio", "OCR", "Help"]
for tab in tabs:
    app._select_tab(tab)
    app.update_idletasks()
    assert app.active_tab == tab
    assert app.ribbon.winfo_children(), tab
    buttons = []
    pending = list(app.ribbon.winfo_children())
    while pending:
        widget = pending.pop()
        pending.extend(widget.winfo_children())
        if widget.winfo_class() == "Button":
            buttons.append(widget)
    assert buttons, tab
    assert all(button.cget("command") for button in buttons), tab

app._escape_current()
assert app.active_tab == "Markup"
assert app.current_tool == "select"
app._set_tool("hand")

commands = app._parse_cad_prompt("draw a 3mm straight line")
assert commands == [{"type": "line", "points": [(0.0, 0.0), (3.0, 0.0)], "layer": "0"}]
before = len(app._current_entries())
app.run_ai_command("draw a 3mm straight line")
assert len(app._current_entries()) == before + 1
assert app._current_entries()[-1]["kind"] == "Line"

line_entry = app._current_entries()[-1]
app.selected_entries = [line_entry]
app.width_var.set("7")
app._schedule_style_apply()
time.sleep(0.18)
app.update()
assert float(app.canvas.itemcget(line_entry["items"][0], "width")) == 7

library_before = len(app._current_entries())
for category, name, kind in module.DEFAULT_TOOL_SETS:
    if kind == "recent":
        continue
    created = app.insert_library_tool({"source": "builtin", "name": name, "kind": kind})
    assert created, (category, name, kind)
assert len(app._current_entries()) == library_before + len(module.DEFAULT_TOOL_SETS) - 1

app.selected_entries = app._current_entries()[-2:]
app.group_selected()
group_id = app.selected_entries[0].get("group")
assert group_id and all(entry.get("group") == group_id for entry in app.selected_entries)
app.ungroup_selected()
assert all(entry.get("group") is None for entry in app.selected_entries)

fitz = app._pdf_renderer()
assert fitz is not None
work = os.path.join(tempfile.gettempdir(), "DieselPDF", "smoke")
os.makedirs(work, exist_ok=True)
source_path = os.path.join(work, "source.pdf")
doc = fitz.open()
for number in range(1, 4):
    page = doc.new_page(width=420, height=600)
    page.insert_text((40, 60), f"DieselPDF smoke page {number}", fontsize=16)
doc.save(source_path)
doc.close()

app.new_project_without_prompt()
app.current_file = source_path
app.current_pdf = source_path
app.pages = app._pdf_pages_metadata(source_path)
app.current_page = 0
app._show_current_page()
app.update_idletasks()
assert len(app.pages) == 3
assert app.pdf_page_item is not None
state = app.canvas.itemcget(app.pdf_page_item, "state")
assert state in {"", "normal"}, (state, app.status_label.cget("text"), app.pages[0])

scale = app.pdf_render_scale * app.zoom_level
app.select_text_at(module.PAGE_ORIGIN[0] + 60 * scale, module.PAGE_ORIGIN[1] + 55 * scale)
app.create_snapshot(
    module.PAGE_ORIGIN[0] + 20,
    module.PAGE_ORIGIN[1] + 20,
    module.PAGE_ORIGIN[0] + 180,
    module.PAGE_ORIGIN[1] + 100,
)
assert any(entry["kind"] == "Snapshot" for entry in app._current_entries())

print_path = os.path.join(work, "print.pdf")
single_path = os.path.join(work, "single.pdf")
app._create_print_ready_pdf(print_path, "A4")
app._create_print_ready_pdf(single_path, "Original", [1])
with fitz.open(print_path) as printed:
    assert len(printed) == 3
with fitz.open(single_path) as printed:
    assert len(printed) == 1

count = len(app.pages)
app.duplicate_page()
assert len(app.pages) == count + 1

images = app.export_pages_to_images(os.path.join(work, "images"))
assert len(images) == len(app.pages)
assert all(os.path.exists(path) for path in images)

app.destroy()
print("dieselpdf-smoke-ok")
