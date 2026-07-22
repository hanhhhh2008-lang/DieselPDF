from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from dieselpdf.domain.common import finite_float
from dieselpdf.domain.geometry import AffineTransform2D, CoordinateSystem2D, Point2D
from dieselpdf.domain.units import LengthUnit


@dataclass(frozen=True, slots=True)
class LegacyCanvasCoordinateAdapter:
    """Characterise the current Canvas ↔ CAD/project coordinate convention."""
    page_height_px: float
    scale_units_per_px: float = 1.0
    page_origin: Tuple[float, float] = (60.0, 46.0)
    project_unit: LengthUnit = LengthUnit.MILLIMETRE

    def __post_init__(self) -> None:
        height=finite_float(self.page_height_px,"page_height_px"); scale=finite_float(self.scale_units_per_px,"scale_units_per_px")
        if height<=0: raise ValueError("page_height_px must be positive")
        if scale<=0: raise ValueError("scale_units_per_px must be positive")
        if len(self.page_origin)!=2: raise ValueError("page_origin must contain X and Y")
        origin=(finite_float(self.page_origin[0],"page_origin_x"),finite_float(self.page_origin[1],"page_origin_y")); unit=LengthUnit.coerce(self.project_unit)
        if not unit.is_physical: raise ValueError("project_unit must be physical")
        object.__setattr__(self,"page_height_px",height); object.__setattr__(self,"scale_units_per_px",scale); object.__setattr__(self,"page_origin",origin); object.__setattr__(self,"project_unit",unit)

    @property
    def canvas_system(self)->CoordinateSystem2D: return CoordinateSystem2D("legacy-canvas","Legacy Tk Canvas",LengthUnit.PIXEL)
    @property
    def project_system(self)->CoordinateSystem2D: return CoordinateSystem2D("project","Project coordinates",self.project_unit)
    @property
    def canvas_to_project_transform(self)->AffineTransform2D:
        x0,y0=self.page_origin; scale=self.scale_units_per_px
        return AffineTransform2D(self.canvas_system,self.project_system,((scale,0.0,-x0*scale),(0.0,-scale,(self.page_height_px+y0)*scale),(0.0,0.0,1.0)),"legacy canvas to project")
    def canvas_to_project(self,x:float,y:float)->Point2D:
        return self.canvas_to_project_transform.apply(Point2D(x,y,LengthUnit.PIXEL,self.canvas_system.coordinate_system_id))
    def project_to_canvas(self,x:float,y:float)->Point2D:
        return self.canvas_to_project_transform.inverse().apply(Point2D(x,y,self.project_unit,self.project_system.coordinate_system_id))
