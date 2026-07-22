from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Union

from dieselpdf.domain.common import finite_float


class LengthUnit(Enum):
    PIXEL = "px"
    PDF_POINT = "pt"
    MILLIMETRE = "mm"
    CENTIMETRE = "cm"
    METRE = "m"
    INCH = "in"
    FOOT = "ft"

    @classmethod
    def coerce(cls, value: Union["LengthUnit", str]) -> "LengthUnit":
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise TypeError("unit must be a LengthUnit or unit string")
        normalized = value.strip().lower()
        aliases = {
            "pixel": "px",
            "pixels": "px",
            "point": "pt",
            "points": "pt",
            "millimeter": "mm",
            "millimeters": "mm",
            "millimetre": "mm",
            "millimetres": "mm",
            "centimeter": "cm",
            "centimeters": "cm",
            "centimetre": "cm",
            "centimetres": "cm",
            "meter": "m",
            "meters": "m",
            "metre": "m",
            "metres": "m",
            "inch": "in",
            "inches": "in",
            "foot": "ft",
            "feet": "ft",
        }
        normalized = aliases.get(normalized, normalized)
        try:
            return cls(normalized)
        except ValueError as exc:
            raise ValueError(f"unsupported length unit: {value!r}") from exc

    @property
    def is_physical(self) -> bool:
        return self is not LengthUnit.PIXEL


_MM_PER_UNIT = {
    LengthUnit.PDF_POINT: 25.4 / 72.0,
    LengthUnit.MILLIMETRE: 1.0,
    LengthUnit.CENTIMETRE: 10.0,
    LengthUnit.METRE: 1000.0,
    LengthUnit.INCH: 25.4,
    LengthUnit.FOOT: 304.8,
}


@dataclass(frozen=True, slots=True)
class Length:
    value: float
    unit: LengthUnit = LengthUnit.MILLIMETRE

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", finite_float(self.value, "value"))
        object.__setattr__(self, "unit", LengthUnit.coerce(self.unit))

    def to(self, target_unit: Union[LengthUnit, str]) -> "Length":
        target = LengthUnit.coerce(target_unit)
        if target is self.unit:
            return self
        if not self.unit.is_physical or not target.is_physical:
            raise ValueError("pixel conversion requires an explicit coordinate transform")
        millimetres = self.value * _MM_PER_UNIT[self.unit]
        return Length(millimetres / _MM_PER_UNIT[target], target)

    @property
    def mm(self) -> float:
        return self.to(LengthUnit.MILLIMETRE).value

    def __add__(self, other: "Length") -> "Length":
        if not isinstance(other, Length):
            return NotImplemented
        return Length(self.value + other.to(self.unit).value, self.unit)

    def __sub__(self, other: "Length") -> "Length":
        if not isinstance(other, Length):
            return NotImplemented
        return Length(self.value - other.to(self.unit).value, self.unit)

    def __mul__(self, scalar: float) -> "Length":
        return Length(self.value * finite_float(scalar, "scalar"), self.unit)

    __rmul__ = __mul__

    def __truediv__(self, scalar: float) -> "Length":
        divisor = finite_float(scalar, "scalar")
        if divisor == 0:
            raise ZeroDivisionError("length division by zero")
        return Length(self.value / divisor, self.unit)
