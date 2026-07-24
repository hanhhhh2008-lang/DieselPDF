from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence, Tuple

from dieselpdf.domain.common import finite_float
from dieselpdf.domain.geometry.points import Point2D
from dieselpdf.domain.geometry.tolerances import ToleranceProfile
from dieselpdf.domain.geometry.transforms import (
    AffineTransform2D,
    CoordinateSystem2D,
    Matrix3,
)


@dataclass(frozen=True, slots=True)
class ControlPointPair:
    source: Point2D
    target: Point2D
    label: str = ""


@dataclass(frozen=True, slots=True)
class CalibrationResidual:
    label: str
    dx: float
    dy: float
    distance: float


class CalibrationDisposition(Enum):
    PASS = "pass"
    WARNING = "warning"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class CalibrationAssessment:
    disposition: CalibrationDisposition
    rms_error: float
    maximum_error: float
    rms_limit: float
    maximum_limit: float
    messages: Tuple[str, ...]

    @property
    def usable_without_confirmation(self) -> bool:
        return self.disposition is CalibrationDisposition.PASS

    @property
    def requires_engineer_confirmation(self) -> bool:
        return self.disposition is CalibrationDisposition.WARNING

    @property
    def blocked(self) -> bool:
        return self.disposition is CalibrationDisposition.REJECT


@dataclass(frozen=True, slots=True)
class CalibrationRecord:
    source_coordinate_system_id: str
    target_coordinate_system_id: str
    method: str
    transform: AffineTransform2D
    control_points: Tuple[ControlPointPair, ...]
    residuals: Tuple[CalibrationResidual, ...]
    rms_error: float
    max_error: float

    @property
    def control_point_count(self) -> int:
        return len(self.control_points)

    def assess(self, profile: ToleranceProfile) -> CalibrationAssessment:
        if not isinstance(profile, ToleranceProfile):
            raise TypeError("profile must be a ToleranceProfile")
        target_unit = self.transform.target.unit
        rms_limit = profile.calibration_residual.to(target_unit).value
        maximum_limit = profile.calibration_max_error.to(target_unit).value
        messages = []

        if self.max_error > maximum_limit:
            messages.append(
                f"maximum residual {self.max_error:.6g} exceeds rejection limit "
                f"{maximum_limit:.6g} {target_unit.value}"
            )
            disposition = CalibrationDisposition.REJECT
        elif self.rms_error > rms_limit:
            messages.append(
                f"RMS residual {self.rms_error:.6g} exceeds warning limit "
                f"{rms_limit:.6g} {target_unit.value}"
            )
            disposition = CalibrationDisposition.WARNING
        else:
            messages.append("calibration residuals are within the selected profile")
            disposition = CalibrationDisposition.PASS

        if profile.prototype_default:
            messages.append(
                "tolerance profile is a prototype default pending real-project review"
            )

        return CalibrationAssessment(
            disposition=disposition,
            rms_error=self.rms_error,
            maximum_error=self.max_error,
            rms_limit=rms_limit,
            maximum_limit=maximum_limit,
            messages=tuple(messages),
        )


def _solve_linear_system(
    matrix: Sequence[Sequence[float]],
    vector: Sequence[float],
) -> Tuple[float, ...]:
    size = len(vector)
    augmented = [list(matrix[row]) + [float(vector[row])] for row in range(size)]
    for pivot_column in range(size):
        pivot_row = max(
            range(pivot_column, size),
            key=lambda row: abs(augmented[row][pivot_column]),
        )
        if abs(augmented[pivot_row][pivot_column]) <= 1e-14:
            raise ValueError("calibration control points are singular or collinear")
        if pivot_row != pivot_column:
            augmented[pivot_column], augmented[pivot_row] = (
                augmented[pivot_row],
                augmented[pivot_column],
            )
        pivot = augmented[pivot_column][pivot_column]
        augmented[pivot_column] = [
            value / pivot for value in augmented[pivot_column]
        ]
        for row in range(size):
            if row == pivot_column:
                continue
            factor = augmented[row][pivot_column]
            if factor == 0:
                continue
            augmented[row] = [
                augmented[row][column]
                - factor * augmented[pivot_column][column]
                for column in range(size + 1)
            ]
    return tuple(augmented[row][-1] for row in range(size))


def _least_squares(
    rows: Sequence[Sequence[float]],
    values: Sequence[float],
) -> Tuple[float, ...]:
    column_count = len(rows[0])
    normal = [[0.0] * column_count for _ in range(column_count)]
    rhs = [0.0] * column_count
    for row, value in zip(rows, values):
        for i in range(column_count):
            rhs[i] += row[i] * value
            for j in range(column_count):
                normal[i][j] += row[i] * row[j]
    return _solve_linear_system(normal, rhs)


def _residual_report(
    transform: AffineTransform2D,
    pairs: Sequence[ControlPointPair],
) -> Tuple[Tuple[CalibrationResidual, ...], float, float]:
    residuals = []
    squared_sum = 0.0
    maximum = 0.0
    for index, pair in enumerate(pairs, start=1):
        predicted = transform.apply(pair.source)
        target = (
            pair.target
            if pair.target.unit is transform.target.unit
            else pair.target.to(transform.target.unit)
        )
        dx = predicted.x - target.x
        dy = predicted.y - target.y
        distance = math.hypot(dx, dy)
        squared_sum += distance * distance
        maximum = max(maximum, distance)
        residuals.append(
            CalibrationResidual(pair.label or f"CP{index}", dx, dy, distance)
        )
    return tuple(residuals), math.sqrt(squared_sum / len(pairs)), maximum


def fit_calibration(
    source: CoordinateSystem2D,
    target: CoordinateSystem2D,
    control_points: Iterable[ControlPointPair],
    *,
    one_point_scale: float = 1.0,
    one_point_rotation_degrees: float = 0.0,
) -> CalibrationRecord:
    pairs = tuple(control_points)
    if not pairs:
        raise ValueError("at least one calibration control point is required")
    for pair in pairs:
        if pair.source.coordinate_system_id not in (
            None,
            source.coordinate_system_id,
        ):
            raise ValueError(
                "source control point uses a different coordinate system"
            )
        if pair.target.coordinate_system_id not in (
            None,
            target.coordinate_system_id,
        ):
            raise ValueError(
                "target control point uses a different coordinate system"
            )

    if len(pairs) == 1:
        pair = pairs[0]
        scale = finite_float(one_point_scale, "one_point_scale")
        if scale == 0:
            raise ValueError("one-point scale must not be zero")
        angle = math.radians(
            finite_float(one_point_rotation_degrees, "one_point_rotation_degrees")
        )
        cosine = math.cos(angle)
        sine = math.sin(angle)
        source_point = (
            pair.source
            if pair.source.unit is source.unit
            else pair.source.to(source.unit)
        )
        target_point = (
            pair.target
            if pair.target.unit is target.unit
            else pair.target.to(target.unit)
        )
        tx = target_point.x - scale * (
            cosine * source_point.x - sine * source_point.y
        )
        ty = target_point.y - scale * (
            sine * source_point.x + cosine * source_point.y
        )
        transform = AffineTransform2D.from_components(
            source,
            target,
            scale,
            scale,
            one_point_rotation_degrees,
            tx,
            ty,
            "one-point similarity",
        )
        method = "one-point similarity"
    elif len(pairs) == 2:
        first, second = pairs
        source_first = (
            first.source
            if first.source.unit is source.unit
            else first.source.to(source.unit)
        )
        source_second = (
            second.source
            if second.source.unit is source.unit
            else second.source.to(source.unit)
        )
        target_first = (
            first.target
            if first.target.unit is target.unit
            else first.target.to(target.unit)
        )
        target_second = (
            second.target
            if second.target.unit is target.unit
            else second.target.to(target.unit)
        )
        source_dx = source_second.x - source_first.x
        source_dy = source_second.y - source_first.y
        target_dx = target_second.x - target_first.x
        target_dy = target_second.y - target_first.y
        source_length = math.hypot(source_dx, source_dy)
        target_length = math.hypot(target_dx, target_dy)
        if source_length <= 1e-14 or target_length <= 1e-14:
            raise ValueError("two-point calibration requires distinct points")
        scale = target_length / source_length
        angle = math.degrees(
            math.atan2(target_dy, target_dx)
            - math.atan2(source_dy, source_dx)
        )
        radians = math.radians(angle)
        cosine = math.cos(radians)
        sine = math.sin(radians)
        tx = target_first.x - scale * (
            cosine * source_first.x - sine * source_first.y
        )
        ty = target_first.y - scale * (
            sine * source_first.x + cosine * source_first.y
        )
        transform = AffineTransform2D.from_components(
            source,
            target,
            scale,
            scale,
            angle,
            tx,
            ty,
            "two-point similarity",
        )
        method = "two-point similarity"
    else:
        rows = []
        values = []
        for pair in pairs:
            source_point = (
                pair.source
                if pair.source.unit is source.unit
                else pair.source.to(source.unit)
            )
            target_point = (
                pair.target
                if pair.target.unit is target.unit
                else pair.target.to(target.unit)
            )
            rows.append((source_point.x, source_point.y, 1.0, 0.0, 0.0, 0.0))
            values.append(target_point.x)
            rows.append((0.0, 0.0, 0.0, source_point.x, source_point.y, 1.0))
            values.append(target_point.y)
        a, b, tx, c, d, ty = _least_squares(rows, values)
        matrix: Matrix3 = (
            (a, b, tx),
            (c, d, ty),
            (0.0, 0.0, 1.0),
        )
        transform = AffineTransform2D(
            source,
            target,
            matrix,
            "affine least squares",
        )
        method = "affine least squares"

    residuals, rms_error, max_error = _residual_report(transform, pairs)
    return CalibrationRecord(
        source.coordinate_system_id,
        target.coordinate_system_id,
        method,
        transform,
        pairs,
        residuals,
        rms_error,
        max_error,
    )
