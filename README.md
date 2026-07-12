# DieselPDF Desktop App

DieselPDF is a native Windows desktop prototype built with Python and Tkinter. The interface uses a cleaner Apple-style visual direction with icon-first toolbars, document tabs, soft panels, and a calmer document canvas.

Run `Launch-DieselPDF-App.cmd` to open the app.

Included workflow areas:
- Bluebeam-style ribbon layout with icon buttons, short labels, and hover status labels
- Open existing PDF files with rendered pages behind the markup layer
- Markup tools: line, circle, cloud, arrow, polyline, rectangle, polygon, pencil, eraser, text box, and callout
- Measurement tools: calibration, distance, perimeter, area, scale, mm/cm/m units, endpoint snapping, and paper-size selection
- Selection resizing with blue drag handles
- Right-click group/ungroup; selecting one item in a group selects the whole group
- Multi-document tabs from the plus button beside `New Document*`
- Panels: bookmarks, markups, pages, layers, and saved library items
- Project save/open using `.dieselpdf.json`

PDF page rendering is handled by the local PyMuPDF package in `vendor_pymupdf`. True OCR still requires a dedicated OCR engine.
