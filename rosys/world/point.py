from __future__ import annotations
from pydantic import BaseModel
import numpy as np


class Point(BaseModel):

    x: float
    y: float

    @staticmethod
    def from_complex(number: complex):

        return Point(
            x=np.real(number),
            y=np.imag(number),
        )

    def distance(self, other: Point) -> float:

        return np.sqrt((other.x - self.x)**2 + (other.y - self.y)**2)

    def direction(self, other: Point) -> float:

        return np.arctan2(other.y - self.y, other.x - self.x)

    def projected_distance(self, other: Point, direction: float) -> float:

        def d(p): return np.sqrt(p.x**2 + p.y**2) * np.cos(direction - np.arctan2(p.y, p.x))
        return d(other) - d(self)

    def polar(self, distance: float, yaw: float):

        return Point(
            x=self.x + distance * np.cos(yaw),
            y=self.y + distance * np.sin(yaw),
        )

    def interpolate(self, other: Point, t: float) -> Point:

        return Point(
            x=(1 - t) * self.x + t * other.x,
            y=(1 - t) * self.y + t * other.y,
        )
