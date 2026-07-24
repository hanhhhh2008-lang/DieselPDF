import unittest

from dieselpdf.domain.geometry import (
    AffineTransform2D,
    CalibrationDisposition,
    CalibrationRecord,
    CoordinateSystem2D,
    MergeDecision,
    Point2D,
    ProjectCoordinatePolicy,
    ProjectOriginKind,
    SnapCandidate,
    SnapKind,
    SnappingService,
    SourceQuality,
    SurveyDatumLink,
    default_tolerance_profiles,
    raster_tolerance_profile,
)
from dieselpdf.domain.units import Length, LengthUnit


class ProjectCoordinatePolicyTests(unittest.TestCase):
    def test_grid_origin_and_shared_storey_axes_are_explicit(self):
        policy = ProjectCoordinatePolicy(
            coordinate_system_id="project",
            origin_kind=ProjectOriginKind.GRID_INTERSECTION,
            origin_reference="Grid A/1",
            x_axis_reference="Grid 1 to Grid 2",
        )
        self.assertEqual(policy.unit, LengthUnit.MILLIMETRE)
        self.assertTrue(policy.shared_xy_across_storeys)
        self.assertTrue(policy.z_positive_up)

    def test_project_policy_rejects_non_millimetre_canonical_units(self):
        with self.assertRaises(ValueError):
            ProjectCoordinatePolicy(
                coordinate_system_id="project",
                origin_kind=ProjectOriginKind.EXPLICIT,
                origin_reference="Building south-west corner",
                x_axis_reference="Primary building axis",
                unit="m",
            )

    def test_survey_datum_link_maps_project_z_to_ahd(self):
        project = CoordinateSystem2D(
            "project",
            "Project",
            LengthUnit.MILLIMETRE,
        )
        survey = CoordinateSystem2D(
            "survey",
            "MGA survey",
            LengthUnit.MILLIMETRE,
        )
        link = SurveyDatumLink(
            project_coordinate_system_id="project",
            survey_coordinate_system_id="survey",
            plan_transform=AffineTransform2D.from_components(
                project,
                survey,
                rotation_degrees=12,
                translate_x=320000,
                translate_y=6250000,
                method="survey control",
            ),
            project_zero_elevation=Length(0, "mm"),
            survey_rl_at_project_zero=Length(52.430, "m"),
            survey_datum_name="AHD",
        )
        level_one_rl = link.project_z_to_survey_rl(Length(3000, "mm"))
        self.assertAlmostEqual(level_one_rl.to("m").value, 55.430)
        self.assertAlmostEqual(
            link.survey_rl_to_project_z(level_one_rl).mm,
            3000,
        )


class PointerSnappingTests(unittest.TestCase):
    def setUp(self):
        self.profile = default_tolerance_profiles()[SourceQuality.GRID]
        self.service = SnappingService(self.profile)
        self.query = Point2D(0, 0, "mm", "project")

    def candidate(self, x):
        return SnapCandidate(
            f"candidate-{x}",
            Point2D(x, 0, "mm", "project"),
            SnapKind.GRID_INTERSECTION,
        )

    def test_pointer_snap_uses_eight_screen_pixels_at_current_zoom(self):
        result = self.service.snap_from_pointer(
            self.query,
            [self.candidate(1.5), self.candidate(2.5)],
            project_units_per_pixel=0.25,
        )
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result.distance, 1.5)

    def test_pointer_snap_is_capped_when_zoomed_out(self):
        maximum = self.profile.pointer_snap_distance(5.0, "mm")
        self.assertAlmostEqual(maximum.mm, 10.0)
        self.assertIsNone(
            self.service.snap_from_pointer(
                self.query,
                [self.candidate(12.0)],
                project_units_per_pixel=5.0,
            )
        )


class MergeBandTests(unittest.TestCase):
    def test_auto_suggest_and_keep_separate_are_distinct(self):
        service = SnappingService(
            default_tolerance_profiles()[SourceQuality.NATIVE_CAD]
        )
        origin = Point2D(0, 0, "mm", "project")
        self.assertEqual(
            service.assess_merge(
                origin,
                Point2D(0.08, 0, "mm", "project"),
            ).decision,
            MergeDecision.AUTO_MERGE,
        )
        self.assertEqual(
            service.assess_merge(
                origin,
                Point2D(1.0, 0, "mm", "project"),
            ).decision,
            MergeDecision.SUGGEST_MERGE,
        )
        self.assertEqual(
            service.assess_merge(
                origin,
                Point2D(3.0, 0, "mm", "project"),
            ).decision,
            MergeDecision.KEEP_SEPARATE,
        )

    def test_merge_points_only_uses_automatic_band(self):
        service = SnappingService(
            default_tolerance_profiles()[SourceQuality.NATIVE_CAD]
        )
        points = (
            Point2D(0, 0, "mm", "project"),
            Point2D(0.08, 0, "mm", "project"),
            Point2D(1.0, 0, "mm", "project"),
        )
        self.assertEqual(len(service.merge_points(points)), 2)
        self.assertEqual(len(service.merge_suggestions(points)), 2)


class RasterToleranceTests(unittest.TestCase):
    def test_raster_profile_uses_dpi_and_scale(self):
        profile = raster_tolerance_profile(dpi=300, scale_denominator=100)
        project_mm_per_pixel = (25.4 / 300) * 100
        self.assertAlmostEqual(profile.snap_distance.mm, project_mm_per_pixel)
        self.assertAlmostEqual(profile.node_merge_distance.mm, 1.0)
        self.assertAlmostEqual(
            profile.merge_suggestion_distance.mm,
            project_mm_per_pixel * 2,
        )
        self.assertAlmostEqual(
            profile.calibration_max_error.mm,
            project_mm_per_pixel * 3,
        )
        self.assertFalse(profile.prototype_default)

    def test_manual_typed_and_pointer_profiles_are_separate(self):
        profiles = default_tolerance_profiles()
        typed = profiles[SourceQuality.MANUAL_TYPED]
        pointer = profiles[SourceQuality.MANUAL_POINTER]
        self.assertLess(typed.node_merge_distance.mm, pointer.node_merge_distance.mm)


class CalibrationAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.project = CoordinateSystem2D(
            "project",
            "Project",
            LengthUnit.MILLIMETRE,
        )
        self.transform = AffineTransform2D.identity(self.project)
        self.profile = default_tolerance_profiles()[SourceQuality.VECTOR_PDF]

    def record(self, rms_error, max_error):
        return CalibrationRecord(
            source_coordinate_system_id="project",
            target_coordinate_system_id="project",
            method="test fixture",
            transform=self.transform,
            control_points=(),
            residuals=(),
            rms_error=rms_error,
            max_error=max_error,
        )

    def test_pass_warning_and_reject_are_explicit(self):
        self.assertEqual(
            self.record(0.5, 0.8).assess(self.profile).disposition,
            CalibrationDisposition.PASS,
        )
        warning = self.record(1.2, 1.8).assess(self.profile)
        self.assertEqual(warning.disposition, CalibrationDisposition.WARNING)
        self.assertTrue(warning.requires_engineer_confirmation)
        rejected = self.record(1.2, 2.1).assess(self.profile)
        self.assertEqual(rejected.disposition, CalibrationDisposition.REJECT)
        self.assertTrue(rejected.blocked)


if __name__ == "__main__":
    unittest.main()
