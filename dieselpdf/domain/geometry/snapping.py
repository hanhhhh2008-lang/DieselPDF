from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Tuple

from dieselpdf.domain.common import non_empty_identifier
from dieselpdf.domain.geometry.grids import GridSystem
from dieselpdf.domain.geometry.points import Point2D
from dieselpdf.domain.geometry.tolerances import ToleranceProfile


class SnapKind(Enum):
    GRID_INTERSECTION="grid_intersection"; GRID_LINE="grid_line"; NODE="node"; ENDPOINT="endpoint"; MIDPOINT="midpoint"; NEAREST="nearest"

_DEFAULT_PRIORITY={SnapKind.NODE:10,SnapKind.GRID_INTERSECTION:20,SnapKind.ENDPOINT:30,SnapKind.MIDPOINT:40,SnapKind.GRID_LINE:50,SnapKind.NEAREST:90}

@dataclass(frozen=True,slots=True)
class SnapCandidate:
    candidate_id:str; point:Point2D; kind:SnapKind; source_id:Optional[str]=None; priority:Optional[int]=None
    def __post_init__(self)->None:
        object.__setattr__(self,"candidate_id",non_empty_identifier(self.candidate_id,"candidate_id"))
        if not isinstance(self.kind,SnapKind): raise TypeError("kind must be a SnapKind")
        if self.source_id is not None: object.__setattr__(self,"source_id",non_empty_identifier(self.source_id,"source_id"))
        if self.priority is not None and (isinstance(self.priority,bool) or not isinstance(self.priority,int)): raise TypeError("priority must be an integer")
    @property
    def effective_priority(self)->int: return _DEFAULT_PRIORITY[self.kind] if self.priority is None else self.priority

@dataclass(frozen=True,slots=True)
class SnapResult:
    query:Point2D; snapped_point:Point2D; candidate:SnapCandidate; distance:float

class SnappingService:
    def __init__(self,profile:ToleranceProfile)->None:
        if not isinstance(profile,ToleranceProfile): raise TypeError("profile must be a ToleranceProfile")
        self.profile=profile
    def snap(self,query:Point2D,candidates:Iterable[SnapCandidate])->Optional[SnapResult]:
        maximum=self.profile.snap_distance.to(query.unit).value; ranked=[]
        for candidate in candidates:
            distance=query.distance_to(candidate.point)
            if distance<=maximum: ranked.append((candidate.effective_priority,distance,candidate.candidate_id,candidate))
        if not ranked: return None
        _,distance,_,selected=min(ranked); return SnapResult(query,selected.point,selected,distance)
    def grid_candidates(self,query:Point2D,grid_system:GridSystem)->Tuple[SnapCandidate,...]:
        candidates=[]
        for value in grid_system.intersections(): candidates.append(SnapCandidate(f"grid-intersection:{value.first_grid_id}:{value.second_grid_id}",value.point,SnapKind.GRID_INTERSECTION,f"{value.first_grid_id}/{value.second_grid_id}"))
        for line in grid_system.lines: candidates.append(SnapCandidate(f"grid-line:{line.grid_id}",line.project(query),SnapKind.GRID_LINE,line.grid_id))
        return tuple(candidates)
    def snap_to_grid(self,query:Point2D,grid_system:GridSystem)->Optional[SnapResult]: return self.snap(query,self.grid_candidates(query,grid_system))
    def merge_points(self,points:Iterable[Point2D])->Tuple[Point2D,...]:
        values=tuple(points)
        if not values: return ()
        base_unit=values[0].unit; base_system=values[0].coordinate_system_id; converted=[]
        for point in values:
            if point.coordinate_system_id not in (None,base_system) and base_system is not None: raise ValueError("cannot merge points from different coordinate systems")
            converted.append(point if point.unit is base_unit else point.to(base_unit))
        converted.sort(key=lambda item:(item.x,item.y)); tolerance=self.profile.node_merge_distance.to(base_unit).value; merged=[]
        for point in converted:
            if not merged or all(point.distance_to(existing)>tolerance for existing in merged): merged.append(point)
        return tuple(merged)
