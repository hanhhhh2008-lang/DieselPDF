# DieselPDF Desktop App

DieselPDF is a native Windows desktop PDF review, markup, measurement, and takeoff application built with Python and Tkinter. Its tab-specific ribbon keeps the current workflow visible without crowding unrelated tools onto the screen.

## Quick start

Windows: run `Launch-DieselPDF-App.cmd`.

macOS: run `Setup-DieselPDF-macOS.command` once, then use
`Launch-DieselPDF-App.command`. The app now prefers platform-installed
PyMuPDF and ezdxf packages and falls back to the bundled Windows packages only
when necessary.

Manual installation:

```text
python3 -m pip install -r requirements-desktop.txt
python3 DieselPDF.pyw
```

Included workflow areas:
- Bluebeam-style ribbon layout with icon buttons, short labels, and hover status labels
- File menu with new/open, save/save-as, flattened PDF export, print, and close commands
- Home review tools: Hand, Select, Select Text, Snapshot, zoom, and whole-page rotation
- Open existing PDF files with rendered pages behind the markup layer
- Markup tools: line, circle, cloud, arrow, polyline, rectangle, polygon, pencil, eraser, text box, and callout
- Measurement tools: two-click calibration and distance, perimeter, area, numbered counts, mm/cm/m units, endpoint snapping, and paper-size selection
- Page-specific calibration: click two known endpoints, enter the real distance in Properties, and apply the calculated scale to the current page
- Editable markup information: subject, comment, and review status feed the Markups List and CSV export
- Endpoint-priority object snap for lines, plus midpoint, intersection, extension, center, quadrant, nearest, and insertion modes
- Polyline drawing starts at the first click and shows a live next-segment preview; double-click or right-click finishes it
- Text boxes and callouts are typed directly on the page with `Ctrl+Enter` or click-away to finish
- Working selected-object properties: stroke/fill colors, line thickness, opacity 0-100%, scale, rotation, line type, font, and font size
- Property edits apply live as soon as a value changes; no Enter key or Apply click is required
- Selection transforms: resize handles, 90/180-degree rotation, horizontal/vertical mirror, group/ungroup, and flatten/lock
- Multipage PDF navigation with a page picker, previous/next buttons, `Page Up`/`Page Down`, and `Ctrl` + mouse wheel zoom
- Print setup with detected Windows printers, copies, page ranges, paper sizes, flattened markups, and Save PDF
- AutoCAD-style command aliases: `L`, `PL`, `REC`, `C`, `CO`/`CP`, `M`, `O`, `RO`, `SC`, `E`, `G`, `X`, `Z`, `PAN`, `TEXT`, `OSNAP`, `ORTHO`, and `PLOT`
- CAD command line: `LINE`, `RECT`, `CIRCLE`, `PLINE`, `TEXT`, `OSNAP`, `ORTHO`, `OTRACK`, `CADTEXT`, `TEXTCAD`, `PDFCAD`, `EXPORTDXF`, and `EXPORTPDF`
- CAD conversion helpers: DXF to text report, text-script to DXF/PDF, PDF vector/text extraction to DXF, and current-page DXF/PDF export
- Selection resizing with blue drag handles
- Right-click group/ungroup; selecting one item in a group selects the whole group
- Multi-document tabs from the plus button beside `New Document*`
- Bluebeam-style Tool Chest with Recent Tools, General, Review, Takeoff, Construction, Safety, and My Tools sets
- Editable built-in symbols include stamps, revision delta, check mark, distance/area/count takeoff tools, scale bar, north arrow, door opening, warning, and fire point
- Save selected groups into My Tools, insert them again as editable grouped markups, and export a detailed Markups list to CSV
- Panels: Tool Chest, bookmarks, markups, pages, layers, and reusable library items
- Page organization: insert, delete, extract, duplicate, merge, split, replace, swap, overlay, crop, resize, rotate, and watermark
- Conversion tools: image import/export, PDF recompression, Word-compatible RTF, Excel-compatible CSV, PowerPoint export, and CAD exchange
- Project save/open using `.dieselpdf.json`
- Startup opens in Select mode; `Esc` cancels the current operation and returns to Hand review mode on the Home tab
- User-created text can be reopened with Select Text or a double-click, then restyled and moved like other markups
- Callouts are editable text boxes with an independently draggable arrow-tip handle for changing leader direction
- Engineering Tool Chest sets include structural steel, concrete, mechanical pipe/valve/pump, electrical, survey, excavation, and safety symbols

PDF page rendering is handled by the local PyMuPDF package in `vendor_pymupdf`. CAD exchange is handled by local `ezdxf` packages in `vendor_cad_py311`. PowerPoint export uses an installed Microsoft PowerPoint desktop application. True image OCR and live multi-user Studio sessions still require dedicated service integrations.

Run the regression smoke test with:

```text
python tests/smoke.py
```

Text CAD script examples:

```text
LAYER Framing
LINE 0 0 100 0
RECT 10 10 80 45
CIRCLE 120 30 20
TEXT 0 70 DieselPDF text to CAD
```

Plain-English examples also work in the Text to CAD panel or command bar:

```text
draw a 100 mm horizontal line from 20,30
draw a 3mm straight line
create a 40 x 25 rectangle at 5,10
make a circle radius 12 at 80,50
```

The text-to-CAD workflow follows the editable-script approach popularized by [CADAM](https://github.com/Adam-CAD/CADAM), while DieselPDF keeps its 2D PDF markup geometry native and exports it through the bundled [ezdxf](https://github.com/mozman/ezdxf) engine. CADAM's GPL web/3D stack is not copied into the desktop application.

## Design references

DieselPDF follows familiar review workflows described in Bluebeam's official documentation, including page calibration before takeoff, reusable Tool Chest items, and a Markups List with subject, comments, and status. DieselPDF is an independent project and does not include or redistribute Bluebeam software or manuals.

- Page scale and calibration: https://support.bluebeam.com/user-manual/menus/tools/set-page-scale.html
- Tool Chest guide: https://support.bluebeam.com/revu/features/tool-chest-guide.html
- Revu Starter Kit: https://support.bluebeam.com/revu/resources/revu-21-starter-kit.html
