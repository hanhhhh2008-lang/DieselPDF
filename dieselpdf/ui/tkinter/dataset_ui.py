from __future__ import annotations

from typing import Callable, Dict, Iterable, Optional, Protocol, Tuple
from uuid import UUID

from dieselpdf.domain.dataset import (
    EllipseGeometry,
    LineGeometry,
    OpaqueGeometry,
    PointGeometry,
    PolygonGeometry,
    PolylineGeometry,
    RawEntityRecord,
    RectangleGeometry,
    TextGeometry,
)
from dieselpdf.domain.geometry import Point2D
from dieselpdf.persistence.sqlite import DatasetRepository
from dieselpdf.ui.tkinter.canvas_projection import CanvasProjectionMap


class CanvasProtocol(Protocol):
    def create_line(self, *coords, **kwargs) -> int: ...
    def create_rectangle(self, *coords, **kwargs) -> int: ...
    def create_oval(self, *coords, **kwargs) -> int: ...
    def create_polygon(self, *coords, **kwargs) -> int: ...
    def create_text(self, *coords, **kwargs) -> int: ...
    def delete(self, item_id: int) -> None: ...


class DatasetCanvasRenderer:
    """Render database-owned raw entities into an ephemeral Tk Canvas view."""

    def __init__(
        self,
        repository: DatasetRepository,
        canvas: CanvasProtocol,
        projection: CanvasProjectionMap,
        project_to_canvas: Callable[[Point2D], Point2D],
    ) -> None:
        self.repository = repository
        self.canvas = canvas
        self.projection = projection
        self.project_to_canvas = project_to_canvas

    def render_entity(self, entity_id: UUID) -> Tuple[int, ...]:
        entity = self.repository.get_raw_entity(entity_id)
        self.clear_entity(entity_id)
        item_ids = self._render_geometry(entity)
        if not item_ids:
            return ()
        self.projection.bind(str(entity.entity_id), item_ids)
        return item_ids

    def render_entities(self, entity_ids: Iterable[UUID]) -> Dict[UUID, Tuple[int, ...]]:
        return {entity_id: self.render_entity(entity_id) for entity_id in entity_ids}

    def clear_entity(self, entity_id: UUID) -> None:
        for item_id in self.projection.items_for_entity(str(entity_id)):
            self.canvas.delete(item_id)
        self.projection.unbind_entity(str(entity_id))

    def _point(self, value: Tuple[float, float]) -> Tuple[float, float]:
        point = self.project_to_canvas(Point2D(value[0], value[1], "mm", "project"))
        return point.x, point.y

    def _render_geometry(self, entity: RawEntityRecord) -> Tuple[int, ...]:
        geometry = entity.geometry
        style = entity.properties.get("style", {})
        fill = style.get("fill") or style.get("outline") or "#111111"
        width = self._safe_width(style.get("width"))

        if isinstance(geometry, LineGeometry):
            start = self._point(geometry.start)
            end = self._point(geometry.end)
            return (self.canvas.create_line(*start, *end, fill=fill, width=width),)
        if isinstance(geometry, PolylineGeometry):
            coords = [coordinate for point in geometry.points for coordinate in self._point(point)]
            if geometry.closed:
                return (self.canvas.create_polygon(*coords, outline=fill, fill="", width=width),)
            return (self.canvas.create_line(*coords, fill=fill, width=width),)
        if isinstance(geometry, PolygonGeometry):
            coords = [coordinate for point in geometry.points for coordinate in self._point(point)]
            return (self.canvas.create_polygon(*coords, outline=fill, fill="", width=width),)
        if isinstance(geometry, RectangleGeometry):
            first = self._point((geometry.min_x, geometry.min_y))
            second = self._point((geometry.max_x, geometry.max_y))
            return (self.canvas.create_rectangle(*first, *second, outline=fill, fill="", width=width),)
        if isinstance(geometry, EllipseGeometry):
            first = self._point((geometry.min_x, geometry.min_y))
            second = self._point((geometry.max_x, geometry.max_y))
            return (self.canvas.create_oval(*first, *second, outline=fill, fill="", width=width),)
        if isinstance(geometry, TextGeometry):
            point = self._point(geometry.insertion)
            return (self.canvas.create_text(*point, text=geometry.text, fill=fill, anchor="nw"),)
        if isinstance(geometry, PointGeometry):
            x, y = self._point(geometry.point)
            radius = 2.0
            return (self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius, outline=fill, fill=fill),)
        if isinstance(geometry, OpaqueGeometry):
            return ()
        raise TypeError(f"unsupported database geometry: {type(geometry).__name__}")

    @staticmethod
    def _safe_width(value) -> float:
        try:
            width = float(value)
        except (TypeError, ValueError):
            return 1.0
        return width if width > 0 else 1.0


class DatasetTreeController:
    """Small adapter around ttk.Treeview-compatible widgets.

    It deliberately stores stable record UUIDs as row IIDs; Canvas item IDs never
    enter the durable dataset table model.
    """

    def __init__(self, treeview) -> None:
        self.treeview = treeview

    def refresh(self, rows) -> None:
        for item in tuple(self.treeview.get_children()):
            self.treeview.delete(item)
        for row in rows:
            self.treeview.insert(
                "",
                "end",
                iid=str(row.record_id),
                values=(
                    row.record_type.value,
                    row.type_name,
                    row.name_or_mark or "",
                    row.storey_id or "",
                    row.review_status.value,
                    str(row.revision_id),
                ),
            )

    def selected_record_ids(self) -> Tuple[UUID, ...]:
        values = []
        for item in self.treeview.selection():
            try:
                values.append(UUID(str(item)))
            except ValueError:
                continue
        return tuple(values)

    def select_records(self, record_ids: Iterable[UUID]) -> None:
        available = set(self.treeview.get_children())
        selected = tuple(str(value) for value in record_ids if str(value) in available)
        self.treeview.selection_set(selected)


class DatasetPanel:
    """Embeddable Tk dataset table with filter and cross-selection callbacks."""

    COLUMNS = ("record_type", "type", "mark", "storey", "status", "revision")

    def __init__(
        self,
        parent,
        service,
        *,
        select_canvas_items: Optional[Callable[[Tuple[int, ...]], None]] = None,
    ) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.service = service
        self.select_canvas_items = select_canvas_items
        self.frame = ttk.Frame(parent)
        self.search_var = tk.StringVar()
        search = ttk.Entry(self.frame, textvariable=self.search_var)
        search.pack(fill="x", padx=4, pady=4)
        search.bind("<KeyRelease>", lambda _event: self.refresh())
        self.tree = ttk.Treeview(
            self.frame,
            columns=self.COLUMNS,
            show="headings",
            selectmode="extended",
        )
        headings = {
            "record_type": "Dataset",
            "type": "Type",
            "mark": "Mark",
            "storey": "Storey",
            "status": "Review",
            "revision": "Revision",
        }
        widths = {
            "record_type": 90,
            "type": 100,
            "mark": 100,
            "storey": 80,
            "status": 85,
            "revision": 240,
        }
        for column in self.COLUMNS:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], stretch=column == "revision")
        self.tree.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.controller = DatasetTreeController(self.tree)
        self.tree.bind("<<TreeviewSelect>>", self._dataset_selected)
        self.refresh()

    def pack(self, *args, **kwargs):
        return self.frame.pack(*args, **kwargs)

    def grid(self, *args, **kwargs):
        return self.frame.grid(*args, **kwargs)

    def refresh(self) -> None:
        from dieselpdf.app import DatasetFilter

        self.controller.refresh(
            self.service.rows(DatasetFilter(text=self.search_var.get()))
        )

    def select_from_canvas(self, canvas_item_ids: Iterable[int]) -> None:
        self.controller.select_records(
            self.service.dataset_ids_for_canvas_items(canvas_item_ids)
        )

    def _dataset_selected(self, _event=None) -> None:
        if self.select_canvas_items is None:
            return
        self.select_canvas_items(
            self.service.canvas_items_for_dataset_ids(
                self.controller.selected_record_ids()
            )
        )
