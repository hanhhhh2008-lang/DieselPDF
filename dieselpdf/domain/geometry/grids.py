from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from dieselpdf.domain.common import finite_float, non_empty_identifier
from dieselpdf.domain.geometry.points import Point2D, Vector2D
from dieselpdf.domain.units import Length


@dataclass(frozen=True, slots=True)
class GridIntersection:
    first_grid_id: str
    second_grid_id: str
    point: Point2D


@dataclass(frozen=True, slots=True)
class GridLine2D:
    grid_id: str
    label: str
    origin: Point2D
    direction: Vector2D
    group: str = "primary"
    extent_start: Optional[float] = None
    extent_end: Optional[float] = None

    def __post_init__(self) -> None:
        object.__setattr__(self,"grid_id",non_empty_identifier(self.grid_id,"grid_id")); object.__setattr__(self,"label",non_empty_identifier(self.label,"label")); object.__setattr__(self,"group",non_empty_identifier(self.group,"group")); object.__setattr__(self,"direction",self.direction.normalized())
        if self.extent_start is not None: object.__setattr__(self,"extent_start",finite_float(self.extent_start,"extent_start"))
        if self.extent_end is not None: object.__setattr__(self,"extent_end",finite_float(self.extent_end,"extent_end"))
        if self.extent_start is not None and self.extent_end is not None and self.extent_start > self.extent_end: raise ValueError("extent_start must not exceed extent_end")

    def point_at(self,parameter:float)->Point2D:
        value=finite_float(parameter,"parameter"); return Point2D(self.origin.x+value*self.direction.x,self.origin.y+value*self.direction.y,self.origin.unit,self.origin.coordinate_system_id)

    def project(self,point:Point2D)->Point2D:
        p=self._compatible_point(point); dx=p.x-self.origin.x; dy=p.y-self.origin.y; return self.point_at(dx*self.direction.x+dy*self.direction.y)

    def signed_distance(self,point:Point2D)->float:
        p=self._compatible_point(point); normal=self.direction.perpendicular_left(); return (p.x-self.origin.x)*normal.x+(p.y-self.origin.y)*normal.y

    def offset(self,offset:Length,grid_id:str,label:str)->"GridLine2D":
        distance=offset.to(self.origin.unit).value; normal=self.direction.perpendicular_left(); shifted=Point2D(self.origin.x+normal.x*distance,self.origin.y+normal.y*distance,self.origin.unit,self.origin.coordinate_system_id)
        return GridLine2D(grid_id,label,shifted,self.direction,self.group,self.extent_start,self.extent_end)

    def intersection(self,other:"GridLine2D",tolerance:float=1e-12)->Optional[GridIntersection]:
        if self.origin.coordinate_system_id != other.origin.coordinate_system_id: raise ValueError("grid lines belong to different coordinate systems")
        if self.origin.unit is not other.origin.unit: other=GridLine2D(other.grid_id,other.label,other.origin.to(self.origin.unit),other.direction,other.group,other.extent_start,other.extent_end)
        denominator=self.direction.cross(other.direction)
        if abs(denominator)<=tolerance: return None
        dx=other.origin.x-self.origin.x; dy=other.origin.y-self.origin.y
        parameter=(dx*other.direction.y-dy*other.direction.x)/denominator; other_parameter=(dx*self.direction.y-dy*self.direction.x)/denominator
        if self.extent_start is not None and parameter < self.extent_start-tolerance: return None
        if self.extent_end is not None and parameter > self.extent_end+tolerance: return None
        if other.extent_start is not None and other_parameter < other.extent_start-tolerance: return None
        if other.extent_end is not None and other_parameter > other.extent_end+tolerance: return None
        return GridIntersection(self.grid_id,other.grid_id,self.point_at(parameter))

    def _compatible_point(self,point:Point2D)->Point2D:
        if self.origin.coordinate_system_id is not None and point.coordinate_system_id is not None and self.origin.coordinate_system_id != point.coordinate_system_id: raise ValueError("point and grid use different coordinate systems")
        return point if point.unit is self.origin.unit else point.to(self.origin.unit)


@dataclass(frozen=True, slots=True)
class GridSystem:
    grid_system_id:str
    name:str
    lines:Tuple[GridLine2D,...]

    def __init__(self,grid_system_id:str,name:str,lines:Iterable[GridLine2D])->None:
        object.__setattr__(self,"grid_system_id",non_empty_identifier(grid_system_id,"grid_system_id")); object.__setattr__(self,"name",non_empty_identifier(name,"name")); line_tuple=tuple(lines)
        ids=[line.grid_id for line in line_tuple]
        if len(set(ids)) != len(ids): raise ValueError("grid line IDs must be unique")
        object.__setattr__(self,"lines",line_tuple)

    def intersections(self)->Tuple[GridIntersection,...]:
        result=[]
        for index,first in enumerate(self.lines):
            for second in self.lines[index+1:]:
                value=first.intersection(second)
                if value is not None: result.append(value)
        return tuple(result)

    def line(self,grid_id:str)->GridLine2D:
        for line in self.lines:
            if line.grid_id==grid_id: return line
        raise KeyError(grid_id)

    def nearest_intersection(self,point:Point2D,maximum_distance:Length)->Optional[GridIntersection]:
        candidates=[]; maximum=maximum_distance.to(point.unit).value
        for intersection in self.intersections():
            distance=point.distance_to(intersection.point)
            if distance<=maximum: candidates.append((distance,intersection.first_grid_id,intersection.second_grid_id,intersection))
        return min(candidates,default=(None,None,None,None))[3]
