from __future__ import annotations

from typing import Dict, Iterable, Tuple

from dieselpdf.domain.common import non_empty_identifier
from dieselpdf.domain.geometry import AffineTransform2D, GridLine2D, GridSystem, Point2D, Vector2D


class GridManager:
    """In-memory Phase 2 application service for immutable grid systems.

    Persistence is deliberately deferred to Phase 3. Every mutation replaces a
    GridSystem value, making future command/audit integration straightforward.
    """

    def __init__(self, systems: Iterable[GridSystem] = ()) -> None:
        self._systems: Dict[str, GridSystem] = {}
        for system in systems:
            self.register(system)

    def register(self, system: GridSystem, *, replace: bool = False) -> GridSystem:
        if not isinstance(system, GridSystem):
            raise TypeError("system must be a GridSystem")
        if system.grid_system_id in self._systems and not replace:
            raise ValueError(f"grid system {system.grid_system_id!r} already exists")
        self._systems[system.grid_system_id] = system
        return system

    def get(self, grid_system_id: str) -> GridSystem:
        identifier = non_empty_identifier(grid_system_id, "grid_system_id")
        try:
            return self._systems[identifier]
        except KeyError as exc:
            raise KeyError(identifier) from exc

    def all(self) -> Tuple[GridSystem, ...]:
        return tuple(self._systems[key] for key in sorted(self._systems))

    def remove(self, grid_system_id: str) -> GridSystem:
        identifier = non_empty_identifier(grid_system_id, "grid_system_id")
        try:
            return self._systems.pop(identifier)
        except KeyError as exc:
            raise KeyError(identifier) from exc

    def upsert_line(self, grid_system_id: str, line: GridLine2D) -> GridSystem:
        system = self.get(grid_system_id)
        lines = [existing for existing in system.lines if existing.grid_id != line.grid_id]
        lines.append(line)
        updated = GridSystem(system.grid_system_id, system.name, lines)
        self._systems[system.grid_system_id] = updated
        return updated

    def remove_line(self, grid_system_id: str, grid_id: str) -> GridSystem:
        system = self.get(grid_system_id)
        identifier = non_empty_identifier(grid_id, "grid_id")
        lines = [line for line in system.lines if line.grid_id != identifier]
        if len(lines) == len(system.lines):
            raise KeyError(identifier)
        updated = GridSystem(system.grid_system_id, system.name, lines)
        self._systems[system.grid_system_id] = updated
        return updated

    def copy_transformed(self, source_grid_system_id: str, new_grid_system_id: str, new_name: str, transform: AffineTransform2D) -> GridSystem:
        source = self.get(source_grid_system_id)
        transformed_lines = []
        for line in source.lines:
            if line.origin.coordinate_system_id not in (None, transform.source.coordinate_system_id):
                raise ValueError("grid line and transform source coordinate systems differ")
            origin = transform.apply(line.origin)
            direction_point = Point2D(line.origin.x + line.direction.x,line.origin.y + line.direction.y,line.origin.unit,line.origin.coordinate_system_id)
            transformed_direction_point = transform.apply(direction_point)
            direction = Vector2D(transformed_direction_point.x - origin.x,transformed_direction_point.y - origin.y)
            transformed_lines.append(GridLine2D(line.grid_id,line.label,origin,direction,line.group,line.extent_start,line.extent_end))
        copied = GridSystem(new_grid_system_id, new_name, transformed_lines)
        return self.register(copied)
