from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

from dieselpdf.domain.common import finite_float, non_empty_identifier
from dieselpdf.domain.geometry.points import Point2D, Vector2D
from dieselpdf.domain.units import LengthUnit

Matrix3 = Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]


def _matrix_multiply(left: Matrix3, right: Matrix3) -> Matrix3:
    return tuple(
        tuple(sum(left[row][k] * right[k][col] for k in range(3)) for col in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class CoordinateSystem2D:
    coordinate_system_id: str
    name: str
    unit: LengthUnit
    axis_x: Vector2D = Vector2D(1.0, 0.0)
    axis_y: Vector2D = Vector2D(0.0, 1.0)

    def __post_init__(self) -> None:
        object.__setattr__(self,"coordinate_system_id",non_empty_identifier(self.coordinate_system_id,"coordinate_system_id"))
        object.__setattr__(self,"name",non_empty_identifier(self.name,"name"))
        object.__setattr__(self,"unit",LengthUnit.coerce(self.unit))
        x_axis=self.axis_x.normalized(); y_axis=self.axis_y.normalized()
        if abs(x_axis.cross(y_axis)) <= 1e-12:
            raise ValueError("coordinate-system axes must not be collinear")
        object.__setattr__(self,"axis_x",x_axis); object.__setattr__(self,"axis_y",y_axis)


@dataclass(frozen=True, slots=True)
class AffineTransform2D:
    source: CoordinateSystem2D
    target: CoordinateSystem2D
    matrix: Matrix3
    method: str = "explicit"

    def __post_init__(self) -> None:
        if len(self.matrix) != 3 or any(len(row) != 3 for row in self.matrix):
            raise ValueError("affine matrix must be 3 x 3")
        normalized=tuple(tuple(finite_float(value,f"matrix[{ri}][{ci}]") for ci,value in enumerate(row)) for ri,row in enumerate(self.matrix))
        if any(abs(normalized[2][index]-expected)>1e-12 for index,expected in enumerate((0.0,0.0,1.0))):
            raise ValueError("last affine-matrix row must be [0, 0, 1]")
        object.__setattr__(self,"matrix",normalized); object.__setattr__(self,"method",non_empty_identifier(self.method,"method"))
        if abs(self.determinant) <= 1e-15:
            raise ValueError("affine transform must be invertible")

    @property
    def determinant(self) -> float:
        return self.matrix[0][0]*self.matrix[1][1]-self.matrix[0][1]*self.matrix[1][0]

    @classmethod
    def identity(cls, coordinate_system: CoordinateSystem2D) -> "AffineTransform2D":
        return cls(coordinate_system,coordinate_system,((1.0,0.0,0.0),(0.0,1.0,0.0),(0.0,0.0,1.0)),"identity")

    @classmethod
    def from_components(cls,source:CoordinateSystem2D,target:CoordinateSystem2D,scale_x:float=1.0,scale_y:float=1.0,rotation_degrees:float=0.0,translate_x:float=0.0,translate_y:float=0.0,method:str="components") -> "AffineTransform2D":
        sx=finite_float(scale_x,"scale_x"); sy=finite_float(scale_y,"scale_y")
        if sx == 0 or sy == 0: raise ValueError("scale must not be zero")
        angle=math.radians(finite_float(rotation_degrees,"rotation_degrees")); cosine=math.cos(angle); sine=math.sin(angle)
        tx=finite_float(translate_x,"translate_x"); ty=finite_float(translate_y,"translate_y")
        return cls(source,target,((cosine*sx,-sine*sy,tx),(sine*sx,cosine*sy,ty),(0.0,0.0,1.0)),method)

    def apply(self, point: Point2D) -> Point2D:
        if point.coordinate_system_id not in (None,self.source.coordinate_system_id): raise ValueError("point does not belong to the transform source coordinate system")
        source_point=point if point.unit is self.source.unit else point.to(self.source.unit)
        x=self.matrix[0][0]*source_point.x+self.matrix[0][1]*source_point.y+self.matrix[0][2]
        y=self.matrix[1][0]*source_point.x+self.matrix[1][1]*source_point.y+self.matrix[1][2]
        return Point2D(x,y,self.target.unit,self.target.coordinate_system_id)

    def inverse(self) -> "AffineTransform2D":
        a,b,tx=self.matrix[0]; c,d,ty=self.matrix[1]; determinant=self.determinant
        ia=d/determinant; ib=-b/determinant; ic=-c/determinant; id_=a/determinant
        itx=-(ia*tx+ib*ty); ity=-(ic*tx+id_*ty)
        return AffineTransform2D(self.target,self.source,((ia,ib,itx),(ic,id_,ity),(0.0,0.0,1.0)),f"inverse:{self.method}")

    def then(self, following: "AffineTransform2D") -> "AffineTransform2D":
        if self.target.coordinate_system_id != following.source.coordinate_system_id: raise ValueError("transform chain has incompatible coordinate systems")
        return AffineTransform2D(self.source,following.target,_matrix_multiply(following.matrix,self.matrix),f"{self.method} -> {following.method}")
