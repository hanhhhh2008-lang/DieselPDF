from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from dieselpdf.app import DatasetService
from dieselpdf.domain.dataset import (
    ActorIdentity,
    ActorRole,
    ReviewStatus,
    deterministic_stable_id,
)
from dieselpdf.persistence import ProjectStore

from .canvas_projection import CanvasProjectionMap
from .dataset_browser import DatasetCanvasRenderer, DatasetTable


class EngineeringDatasetWindow(tk.Toplevel):
    """Phase 3 database-owned dataset, review, and Canvas projection surface."""

    def __init__(self, master: tk.Misc, dataset_path: str):
        super().__init__(master)
        self.store = ProjectStore.open(dataset_path)
        self.service = DatasetService(self.store)
        self.title(f"Engineering Dataset — {self.store.project().name}")
        self.geometry("1280x760")
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.actor_name = tk.StringVar(value="Aaron Han")
        self.actor_role = tk.StringVar(value=ActorRole.ENGINEER.value)
        self.approval_authority = tk.BooleanVar(value=True)
        self._build_toolbar(dataset_path)
        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(paned, bg="#f1f3f5", highlightthickness=0)
        self.projection = CanvasProjectionMap()
        self.renderer = DatasetCanvasRenderer(self.canvas, self.projection)
        self.table = DatasetTable(paned, self.store, self._table_selected)
        paned.add(self.table, weight=1)
        paned.add(self.canvas, weight=3)
        self.canvas.bind("<Button-1>", self._canvas_selected)
        self.canvas.bind("<Configure>", lambda _event: self.after_idle(self.refresh))
        self.after_idle(self.refresh)

    def _build_toolbar(self, dataset_path: str) -> None:
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text=dataset_path).pack(side="left", padx=(0, 16))
        ttk.Label(toolbar, text="Reviewer").pack(side="left")
        ttk.Entry(toolbar, textvariable=self.actor_name, width=20).pack(side="left", padx=4)
        ttk.Combobox(
            toolbar,
            textvariable=self.actor_role,
            values=tuple(role.value for role in ActorRole),
            state="readonly",
            width=12,
        ).pack(side="left", padx=4)
        ttk.Checkbutton(
            toolbar,
            text="Engineering approval authority",
            variable=self.approval_authority,
        ).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Review Required", command=lambda: self._review(ReviewStatus.ENGINEER_REVIEW_REQUIRED)).pack(side="right", padx=3)
        ttk.Button(toolbar, text="Reject", command=lambda: self._review(ReviewStatus.REJECTED)).pack(side="right", padx=3)
        ttk.Button(toolbar, text="Engineer Approve", command=lambda: self._review(ReviewStatus.ENGINEER_APPROVED)).pack(side="right", padx=3)
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side="right", padx=3)

    def refresh(self) -> None:
        if not self.winfo_exists():
            return
        self.table.refresh()
        self.renderer.render(self.store.entities(include_superseded=True))

    def _table_selected(self, kind: str, stable_id: str) -> None:
        self.renderer.select(stable_id if kind == "entity" else None)

    def _canvas_selected(self, event: tk.Event) -> None:
        items = self.canvas.find_overlapping(event.x - 2, event.y - 2, event.x + 2, event.y + 2)
        for item in reversed(items):
            entity_id = self.projection.entity_for_item(item)
            if entity_id is not None:
                self.table.view_var.set("Raw Geometry")
                self.table.refresh()
                self.table.select_item(entity_id)
                self.renderer.select(entity_id)
                return

    def _actor(self) -> ActorIdentity:
        role = ActorRole(self.actor_role.get())
        name = self.actor_name.get().strip()
        return ActorIdentity(
            actor_id=deterministic_stable_id("actor", name, role.value),
            display_name=name,
            role=role,
            can_approve_engineering=(
                role is ActorRole.ENGINEER and self.approval_authority.get()
            ),
        )

    def _review(self, target: ReviewStatus) -> None:
        selected = self.table.selected_item()
        if selected is None or selected[0] == "revision":
            messagebox.showinfo("Engineering review", "Select a dataset entity, object, or relationship first.", parent=self)
            return
        comment = simpledialog.askstring(
            "Engineering review record",
            "Enter the evidence or reason for this decision:",
            parent=self,
        )
        if not comment or not comment.strip():
            return
        try:
            self.service.review(selected[0], selected[1], target, self._actor(), comment)
        except Exception as exc:
            messagebox.showerror("Engineering review blocked", str(exc), parent=self)
            return
        self.refresh()
        self.table.select_item(selected[1])

    def _close(self) -> None:
        self.store.close()
        self.destroy()
