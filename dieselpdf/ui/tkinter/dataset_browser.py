from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable, Dict, Iterable, Optional, Tuple

from dieselpdf.domain.dataset import EntityType, GeometryEntity, ReviewStatus
from dieselpdf.persistence import ProjectStore

from .canvas_projection import CanvasProjectionMap


_STATUS_COLOURS = {
    ReviewStatus.WORKING: "#0071e3",
    ReviewStatus.AI_PROPOSED: "#8e44ad",
    ReviewStatus.ENGINEER_REVIEW_REQUIRED: "#ff9500",
    ReviewStatus.ENGINEER_APPROVED: "#16883f",
    ReviewStatus.REJECTED: "#d70015",
    ReviewStatus.SUPERSEDED: "#8e8e93",
}


@dataclass(frozen=True, slots=True)
class ViewportProjector:
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    width: float
    height: float
    padding: float = 32.0

    @classmethod
    def fit(
        cls,
        entities: Iterable[GeometryEntity],
        width: float,
        height: float,
        padding: float = 32.0,
    ) -> "ViewportProjector":
        values = tuple(entities)
        if not values:
            return cls(0, 0, 1, 1, width, height, padding)
        min_x = min(item.bounding_box.min_x for item in values)
        min_y = min(item.bounding_box.min_y for item in values)
        max_x = max(item.bounding_box.max_x for item in values)
        max_y = max(item.bounding_box.max_y for item in values)
        if min_x == max_x:
            max_x += 1
        if min_y == max_y:
            max_y += 1
        return cls(min_x, min_y, max_x, max_y, width, height, padding)

    @property
    def scale(self) -> float:
        available_width = max(1.0, self.width - 2 * self.padding)
        available_height = max(1.0, self.height - 2 * self.padding)
        return min(
            available_width / (self.max_x - self.min_x),
            available_height / (self.max_y - self.min_y),
        )

    def point(self, entity: GeometryEntity, x: float, y: float) -> Tuple[float, float]:
        canvas_x = self.padding + (x - self.min_x) * self.scale
        if entity.geometry.unit == "px":
            canvas_y = self.padding + (y - self.min_y) * self.scale
        else:
            canvas_y = self.height - self.padding - (y - self.min_y) * self.scale
        return canvas_x, canvas_y


class DatasetCanvasRenderer:
    """Render current database-owned entities onto a Tk Canvas projection."""

    def __init__(self, canvas: tk.Canvas, projection: Optional[CanvasProjectionMap] = None):
        self.canvas = canvas
        self.projection = projection if projection is not None else CanvasProjectionMap()
        self.entities: Dict[str, GeometryEntity] = {}

    def render(self, entities: Iterable[GeometryEntity]) -> CanvasProjectionMap:
        values = tuple(entities)
        self.canvas.delete("diesel_dataset")
        self.projection.clear()
        self.entities = {entity.entity_id: entity for entity in values}
        width = max(400, int(self.canvas.winfo_width()))
        height = max(300, int(self.canvas.winfo_height()))
        projector = ViewportProjector.fit(values, width, height)
        for entity in values:
            items = self._render_entity(entity, projector)
            if items:
                self.projection.bind(entity.entity_id, items)
        return self.projection

    def select(self, entity_id: Optional[str]) -> None:
        for stable_id, entity in self.entities.items():
            selected = stable_id == entity_id
            colour = "#ff2d55" if selected else _STATUS_COLOURS[entity.review_status]
            for item in self.projection.items_for_entity(stable_id):
                kind = self.canvas.type(item)
                if kind in {"rectangle", "oval", "polygon"}:
                    self.canvas.itemconfigure(item, outline=colour, width=3 if selected else 2)
                elif kind == "text":
                    self.canvas.itemconfigure(item, fill=colour)
                else:
                    self.canvas.itemconfigure(item, fill=colour, width=3 if selected else 2)

    def _render_entity(
        self, entity: GeometryEntity, projector: ViewportProjector
    ) -> Tuple[int, ...]:
        geometry = entity.geometry
        coordinates = geometry.coordinates
        colour = _STATUS_COLOURS[entity.review_status]
        tags = ("diesel_dataset", entity.entity_id)

        def points(values: Iterable[float]) -> list[float]:
            raw = list(values)
            result: list[float] = []
            for index in range(0, len(raw), 2):
                result.extend(projector.point(entity, raw[index], raw[index + 1]))
            return result

        if entity.entity_type is EntityType.POINT and len(coordinates) == 2:
            x, y = projector.point(entity, coordinates[0], coordinates[1])
            return (self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=colour, outline=colour, tags=tags),)
        if entity.entity_type in {EntityType.LINE, EntityType.POLYLINE, EntityType.LEADER, EntityType.DIMENSION}:
            return (self.canvas.create_line(*points(coordinates), fill=colour, width=2, tags=tags),)
        if entity.entity_type is EntityType.POLYGON:
            return (self.canvas.create_polygon(*points(coordinates), fill="", outline=colour, width=2, tags=tags),)
        if entity.entity_type is EntityType.RECTANGLE and len(coordinates) == 4:
            x0, y0 = projector.point(entity, coordinates[0], coordinates[1])
            x1, y1 = projector.point(entity, coordinates[2], coordinates[3])
            return (self.canvas.create_rectangle(x0, y0, x1, y1, fill="", outline=colour, width=2, tags=tags),)
        if entity.entity_type is EntityType.CIRCLE and len(coordinates) == 3:
            x, y = projector.point(entity, coordinates[0], coordinates[1])
            radius = abs(coordinates[2]) * projector.scale
            return (self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill="", outline=colour, width=2, tags=tags),)
        if entity.entity_type is EntityType.ELLIPSE and len(coordinates) == 4:
            x0, y0 = projector.point(entity, coordinates[0], coordinates[1])
            x1, y1 = projector.point(entity, coordinates[2], coordinates[3])
            return (self.canvas.create_oval(x0, y0, x1, y1, fill="", outline=colour, width=2, tags=tags),)
        if entity.entity_type is EntityType.TEXT and len(coordinates) == 2:
            x, y = projector.point(entity, coordinates[0], coordinates[1])
            return (self.canvas.create_text(x, y, text=geometry.text or "", fill=colour, anchor="sw", tags=tags),)
        box = entity.bounding_box
        x0, y0 = projector.point(entity, box.min_x, box.min_y)
        x1, y1 = projector.point(entity, box.max_x, box.max_y)
        item = self.canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            fill="",
            outline=colour,
            width=2,
            dash=(5, 3),
            tags=tags,
        )
        return (item,)


class DatasetTable(ttk.Frame):
    VIEW_KINDS = ("Raw Geometry", "Semantic Objects", "Relationships", "Revisions")

    def __init__(
        self,
        master: tk.Misc,
        store: ProjectStore,
        on_select: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        super().__init__(master)
        self.store = store
        self.on_select = on_select
        self.view_var = tk.StringVar(value=self.VIEW_KINDS[0])
        self.kind_by_id: Dict[str, str] = {}
        chooser = ttk.Combobox(
            self,
            textvariable=self.view_var,
            values=self.VIEW_KINDS,
            state="readonly",
        )
        chooser.pack(fill="x", padx=8, pady=8)
        chooser.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        columns = ("type", "status", "revision")
        self.tree = ttk.Treeview(self, columns=columns, show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Stable ID")
        self.tree.heading("type", text="Type")
        self.tree.heading("status", text="Review status")
        self.tree.heading("revision", text="Revision")
        self.tree.column("#0", width=250, stretch=True)
        self.tree.column("type", width=120)
        self.tree.column("status", width=150)
        self.tree.column("revision", width=100)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8))
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)
        self.refresh()

    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.kind_by_id.clear()
        view = self.view_var.get()
        if view == "Raw Geometry":
            rows = (
                (value.entity_id, value.entity_type.value, value.review_status.value, value.revision_id, "entity")
                for value in self.store.entities(include_superseded=True)
            )
        elif view == "Semantic Objects":
            rows = (
                (value.object_id, value.object_type, value.review_status.value, value.revision_id, "semantic_object")
                for value in self.store.semantic_objects(include_superseded=True)
            )
        elif view == "Relationships":
            rows = (
                (
                    value.relationship_id,
                    value.relationship_type.value,
                    value.review_status.value,
                    value.revision_id,
                    "relationship",
                )
                for value in self.store.relationships(include_superseded=True)
            )
        else:
            rows = (
                (value.revision_id, value.status.value, value.author.display_name, str(value.sequence), "revision")
                for value in self.store.revisions()
            )
        for stable_id, value_type, status, revision, kind in rows:
            self.kind_by_id[stable_id] = kind
            self.tree.insert("", "end", iid=stable_id, text=stable_id, values=(value_type, status, revision))

    def selected_item(self) -> Optional[Tuple[str, str]]:
        selected = self.tree.selection()
        if not selected:
            return None
        stable_id = selected[0]
        return self.kind_by_id[stable_id], stable_id

    def select_item(self, stable_id: str) -> None:
        if self.tree.exists(stable_id):
            self.tree.selection_set(stable_id)
            self.tree.see(stable_id)

    def _selection_changed(self, _event: object) -> None:
        selected = self.selected_item()
        if selected is not None and self.on_select is not None:
            self.on_select(*selected)
