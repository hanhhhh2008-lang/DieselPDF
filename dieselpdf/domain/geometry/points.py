from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple, Union

from dieselpdf.domain.common import finite_float
from dieselpdf.domain.units import LengthUnit


@dataclass(frozen=True, slots=True)
class Point2D:
    x: float
    y: float
    unit: LengthUnit = LengthUnit.MILLIMETRE
    coordinate_system_id: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", finite_float(self.x, "x"))
        object.__setattr__(self, "y", finite_float(self.y, "y"))
        object.__setattr__(self, "unit", LengthUnit.coerce(self.unit))
        if self.coordinate_system_id is not None:
            if not isinstance(self.coordinate_system_id, str) or not self.coordinate_system_id.strip():
                raise ValueError("coordinate_system_id must be a non-empty string when provided")
            object.__setattr__(self, "coordinate_system_id", self.coordinate_system_id.strip())

    def to(self, target_unit: Union[LengthUnit, str]) -> "Point2D":
        target = LengthUnit.coerce(target_unit)
        if target is self.unit:
            return self
        if not self.unit.is_physical or not target.is_physical:
            raise ValueError("pixel conversion requires an explicit coordinate transform")
        from dieselpdf.domain.units import Length

        return Point2D(
            Length(self.x, self.unit).to(target).value,
            Length(self.y, self.unit).to(target).value,
            target,
            self.coordinate_system_id,
        )

    def distance_to(self, other: "Point2D") -> float:
        self._require_compatible_system(other)
        converted = other.to(self.unit)
        return math.hypot(self.x - converted.x, self.y - converted.y)

    def almost_equals(self, other: "Point2D", tolerance: float) -> bool:
        return self.distance_to(other) <= finite_float(tolerance, "tolerance")

    def as_tuple(self) -> Tuple[float, float]:
        return self.x, self.y

    def _require_compatible_system(self, other: "Point2D") -> None:
        if not isinstance(other, Point2D):
            raise TypeError("other must be a Point2D")
        if (
            self.coordinate_system_id is not None
            and other.coordinate_system_id is not None
            and self.coordinate_system_id != other.coordinate_system_id
        ):
            raise ValueError("points belong to different coordinate systems")


@dataclass(frozen=True, slots=True)
class Point3D:
    x: float
    y: float
    z: float
    unit: LengthUnit = LengthUnit.MILLIMETRE
    coordinate_system_id: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", finite_float(self.x, "x"))
        object.__setattr__(self, "y", finite_float(self.y, "y"))
        object.__setattr__(self, "z", finite_float(self.z, "z"))
        object.__setattr__(self, "unit", LengthUnit.coerce(self.unit))
        if self.coordinate_system_id is not None:
            if not isinstance(self.coordinate_system_id, str) or not self.coordinate_system_id.strip():
                raise ValueError("coordinate_system_id must be a non-empty string when provided")
            object.__setattr__(self, "coordinate_system_id", self.coordinate_system_id.strip())

    def to(self, target_unit: Union[LengthUnit, str]) -> "Point3D":
        target = LengthUnit.coerce(target_unit)
        if target is self.unit:
            return self
        if not self.unit.is_physical or not target.is_physical:
            raise ValueError("pixel conversion requires an explicit coordinate transform")
        from dieselpdf.domain.units import Length

        return Point3D(
            Length(self.x, self.unit).to(target).value,
            Length(self.y, self.unit).to(target).value,
            Length(self.z, self.unit).to(target).value,
            target,
            self.coordinate_system_id,
        )


@dataclass(frozen=True, slots=True)
class Vector2D:
    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", finite_float(self.x, "x"))
        object.__setattr__(self, "y", finite_float(self.y, "y"))
        if self.length == 0:
            raise ValueError("vector must not be zero length")

    @property
    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> "Vector2D":
        magnitude = self.length
        return Vector2D(self.x / magnitude, self.y / magnitude)

    def perpendicular_left(self) -> "Vector2D":
        unit = self.normalized()
        return Vector2D(-unit.y, unit.x)

    def dot(self, other: "Vector2D") -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: "Vector2D") -> float:
        return self.x * other.y - self.y * other.x
