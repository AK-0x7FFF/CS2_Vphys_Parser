from operator import itemgetter
from pickle import load
from struct import unpack

from .kd_tree import KdTree
from .math_helper import Triangle, Vec3, world_2_screen, Vec2
from .offsets import LOCAL_PLAYER_PAWN, VIEW_MATRIX, M_V_OLD_ORIGIN
from .pyMeow import pyMeow as meow
from .pyMeow import Module
from .pyMeow.process import Process
from vphys_2_tri_algo_1 import TimeCounter



def read_triangles_by_pkl(file_location: str) -> list[Triangle]:
    with open(file_location, "rb") as file:
        return load(file)


def read_triangles_by_tri(file_location: str) -> list[Triangle]:
    with open(file_location, "r") as file:
        content = file.read()
    bytes_content = bytes.fromhex(content)

    triangles: list[Triangle] = list()
    for index in range(len(bytes_content) // 36):
        index *= 36

        p1, p2, p3 = [
            Vec3(*unpack("fff", byte_split))
            for byte_split in itemgetter(
                slice(index, index + 12),
                slice(index + 12, index + 24),
                slice(index + 24, index + 36)
            )(bytes_content)
        ]
        triangles.append(Triangle(p1, p2, p3))
    return triangles


def main() -> None:
    cs2 = Process("cs2.exe")
    client: Module = itemgetter("client.dll")({module.name: module for module in cs2.modules()})

    local_Player_pawn_address = cs2.u64(client.base + LOCAL_PLAYER_PAWN)
    local_player_pos_address = local_Player_pawn_address + M_V_OLD_ORIGIN
    # local_player_head_pos_address = cs2.u64(cs2.u64(cs2.u64(local_Player_pawn_address + M_P_GAME_SCENE_NODE) + M_MODEL_STATE) + 0x80) + 0x20 * 6

    triangles = read_triangles_by_pkl("output.pkl")
    with TimeCounter("build_kd_tree", True):
        kd_tree = KdTree(triangles)

    target_points = (
        Vec3(124, -357, -110),
        Vec3(-1953, -622, -104)
    )

    meow.overlay_init(fps=144, target="Counter-Strike 2")
    while meow.overlay_loop():
        with TimeCounter("loop_time_cast", True):
            meow.begin_drawing()

            meow.draw_fps(10, 10)
            view_matrix = cs2.vec(client.base + VIEW_MATRIX, 16)
            screen = Vec2(meow.get_screen_width(), meow.get_screen_height())

            local_player_pos = cs2.vec(local_player_pos_address, 3)
            if local_player_pos is None:
                meow.end_drawing()
                continue
            local_player_pos = Vec3(*local_player_pos)
            local_player_pos.z += 64

            for target_point in target_points:
                intersects = kd_tree.ray_intersects_kd_tree(local_player_pos, target_point)

                point = world_2_screen(view_matrix, screen, target_point)
                if point is not None:
                    meow.draw_circle(
                        *point, 2,
                        meow.new_color(255, 0, 0, 255) if intersects is not None else meow.new_color(0, 255, 0, 255)
                    )

                if intersects is not None:
                    p1 = world_2_screen(view_matrix, screen, intersects.p1)
                    p2 = world_2_screen(view_matrix, screen, intersects.p2)
                    p3 = world_2_screen(view_matrix, screen, intersects.p3)
                    if not all((p1, p2, p3)):
                        continue

                    meow.draw_triangle_lines(
                        *p1.to_list(), *p2.to_list(), *p3.to_list(),
                        meow.new_color(255, 255, 255, 255)
                    )
            meow.end_drawing()




if __name__ == '__main__':
    main()
    # system("pause.")