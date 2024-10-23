from dataclasses import dataclass

from math import sqrt, atan2, degrees
from typing import Iterable

from numpy import array, float64


@dataclass
class Vec2:
    x: float = .0
    y: float = .0

    def __repr__(self):
        return "Vec3(%f, %f, %f)" % (self.x, self.y, self.z)

    def __iter__(self):
        return iter((self.x, self.y))

    def __getitem__(self, item: int | str) -> float:
        if isinstance(item, int): return (self.x, self.y)[item]
        elif isinstance(item, str): return dict(x=self.x, y=self.y)[item]
        else: raise ValueError()

    def __len__(self) -> int:
        return 2

    @classmethod
    def from_dict(cls, dict: dict[str, float | None]) -> "Vec2":
        x: float = dict.get("x", None)
        y: float = dict.get("y", None)
        if None in (x, y): raise ValueError()

        return Vec2(x, y)

    def __add__(self, other) -> "Vec2":
        if not isinstance(other, Vec2): return NotImplemented

        return Vec2(
            self.x + other.x,
            self.y + other.y
        )

    def __sub__(self, other) -> "Vec2":
        if not isinstance(other, Vec2): return NotImplemented

        return Vec2(
            self.x - other.x,
            self.y - other.y
        )

    def distance(self, vec2: "Vec2") -> float:
        opp_pos = self - vec2

        distance = sqrt(sum((
            opp_pos.x ** 2,
            opp_pos.y ** 2
        )))
        return distance

    def angle(self, vec2: "Vec2") -> float:
        opp_pos = self - vec2

        angle = atan2(opp_pos.y, opp_pos.x)
        degree = degrees(angle)
        return degree

@dataclass
class Vec3:
    x: float = .0
    y: float = .0
    z: float = .0

    def __repr__(self):
        return "Vec3(%f, %f, %f)" % (self.x, self.y, self.z)

    def __iter__(self) -> Iterable:
        return iter((self.x, self.y, self.z))

    def __getitem__(self, item: int | str) -> float:
        if isinstance(item, int): return (self.x, self.y, self.z)[item]
        elif isinstance(item, str): return dict(x=self.x, y=self.y, z=self.z)[item]
        else: raise ValueError()

    @classmethod
    def from_dict(cls, dict: dict[str, float | None]) -> "Vec3":
        x: float = dict.get("x", None)
        y: float = dict.get("y", None)
        z: float = dict.get("z", None)
        if None in (x, y, z): raise ValueError()

        return Vec3(x, y, z)

    def __len__(self) -> int:
        return 3

    def __add__(self, other) -> "Vec3":
        if not isinstance(other, Vec3): return NotImplemented

        return Vec3(
            self.x + other.x,
            self.y + other.y,
            self.z + other.z
        )

    def __sub__(self, other) -> "Vec3":
        if not isinstance(other, Vec3): return NotImplemented

        return Vec3(
            self.x - other.x,
            self.y - other.y,
            self.z - other.z
        )

    def __floordiv__(self, other: "Vec3") -> "Vec3":
        return Vec3(
            self.x * other.x,
            self.y * other.y,
            self.z * other.z,
        )

    def __truediv__(self, other: "Vec3") -> "Vec3":
        return Vec3(
            self.x / other.x,
            self.y / other.y,
            self.z / other.z,
        )

    def distance(self, vec3: "Vec3") -> float:
        opp_pos = self - vec3

        distance = sqrt(sum((
            opp_pos.x ** 2,
            opp_pos.y ** 2,
            opp_pos.z ** 2
        )))
        return distance

    def normalize(self) -> "Vec3":
        length = sqrt(sum((self.x ** 2, self.y ** 2, self.z ** 2)))
        return Vec3(
            self.x / length,
            self.y / length,
            self.z / length
        )

    def cross(self, other: "Vec3") -> "Vec3":
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def dot(self, other: "Vec3") -> float:
        return sum((
            self.x * other.x,
            self.y * other.y,
            self.z * other.z,
        ))


@dataclass
class Triangle:
    p1: Vec3
    p2: Vec3
    p3: Vec3

    def intersect_check(self, ray_origin: Vec3, ray_end: Vec3) -> bool:
        EPSILON = 1e-6

        edge1 = self.p2 - self.p1
        edge2 = self.p3 - self.p1
        ray_direction = ray_end - ray_origin

        h = ray_direction.cross(edge2)
        a = edge1.dot(h)
        if -EPSILON < a < EPSILON: return False  # 光线与三角形平行，不相交

        f = 1.0 / a
        s = ray_origin - self.p1
        u = f * s.dot(h)
        if u < 0.0 or u > 1.0: return False

        q = s.cross(edge1)
        v = f * ray_direction.dot(q)
        if v < 0.0 or u + v > 1.0: return False

        t = f * edge2.dot(q)
        if EPSILON < t < 1.0: return True  # 确保 t 在 0 和 1 之间，表示交点在线段上

        return False  # 这意味着光线与三角形不相交或者在三角形的边界上


@dataclass
class BoundingBox:
    min: Vec3
    max: Vec3

    def intersect_check(self, ray_origin: Vec3, ray_end: Vec3) -> bool:
        dir = (ray_end - ray_origin).normalize()

        t1 = (self.min.x - ray_origin.x) / dir.x
        t2 = (self.max.x - ray_origin.x) / dir.x
        t3 = (self.min.y - ray_origin.y) / dir.y
        t4 = (self.max.y - ray_origin.y) / dir.y
        t5 = (self.min.z - ray_origin.z) / dir.z
        t6 = (self.max.z - ray_origin.z) / dir.z

        t_min = max(max(min(t1, t2), min(t3, t4)), min(t5, t6))
        t_max = min(min(max(t1, t2), max(t3, t4)), max(t5, t6))

        if t_max < 0: return False
        if t_min > t_max: return False

        return True

def world_2_screen(view_matrix: list[float], screen: Vec2, pos: Vec3, out_of_screen: bool = True) -> Vec2 | None:
    if pos is None: return None

    clip = Vec3()

    pos_array = array((pos.x, pos.y, pos.z, 1), dtype=float64)
    view_matrix_array = array(view_matrix, dtype=float64).reshape((4, 4))

    clip.z = sum(pos_array * view_matrix_array[3])
    if clip.z < 0.1: return None

    clip.x = sum(pos_array * view_matrix_array[0])
    clip.y = sum(pos_array * view_matrix_array[1])

    if (
        not out_of_screen and
        (
            not -clip.z < clip.x < clip.z
            or
            not -clip.z < clip.y < clip.z
        )
    ): return None

    ndc = Vec2(
        clip.x / clip.z,
        clip.y / clip.z
    )

    return Vec2(
        (screen.x / 2 * ndc.x) + (ndc.x + screen.x / 2),
        -(screen.y / 2 * ndc.y) + (ndc.y + screen.y / 2)
    )