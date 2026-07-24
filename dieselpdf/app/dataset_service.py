from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Protocol, Tuple
from uuid import UUID

from dieselpdf.domain.dataset import DatasetRow, RecordType, ReviewStatus
from dieselpdf.persistence.sqlite import DatasetRepository


class ProjectionMap(Protocol):
    def items_for_entity(self, entity_id: str) -> Tuple[int, ...]: ...
    def entities_for_items(self, canvas_item_ids: Iterable[int]) -> Tuple[str, ...]: ...


@dataclass(frozen=True, slots=True)
class DatasetFilter:
    record_types: Tuple[RecordType, ...] = (
        RecordType.RAW_ENTITY,
        RecordType.SEMANTIC_OBJECT,
    )
    review_statuses: Tuple[ReviewStatus, ...] = tuple(ReviewStatus)
    storey_id: Optional[str] = None
    text: str = ""


class DatasetService:
    """Application-facing dataset table and cross-selection service."""

    def __init__(
        self,
        repository: DatasetRepository,
        project_id: UUID,
        projection: ProjectionMap,
    ) -> None:
        self.repository = repository
        self.project_id = project_id
        self.projection = projection

    def rows(self, filter_: Optional[DatasetFilter] = None) -> Tuple[DatasetRow, ...]:
        filter_ = filter_ or DatasetFilter()
        text = filter_.text.strip().lower()
        values = []
        for row in self.repository.dataset_rows(self.project_id):
            if row.record_type not in filter_.record_types:
                continue
            if row.review_status not in filter_.review_statuses:
                continue
            if filter_.storey_id is not None and row.storey_id != filter_.storey_id:
                continue
            if text:
                haystack = " ".join(
                    value
                    for value in (
                        row.type_name,
                        row.name_or_mark or "",
                        row.storey_id or "",
                        str(row.record_id),
                    )
                    if value
                ).lower()
                if text not in haystack:
                    continue
            values.append(row)
        return tuple(values)

    def canvas_items_for_dataset_ids(self, record_ids: Iterable[UUID]) -> Tuple[int, ...]:
        items = set()
        for record_id in record_ids:
            direct = self.projection.items_for_entity(str(record_id))
            if direct:
                items.update(direct)
                continue
            try:
                semantic = self.repository.get_semantic_object(record_id)
            except KeyError:
                continue
            for entity_id in semantic.source_entity_ids:
                items.update(self.projection.items_for_entity(str(entity_id)))
        return tuple(sorted(items))

    def dataset_ids_for_canvas_items(self, item_ids: Iterable[int]) -> Tuple[UUID, ...]:
        values = set()
        for entity_id in self.projection.entities_for_items(item_ids):
            try:
                raw_id = UUID(entity_id)
            except ValueError:
                continue
            values.add(raw_id)
            values.update(self.repository.semantic_object_ids_for_entity(raw_id))
        return tuple(sorted(values, key=str))
