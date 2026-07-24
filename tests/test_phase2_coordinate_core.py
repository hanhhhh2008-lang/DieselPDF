import unittest

from dieselpdf.adapters.legacy import LegacyCanvasCoordinateAdapter
from dieselpdf.app import GridManager
from dieselpdf.domain.documents import BuildingVerticalModel, LevelType, PhysicalLevel, Storey
from dieselpdf.domain.geometry import AffineTransform2D, ControlPointPair, CoordinateSystem2D, GridLine2D, GridSystem, Point2D, SnapCandidate, SnapKind, SnappingService, SourceQuality, Vector2D, default_tolerance_profiles, fit_calibration
from dieselpdf.domain.units import Length, LengthUnit
from dieselpdf.ui.tkinter import CanvasProjectionMap

class UnitAndPointTests(unittest.TestCase):
    def test_length_converts_to_millimetres(self):
        self.assertAlmostEqual(Length(2.5,"m").mm,2500); self.assertAlmostEqual(Length(12,"in").mm,304.8)
    def test_pixel_requires_transform(self):
        with self.assertRaises(ValueError): Length(10,"px").to("mm")
    def test_strict_numbers_reject_boolean_and_nan(self):
        with self.assertRaises(TypeError): Point2D(True,0)
        with self.assertRaises(ValueError): Point2D(float("nan"),0)
    def test_point_distance_converts_units(self): self.assertAlmostEqual(Point2D(0,0,"mm","project").distance_to(Point2D(1,0,"m","project")),1000)

class TransformTests(unittest.TestCase):
    def setUp(self):
        self.page=CoordinateSystem2D("page","PDF page",LengthUnit.PDF_POINT); self.project=CoordinateSystem2D("project","Project",LengthUnit.MILLIMETRE); self.canvas=CoordinateSystem2D("canvas","Canvas",LengthUnit.PIXEL)
    def test_forward_inverse_round_trip(self):
        transform=AffineTransform2D.from_components(self.page,self.project,2,2,30,120,-40); original=Point2D(20,35,LengthUnit.PDF_POINT,"page"); recovered=transform.inverse().apply(transform.apply(original)); self.assertAlmostEqual(recovered.x,original.x,places=9); self.assertAlmostEqual(recovered.y,original.y,places=9)
    def test_composition(self):
        a=AffineTransform2D.from_components(self.page,self.project,2,2,0,100,200,"page-project"); b=AffineTransform2D.from_components(self.project,self.canvas,.5,-.5,0,60,900,"project-canvas"); point=Point2D(10,20,LengthUnit.PDF_POINT,"page"); direct=b.apply(a.apply(point)); chained=a.then(b).apply(point); self.assertAlmostEqual(chained.x,direct.x); self.assertAlmostEqual(chained.y,direct.y)

class CalibrationTests(unittest.TestCase):
    def setUp(self): self.source=CoordinateSystem2D("page","Page",LengthUnit.PIXEL); self.target=CoordinateSystem2D("project","Project",LengthUnit.MILLIMETRE)
    def pair(self,sx,sy,tx,ty,label=""): return ControlPointPair(Point2D(sx,sy,"px","page"),Point2D(tx,ty,"mm","project"),label)
    def test_one_point_translation(self):
        record=fit_calibration(self.source,self.target,[self.pair(10,20,100,200)]); mapped=record.transform.apply(Point2D(15,25,"px","page")); self.assertEqual(record.method,"one-point similarity"); self.assertAlmostEqual(mapped.x,105); self.assertAlmostEqual(mapped.y,205); self.assertAlmostEqual(record.max_error,0)
    def test_two_point_scale_rotation(self):
        record=fit_calibration(self.source,self.target,[self.pair(0,0,100,200),self.pair(10,0,100,220)]); mapped=record.transform.apply(Point2D(0,5,"px","page")); self.assertAlmostEqual(mapped.x,90); self.assertAlmostEqual(mapped.y,200); self.assertAlmostEqual(record.rms_error,0,places=10)
    def test_three_point_affine(self):
        record=fit_calibration(self.source,self.target,[self.pair(0,0,5,7),self.pair(10,0,25,17),self.pair(0,10,35,47)]); mapped=record.transform.apply(Point2D(2,3,"px","page")); self.assertAlmostEqual(mapped.x,18); self.assertAlmostEqual(mapped.y,21); self.assertAlmostEqual(record.max_error,0,places=9)
    def test_collinear_affine_points_are_rejected(self):
        with self.assertRaises(ValueError): fit_calibration(self.source,self.target,[self.pair(0,0,0,0),self.pair(1,1,2,2),self.pair(2,2,4,4)])

class StoreyAndLevelTests(unittest.TestCase):
    def test_split_roof_and_footing_levels(self):
        levels=[PhysicalLevel("FND","Footing",Length(-600,"mm"),LevelType.FOOTING),PhysicalLevel("GF","Ground Floor",Length(0,"mm"),LevelType.GROUND,"S-GF"),PhysicalLevel("SPLIT","Split Level",Length(900,"mm"),LevelType.SPLIT,"S-GF"),PhysicalLevel("L1","Level 1",Length(3000,"mm"),LevelType.FLOOR,"S-L1"),PhysicalLevel("ROOF","Roof",Length(6000,"mm"),LevelType.ROOF,"S-L1")]
        model=BuildingVerticalModel(levels,[Storey("S-GF","Ground",0,"GF","L1",("SPLIT",)),Storey("S-L1","Level 1",1,"L1","ROOF")]); self.assertAlmostEqual(model.nominal_height("S-GF").mm,3000); self.assertEqual(model.level("SPLIT").level_type,LevelType.SPLIT); self.assertEqual(model.level("FND").elevation_mm,-600)
    def test_storey_rejects_top_below_base(self):
        levels=[PhysicalLevel("A","A",Length(1000,"mm"),LevelType.FLOOR),PhysicalLevel("B","B",Length(0,"mm"),LevelType.FLOOR)]
        with self.assertRaises(ValueError): BuildingVerticalModel(levels,[Storey("S","Invalid",0,"A","B")])

class GridTests(unittest.TestCase):
    def setUp(self): self.origin=Point2D(0,0,"mm","project")
    def test_orthogonal_grid_intersection(self):
        value=GridLine2D("A","A",self.origin,Vector2D(0,1)).intersection(GridLine2D("1","1",Point2D(5000,0,"mm","project"),Vector2D(1,0))); self.assertEqual(value.point.as_tuple(),(0.0,0.0))
    def test_rotated_grid_intersection(self):
        point=GridLine2D("R1","R1",self.origin,Vector2D(1,1)).intersection(GridLine2D("R2","R2",Point2D(0,10,"mm","project"),Vector2D(1,-1))).point; self.assertAlmostEqual(point.x,5); self.assertAlmostEqual(point.y,5)
    def test_offset_grid(self):
        offset=GridLine2D("A","A",self.origin,Vector2D(1,0)).offset(Length(3000,"mm"),"B","B"); self.assertAlmostEqual(offset.origin.x,0); self.assertAlmostEqual(offset.origin.y,3000)
    def test_grid_system_rejects_duplicate_ids(self):
        line=GridLine2D("A","A",self.origin,Vector2D(1,0))
        with self.assertRaises(ValueError): GridSystem("G","Grid",[line,line])

class GridManagerTests(unittest.TestCase):
    def test_upsert_remove_and_transformed_copy(self):
        source=CoordinateSystem2D("source","Source",LengthUnit.MILLIMETRE); target=CoordinateSystem2D("target","Target",LengthUnit.MILLIMETRE); system=GridSystem("GF","Ground Floor",[GridLine2D("A","A",Point2D(0,0,"mm","source"),Vector2D(0,1))]); manager=GridManager([system]); manager.upsert_line("GF",GridLine2D("1","1",Point2D(0,0,"mm","source"),Vector2D(1,0))); self.assertEqual(len(manager.get("GF").intersections()),1); copied=manager.copy_transformed("GF","L1","Level 1",AffineTransform2D.from_components(source,target,1,1,30,5000,2500,"storey copy")); self.assertAlmostEqual(copied.line("A").origin.x,5000); manager.remove_line("GF","1"); self.assertEqual(len(manager.get("GF").lines),1)

class SnappingTests(unittest.TestCase):
    def test_snap_is_deterministic_by_priority(self):
        service=SnappingService(default_tolerance_profiles()[SourceQuality.GRID]); result=service.snap(Point2D(.5,0,"mm","project"),[SnapCandidate("z",Point2D(0,0,"mm","project"),SnapKind.GRID_LINE),SnapCandidate("a",Point2D(1,0,"mm","project"),SnapKind.NODE)]); self.assertEqual(result.candidate.candidate_id,"a")
    def test_snap_to_grid_prefers_intersection(self):
        service=SnappingService(default_tolerance_profiles()[SourceQuality.RASTER_PDF]); grids=GridSystem("G","Primary",[GridLine2D("A","A",Point2D(0,0,"mm","project"),Vector2D(0,1)),GridLine2D("1","1",Point2D(0,0,"mm","project"),Vector2D(1,0))]); self.assertEqual(service.snap_to_grid(Point2D(1,1,"mm","project"),grids).candidate.kind,SnapKind.GRID_INTERSECTION)
    def test_merge_points_is_input_order_independent(self):
        service=SnappingService(default_tolerance_profiles()[SourceQuality.GRID]); points=[Point2D(10,10,"mm","project"),Point2D(.2,0,"mm","project"),Point2D(0,0,"mm","project")]; first=service.merge_points(points); self.assertEqual(first,service.merge_points(reversed(points))); self.assertEqual(len(first),2)

class CanvasProjectionTests(unittest.TestCase):
    def test_cross_selection_and_rebind(self):
        projection=CanvasProjectionMap(); projection.bind("beam-1",[10,11]); projection.bind("column-1",[20]); self.assertEqual(projection.items_for_entity("beam-1"),(10,11)); self.assertEqual(projection.entities_for_items([11,20]),("beam-1","column-1")); projection.bind("column-1",[11]); self.assertEqual(projection.items_for_entity("beam-1"),(10,)); self.assertEqual(projection.entity_for_item(11),"column-1")
    def test_mapping_is_ephemeral_and_clearable(self):
        projection=CanvasProjectionMap(); projection.bind("wall-1",[1]); projection.clear(); self.assertEqual(len(projection),0); self.assertFalse(hasattr(projection,"to_json"))

class LegacyCoordinateCharacterisationTests(unittest.TestCase):
    def test_a4_page_origin_and_y_axis_characterisation(self):
        adapter=LegacyCanvasCoordinateAdapter(page_height_px=891,scale_units_per_px=1); self.assertEqual(adapter.canvas_to_project(60,937).as_tuple(),(0.0,0.0)); self.assertEqual(adapter.canvas_to_project(60,46).as_tuple(),(0.0,891.0))
    def test_legacy_round_trip_matches_current_formulas(self):
        adapter=LegacyCanvasCoordinateAdapter(page_height_px=891,scale_units_per_px=2.5); project=adapter.canvas_to_project(160,846); self.assertAlmostEqual(project.x,250); self.assertAlmostEqual(project.y,(891-(846-46))*2.5); canvas=adapter.project_to_canvas(project.x,project.y); self.assertAlmostEqual(canvas.x,160); self.assertAlmostEqual(canvas.y,846)

if __name__ == "__main__": unittest.main()
