from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from dieselpdf.domain.dataset import (
    ActorIdentity,
    ActorRole,
    AuditEvent,
    BoundingBox2D,
    DocumentRecord,
    EntityType,
    GeometryEntity,
    GeometryPayload,
    ProjectRecord,
    PageRecord,
    ReviewStatus,
    RevisionRecord,
    SourceTrace,
    deterministic_stable_id,
)
from dieselpdf.domain.units import LengthUnit
from dieselpdf.persistence import ProjectStore

from .canvas_coordinates import LegacyCanvasCoordinateAdapter


@dataclass(frozen=True, slots=True)
class LegacyImportReport:
    source_path: str
    source_hash: str
    project_id: str
    revision_id: str
    page_count: int
    entry_count: int
    object_count: int
    entity_count: int
    unmapped_fields: Tuple[str, ...]
    warnings: Tuple[str, ...]
    original_preserved: bool

    def as_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["unmapped_fields"] = list(self.unmapped_fields)
        value["warnings"] = list(self.warnings)
        return value


class LegacyProjectImporter:
    """Immutable `.dieselpdf.json` to Phase 3 dataset migration boundary."""

    TOP_LEVEL_FIELDS = {
        "app",
        "source_file",
        "pdf_file",
        "scale_units_per_px",
        "scale_unit",
        "scale_label",
        "unit",
        "layers",
        "current_layer",
        "bookmarks",
        "pages",
    }
    PAGE_FIELDS = {"paper", "pdf_index", "width", "height", "entries"}
    ENTRY_FIELDS = {"id", "kind", "detail", "group", "flattened", "layer", "objects"}
    OBJECT_FIELDS = {
        "type",
        "coords",
        "fill",
        "outline",
        "width",
        "dash",
        "arrow",
        "text",
        "font",
        "stipple",
    }

    def import_file(
        self,
        source_path: str,
        dataset_path: str,
        *,
        project_name: Optional[str] = None,
        actor: Optional[ActorIdentity] = None,
    ) -> LegacyImportReport:
        source = Path(source_path)
        original_bytes = source.read_bytes()
        source_hash = hashlib.sha256(original_bytes).hexdigest()
        try:
            payload = json.loads(original_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid legacy DieselPDF JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("legacy DieselPDF project must contain a JSON object")
        pages = payload.get("pages", [])
        if not isinstance(pages, list):
            raise ValueError("legacy project pages must be a list")

        imported_at = datetime.now(timezone.utc)
        project_id = deterministic_stable_id("project", "legacy", source_hash)
        revision_id = deterministic_stable_id("revision", source_hash, "initial-import")
        importer = actor or ActorIdentity(
            actor_id=deterministic_stable_id("actor", "dieselpdf", "legacy-importer"),
            display_name="DieselPDF legacy importer",
            role=ActorRole.IMPORTER,
        )
        project = ProjectRecord(
            project_id=project_id,
            name=project_name or source.stem.replace(".dieselpdf", ""),
            description="Migrated from a legacy .dieselpdf.json project",
            created_at=imported_at,
            metadata={
                "legacy_source_path": str(source.resolve()),
                "legacy_source_hash": source_hash,
                "legacy_app": payload.get("app"),
                "legacy_source_file": payload.get("source_file"),
                "legacy_pdf_file": payload.get("pdf_file"),
                "legacy_layers": payload.get("layers", []),
                "legacy_bookmarks": payload.get("bookmarks", []),
            },
        )
        revision = RevisionRecord(
            revision_id=revision_id,
            project_id=project_id,
            sequence=1,
            author=importer,
            reason="Immutable import of legacy .dieselpdf.json project",
            created_at=imported_at,
            source_revision=source_hash,
        )

        warnings: List[str] = []
        unmapped_fields = self._collect_unmapped_fields(payload)
        entities: List[GeometryEntity] = []
        legacy_ids: List[Tuple[str, str, str]] = []
        entry_count = 0
        object_count = 0
        calibrated = payload.get("scale_units_per_px") is not None
        try:
            source_unit = LengthUnit.coerce(payload.get("scale_unit", payload.get("unit", "mm")))
        except (TypeError, ValueError):
            source_unit = LengthUnit.MILLIMETRE
            calibrated = False
            warnings.append("legacy scale unit was invalid; geometry remains in page-local pixels")
        if not calibrated:
            warnings.append(
                "project was not calibrated; raw geometry remains in page-local pixel coordinates"
            )

        document_id = deterministic_stable_id("document", source_hash, "legacy-project")
        document = DocumentRecord(
            document_id=document_id,
            project_id=project_id,
            revision_id=revision_id,
            file_name=source.name,
            source_path=str(source.resolve()),
            media_type="application/vnd.dieselpdf.legacy+json",
            source_hash=source_hash,
            created_at=imported_at,
            metadata={
                "referenced_source_file": payload.get("source_file"),
                "referenced_pdf_file": payload.get("pdf_file"),
            },
        )
        page_records: List[PageRecord] = []
        for page_index, page in enumerate(pages):
            if not isinstance(page, dict):
                warnings.append(f"page {page_index} was not an object and was preserved only in raw import data")
                continue
            page_id = deterministic_stable_id("page", source_hash, page_index)
            page_height = self._positive_number(page.get("height")) or self._paper_height(page.get("paper"))
            adapter = None
            if calibrated:
                adapter = LegacyCanvasCoordinateAdapter(
                    page_height_px=page_height,
                    scale_units_per_px=float(payload["scale_units_per_px"]),
                    project_unit=source_unit,
                )
            page_records.append(
                PageRecord(
                    page_id=page_id,
                    project_id=project_id,
                    document_id=document_id,
                    revision_id=revision_id,
                    page_index=page_index,
                    paper_name=str(page.get("paper")) if page.get("paper") else None,
                    width=self._positive_number(page.get("width")),
                    height=page_height,
                    coordinate_system_id=(
                        "project" if adapter is not None else f"legacy_canvas_page_{page_index + 1}"
                    ),
                    created_at=imported_at,
                    metadata={
                        "legacy_pdf_index": page.get("pdf_index"),
                        "calibrated": adapter is not None,
                    },
                )
            )
            entries = page.get("entries", [])
            if not isinstance(entries, list):
                warnings.append(f"page {page_index} entries were not a list and were preserved only in raw import data")
                continue
            for entry_index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    warnings.append(
                        f"page {page_index} entry {entry_index} was not an object and was preserved only in raw import data"
                    )
                    continue
                entry_count += 1
                objects = entry.get("objects", [])
                if not isinstance(objects, list):
                    warnings.append(
                        f"page {page_index} entry {entry_index} objects were not a list and were preserved only in raw import data"
                    )
                    continue
                for object_index, legacy_object in enumerate(objects):
                    object_count += 1
                    legacy_key = f"page:{page_index}/entry:{entry_index}/object:{object_index}"
                    entity_id = deterministic_stable_id("entity", source_hash, legacy_key)
                    legacy_ids.append((legacy_key, "entity", entity_id))
                    entity, warning = self._entity_from_object(
                        legacy_object,
                        entry,
                        legacy_key,
                        entity_id,
                        project_id,
                        revision_id,
                        document_id,
                        page_id,
                        source_hash,
                        adapter,
                        page_index,
                        imported_at,
                    )
                    entities.append(entity)
                    if warning:
                        warnings.append(warning)

        report = LegacyImportReport(
            source_path=str(source.resolve()),
            source_hash=source_hash,
            project_id=project_id,
            revision_id=revision_id,
            page_count=len(pages),
            entry_count=entry_count,
            object_count=object_count,
            entity_count=len(entities),
            unmapped_fields=tuple(sorted(unmapped_fields)),
            warnings=tuple(warnings),
            original_preserved=hashlib.sha256(source.read_bytes()).hexdigest() == source_hash,
        )
        if report.entity_count != report.object_count:
            raise RuntimeError("legacy migration would silently lose Canvas objects")

        import_id = deterministic_stable_id("import", source_hash, "legacy-project")
        event_id = deterministic_stable_id("event", source_hash, "legacy-import-complete")
        with ProjectStore.create(dataset_path, project, revision) as store:
            store.add_document(document)
            for page_record in page_records:
                store.add_page(page_record)
            for entity in entities:
                store.add_entity(entity)
            store.record_import_run(
                import_id=import_id,
                project_id=project_id,
                revision_id=revision_id,
                source_path=str(source.resolve()),
                source_hash=source_hash,
                source_payload=payload,
                report=report.as_dict(),
                created_at=imported_at.isoformat(),
                legacy_ids=legacy_ids,
            )
            store.record_audit_event(
                AuditEvent(
                    event_id=event_id,
                    project_id=project_id,
                    revision_id=revision_id,
                    event_type="legacy_project_imported",
                    actor=importer,
                    payload=report.as_dict(),
                    created_at=imported_at,
                )
            )
            if store.integrity_check() != ("ok",):
                raise RuntimeError("SQLite integrity check failed after legacy import")
        return report

    def _entity_from_object(
        self,
        legacy_object: object,
        entry: Mapping[str, Any],
        legacy_key: str,
        entity_id: str,
        project_id: str,
        revision_id: str,
        document_id: str,
        page_id: str,
        source_hash: str,
        adapter: Optional[LegacyCanvasCoordinateAdapter],
        page_index: int,
        imported_at: datetime,
    ) -> Tuple[GeometryEntity, Optional[str]]:
        warning = None
        if not isinstance(legacy_object, dict):
            legacy_object = {"raw_value": legacy_object, "type": "unsupported", "coords": []}
            warning = f"{legacy_key} was not an object; stored as an unresolved block reference"
        legacy_type = str(legacy_object.get("type", "unsupported")).strip().lower()
        entity_type = self._entity_type(legacy_type, legacy_object)
        raw_coordinates, coordinate_warning = self._numeric_coordinates(legacy_object.get("coords", []))
        if coordinate_warning:
            warning = f"{legacy_key}: {coordinate_warning}"
        coordinates = self._transform_coordinates(raw_coordinates, adapter)
        coordinate_system_id = "project" if adapter is not None else f"legacy_canvas_page_{page_index + 1}"
        unit = "mm" if adapter is not None else "px"
        if entity_type is EntityType.CIRCLE and len(coordinates) == 4:
            x0, y0, x1, y1 = coordinates
            if abs(abs(x1 - x0) - abs(y1 - y0)) <= 1e-6:
                coordinates = [(x0 + x1) / 2.0, (y0 + y1) / 2.0, abs(x1 - x0) / 2.0]
            else:
                entity_type = EntityType.ELLIPSE
        if entity_type is EntityType.TEXT and len(coordinates) != 2:
            entity_type = EntityType.BLOCK_REFERENCE
        if entity_type in {EntityType.LINE, EntityType.RECTANGLE} and len(coordinates) != 4:
            entity_type = EntityType.BLOCK_REFERENCE
        if entity_type in {EntityType.POLYLINE, EntityType.POLYGON} and (
            len(coordinates) < 4 or len(coordinates) % 2
        ):
            entity_type = EntityType.BLOCK_REFERENCE
        bbox = self._bounding_box(coordinates)
        payload = GeometryPayload(
            entity_type=entity_type,
            coordinate_system_id=coordinate_system_id,
            unit=unit,
            coordinates=coordinates,
            text=str(legacy_object.get("text", "")) if entity_type is EntityType.TEXT else None,
            closed=entity_type is EntityType.POLYGON,
            parameters={
                "legacy_type": legacy_type,
                "legacy_entry_id": entry.get("id"),
                "legacy_kind": entry.get("kind"),
                "legacy_detail": entry.get("detail"),
                "legacy_group": entry.get("group"),
                "legacy_layer": entry.get("layer", "0"),
                "legacy_visual_properties": {
                    key: value
                    for key, value in legacy_object.items()
                    if key not in {"type", "coords", "text"}
                },
                "legacy_raw_coordinates": legacy_object.get("coords", []),
            },
        )
        return (
            GeometryEntity(
                entity_id=entity_id,
                project_id=project_id,
                revision_id=revision_id,
                version_sequence=1,
                review_status=ReviewStatus.ENGINEER_REVIEW_REQUIRED,
                entity_type=entity_type,
                geometry=payload,
                bounding_box=bbox,
                coordinate_system_id=coordinate_system_id,
                source=SourceTrace(
                    source_document_id=document_id,
                    source_page_id=page_id,
                    source_external_id=legacy_key,
                    source_method="legacy_dieselpdf_json_import",
                    source_hash=source_hash,
                    evidence_summary="Original JSON payload retained in immutable import_runs record",
                ),
                created_at=imported_at,
                updated_at=imported_at,
            ),
            warning,
        )

    def _collect_unmapped_fields(self, payload: Mapping[str, Any]) -> set[str]:
        result = {f"project.{key}" for key in payload if key not in self.TOP_LEVEL_FIELDS}
        pages = payload.get("pages", [])
        if not isinstance(pages, list):
            return result
        for page_index, page in enumerate(pages):
            if not isinstance(page, dict):
                continue
            result.update(
                f"pages[{page_index}].{key}" for key in page if key not in self.PAGE_FIELDS
            )
            entries = page.get("entries", [])
            if not isinstance(entries, list):
                continue
            for entry_index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    continue
                result.update(
                    f"pages[{page_index}].entries[{entry_index}].{key}"
                    for key in entry
                    if key not in self.ENTRY_FIELDS
                )
                objects = entry.get("objects", [])
                if not isinstance(objects, list):
                    continue
                for object_index, legacy_object in enumerate(objects):
                    if not isinstance(legacy_object, dict):
                        continue
                    result.update(
                        f"pages[{page_index}].entries[{entry_index}].objects[{object_index}].{key}"
                        for key in legacy_object
                        if key not in self.OBJECT_FIELDS
                    )
        return result

    @staticmethod
    def _entity_type(legacy_type: str, value: Mapping[str, Any]) -> EntityType:
        mapping = {
            "line": EntityType.POLYLINE if len(value.get("coords", [])) > 4 else EntityType.LINE,
            "rectangle": EntityType.RECTANGLE,
            "oval": EntityType.CIRCLE,
            "polygon": EntityType.POLYGON,
            "text": EntityType.TEXT,
            "arc": EntityType.ARC,
            "image": EntityType.IMAGE,
        }
        return mapping.get(legacy_type, EntityType.BLOCK_REFERENCE)

    @staticmethod
    def _numeric_coordinates(value: object) -> Tuple[List[float], Optional[str]]:
        if not isinstance(value, (list, tuple)):
            return [], "coordinates were not a list; raw value retained"
        result: List[float] = []
        for item in value:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                return [], "coordinates contained a non-numeric value; raw value retained"
            number = float(item)
            if not math.isfinite(number):
                return [], "coordinates contained a non-finite value; raw value retained"
            result.append(number)
        if len(result) % 2:
            return result, "coordinates contained an unmatched ordinate; raw value retained"
        return result, None

    @staticmethod
    def _transform_coordinates(
        coordinates: Sequence[float], adapter: Optional[LegacyCanvasCoordinateAdapter]
    ) -> List[float]:
        if adapter is None:
            return list(coordinates)
        result: List[float] = []
        for index in range(0, len(coordinates), 2):
            point = adapter.canvas_to_project(coordinates[index], coordinates[index + 1]).to(
                LengthUnit.MILLIMETRE
            )
            result.extend((point.x, point.y))
        return result

    @staticmethod
    def _bounding_box(coordinates: Sequence[float]) -> BoundingBox2D:
        if len(coordinates) < 2:
            return BoundingBox2D(min_x=0, min_y=0, max_x=0, max_y=0)
        if len(coordinates) == 3:
            x, y, radius = coordinates
            return BoundingBox2D(
                min_x=x - abs(radius),
                min_y=y - abs(radius),
                max_x=x + abs(radius),
                max_y=y + abs(radius),
            )
        xs = coordinates[0::2]
        ys = coordinates[1::2]
        return BoundingBox2D(min_x=min(xs), min_y=min(ys), max_x=max(xs), max_y=max(ys))

    @staticmethod
    def _positive_number(value: object) -> Optional[float]:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        result = float(value)
        return result if math.isfinite(result) and result > 0 else None

    @staticmethod
    def _paper_height(value: object) -> float:
        paper_heights = {"A0": 3567.0, "A1": 2523.0, "A2": 1782.0, "A3": 1260.0, "A4": 891.0}
        return paper_heights.get(str(value).upper(), 891.0)
