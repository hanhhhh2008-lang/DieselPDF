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
assert app.current_tool == "select"
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

app.pages.append(module.blank_page())
app.current_page = 1
app._show_current_page()
app._apply_scale_to_current_page(0.01, "cm")
app.current_page = 0
app._show_current_page()
assert app.scale_unit == "mm"
assert abs(app.scale_units_per_px - module.DEFAULT_MM_PER_BASE_PX) < 1e-9
app.current_page = 1
app._show_current_page()
assert app.scale_unit == "cm"
assert app.scale_units_per_px == 0.01
app.pages.pop()
app.current_page = 0
app._show_current_page()

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
assert app.active_tab == "Home"
assert app.current_tool == "hand"
app._set_tool("select")

commands = app._parse_cad_prompt("draw a 3mm straight line")
assert commands == [{"type": "line", "points": [(0.0, 0.0), (3.0, 0.0)], "layer": "0"}]
before = len(app._current_entries())
app.run_ai_command("draw a 3mm straight line")
assert len(app._current_entries()) == before + 1
assert app._current_entries()[-1]["kind"] == "Line"

line_entry = app._current_entries()[-1]
app.selected_entries = [line_entry]
app.subject_var.set("RFI")
app.comment_var.set("Verify opening")
app.markup_status_var.set("Review")
app.apply_metadata_to_selected()
assert line_entry["subject"] == "RFI"
assert line_entry["comment"] == "Verify opening"
assert line_entry["status"] == "Review"
markup_values = app.markup_list.item(str(line_entry["id"]), "values")
assert markup_values[0] == "RFI"
assert markup_values[3] == "Verify opening"

app.selected_entries = [line_entry]
app.width_var.set("7")
app._schedule_style_apply()
time.sleep(0.18)
app.update()
assert float(app.canvas.itemcget(line_entry["items"][0], "width")) == 7

app._set_tool("callout")
callout_before = len(app._current_entries())
app.start_inline_text("Callout", (260, 170, 460, 250), tip=(190, 310))
app.inline_editor.insert("1.0", "Original note")
app.commit_inline_text()
callout = app._current_entries()[-1]
assert len(app._current_entries()) == callout_before + 1
assert callout["kind"] == "Callout"
arrow = next(item for item in callout["items"] if app.canvas.type(item) == "line")
text_item = next(item for item in callout["items"] if app.canvas.type(item) == "text")

app.edit_markup_text(callout)
app.inline_editor.delete("1.0", "end")
app.inline_editor.insert("1.0", "Updated engineering note")
app.commit_inline_text()
assert app.canvas.itemcget(text_item, "text") == "Updated engineering note"
assert callout["detail"] == "Updated engineering note"

app.selected_entries = [callout]
app.font_family_var.set("Calibri")
app.line_color_var.set("#0055aa")
app.apply_style_to_selected()
assert app.canvas.itemcget(text_item, "fill") == "#0055aa"
assert "Calibri" in app.canvas.itemcget(text_item, "font")

app.draw_selection()
tip_handle = next(handle for handle in app.resize_handles if handle["anchor"] == "callout_tip")
old_tip = app.canvas.coords(arrow)[-2:]
app._begin_resize(tip_handle, old_tip[0], old_tip[1])
drag_event = type("Event", (), {"x": int(old_tip[0] + 45), "y": int(old_tip[1] - 35)})()
app.on_drag(drag_event)
app.on_release(drag_event)
assert app.canvas.coords(arrow)[-2:] != old_tip

rect = next(item for item in callout["items"] if app.canvas.type(item) == "rectangle")
rect_before = app.canvas.coords(rect)[:]
app._set_tool("select")
click_event = type("Event", (), {"x": int(rect_before[0] + 12), "y": int(rect_before[1] + 12), "state": 0})()
move_event = type("Event", (), {"x": click_event.x + 30, "y": click_event.y + 20, "state": 0})()
app.on_press(click_event)
app.on_drag(move_event)
app.on_release(move_event)
rect_after = app.canvas.coords(rect)
assert rect_after[0] > rect_before[0]
assert rect_after[1] > rect_before[1]

app.known_distance_var.set("600")
app._set_tool("calibrate")
calibration_before = len(app._current_entries())
app.add_measurement_click("calibrate", 120, 180)
assert app.measurement_start is not None
app.add_measurement_click("calibrate", 420, 180)
assert app.measurement_start is None
assert len(app._current_entries()) == calibration_before + 1
calibration = app._current_entries()[-1]
assert calibration["kind"] == "Calibration"
assert abs(app.scale_units_per_px - 2.0) < 1e-9
assert abs(app.pages[0]["scale_units_per_px"] - 2.0) < 1e-9

app.known_distance_var.set("300")
app.selected_entries = [calibration]
app.apply_known_distance_to_page()
assert abs(app.scale_units_per_px - 1.0) < 1e-9

app._set_tool("distance")
distance_before = len(app._current_entries())
app.add_measurement_click("distance", 140, 240)
assert app.measurement_start is not None
app.add_measurement_click("distance", 260, 240)
assert app.measurement_start is None
assert len(app._current_entries()) == distance_before + 1
assert app._current_entries()[-1]["kind"] == "Distance"
assert app._current_entries()[-1]["detail"] == "120 mm"

distance = app._current_entries()[-1]
app.selected_entries = [calibration]
app.known_distance_var.set("600")
app.apply_known_distance_to_page()
assert distance["detail"] == "240 mm"
app.known_distance_var.set("300")
app.apply_known_distance_to_page()
assert distance["detail"] == "120 mm"

count_before = len(app._current_entries())
app._set_tool("count")
app.create_count(260, 300)
count = app._current_entries()[-1]
assert len(app._current_entries()) == count_before + 1
assert count["kind"] == "Count"
assert count["detail"].startswith("Count ")

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
