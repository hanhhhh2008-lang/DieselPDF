from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Union

from dieselpdf.domain.common import finite_float, non_empty_identifier
from dieselpdf.domain.units import Length, LengthUnit


class SourceQuality(Enum):
    NATIVE_CAD = "native_cad"
    VECTOR_PDF = "vector_pdf"
    RASTER_PDF = "raster_pdf"
    MANUAL = "manual"  # Backwards-compatible prototype profile.
    MANUAL_TYPED = "manual_typed"
    MANUAL_POINTER = "manual_pointer"
    GRID = "grid"


@dataclass(frozen=True, slots=True)
class ToleranceProfile:
    """Configurable software-processing tolerances.

    These values are not construction, survey or structural acceptance
    tolerances.  They control geometric processing and must be reviewed against
    real project fixtures before production round-trip acceptance.
    """

    profile_id: str
    source_quality: SourceQuality
    snap_distance: Length
    node_merge_distance: Length
    calibration_residual: Length
    round_trip_distance: Length
    angular_degrees: float = 0.1
    merge_suggestion_distance: Optional[Length] = None
    calibration_max_error: Optional[Length] = None
    pointer_snap_pixels: float = 8.0
    pointer_snap_max_distance: Optional[Length] = None
    prototype_default: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "profile_id",
            non_empty_identifier(self.profile_id, "profile_id"),
        )
        if not isinstance(self.source_quality, SourceQuality):
            raise TypeError("source_quality must be a SourceQuality")

        required_lengths = (
            "snap_distance",
            "node_merge_distance",
            "calibration_residual",
            "round_trip_distance",
        )
        for field_name in required_lengths:
            self._validate_length(field_name, getattr(self, field_name))

        merge_suggestion = self.merge_suggestion_distance
        if merge_suggestion is None:
            merge_suggestion = self.node_merge_distance * 10.0
            object.__setattr__(self, "merge_suggestion_distance", merge_suggestion)
        self._validate_length("merge_suggestion_distance", merge_suggestion)
        if merge_suggestion.mm < self.node_merge_distance.mm:
            raise ValueError(
                "merge_suggestion_distance must be at least node_merge_distance"
            )

        maximum_error = self.calibration_max_error
        if maximum_error is None:
            maximum_error = self.calibration_residual * 2.0
            object.__setattr__(self, "calibration_max_error", maximum_error)
        self._validate_length("calibration_max_error", maximum_error)
        if maximum_error.mm < self.calibration_residual.mm:
            raise ValueError(
                "calibration_max_error must be at least calibration_residual"
            )

        pointer_maximum = self.pointer_snap_max_distance
        if pointer_maximum is None:
            pointer_maximum = self.snap_distance * 10.0
            object.__setattr__(self, "pointer_snap_max_distance", pointer_maximum)
        self._validate_length("pointer_snap_max_distance", pointer_maximum)
        if pointer_maximum.mm < self.snap_distance.mm:
            raise ValueError(
                "pointer_snap_max_distance must be at least snap_distance"
            )

        angle = finite_float(self.angular_degrees, "angular_degrees")
        if angle < 0:
            raise ValueError("angular_degrees must not be negative")
        object.__setattr__(self, "angular_degrees", angle)

        pointer_pixels = finite_float(self.pointer_snap_pixels, "pointer_snap_pixels")
        if pointer_pixels <= 0:
            raise ValueError("pointer_snap_pixels must be greater than zero")
        object.__setattr__(self, "pointer_snap_pixels", pointer_pixels)

        if not isinstance(self.prototype_default, bool):
            raise TypeError("prototype_default must be a bool")

    @staticmethod
    def _validate_length(field_name: str, value: Length) -> None:
        if not isinstance(value, Length):
            raise TypeError(f"{field_name} must be a Length")
        if not value.unit.is_physical:
            raise ValueError(f"{field_name} must use a physical unit")
        if value.mm < 0:
            raise ValueError(f"{field_name} must not be negative")

    def pointer_snap_distance(
        self,
        project_units_per_pixel: float,
        unit: Union[LengthUnit, str] = LengthUnit.MILLIMETRE,
    ) -> Length:
        """Return the zoom-aware pointer snap radius in project units.

        The screen radius is converted using the active view scale and capped by
        a profile-specific engineering distance so zooming out cannot cause an
        uncontrolled long-distance snap.
        """

        target_unit = LengthUnit.coerce(unit)
        if not target_unit.is_physical:
            raise ValueError("pointer snap distance requires a physical unit")
        units_per_pixel = finite_float(
            project_units_per_pixel,
            "project_units_per_pixel",
        )
        if units_per_pixel <= 0:
            raise ValueError("project_units_per_pixel must be greater than zero")
        screen_distance = Length(
            self.pointer_snap_pixels * units_per_pixel,
            target_unit,
        )
        maximum = self.pointer_snap_max_distance.to(target_unit)
        return Length(min(screen_distance.value, maximum.value), target_unit)


def raster_tolerance_profile(
    *,
    dpi: float,
    scale_denominator: float,
    scale_numerator: float = 1.0,
    profile_id: str = "raster-derived-v1",
) -> ToleranceProfile:
    """Create a raster profile from scan resolution and drawing scale.

    Example: at 300 dpi and 1:100, one image pixel represents approximately
    8.47 mm in project space.  Raster geometry is never given a large automatic
    node-merge distance; uncertainty is instead routed to the suggestion band.
    """

    dots_per_inch = finite_float(dpi, "dpi")
    numerator = finite_float(scale_numerator, "scale_numerator")
    denominator = finite_float(scale_denominator, "scale_denominator")
    if dots_per_inch <= 0:
        raise ValueError("dpi must be greater than zero")
    if numerator <= 0 or denominator <= 0:
        raise ValueError("drawing scale values must be greater than zero")

    project_mm_per_pixel = (25.4 / dots_per_inch) * (denominator / numerator)
    automatic_merge_mm = min(1.0, project_mm_per_pixel * 0.25)

    return ToleranceProfile(
        profile_id=profile_id,
        source_quality=SourceQuality.RASTER_PDF,
        snap_distance=Length(project_mm_per_pixel, "mm"),
        node_merge_distance=Length(automatic_merge_mm, "mm"),
        calibration_residual=Length(project_mm_per_pixel * 1.5, "mm"),
        round_trip_distance=Length(project_mm_per_pixel, "mm"),
        angular_degrees=0.5,
        merge_suggestion_distance=Length(project_mm_per_pixel * 2.0, "mm"),
        calibration_max_error=Length(project_mm_per_pixel * 3.0, "mm"),
        pointer_snap_pixels=8.0,
        pointer_snap_max_distance=Length(project_mm_per_pixel * 2.0, "mm"),
        prototype_default=False,
    )


def default_tolerance_profiles() -> Dict[SourceQuality, ToleranceProfile]:
    """Return prototype defaults pending real-project calibration."""

    mm = LengthUnit.MILLIMETRE
    profiles = {
        SourceQuality.NATIVE_CAD: ToleranceProfile(
            "native-cad-v2",
            SourceQuality.NATIVE_CAD,
            Length(0.10, mm),
            Length(0.10, mm),
            Length(0.05, mm),
            Length(0.01, mm),
            angular_degrees=0.01,
            merge_suggestion_distance=Length(2.0, mm),
            calibration_max_error=Length(0.10, mm),
            pointer_snap_pixels=8.0,
            pointer_snap_max_distance=Length(5.0, mm),
        ),
        SourceQuality.VECTOR_PDF: ToleranceProfile(
            "vector-pdf-v2",
            SourceQuality.VECTOR_PDF,
            Length(1.0, mm),
            Length(1.0, mm),
            Length(1.0, mm),
            Length(0.5, mm),
            angular_degrees=0.1,
            merge_suggestion_distance=Length(3.0, mm),
            calibration_max_error=Length(2.0, mm),
            pointer_snap_pixels=8.0,
            pointer_snap_max_distance=Length(10.0, mm),
        ),
        SourceQuality.RASTER_PDF: ToleranceProfile(
            "raster-pdf-unknown-metadata-v2",
            SourceQuality.RASTER_PDF,
            Length(5.0, mm),
            Length(1.0, mm),
            Length(10.0, mm),
            Length(5.0, mm),
            angular_degrees=0.5,
            merge_suggestion_distance=Length(15.0, mm),
            calibration_max_error=Length(20.0, mm),
            pointer_snap_pixels=8.0,
            pointer_snap_max_distance=Length(20.0, mm),
        ),
        SourceQuality.MANUAL: ToleranceProfile(
            "manual-legacy-v2",
            SourceQuality.MANUAL,
            Length(1.0, mm),
            Length(1.0, mm),
            Length(1.0, mm),
            Length(0.5, mm),
            angular_degrees=0.1,
            merge_suggestion_distance=Length(3.0, mm),
            calibration_max_error=Length(2.0, mm),
            pointer_snap_pixels=8.0,
            pointer_snap_max_distance=Length(10.0, mm),
        ),
        SourceQuality.MANUAL_TYPED: ToleranceProfile(
            "manual-typed-v1",
            SourceQuality.MANUAL_TYPED,
            Length(0.10, mm),
            Length(0.10, mm),
            Length(0.10, mm),
            Length(0.05, mm),
            angular_degrees=0.01,
            merge_suggestion_distance=Length(1.0, mm),
            calibration_max_error=Length(0.20, mm),
            pointer_snap_pixels=8.0,
            pointer_snap_max_distance=Length(1.0, mm),
        ),
        SourceQuality.MANUAL_POINTER: ToleranceProfile(
            "manual-pointer-v1",
            SourceQuality.MANUAL_POINTER,
            Length(1.0, mm),
            Length(1.0, mm),
            Length(1.0, mm),
            Length(0.5, mm),
            angular_degrees=0.1,
            merge_suggestion_distance=Length(3.0, mm),
            calibration_max_error=Length(2.0, mm),
            pointer_snap_pixels=8.0,
            pointer_snap_max_distance=Length(10.0, mm),
        ),
        SourceQuality.GRID: ToleranceProfile(
            "grid-v2",
            SourceQuality.GRID,
            Length(1.0, mm),
            Length(0.5, mm),
            Length(0.5, mm),
            Length(0.25, mm),
            angular_degrees=0.05,
            merge_suggestion_distance=Length(2.0, mm),
            calibration_max_error=Length(1.0, mm),
            pointer_snap_pixels=8.0,
            pointer_snap_max_distance=Length(10.0, mm),
        ),
    }
    return profiles
