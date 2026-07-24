from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dieselpdf.domain.common import non_empty_identifier
from dieselpdf.domain.geometry.transforms import AffineTransform2D
from dieselpdf.domain.units import Length, LengthUnit


class ProjectOriginKind(Enum):
    GRID_INTERSECTION = "grid_intersection"
    SURVEY_CONTROL = "survey_control"
    BUILDING_CORNER = "building_corner"
    EXPLICIT = "explicit"


@dataclass(frozen=True, slots=True)
class ProjectCoordinatePolicy:
    """Defines the stable project origin and axis convention.

    Project X/Y is shared by all storeys.  A PDF page or Canvas origin may be
    connected by a transform but can never become the permanent project origin.
    """

    coordinate_system_id: str
    origin_kind: ProjectOriginKind
    origin_reference: str
    x_axis_reference: str
    unit: LengthUnit = LengthUnit.MILLIMETRE
    x_positive_right: bool = True
    y_positive_up: bool = True
    z_positive_up: bool = True
    shared_xy_across_storeys: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "coordinate_system_id",
            non_empty_identifier(
                self.coordinate_system_id,
                "coordinate_system_id",
            ),
        )
        if not isinstance(self.origin_kind, ProjectOriginKind):
            raise TypeError("origin_kind must be a ProjectOriginKind")
        object.__setattr__(
            self,
            "origin_reference",
            non_empty_identifier(self.origin_reference, "origin_reference"),
        )
        object.__setattr__(
            self,
            "x_axis_reference",
            non_empty_identifier(self.x_axis_reference, "x_axis_reference"),
        )
        unit = LengthUnit.coerce(self.unit)
        if unit is not LengthUnit.MILLIMETRE:
            raise ValueError("canonical project coordinate policy must use millimetres")
        object.__setattr__(self, "unit", unit)
        for field_name in (
            "x_positive_right",
            "y_positive_up",
            "z_positive_up",
            "shared_xy_across_storeys",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a bool")
        if not (
            self.x_positive_right
            and self.y_positive_up
            and self.z_positive_up
            and self.shared_xy_across_storeys
        ):
            raise ValueError(
                "Phase 2 canonical policy requires X right, Y up, Z up and "
                "shared X/Y across storeys"
            )


@dataclass(frozen=True, slots=True)
class SurveyDatumLink:
    """Connect project-relative coordinates and levels to survey coordinates."""

    project_coordinate_system_id: str
    survey_coordinate_system_id: str
    plan_transform: AffineTransform2D
    project_zero_elevation: Length
    survey_rl_at_project_zero: Length
    survey_datum_name: str = "AHD"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "project_coordinate_system_id",
            non_empty_identifier(
                self.project_coordinate_system_id,
                "project_coordinate_system_id",
            ),
        )
        object.__setattr__(
            self,
            "survey_coordinate_system_id",
            non_empty_identifier(
                self.survey_coordinate_system_id,
                "survey_coordinate_system_id",
            ),
        )
        object.__setattr__(
            self,
            "survey_datum_name",
            non_empty_identifier(self.survey_datum_name, "survey_datum_name"),
        )
        if not isinstance(self.plan_transform, AffineTransform2D):
            raise TypeError("plan_transform must be an AffineTransform2D")
        if (
            self.plan_transform.source.coordinate_system_id
            != self.project_coordinate_system_id
            or self.plan_transform.target.coordinate_system_id
            != self.survey_coordinate_system_id
        ):
            raise ValueError(
                "plan_transform must map the declared project system to the "
                "declared survey system"
            )
        for field_name in (
            "project_zero_elevation",
            "survey_rl_at_project_zero",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, Length):
                raise TypeError(f"{field_name} must be a Length")
            if not value.unit.is_physical:
                raise ValueError(f"{field_name} must use a physical unit")

    def project_z_to_survey_rl(self, project_z: Length) -> Length:
        if not isinstance(project_z, Length):
            raise TypeError("project_z must be a Length")
        relative = project_z - self.project_zero_elevation
        return self.survey_rl_at_project_zero + relative

    def survey_rl_to_project_z(self, survey_rl: Length) -> Length:
        if not isinstance(survey_rl, Length):
            raise TypeError("survey_rl must be a Length")
        relative = survey_rl - self.survey_rl_at_project_zero
        return self.project_zero_elevation + relative
