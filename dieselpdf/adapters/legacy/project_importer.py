from __future__ import annotations

import hashlib
import json
import mimetypes
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import NAMESPACE_URL, UUID, uuid5

from dieselpdf.adapters.legacy.canvas_coordinates import LegacyCanvasCoordinateAdapter
from dieselpdf.domain.dataset import (
    ActorRole,
    BoundingBox2D,
    DocumentDraft,
    EllipseGeometry,
    ImportBatchRecord,
    LineGeometry,
    OpaqueGeometry,
    PageDraft,
    PolygonGeometry,
    PolylineGeometry,
    ProjectDraft,
    Provenance,
    RawEntityDraft,
    RectangleGeometry,
    ReviewStatus,
    TextGeometry,
)
from dieselpdf.domain.units import LengthUnit
from dieselpdf.persistence.sqlite import DatasetRepository, ProjectBundle


@dataclass(frozen=True, slots=True)
class LegacyImportReport:
    project_id: UUID
    revision_id: UUID
    source_path: Path
    source_sha256: str
    source_unchanged: bool
    page_count: int
    entry_count: int
    source_object_count: int
    imported_entity_count: int
    supported_entity_count: int
    preserved_unsupported_count: int
    counts_by_type: Dict[str, int]
    warnings: Tuple[str, ...]
    reconciliation_artifact: Optional[Path] = None

    @property
    def complete_without_silent_loss(self) -> bool:
        return (
            self.source_unchanged
            and self.imported_entity_count == self.source_object_count
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "project_id": str(self.project_id),
            "revision_id": str(self.revision_id),
            "source_path": str(self.source_path),
            "source_sha256": self.source_sha256,
            "source_unchanged": self.source_unchanged,
            "page_count": self.page_count,
            "entry_count": self.entry_count,
            "source_object_count": self.source_object_count,
            "imported_entity_count": self.imported_entity_count,
            "supported_entity_count": self.supported_entity_count,
            "preserved_unsupported_count": self.preserved_unsupported_count,
            "counts_by_type": dict(self.counts_by_type),
            "warnings": list(self.warnings),
            "complete_without_silent_loss": self.complete_without_silent_loss,
            "reconciliation_artifact": (
                str(self.reconciliation_artifact)
                if self.reconciliation_artifact
                else None
            ),
        }


class LegacyProjectImporter:
    """Immutable importer for the existing Canvas-owned .dieselpdf.json format."""

    importer_name = "legacy-dieselpdf-json-v1"

    def __init__(self, repository: DatasetRepository) -> None:
        self.repository = repository

    def import_file(
        self,
        source_path: Path,
        *,
        project_name: Optional[str] = None,
        bundle: Optional[ProjectBundle] = None,
        actor_id: str = "legacy-importer",
    ) -> LegacyImportReport:
        source_path = Path(source_path)
        source_bytes = source_path.read_bytes()
        source_sha = hashlib.sha256(source_bytes).hexdigest()
        data = json.loads(source_bytes.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("legacy project root must be a JSON object")

        project_id = uuid5(NAMESPACE_URL, f"dieselpdf-project:{source_sha}")
        try:
            project = self.repository.get_project(project_id)
        except KeyError:
            project = self.repository.create_project(
                ProjectDraft(
                    project_id=project_id,
                    name=project_name or source_path.stem,
                    description="Imported from legacy .dieselpdf.json",
                ),
                actor_id=actor_id,
                actor_role=ActorRole.ADMIN,
                reason="Create legacy import project",
            )
        else:
            existing = self.repository.connection.execute(
                """
                SELECT 1 FROM import_batches
                WHERE project_id = ? AND source_sha256 = ?
                """,
                (str(project_id), source_sha),
            ).fetchone()
            if existing is not None:
                raise ValueError("this immutable legacy source has already been imported")

        pages = data.get("pages", [])
        if not isinstance(pages, list):
            raise ValueError("legacy pages must be a list")
        scale = float(data.get("scale_units_per_px") or 1.0)
        project_unit = LengthUnit.coerce(data.get("scale_unit", "mm"))
        document_id = uuid5(NAMESPACE_URL, f"dieselpdf-document:{source_sha}")
        warnings: List[str] = []
        counts: Counter[str] = Counter()
        entry_count = 0
        source_object_count = 0
        imported_count = 0
        supported_count = 0
        unsupported_count = 0

        with self.repository.begin_revision(
            project.project_id,
            actor_id=actor_id,
            actor_role=ActorRole.SYSTEM_IMPORTER,
            reason=f"Import immutable legacy source {source_path.name}",
        ) as revision:
            document = revision.add_document(
                DocumentDraft(
                    document_id=document_id,
                    project_id=project.project_id,
                    title=source_path.name,
                    source_path=str(source_path),
                    source_sha256=source_sha,
                    media_type=mimetypes.guess_type(source_path.name)[0]
                    or "application/json",
                )
            )

            for page_index, page_data in enumerate(pages):
                if not isinstance(page_data, dict):
                    warnings.append(f"page {page_index} was not an object and was skipped")
                    continue
                page_height = float(page_data.get("height") or 891.0)
                page_width = float(page_data.get("width") or 630.0)
                adapter = LegacyCanvasCoordinateAdapter(
                    page_height_px=page_height,
                    scale_units_per_px=scale,
                    project_unit=project_unit,
                )
                page_id = uuid5(
                    NAMESPACE_URL,
                    f"dieselpdf-page:{source_sha}:{page_index}",
                )
                page = revision.add_page(
                    PageDraft(
                        page_id=page_id,
                        project_id=project.project_id,
                        document_id=document.document_id,
                        page_index=page_index,
                        name=f"Page {page_index + 1}",
                        width=page_width,
                        height=page_height,
                        coordinate_system_id=f"legacy-page-{page_index}",
                        properties={
                            "paper": page_data.get("paper"),
                            "pdf_index": page_data.get("pdf_index"),
                            "legacy_canvas_width": page_width,
                            "legacy_canvas_height": page_height,
                        },
                    )
                )
                entries = page_data.get("entries", [])
                if not isinstance(entries, list):
                    warnings.append(f"page {page_index + 1} entries were not a list")
                    continue
                entry_count += len(entries)
                for entry_position, entry in enumerate(entries):
                    if not isinstance(entry, dict):
                        warnings.append(
                            f"page {page_index + 1} entry {entry_position} was not an object"
                        )
                        continue
                    objects = entry.get("objects", [])
                    if not isinstance(objects, list):
                        warnings.append(
                            f"page {page_index + 1} entry {entry_position} objects were not a list"
                        )
                        continue
                    source_object_count += len(objects)
                    entry_id = entry.get("id", entry_position)
                    for object_index, legacy_object in enumerate(objects):
                        if not isinstance(legacy_object, dict):
                            legacy_object = {
                                "type": "invalid",
                                "payload": legacy_object,
                                "coords": [],
                            }
                        entity_id = uuid5(
                            NAMESPACE_URL,
                            f"dieselpdf-entity:{source_sha}:{page_index}:{entry_id}:{object_index}",
                        )
                        entity_type, geometry, supported, object_warnings = self._convert_geometry(
                            legacy_object,
                            adapter,
                        )
                        warnings.extend(
                            f"page {page_index + 1} entry {entry_id} object {object_index}: {message}"
                            for message in object_warnings
                        )
                        if supported:
                            supported_count += 1
                        else:
                            unsupported_count += 1
                        counts[entity_type] += 1
                        revision.add_raw_entity(
                            RawEntityDraft(
                                entity_id=entity_id,
                                project_id=project.project_id,
                                entity_type=entity_type,
                                geometry=geometry,
                                coordinate_system_id="project",
                                layer_id=str(entry.get("layer", "0")),
                                style_id=None,
                                provenance=Provenance(
                                    source_document_id=document.document_id,
                                    source_page_id=page.page_id,
                                    source_external_id=(
                                        f"entry:{entry_id}:object:{object_index}"
                                    ),
                                    source_method=self.importer_name,
                                    source_sha256=source_sha,
                                    adapter_version="1.0",
                                    original_payload={
                                        "entry": {
                                            key: value
                                            for key, value in entry.items()
                                            if key != "objects"
                                        },
                                        "object": legacy_object,
                                    },
                                ),
                                review_status=ReviewStatus.UNREVIEWED,
                                properties={
                                    "legacy_entry_kind": entry.get("kind"),
                                    "legacy_detail": entry.get("detail"),
                                    "legacy_group": entry.get("group"),
                                    "legacy_flattened": entry.get("flattened", False),
                                    "style": {
                                        key: legacy_object.get(key)
                                        for key in (
                                            "fill",
                                            "outline",
                                            "width",
                                            "dash",
                                            "arrow",
                                            "font",
                                            "stipple",
                                        )
                                        if legacy_object.get(key) not in (None, "")
                                    },
                                },
                            )
                        )
                        imported_count += 1

            source_unchanged_at_reconciliation = hashlib.sha256(source_path.read_bytes()).hexdigest() == source_sha
            preliminary = LegacyImportReport(
                project_id=project.project_id,
                revision_id=revision.revision_id,
                source_path=source_path,
                source_sha256=source_sha,
                source_unchanged=source_unchanged_at_reconciliation,
                page_count=len(pages),
                entry_count=entry_count,
                source_object_count=source_object_count,
                imported_entity_count=imported_count,
                supported_entity_count=supported_count,
                preserved_unsupported_count=unsupported_count,
                counts_by_type=dict(counts),
                warnings=tuple(warnings),
            )
            revision.add_import_batch(
                ImportBatchRecord(
                    project_id=project.project_id,
                    revision_id=revision.revision_id,
                    source_path=str(source_path),
                    source_sha256=source_sha,
                    importer=self.importer_name,
                    imported_count=imported_count,
                    warning_count=len(warnings),
                    report=preliminary.as_dict(),
                )
            )

        source_unchanged = hashlib.sha256(source_path.read_bytes()).hexdigest() == source_sha
        artifact_path = None
        final = LegacyImportReport(
            project_id=project.project_id,
            revision_id=revision.revision_id,
            source_path=source_path,
            source_sha256=source_sha,
            source_unchanged=source_unchanged,
            page_count=len(pages),
            entry_count=entry_count,
            source_object_count=source_object_count,
            imported_entity_count=imported_count,
            supported_entity_count=supported_count,
            preserved_unsupported_count=unsupported_count,
            counts_by_type=dict(counts),
            warnings=tuple(warnings),
        )
        if bundle is not None:
            artifact_path = bundle.write_artifact_json(
                f"imports/{revision.revision_id}-legacy-reconciliation.json",
                final.as_dict(),
            )
            final = replace(final, reconciliation_artifact=artifact_path)
        if not final.complete_without_silent_loss:
            raise RuntimeError("legacy import reconciliation detected silent data loss")
        return final

    @staticmethod
    def _convert_geometry(
        legacy_object: Dict[str, Any],
        adapter: LegacyCanvasCoordinateAdapter,
    ):
        legacy_type = str(legacy_object.get("type") or "unknown").lower()
        raw_coords = legacy_object.get("coords") or []
        warnings: List[str] = []
        try:
            coords = tuple(float(value) for value in raw_coords)
        except (TypeError, ValueError):
            coords = ()
            warnings.append("coordinates were invalid and preserved as opaque payload")

        def project_points(values: Sequence[float]) -> Tuple[Tuple[float, float], ...]:
            if len(values) % 2:
                raise ValueError("coordinate list must contain X/Y pairs")
            points = []
            for index in range(0, len(values), 2):
                point = adapter.canvas_to_project(values[index], values[index + 1]).to("mm")
                points.append((point.x, point.y))
            return tuple(points)

        try:
            points = project_points(coords)
        except ValueError as exc:
            points = ()
            warnings.append(str(exc))

        if legacy_type == "line" and len(points) == 2:
            return "line", LineGeometry(start=points[0], end=points[1]), True, warnings
        if legacy_type == "line" and len(points) >= 2:
            return "polyline", PolylineGeometry(points=points), True, warnings
        if legacy_type == "polygon" and len(points) >= 3:
            return "polygon", PolygonGeometry(points=points), True, warnings
        if legacy_type == "rectangle" and len(points) >= 2:
            box = LegacyProjectImporter._bounds(points)
            return "rectangle", RectangleGeometry(**box.model_dump()), True, warnings
        if legacy_type == "oval" and len(points) >= 2:
            box = LegacyProjectImporter._bounds(points)
            return "ellipse", EllipseGeometry(**box.model_dump()), True, warnings
        if legacy_type == "text" and points:
            return (
                "text",
                TextGeometry(
                    insertion=points[0],
                    text=str(legacy_object.get("text") or ""),
                ),
                True,
                warnings,
            )

        bounds = LegacyProjectImporter._bounds(points or ((0.0, 0.0),))
        warnings.append(f"unsupported legacy object type {legacy_type!r} preserved losslessly")
        return (
            f"legacy_{legacy_type}",
            OpaqueGeometry(
                source_type=legacy_type,
                payload=legacy_object,
                declared_bounds=bounds,
            ),
            False,
            warnings,
        )

    @staticmethod
    def _bounds(points: Sequence[Tuple[float, float]]) -> BoundingBox2D:
        xs = tuple(point[0] for point in points)
        ys = tuple(point[1] for point in points)
        return BoundingBox2D(
            min_x=min(xs),
            max_x=max(xs),
            min_y=min(ys),
            max_y=max(ys),
        )
