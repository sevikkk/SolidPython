from euclid3 import Point3, Vector3, Matrix4

from .objects import OpenSCADObject, union, multmatrix
from .utils import draw_segment, Green, scad_matrix, Red


class Connector(OpenSCADObject):
    def __init__(self, position, direction, up=None, meta=None):
        OpenSCADObject.__init__(self, "connector", {})
        self.position = position
        self.direction = direction.normalized()
        self.meta = meta
        self.up = up

    def generate(self):
        out = union()(
            draw_segment(
                [self.position, -self.direction * 50],
                vec_color=Red,
                arrow_rad=3
            )
        )

        if self.up:
            out.add(draw_segment(
                [self.position, -self.up * 20],
                vec_color=Green,
                arrow_rad=2
            ))

        return out

    def _render(self, render_holes=False):
        if not self.children:
            self.add(self.generate())

        return OpenSCADObject._render(self, render_holes)

    def transform(self, m):
        new_position = m * self.position
        new_direction = m * self.direction
        if self.up:
            new_up = m * self.up
        else:
            new_up = self.up
        return Connector(new_position, new_direction, new_up, self.meta)

class Container(OpenSCADObject):
    origin = Connector(
        Point3(0, 0, 0),
        Vector3(0, 1, 0),
        Vector3(0, 0, 1)
    )

    origin_output_connectors = {}

    def __init__(self, input_connectors=None):
        OpenSCADObject.__init__(self, "container", {})
        self.position = self.origin()
        self.adjust_to_input(input_connectors)
        self.transform_matrix = self.generate_transform_matrix()
        self.add(self.generate())
        self.output_connectors = self.generate_output_connectors()

    def adjust_to_input(self, input_connectors):
        return

    def generate_at_origin(self):
        return union()

    def generate(self):
        obj = self.generate_at_origin()
        matrix = scad_matrix(self.transform_matrix)
        return multmatrix(m=matrix)(obj)

    def recursive_transform(self, v):
        m = self.transform_matrix

        if not v:
            return v
        if isinstance(v, Connector):
            return v.transform(m)
        elif isinstance(v, Point3):
            return m * v
        elif isinstance(v, Vector3):
            return m * v
        elif isinstance(v, dict):
            new_v = {}
            for k, v1 in v.items():
                new_v[k] = self.recursive_transform(v1)
            return new_v
        elif isinstance(v, list):
            new_v = []
            for v1 in v:
                new_v.append(self.recursive_transform(v1))
            return new_v
        else:
            raise RuntimeError("Unsupported type")

    def generate_output_connectors(self):
        m = self.transform_matrix

        return self.recursive_transform(self.origin_output_connectors)

    def generate_transform_matrix(self):
        m_rotate_base = Matrix4.new_look_at(
            Point3(0, 0, 0),
            -self.origin.direction,
            self.origin.up).inverse()
        m = Matrix4.new_look_at(
            Point3(0, 0, 0),
            -self.position.direction,
            self.position.up) * m_rotate_base
        move = self.position.position - self.origin.position
        m.d, m.h, m.l = move.x, move.y, move.z
        return m