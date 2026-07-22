from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Tuple

from dieselpdf.domain.common import non_empty_identifier
from dieselpdf.domain.units import Length, LengthUnit

class LevelType(Enum):
    DATUM="datum"; FOOTING="footing"; GROUND="ground"; FLOOR="floor"; SPLIT="split"; CEILING="ceiling"; ROOF="roof"; OTHER="other"

@dataclass(frozen=True,slots=True)
class PhysicalLevel:
    level_id:str; name:str; elevation:Length; level_type:LevelType; storey_id:Optional[str]=None
    def __post_init__(self)->None:
        object.__setattr__(self,"level_id",non_empty_identifier(self.level_id,"level_id")); object.__setattr__(self,"name",non_empty_identifier(self.name,"name"))
        if not isinstance(self.elevation,Length) or not self.elevation.unit.is_physical: raise TypeError("elevation must be a physical Length")
        if not isinstance(self.level_type,LevelType): raise TypeError("level_type must be a LevelType")
        if self.storey_id is not None: object.__setattr__(self,"storey_id",non_empty_identifier(self.storey_id,"storey_id"))
    @property
    def elevation_mm(self)->float: return self.elevation.to(LengthUnit.MILLIMETRE).value

@dataclass(frozen=True,slots=True)
class Storey:
    storey_id:str; name:str; sequence:int; base_level_id:str; top_level_id:str; included_level_ids:Tuple[str,...]=()
    def __post_init__(self)->None:
        object.__setattr__(self,"storey_id",non_empty_identifier(self.storey_id,"storey_id")); object.__setattr__(self,"name",non_empty_identifier(self.name,"name"))
        if isinstance(self.sequence,bool) or not isinstance(self.sequence,int): raise TypeError("sequence must be an integer")
        object.__setattr__(self,"base_level_id",non_empty_identifier(self.base_level_id,"base_level_id")); object.__setattr__(self,"top_level_id",non_empty_identifier(self.top_level_id,"top_level_id"))
        normalized=tuple(non_empty_identifier(value,"included_level_id") for value in self.included_level_ids)
        if len(set(normalized)) != len(normalized): raise ValueError("included level IDs must be unique")
        object.__setattr__(self,"included_level_ids",normalized)

@dataclass(frozen=True,slots=True)
class BuildingVerticalModel:
    levels:Tuple[PhysicalLevel,...]; storeys:Tuple[Storey,...]
    def __init__(self,levels:Iterable[PhysicalLevel],storeys:Iterable[Storey])->None:
        level_tuple=tuple(levels); storey_tuple=tuple(storeys); level_ids=[v.level_id for v in level_tuple]; storey_ids=[v.storey_id for v in storey_tuple]
        if len(level_ids)!=len(set(level_ids)): raise ValueError("level IDs must be unique")
        if len(storey_ids)!=len(set(storey_ids)): raise ValueError("storey IDs must be unique")
        if len({v.sequence for v in storey_tuple})!=len(storey_tuple): raise ValueError("storey sequences must be unique")
        level_map={v.level_id:v for v in level_tuple}
        for storey in storey_tuple:
            try: base=level_map[storey.base_level_id]; top=level_map[storey.top_level_id]
            except KeyError as exc: raise ValueError(f"storey references unknown level {exc.args[0]!r}") from exc
            if top.elevation_mm <= base.elevation_mm: raise ValueError("storey top level must be above its base level")
            for level_id in storey.included_level_ids:
                if level_id not in level_map: raise ValueError(f"storey references unknown included level {level_id!r}")
                elevation=level_map[level_id].elevation_mm
                if not (base.elevation_mm<=elevation<=top.elevation_mm): raise ValueError("included level must lie within its storey vertical range")
        object.__setattr__(self,"levels",level_tuple); object.__setattr__(self,"storeys",tuple(sorted(storey_tuple,key=lambda item:item.sequence)))
    def level(self,level_id:str)->PhysicalLevel:
        for value in self.levels:
            if value.level_id==level_id:return value
        raise KeyError(level_id)
    def storey(self,storey_id:str)->Storey:
        for value in self.storeys:
            if value.storey_id==storey_id:return value
        raise KeyError(storey_id)
    def nominal_height(self,storey_id:str,unit:LengthUnit=LengthUnit.MILLIMETRE)->Length:
        storey=self.storey(storey_id); difference=self.level(storey.top_level_id).elevation_mm-self.level(storey.base_level_id).elevation_mm
        return Length(difference,LengthUnit.MILLIMETRE).to(unit)
