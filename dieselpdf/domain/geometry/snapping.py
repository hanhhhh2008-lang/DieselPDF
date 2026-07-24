from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Tuple

from dieselpdf.domain.common import non_empty_identifier
from dieselpdf.domain.geometry.grids import GridSystem
from dieselpdf.domain.geometry.points import Point2D
from dieselpdf.domain.geometry.tolerances import ToleranceProfile


class SnapKind(Enum):
    GRID_INTERSECTION = "grid_intersection"
    GRID_LINE = "grid_line"
    NODE = "node"
    ENDPOINT = "endpoint"
    MIDPOINT = "midpoint"
    NEAREST = "nearest"


class MergeDecision(Enum):
    AUTO_MERGE = "auto_merge"
    SUGGEST_MERGE = "suggest_merge"
    KEEP_SEPARATE = "keep_separate"


_DEFAULT_PRIORITY = {
    SnapKind.NODE: 10,
    SnapKind.GRID_INTERSECTION: 20,
    SnapKind.ENDPOINT: 30,
    SnapKind.MIDPOINT: 40,
    SnapKind.GRID_LINE: 50,
    SnapKind.NEAREST: 90,
}


@dataclass(frozen=True, slots=True)
class SnapCandidate:
    candidate_id: str
    point: Point2D
    kind: SnapKind
    source_id: Optional[str] = None
    priority: Optional[int] = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_id",
            non_empty_identifier(self.candidate_id, "candidate_id"),
        )
        if not isinstance(self.kind, SnapKind):
            raise TypeError("kind must be a SnapKind")
        if self.source_id is not None:
            object.__setattr__(
                self,
                "source_id",
                non_empty_identifier(self.source_id, "source_id"),
            )
        if self.priority is not None and (
            isinstance(self.priority, bool) or not isinstance(self.priority, int)
        ):
            raise TypeError("priority must be an integer")

    @property
    def effective_priority(self) -> int:
        return _DEFAULT_PRIORITY[self.kind] if self.priority is None else self.priority


@dataclass(frozen=True, slots=True)
class SnapResult:
    query: Point2D
    snapped_point: Point2D
    candidate: SnapCandidate
    distance: float


@dataclass(frozen=True, slots=True)
class MergeAssessment:
    first: Point2D
    second: Point2D
    distance: float
    decision: MergeDecision


class SnappingService:
    def __init__(self, profile: ToleranceProfile) -> None:
        if not isinstance(profile, ToleranceProfile):
            raise TypeError("profile must be a ToleranceProfile")
        self.profile = profile

    def snap(
        self,
        query: Point2D,
        candidates: Iterable[SnapCandidate],
        *,
        maximum_distance: Optional[float] = None,
    ) -> Optional[SnapResult]:
        maximum = (
            self.profile.snap_distance.to(query.unit).value
            if maximum_distance is None
            else float(maximum_distance)
        )
        if maximum < 0:
            raise ValueError("maximum_distance must not be negative")

        ranked = []
        for candidate in candidates:
            distance = query.distance_to(candidate.point)
            if distance <= maximum:
                ranked.append(
                    (
                        candidate.effective_priority,
                        distance,
                        candidate.candidate_id,
                        candidate,
                    )
                )
        if not ranked:
            return None
        _, distance, _, selected = min(ranked)
        return SnapResult(query, selected.point, selected, distance)

    def snap_from_pointer(
        self,
        query: Point2D,
        candidates: Iterable[SnapCandidate],
        *,
        project_units_per_pixel: float,
    ) -> Optional[SnapResult]:
        """Snap using a zoom-aware screen radius capped in project space."""

        maximum = self.profile.pointer_snap_distance(
            project_units_per_pixel,
            query.unit,
        ).value
        return self.snap(query, candidates, maximum_distance=maximum)

    def grid_candidates(
        self,
        query: Point2D,
        grid_system: GridSystem,
    ) -> Tuple[SnapCandidate, ...]:
        candidates = []
        for value in grid_system.intersections():
            candidates.append(
                SnapCandidate(
                    f"grid-intersection:{value.first_grid_id}:{value.second_grid_id}",
                    value.point,
                    SnapKind.GRID_INTERSECTION,
                    f"{value.first_grid_id}/{value.second_grid_id}",
                )
            )
        for line in grid_system.lines:
            candidates.append(
                SnapCandidate(
                    f"grid-line:{line.grid_id}",
                    line.project(query),
                    SnapKind.GRID_LINE,
                    line.grid_id,
                )
            )
        return tuple(candidates)

    def snap_to_grid(
        self,
        query: Point2D,
        grid_system: GridSystem,
    ) -> Optional[SnapResult]:
        return self.snap(query, self.grid_candidates(query, grid_system))

    def assess_merge(self, first: Point2D, second: Point2D) -> MergeAssessment:
        distance = first.distance_to(second)
        automatic = self.profile.node_merge_distance.to(first.unit).value
        suggestion = self.profile.merge_suggestion_distance.to(first.unit).value
        if distance <= automatic:
            decision = MergeDecision.AUTO_MERGE
        elif distance <= suggestion:
            decision = MergeDecision.SUGGEST_MERGE
        else:
            decision = MergeDecision.KEEP_SEPARATE
        return MergeAssessment(first, second, distance, decision)

    def merge_suggestions(
        self,
        points: Iterable[Point2D],
    ) -> Tuple[MergeAssessment, ...]:
        values = self._normalise_points(points)
        suggestions = []
        for index, first in enumerate(values):
            for second in values[index + 1 :]:
                assessment = self.assess_merge(first, second)
                if assessment.decision is MergeDecision.SUGGEST_MERGE:
                    suggestions.append(assessment)
        return tuple(suggestions)

    def merge_points(self, points: Iterable[Point2D]) -> Tuple[Point2D, ...]:
        """Automatically merge only points inside the strict merge band."""

        converted = self._normalise_points(points)
        if not converted:
            return ()
        tolerance = self.profile.node_merge_distance.to(converted[0].unit).value
        merged = []
        for point in converted:
            if not merged or all(
                point.distance_to(existing) > tolerance for existing in merged
            ):
                merged.append(point)
        return tuple(merged)

    @staticmethod
    def _normalise_points(points: Iterable[Point2D]) -> Tuple[Point2D, ...]:
        values = tuple(points)
        if not values:
            return ()
        base_unit = values[0].unit
        base_system = values[0].coordinate_system_id
        converted = []
        for point in values:
            if (
                point.coordinate_system_id not in (None, base_system)
                and base_system is not None
            ):
                raise ValueError("cannot merge points from different coordinate systems")
            converted.append(point if point.unit is base_unit else point.to(base_unit))
        converted.sort(key=lambda item: (item.x, item.y))
        return tuple(converted)
