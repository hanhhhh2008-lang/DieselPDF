from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict

from dieselpdf.domain.common import finite_float, non_empty_identifier
from dieselpdf.domain.units import Length, LengthUnit


class SourceQuality(Enum):
    NATIVE_CAD = "native_cad"
    VECTOR_PDF = "vector_pdf"
    RASTER_PDF = "raster_pdf"
    MANUAL = "manual"
    GRID = "grid"


@dataclass(frozen=True, slots=True)
class ToleranceProfile:
    profile_id: str
    source_quality: SourceQuality
    snap_distance: Length
    node_merge_distance: Length
    calibration_residual: Length
    round_trip_distance: Length
    angular_degrees: float = 0.1

    def __post_init__(self) -> None:
        object.__setattr__(self, "profile_id", non_empty_identifier(self.profile_id, "profile_id"))
        if not isinstance(self.source_quality, SourceQuality):
            raise TypeError("source_quality must be a SourceQuality")
        for field_name in ("snap_distance","node_merge_distance","calibration_residual","round_trip_distance"):
            value=getattr(self,field_name)
            if not isinstance(value,Length): raise TypeError(f"{field_name} must be a Length")
            if not value.unit.is_physical: raise ValueError(f"{field_name} must use a physical unit")
            if value.mm < 0: raise ValueError(f"{field_name} must not be negative")
        angle=finite_float(self.angular_degrees,"angular_degrees")
        if angle < 0: raise ValueError("angular_degrees must not be negative")
        object.__setattr__(self,"angular_degrees",angle)


def default_tolerance_profiles() -> Dict[SourceQuality,ToleranceProfile]:
    """Return configurable software-processing defaults, not design tolerances."""
    mm=LengthUnit.MILLIMETRE
    return {
        SourceQuality.NATIVE_CAD:ToleranceProfile("native-cad-v1",SourceQuality.NATIVE_CAD,Length(.10,mm),Length(.10,mm),Length(.05,mm),Length(.01,mm),.01),
        SourceQuality.VECTOR_PDF:ToleranceProfile("vector-pdf-v1",SourceQuality.VECTOR_PDF,Length(1,mm),Length(1,mm),Length(1,mm),Length(.5,mm),.1),
        SourceQuality.RASTER_PDF:ToleranceProfile("raster-pdf-v1",SourceQuality.RASTER_PDF,Length(5,mm),Length(5,mm),Length(10,mm),Length(5,mm),.5),
        SourceQuality.MANUAL:ToleranceProfile("manual-v1",SourceQuality.MANUAL,Length(1,mm),Length(1,mm),Length(1,mm),Length(.5,mm),.1),
        SourceQuality.GRID:ToleranceProfile("grid-v1",SourceQuality.GRID,Length(1,mm),Length(.5,mm),Length(.5,mm),Length(.25,mm),.05),
    }
