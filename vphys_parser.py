from dataclasses import dataclass
from struct import unpack
from typing import Union



class VphysConst:
    DICT_PREFIX = 0x0
    DICT_SUFFIX = 0x1
    LIST_PREFIX = 0x2
    HEX_PREFIX = 0x3
    LIST_SUFFIX = HEX_SUFFIX = 0x4

    INT_TYPE = 0x0
    FLOAT_TYPE = 0x1
    DICT_TYPE = 0x2
    LIST_TYPE = 0x3
    HEX_TYPE = 0x4

    # BOUNDARY_TYPE_MAPPING = {
    #     "{": DICT_PREFIX,
    #     "}": DICT_SUFFIX,
    #     "#[": HEX_PREFIX,
    #     "[": LIST_PREFIX,
    #     "]": LIST_SUFFIX,
    # }


class VphysContainer:
    def __init__(self, parser: "VphysParser", boundary_start: int) -> None:
        self.parser = parser

        self.boundary_start = boundary_start
        # self.__boundary_end: int | None = None
        self.boundary_end = self.get_boundary_end(boundary_start)

    # @property
    # def boundary_end(self) -> int | None:
    #     if self.__boundary_end is None:
    #         self.__boundary_end = self.get_boundary_end(self.boundary_start)
    #     return self.__boundary_end

    def get_boundary_end(self, start_line: int) -> int | None:
        if start_line not in self.parser.object_boundaries.keys(): ValueError()

        if (end_line_from_cache := self.parser.object_boundaries_box_cache.get(start_line, None)) is not None:
            return end_line_from_cache

        prefix_type = self.parser.get_boundary_mark_type(start_line)
        suffix_type = {
            VphysConst.DICT_PREFIX: VphysConst.DICT_SUFFIX,
            VphysConst.LIST_PREFIX: VphysConst.LIST_SUFFIX,
            VphysConst.HEX_PREFIX: VphysConst.HEX_SUFFIX,
        }.get(prefix_type, None)
        if prefix_type is None or suffix_type is None: return None

        # prefix_count, suffix_count = 1, 0
        # for line, boundary_type in {x: y for x, y in self.parser.object_boundaries.items() if x > start_line}.items():
        #     if boundary_type == prefix_type: prefix_count += 1
        #     if boundary_type == suffix_type: suffix_count += 1
        #
        #     if prefix_type == VphysConst.LIST_PREFIX:
        #         if boundary_type == VphysConst.HEX_PREFIX: prefix_count += 1
        #
        #     if prefix_count == suffix_count:
        #         self.parser.object_boundaries_box_cache.update({start_line: line})
        #         return line
            # print(prefix_count, suffix_count)
        prefix_count, suffix_count = 1, 0

        for line, boundary_type in ((line_filtering, boundary_type_filtering) for line_filtering, boundary_type_filtering in self.parser.object_boundaries.items() if line_filtering > start_line):
            if boundary_type == prefix_type: prefix_count += 1
            if boundary_type == suffix_type: suffix_count += 1

            if prefix_type == VphysConst.LIST_PREFIX:
                if boundary_type == VphysConst.HEX_PREFIX: prefix_count += 1

            if prefix_count == suffix_count:
                self.parser.object_boundaries_box_cache.update({start_line: line})
                return line



class VphysList(VphysContainer):
    def __init__(self, parser: "VphysParser", boundary_start: int):
        super().__init__(parser, boundary_start)

    def get_index_value(self, target_line: int) -> Union[float, "VphysDict", "VphysList", "VphysHex", None]:
        content = self.parser.get_line_content(target_line)

        match self.parser.get_boundary_mark_type(target_line):
            case VphysConst.DICT_PREFIX:
                return VphysDict(self.parser, target_line)
            case VphysConst.LIST_PREFIX:
                return VphysList(self.parser, target_line)
            case VphysConst.HEX_PREFIX:
                return VphysHex(self.parser, target_line)
            case None:
                return float(content.replace(",", ""))
        return None


    def get_index(self, target_index: int) -> Union[float, "VphysDict", None]:
        # line_index = self.boundary_start + 1
        # read_index = -1

        cached_list_boundary = self.parser.list_index_cache.get(self.boundary_start, {})
        if (cached_boundary := cached_list_boundary.get(target_index)) is not None:
            line_index =  cached_boundary[0]
            read_index = target_index - 1
        else:
            if cached_list_boundary.keys() and (max_index_in_cache := max(cached_list_boundary.keys())) < target_index:
                cached_boundary = cached_list_boundary[max_index_in_cache]

                line_index = cached_boundary[0]
                read_index = max_index_in_cache - 1
            else:
                line_index = self.boundary_start + 1
                read_index = -1

        while line_index < self.boundary_end:
            if self.parser.is_blank_line(line_index):
                line_index += 1
                continue

            var_type = self.parser.get_boundary_mark_type(line_index)
            read_index += 1

            if target_index == read_index:
                value = self.get_index_value(line_index)
                return value


            if var_type is None: line_index_next = line_index
            else:
                if var_type not in (VphysConst.DICT_PREFIX, VphysConst.LIST_PREFIX, VphysConst.HEX_PREFIX): return None
                line_index_next = boundary_end if (boundary_end := self.get_boundary_end(line_index)) is not None else line_index

            self.parser.list_index_cache.setdefault(self.boundary_start, {}).update({read_index: (line_index, line_index_next)})
            line_index = line_index_next + 1


class VphysDict(VphysContainer):
    def __init__(self, parser: "VphysParser", boundary_start: int):
        super().__init__(parser, boundary_start)

    def __getitem__(self, keyword: str) -> Union[int, float, "VphysDict", "VphysList", "VphysHex", None]:
        return self.get_var(keyword)

    def get_var_name(self, target_line: int) -> str | None:
        target_content_split = self.parser.get_line_content(target_line).split(" = ")

        if len(target_content_split) != 2: return None
        return target_content_split[0]

    def get_var_value(self, target_line: int) -> Union[int, float, "VphysDict", VphysList, "VphysHex", None]:
        target_content_split = self.parser.get_line_content(target_line).split(" = ")
        if len(target_content_split) != 2: return None
        content_var = target_content_split[1]


        if content_var != "":
            return float(content_var) if "." in content_var else int(content_var)
        else:
            target_line += 1

            match self.parser.get_boundary_mark_type(target_line):
                case VphysConst.DICT_PREFIX:
                    return VphysDict(self.parser, target_line)
                case VphysConst.LIST_PREFIX:
                    return VphysList(self.parser, target_line)
                case VphysConst.HEX_PREFIX:
                    return VphysHex(self.parser, target_line)
            return None

    def get_var(self, target_var_name: str) -> Union[int, float, "VphysDict", VphysList, "VphysHex", None]:
        line_index = self.boundary_start + 1
        while line_index < self.boundary_end:
            if self.parser.is_blank_line(line_index):
                line_index += 1
                continue

            var_name = self.get_var_name(line_index)
            if var_name is not None and var_name == target_var_name:
                return self.get_var_value(line_index)

            # line_index = line_index_next + 1 if (line_index_next := self.get_boundary_end(line_index)) is not None else line_index + 1
            line_index = self.get_boundary_end(line_index) + 1 if self.parser.get_boundary_mark_type(line_index) is not None else line_index + 1
        return None


class VphysHex(VphysContainer):
    def __init__(self, parser: "VphysParser", boundary_start: int):
        super().__init__(parser, boundary_start)

    def get_str(self) -> str | None:
        return " ".join(self.parser.get_line_content(line) for line in range(self.boundary_start + 1, self.boundary_end)).strip()

    def get_bytes(self) -> bytes:
        return bytes.fromhex(self.get_str())


class VphysParser:
    DICT_PREFIX = 0x0
    DICT_SUFFIX = 0x1
    LIST_PREFIX = 0x2
    HEX_PREFIX = 0x3
    LIST_SUFFIX = HEX_SUFFIX = 0x4

    INT_TYPE = 0x0
    FLOAT_TYPE = 0x1
    DICT_TYPE = 0x2
    LIST_TYPE = 0x3
    HEX_TYPE = 0x4

    def __init__(self, content: str) -> None:
        self.content = content.replace("\t", "").splitlines()
        self.object_boundaries = self.object_boundaries_build(self.content)

        self.object_boundaries_box_cache: dict[int, int] = dict()
        self.list_index_cache: dict[int, dict[int, tuple[int, int]]] = dict()

        self.main_dict = VphysDict(self, tuple(self.object_boundaries.keys())[0])


    @classmethod
    def from_file_name(cls, file_name: str) -> "VphysParser":
        with open(file_name, "r") as vphys_file:
            vphys_content = vphys_file.read()
            return VphysParser(vphys_content)


    def get_line_content(self, target_line: int) -> str:
        return self.content[target_line].lstrip()


    def get_boundary_mark_type(self, target_line: int) -> int | None:
        content = self.get_line_content(target_line).replace(",", "")
        return {
            "{": VphysConst.DICT_PREFIX,
            "}": VphysConst.DICT_SUFFIX,
            "#[": VphysConst.HEX_PREFIX,
            "[": VphysConst.LIST_PREFIX,
            "]": VphysConst.LIST_SUFFIX,
        }.get(content, None)


    def is_blank_line(self, target_line: int) -> bool:
        return self.get_line_content(target_line) == ""


    def object_boundaries_build(self, content: list) -> dict[int, int]:
        object_boundaries = dict()
        for line, line_content in enumerate(content):
            if "<!" in line_content: continue

            boundary_type = self.get_boundary_mark_type(line)
            if boundary_type is None: continue

            object_boundaries.update({line: boundary_type})
        boundaries = list(object_boundaries.values())
        if (
            boundaries.count(VphysConst.DICT_PREFIX) != boundaries.count(VphysConst.DICT_SUFFIX) or
            (boundaries.count(VphysConst.LIST_PREFIX) + boundaries.count(VphysConst.HEX_PREFIX)) != boundaries.count(VphysConst.LIST_SUFFIX)
        ):
            raise

        return object_boundaries


    def search(self, *args: int | str) -> int | float | bytes | None:
        target_object = self.main_dict
        for keyword in args:
            if isinstance(keyword, str):
                if isinstance(target_object, VphysDict): target_object = target_object.get_var(keyword)
                if isinstance(target_object, VphysHex): target_object = target_object.get_bytes()
                if target_object is None: return None
            elif isinstance(keyword, int):
                target_object = target_object.get_index(keyword)
            else: raise ValueError()

        return target_object


@dataclass
class Vec3:
    x: float
    y: float
    z: float

@dataclass
class Triangle:
    p1: Vec3
    p2: Vec3
    p3: Vec3

@dataclass
class Edge:
    next: int
    twin: int
    origin: int
    face: int


def bytes_merge(bytes_str: bytes, size: int) -> list[bytes]:
    bytes_count = len(bytes_str) // size

    a = list()
    for index in range(bytes_count):
        index *= size
        a.append(bytes_str[index:index + size])

    return a


class BytesUnpacker:
    @staticmethod
    def uint8(value: bytes) -> int:
        return unpack("B", value)[0]

    @staticmethod
    def int32(value: bytes) -> int:
        return unpack("i", value)[0]

    @staticmethod
    def float(value: bytes) -> float:
        return unpack("f", value)[0]



def main() -> None:
    parser = VphysParser.from_file_name("world_physics.vphys")
    saved_triangles = list()

    index = 0
    while True:
        collision = parser.search("m_parts", 0, "m_rnShape", "m_hulls", index, "m_nCollisionAttributeIndex")
        if collision == 0:
            # with TimeCounter('      search'):
            vertices_raw = parser.search("m_parts", 0, "m_rnShape", "m_hulls", index, "m_Hull", "m_Vertices")
            faces_raw = parser.search("m_parts", 0, "m_rnShape", "m_hulls", index, "m_Hull", "m_Faces")
            edges_raw = parser.search("m_parts", 0, "m_rnShape", "m_hulls", index, "m_Hull", "m_Edges")

            vertices = list()
            vertices_merged = bytes_merge(vertices_raw, 4)
            for i in range(len(vertices_merged) // 3):
                i *= 3
                vertices.append(Vec3(
                    BytesUnpacker.float(vertices_merged[i]),
                    BytesUnpacker.float(vertices_merged[i + 1]),
                    BytesUnpacker.float(vertices_merged[i + 2])
                ))

            faces = [
                BytesUnpacker.uint8(byte)
                for byte in bytes_merge(faces_raw, 1)
            ]

            edges = list()
            edges_merged = bytes_merge(edges_raw, 1)
            for i in range(len(edges_merged) // 4):
                i *= 4
                edges.append(Edge(
                    BytesUnpacker.uint8(edges_merged[i]),
                    BytesUnpacker.uint8(edges_merged[i + 1]),
                    BytesUnpacker.uint8(edges_merged[i + 2]),
                    BytesUnpacker.uint8(edges_merged[i + 3])
                ))

            for start_edge in faces:
                edge = edges[start_edge].next
                while edge != start_edge:
                    next_edge = edges[edge].next

                    saved_triangles.append(Triangle(
                        vertices[edges[start_edge].origin],
                        vertices[edges[edge].origin],
                        vertices[edges[next_edge].origin],
                    ))

                    edge = next_edge
            index += 1
        else: break


    index = 0
    while True:
        collision = parser.search("m_parts", 0, "m_rnShape", "m_meshes", index, "m_nCollisionAttributeIndex")
        if collision == 0:
            triangles_raw = parser.search("m_parts", 0, "m_rnShape", "m_meshes", index, "m_Mesh", "m_Triangles")
            vertices_raw = parser.search("m_parts", 0, "m_rnShape", "m_meshes", index, "m_Mesh", "m_Vertices")

            vertices = list()
            vertices_merged = bytes_merge(vertices_raw, 4)
            for i in range(len(vertices_merged) // 3):
                i *= 3
                vertices.append(Vec3(
                    BytesUnpacker.float(vertices_merged[i]),
                    BytesUnpacker.float(vertices_merged[i + 1]),
                    BytesUnpacker.float(vertices_merged[i + 2])
                ))

            # triangles_merged = bytes_merge(triangles_raw, 4)
            triangles_merged = [
                BytesUnpacker.int32(byte)
                for byte in bytes_merge(triangles_raw, 4)
            ]
            for i in range(len(triangles_merged) // 3):
                i *= 3
                saved_triangles.append(Triangle(
                    vertices[triangles_merged[i]],
                    vertices[triangles_merged[i + 1]],
                    vertices[triangles_merged[i + 2]],
                ))

            index += 1
        else: break


    from pickle import dump, HIGHEST_PROTOCOL
    with open("output.pkl", "wb") as file:
        dump(saved_triangles, file, protocol=HIGHEST_PROTOCOL)

    from struct import pack
    def pack_float(value: float) -> str:
        return pack("f", value).hex(" ").upper()
    byte_raw = list()

    for triangle in saved_triangles:
        for point in (triangle.p1, triangle.p2, triangle.p3):
            byte_raw.append(point.x)
            byte_raw.append(point.y)
            byte_raw.append(point.z)
    triangles_byte = " ".join([pack_float(i) for i in byte_raw])
    print(triangles_byte)
    with open("output.tri", "w") as file:
        file.write(triangles_byte)



if __name__ == '__main__':
    main()