from copy import copy
from dataclasses import dataclass
from functools import cmp_to_key
from heapq import nlargest

from .math_helper import Triangle, BoundingBox, Vec3


@dataclass
class KDNode:
    def __init__(self, bbox: BoundingBox, axis: int) -> None:
        self.bbox = bbox
        self.axis = axis

        self.triangles: list[Triangle] | None = None
        self.left: KDNode | None = None
        self.right: KDNode | None = None

    def __repr__(self) -> str:
        return "KDNode(tri=%s, has_left=%s, has_right=%s)" % (self.triangles, self.left is not None, self.right is not None)


# def build_kd_tree(triangles: list[Triangle], depth: int = 0) -> KDNode:
#     axis = depth % 3
#     bbox = BoundingBox(
#         copy(triangles[0].p1),
#         copy(triangles[0].p1)
#     )
#     for triangle in triangles:
#         for point in (triangle.p1, triangle.p2, triangle.p3):
#             # bbox.min.x, _, bbox.max.x = sorted((point.x, bbox.min.x, bbox.max.x))
#             # bbox.min.y, _, bbox.max.y = sorted((point.y, bbox.min.y, bbox.max.y))
#             # bbox.min.z, _, bbox.max.z = sorted((point.z, bbox.min.z, bbox.max.z))
#             bbox.min.x = min(bbox.min.x, point.x)
#             bbox.min.y = min(bbox.min.y, point.y)
#             bbox.min.z = min(bbox.min.z, point.z)
#             bbox.max.x = min(bbox.max.x, point.x)
#             bbox.max.y = min(bbox.max.y, point.y)
#             bbox.max.z = min(bbox.max.z, point.z)
#     node = KDNode(bbox, axis)
#
#     if len(triangles) <= 3:
#         node.triangles = triangles
#         return node
#
#     def comparator(a: Triangle, b: Triangle) -> bool:
#         a_center = b_center = 0
#
#         match axis:
#             case 0:
#                 a_center = (a.p1.x + a.p2.x + a.p3.x) / 3
#                 b_center = (b.p1.x + b.p2.x + b.p3.x) / 3
#             case 1:
#                 a_center = (a.p1.y + a.p2.y + a.p3.y) / 3
#                 b_center = (b.p1.y + b.p2.y + b.p3.y) / 3
#             case 2:
#                 a_center = (a.p1.z + a.p2.z + a.p3.z) / 3
#                 b_center = (b.p1.z + b.p2.z + b.p3.z) / 3
#
#         return a_center < b_center
#     # triangles = sorted(triangles, key=cmp_to_key(comparator))
#     triangles = nlargest(len(triangles), triangles, key=cmp_to_key(comparator))
#
#     left_triangles = triangles[:len(triangles) // 2]
#     node.left = KdTree.build_kd_tree(left_triangles, depth + 1)
#
#     right_triangles = triangles[len(triangles) // 2:]
#     node.right = KdTree.build_kd_tree(right_triangles, depth + 1)
#
#     return node



class KdTree:
    def __init__(self, triangles: list[Triangle]):
        self.triangles = triangles
        self.tree = self.build_kd_tree(triangles, 0)

    @staticmethod
    def build_kd_tree(triangles: list[Triangle], depth: int = 0) -> KDNode:
        axis = depth % 3
        bbox = BoundingBox(
            copy(triangles[0].p1),
            copy(triangles[0].p1)
        )
        for triangle in triangles:
            for point in (triangle.p1, triangle.p2, triangle.p3):
                bbox.min.x, _, bbox.max.x = sorted((point.x, bbox.min.x, bbox.max.x))
                bbox.min.y, _, bbox.max.y = sorted((point.y, bbox.min.y, bbox.max.y))
                bbox.min.z, _, bbox.max.z = sorted((point.z, bbox.min.z, bbox.max.z))
                # bbox.min.x = min(bbox.min.x, point.x)
                # bbox.min.y = min(bbox.min.y, point.y)
                # bbox.min.z = min(bbox.min.z, point.z)
                # bbox.max.x = min(bbox.max.x, point.x)
                # bbox.max.y = min(bbox.max.y, point.y)
                # bbox.max.z = min(bbox.max.z, point.z)
        node = KDNode(bbox, axis)

        if len(triangles) <= 3:
            node.triangles = triangles
            return node

        def comparator(a: Triangle, b: Triangle) -> bool:
            a_center, b_center = 0, 0

            match axis:
                case 0:
                    a_center = (a.p1.x + a.p2.x + a.p3.x) / 3
                    b_center = (b.p1.x + b.p2.x + b.p3.x) / 3
                case 1:
                    a_center = (a.p1.y + a.p2.y + a.p3.y) / 3
                    b_center = (b.p1.y + b.p2.y + b.p3.y) / 3
                case 2:
                    a_center = (a.p1.z + a.p2.z + a.p3.z) / 3
                    b_center = (b.p1.z + b.p2.z + b.p3.z) / 3

            return a_center < b_center

        # triangles = sorted(triangles, key=cmp_to_key(comparator))
        triangles = nlargest(len(triangles), triangles, key=cmp_to_key(comparator))

        left_triangles = triangles[:len(triangles) // 2]
        node.left = KdTree.build_kd_tree(left_triangles, depth + 1)

        right_triangles = triangles[len(triangles) // 2:]
        node.right = KdTree.build_kd_tree(right_triangles, depth + 1)

        return node


    def ray_intersects_kd_tree(self, ray_origin: Vec3, ray_end: Vec3) -> Triangle | None:
        return self.ray_intersects_node(self.tree, ray_origin, ray_end)


    def ray_intersects_node(self, node: KDNode, ray_origin: Vec3, ray_end: Vec3) -> Triangle | None:
        if node is None: return None
        if not node.bbox.intersect_check(ray_origin, ray_end): return None

        if node.triangles is not None and len(node.triangles) > 0:
            # print(node.triangles)
            for triangle in node.triangles:
                if triangle.intersect_check(ray_origin, ray_end):
                    return triangle
            return None

        return (
            self.ray_intersects_node(node.left, ray_origin, ray_end)
            or
            self.ray_intersects_node(node.right, ray_origin, ray_end)
        )

    def ray_intersects_triangle(self, ray_origin: Vec3, ray_end: Vec3) -> Triangle | None:
        for triangle in self.triangles:
            if triangle.intersect_check(ray_origin, ray_end):
                return triangle
        return None