# import math
import array
import math
import sys
import textwrap

# increase the max number of recursive calls
sys.setrecursionlimit(10000)  # my default is 1000

# Nomenclature

# geometry: list of Geom()
# igeom: 2, index of a Geom() in geometry

# faces: [0,1,2, 0,2,3], list of connectivity of all faces
# nfaces: range(int(len(faces)/3))
# face: [0,2,3], connectivity of one face

# ifaces: [0,1,2,7,11,], list of indexes of selected faces
# iface: 7, index of a face

# verts: [-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], list of coo of all vertices
# nverts: range(int(len(verts)/3))
# vert: [1,-1,1], Vector of one vertex

# iverts: [3,4,5,9,], list of indexes of selected verts
# ivert: 7, index of a vert

EPSILON = 1e-07
EPSILON2 = 1e-05

geometry = [None, None, None, None ]


class Geom():
    def __init__(self, verts, faces):
        # Check lenght
        if (len(verts) % 3) != 0:
            raise Exception('Invalid geom, verts lenght not 3n.')
        if (len(faces) % 3) != 0:
            raise Exception('Invalid geom, faces lenght not 3n.')
        # Init tmp geometry
        self.verts = array.array('f', verts)
        self.faces = array.array('i', faces)
        # Keep a link between new ifaces and their parent
        # Example: {1: (3, 4)} ifaces 3 and 4 are fragments of 1
        self.iface_to_children = {}

    def __repr__(self):
        return 'Geom(\n     {},\n     {},\n)'.format(self.verts, self.faces,)

    def clone(self):
        return Geom(verts=self.verts[:], faces=self.faces[:])


def check_geom_sanity(igeom):
    """
    Check geometry sanity

    If the mesh is correct and encloses a volume, this can be checked with
    prior tests: checking orientability, non-borders, non-self-intersecting.
    After that we can calculate its topological features and check if
    Euler's formula  C+V=A+2(S-H) is satisfied.
    If the mesh is not correct, many geometric algorithms will fail.
    The only solution in this case is the user repairing the mesh.

    >>> geometry[0] = Geom([-1,-1,0, 1,-1,0, 0,1,0, 0,0,1], [2,1,0, 0,1,3, 1,2,3, 2,0,3])  # Good tet
    >>> check_geom_sanity(0)
    True

    >>> geometry[0] = Geom([-1,-1,0, 1,-1,0, 0,1,0, 0,0,1,  0,0,2], [2,1,0, 0,1,3, 1,2,3, 2,0,3])  # Tet, loose vert
    >>> check_geom_sanity(0)
    Traceback (most recent call last):
    ...
    Exception: Invalid GEOM, loose verts.

    >>> geometry[0] = Geom([-1,-1,0, 1,-1,0, 0,0,1, 0,0,1], [2,1,0, 0,1,3, 1,2,3, 2,0,3])  # Tet, zero edge
    >>> check_geom_sanity(0)
    Traceback (most recent call last):
    ...
    Exception: ('Invalid GEOM, zero lenght edge in face:', 2)
    
    >>> geometry[0] = Geom([-1,-1,0, 1,-1,0, 0,-1,0, 0,0,1], [2,1,0, 0,1,3, 1,2,3, 2,0,3])  # Tet, zero face
    >>> check_geom_sanity(0)
    Traceback (most recent call last):
    ...
    Exception: ('Invalid GEOM, zero area iface:', 0)

    >>> geometry[0] = Geom([-1,-1,0, 1,-1,0, 0,1,0, 0,0,1], [0,1,2, 0,1,3, 1,2,3, 2,0,3])  # Tet, unorientable
    >>> check_geom_sanity(0)
    Traceback (most recent call last):
    ...
    Exception: ('Invalid GEOM, non-manifold or unorientable. iface, straight_edge:', 1, (0, 1))

    >>> geometry[0] = Geom([-1,-1,0, 1,-1,0, 0,1,0, 0,0,1], [       0,1,3, 1,2,3, 2,0,3])  # Tet, no base
    >>> check_geom_sanity(0)
    Traceback (most recent call last):
    ...
    Exception: ('Invalid GEOM, non closed at edge:', [0, None])
    
#    >>> geometry[0] = from_STL('self_intersecting.stl')
#    >>> check_geom_sanity(0)
#    Traceback (most recent call last):
#    ...
#    Exception: ('Invalid GEOM, self-intersecting:', 79, 145)
    """
    # Init
    nverts = get_nverts(igeom) 
    nfaces = get_nfaces(igeom)
    
    # Check loose vertices: vertices that have no connectivity
    used_iverts = []
    for iface in range(nfaces):
        used_iverts.extend(get_face(igeom, iface))
    used_iverts = set(used_iverts)
    if nverts != len(used_iverts) or nverts != max(used_iverts) + 1:
        raise Exception("Invalid GEOM, loose verts.")

    # Check degenerate geometry: zero lenght edge, zero area faces
    for iface in range(nfaces):      
        face = get_face(igeom, iface)
        a, b, c = get_vert(igeom, face[0]), get_vert(igeom, face[1]), get_vert(igeom, face[2])
        if (a - b).isZero() or (b - c).isZero() or (c - a).isZero():
            raise Exception("Invalid GEOM, zero lenght edge in face:", iface)
        if (a - b).cross(a - c).isZero():
            raise Exception('Invalid GEOM, zero area iface:', iface)
        
    # Check surface:
    # - 2-manifold and closed, each edge should join two faces, no more no less
    # - orientable, adjoining faces should have normals in the same directions
    edges = get_edges(igeom)  # This also checks orientability and 2-manifoldness
    nedges = len(edges)
    for edge in edges.values():
        if edge[1] is None:
            raise Exception("Invalid GEOM, non closed at edge:", edge)
        
#    # Check self intersection  # FIXME not working
#    ifaces = get_ifaces(igeom)
#    bsp = build_bsp(igeom, ifaces)
#    inverted_bsp = get_inverted_bsp(bsp)
#    clip_to(bsp, inverted_bsp)
#    remaining_ifaces = get_all_ifaces_from_bsp(bsp)
#    if remaining_ifaces:
#        raise Exception('Invalid GEOM, self-intersecting at faces:', remaining_ifaces)
    
    # Euler formula: nverts - nedges + nfaces = chi FIXME use it!
    # Euler characteristic chi of the connected sum of g tori is: chi = 2 − 2g, with g genus
    # g = 0, 1, 2, 3, ... => chi = 2, 0, -2, -4, ...
    chi = nverts - nedges + nfaces
    if chi not in range(2, 100, 2):
        raise Exception('Invalid GEOM, in Euler formula chi is:', chi)
        
    return True


#def get_pyfaces(igeom):  # FIXME currently not used
#    """
#    Get pyfaces
#    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, 0,2,3])
#    >>> get_pyfaces(0)
#    [array('i', [0, 1, 2]), array('i', [0, 2, 3])]
#    """
#    faces = geometry[igeom].faces
#    return [faces[3*iface:3*iface+3] for iface in range(get_nfaces(igeom))]


def get_face(igeom, iface):
    """
    Get iface face connectivity
    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, 0,2,3])
    >>> get_face(0, 1)
    array('i', [0, 2, 3])
    """
    return geometry[igeom].faces[3*iface:3*iface+3]


def set_face(igeom, iface, face):
    """
    Set iface face connectivity
    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, 0,2,3])
    >>> set_face(0, 1, (3,2,0))
    >>> get_face(0, 1)    
    array('i', [3, 2, 0])
    """
    geometry[igeom].faces[3*iface:3*iface+3] = array.array('i', face)


def append_face(igeom, face, iface_parent):
    """
    Append a face to the Geom, return its index iface.
    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, ])
    >>> iface = append_face(0, [0,2,3], 0)
    >>> get_face(0, iface)
    array('i', [0, 2, 3])
    """
    # Append face
    geometry[igeom].faces.extend(face)
    iface = get_nfaces(igeom) - 1
    # Register child
    children = geometry[igeom].iface_to_children
    if iface_parent in children:
        geometry[igeom].iface_to_children[iface_parent].append(iface)
    else:
        geometry[igeom].iface_to_children[iface_parent] = [iface, ]
    # Return
    return iface


def get_iface_children(igeom, iface):
    """
    Get iface children (not descendants)
    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, ])
    >>> iface = append_face(0, [0,2,3], 0)
    >>> iface = append_face(0, [0,2,3], 0)
    >>> iface = append_face(0, [0,2,3], 2)
    >>> iface = append_face(0, [0,2,3], 3)
    >>> get_iface_children(0, 0)
    [1, 2]
    >>> get_iface_children(0, 4)
    []
    """
    if iface not in geometry[igeom].iface_to_children:
        return []
    return geometry[igeom].iface_to_children[iface]


def get_nfaces(igeom):
    """
    Get the len of faces
    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, 0,2,3])
    >>> get_nfaces(0)
    2
    """
    return int(len(geometry[igeom].faces)/3)


def get_ifaces(igeom):
    """
    Get the range for faces
    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, 0,2,3])
    >>> get_ifaces(0)
    [0, 1]
    """
    return [i for i in range(int(len(geometry[igeom].faces)/3))]


def get_face_plane(igeom, iface):
    """
    Get plane from face normal and distance.
    >>> geometry[0] = Geom([1,0,0, 0,1,0, 0,0,1,], [0,1,2, ])
    >>> n, w = get_face_plane(0, 0)
    >>> print('n:', n, 'w:', w)
    n: Vector(0.577, 0.577, 0.577) w: 0.5773502691896258
    """
    face = get_face(igeom, iface)
    a, b, c = (
        Vector(get_vert(igeom, face[0])),
        Vector(get_vert(igeom, face[1])),
        Vector(get_vert(igeom, face[2])),
    )
    normal = b.minus(a).cross(c.minus(a)).unit()  # plane normal vector
    distance = normal.dot(a)  # plane distance from origin
    return normal, distance


def flip_iface_normal(igeom, iface):
    """
    Flip face normal.
    >>> geometry[0] = Geom([1,0,0, 0,1,0, 0,0,1,], [0,1,2, ])
    >>> flip_iface_normal(igeom=0, iface=0)
    >>> n, w = get_face_plane(igeom=0, iface=0)
    >>> print('n:', n, 'w:', w)
    n: Vector(-0.577, -0.577, -0.577) w: -0.5773502691896258
    """
    face = get_face(igeom, iface)
    set_face(igeom, iface, face=(face[2], face[1], face[0]))


def get_vert(igeom, ivert):
    """
    Get ivert vertex coordinates
    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, 0,2,3])
    >>> get_vert(0, 2)
    Vector(1.000, 1.000, 1.000)
    """
    return Vector(geometry[igeom].verts[3*ivert:3*ivert+3])


def append_vert(igeom, vert):
    """
    Append a vert to the Geom, return its index.
    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, 0,2,3])
    >>> ivert = append_vert(0, Vector(1., 1., 2.))
    >>> get_vert(0, ivert)
    Vector(1.000, 1.000, 2.000)
    """
    geometry[igeom].verts.extend(list(vert))
    return get_nverts(igeom)-1


def get_nverts(igeom):
    """
    Get the len of vertices
    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, 0,2,3])
    >>> get_nverts(0)
    4
    """
    return int(len(geometry[igeom].verts)/3)


def get_iverts(igeom):
    """
    Get the range for verts
    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, 0,2,3])
    >>> get_iverts(0)
    [0, 1, 2, 3]
    """
    return [i for i in range(int(len(geometry[igeom].verts)/3))]


def get_edges(igeom):
    """
    Get edge dict
    Eg: {(1,2):7,8]}
    {(ivert0, ivert1) : [iface on the left, iface on the right]}
    according to iface0 normal up, None if non-manifold.
    Raise exception if wrong normals.
    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, 0,2,3])
    >>> print(get_edges(0))
    {(0, 1): [0, None], (1, 2): [0, None], (2, 0): [0, 1], (2, 3): [1, None], (3, 0): [1, None]}
    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, 0,1,3])
    >>> print(get_edges(0))
    Traceback (most recent call last):
    ...
    Exception: ('Invalid GEOM, non-manifold or unorientable. iface, straight_edge:', 1, (0, 1))
    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, 3,2,0])
    >>> print(get_edges(0))
    Traceback (most recent call last):
    ...
    Exception: ('Invalid GEOM, non-manifold or unorientable. iface, straight_edge:', 1, (2, 0))
    """
    edges = dict()
    ifaces = get_ifaces(igeom)
    for iface in ifaces:
        face = get_face(igeom, iface)
        for i in range(3):
            # Set opposite edge
            opposite_edge = (face[(i+1) % 3], face[i])
            if opposite_edge in edges:
                if edges[opposite_edge][1]:
                    raise Exception('Invalid GEOM, non-manifold or unorientable. iface, opposite_edge:', iface, opposite_edge)
                else:
                    edges[opposite_edge][1] = iface
                    continue
            # Set straight edge
            straight_edge = (face[i], face[(i+1) % 3])
            if straight_edge in edges:
                raise Exception('Invalid GEOM, non-manifold or unorientable. iface, straight_edge:', iface, straight_edge)
            else:
                edges[straight_edge] = [iface, None]
    return edges


def to_STL(igeom, filename):
    """
    Write self to STL file
    """
    with open(filename, 'w') as f:
        f.write('solid name\n')
        for iface in get_ifaces(igeom):
            f.write('facet normal 0 0 0\n')
            f.write('    outer loop\n')
            for ivert in get_face(igeom, iface):
                f.write('        vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n'.format(v=get_vert(igeom, ivert)))
            f.write('    endloop\n')
            f.write('endfacet\n')
        f.write('endsolid name\n')


def from_STL(filename):
    """
    Import verts and faces from STL file into self
    >>> geometry[0] = Geom([-1,-1,1, 1,-1,1, 1,1,1, -1,1,1], [0,1,2, 0,2,3])
    >>> to_STL(0,'doctest.stl')
    >>> from_STL('doctest.stl')
    Geom(
         array('f', [-1.0, -1.0, 1.0, 1.0, -1.0, 1.0, 1.0, 1.0, 1.0, -1.0, 1.0, 1.0]),
         array('i', [0, 1, 2, 0, 2, 3]),
    )
    """
    # Get STL mesh
    from stl import mesh
    mesh = mesh.Mesh.from_file(filename)
    verts, faces, py_verts = [], [], []
    for iface, p in enumerate(mesh.points):
        # p is [-1.0, -1.0, -1.0, -1.0, -1.0, 1.0, -1.0, 1.0, 1.0]
        verts.extend(p)
        faces.extend((3*iface, 3*iface+1, 3*iface+2))
        py_verts.append((p[0], p[1], p[2]))
        py_verts.append((p[3], p[4], p[5]))
        py_verts.append((p[6], p[7], p[8]))
    # Remove duplicated verts
    unique_py_verts = [x for n, x in enumerate(py_verts) if x not in py_verts[:n]]
    new_faces = []
    for ivert in faces:
        new_ivert = unique_py_verts.index(py_verts[ivert])  # Get new index
        new_faces.append(new_ivert)  # Append it to the faces
    unique_verts = [v for vs in unique_py_verts for v in vs]  # Flatten
    return Geom(unique_verts, new_faces)


def get_joined_geom(igeom0, igeom1):  # FIXME
    verts = geometry[igeom0].verts[:]
    faces = geometry[igeom0].faces[:]
    nverts0 = int(len(verts)/3)
    verts.extend(geometry[igeom1].verts[:])
    for ivert in geometry[igeom1].faces[:]:
        new_ivert = ivert + nverts0
        faces.append(new_ivert)
    return Geom(verts, faces)


class Vector(object):
    def __init__(self, *args):  # FIXME simplify
        self.x, self.y, self.z = 0., 0., 0.
        if len(args) == 3:  # Vector(1,2,3)
            self.x, self.y, self.z = args[0], args[1], args[2]
        elif len(args) == 1:  # Vector([1,2,3])
            a = args[0]
            if isinstance(a, dict):
                self.x, self.y, self.z = \
                    a.get('x', 0.0), a.get('y', 0.0), a.get('z', 0.0)
            elif a is not None and len(a) == 3:
                self.x, self.y, self.z = a[0], a[1], a[2]

    def __repr__(self):
        return 'Vector({0:.3f}, {1:.3f}, {2:.3f})'.format(self.x, self.y, self.z)

    def clone(self):
        return Vector(self.x, self.y, self.z)

    def negated(self):
        return Vector(-self.x, -self.y, -self.z)

    def __neg__(self):
        return self.negated()

    def plus(self, a):
        return Vector(self.x+a.x, self.y+a.y, self.z+a.z)

    def __add__(self, a):
        return self.plus(a)

    def minus(self, a):
        return Vector(self.x-a.x, self.y-a.y, self.z-a.z)

    def __sub__(self, a):
        return self.minus(a)

    def times(self, a):
        return Vector(self.x*a, self.y*a, self.z*a)

    def __mul__(self, a):
        return self.times(a)

    def dividedBy(self, a):
        return Vector(self.x/a, self.y/a, self.z/a)

    def __truediv__(self, a):
        return self.dividedBy(float(a))

    def __div__(self, a):
        return self.dividedBy(float(a))

    def dot(self, a):
        return self.x*a.x + self.y*a.y + self.z*a.z

    def lerp(self, a, t):
        "Linear interpolation from self to a"
        return self.plus(a.minus(self).times(t))

    def length(self):
        return math.sqrt(self.dot(self))

    def unit(self):
        return self.dividedBy(self.length())

    def cross(self, a):
        return Vector(
            self.y * a.z - self.z * a.y,
            self.z * a.x - self.x * a.z,
            self.x * a.y - self.y * a.x,
            )

    def __getitem__(self, key):
        return (self.x, self.y, self.z)[key]

    def __setitem__(self, key, value):
        ll = [self.x, self.y, self.z]
        ll[key] = value
        self.x, self.y, self.z = ll

    def __len__(self):
        return 3

    def __iter__(self):
        return iter((self.x, self.y, self.z))

    def __eq__(self, other):
        return \
            math.isclose(self.x, other.x, rel_tol=EPSILON) and \
            math.isclose(self.y, other.y, rel_tol=EPSILON) and \
            math.isclose(self.z, other.z, rel_tol=EPSILON)

    def __hash__(self):
        return hash((self.x, self.y, self.z))

    def isZero(self):
        return abs(self.x) < EPSILON and \
               abs(self.y) < EPSILON and \
               abs(self.z) < EPSILON


class BSP():
    """
    BSP tree of igeom geometry
    """
    def __init__(self, igeom):
        self.igeom = igeom     # Referred igeom
        self.ifaces = []       # Coplanar ifaces, first iface is splitting
        self.front_bsp = None  # link to child BSPNode
        self.back_bsp = None   # link to child BSPNode

    def __repr__(self):
        return '\nBSP tree of igeom: {}{}'.format(self.igeom, self._repr_tree())

    def _repr_tree(self):
        # Get children trees
        front_tree = "None"
        if self.front_bsp:
            front_tree = self.front_bsp._repr_tree()
        back_tree = "None"
        if self.back_bsp:
            back_tree = self.back_bsp._repr_tree()
        # Join texts
        text = '\nifaces: {}\nfront_bsp: {}\nback_bsp: {}'.format(
            self.ifaces,
            front_tree,
            back_tree,
        )
        return textwrap.indent(text, ' ')

    def clone(self):
        cloned = BSP(igeom=self.igeom)
        cloned.ifaces = self.ifaces[:]
        if self.front_bsp:
            cloned.front_bsp = self.front_bsp.clone()
        if self.back_bsp:
            cloned.back_bsp = self.back_bsp.clone()
        return cloned

def get_new_geom_from_bsp(bsp):
    """
    Return a new Geom according to bsp contents
    """
    DEBUG = True
    igeom = bsp.igeom
    verts = geometry[igeom].verts  # FIXME to be cleaned of unused verts
    ifaces = get_ifaces(igeom)
    bsp_ifaces = set(get_all_ifaces_from_bsp(bsp))
    selected_ifaces = []
    # Choose the best faces
    if DEBUG:  # FIXME
        selected_ifaces = bsp_ifaces
    else:
        for iface in ifaces:
            if check_iface_export(igeom, iface, bsp_ifaces):
                selected_ifaces.append(iface)
                bsp_ifaces -= set(get_iface_descendants(igeom, iface))
    # Create the new faces from selected ifaces
    # selected_ifaces = bsp_ifaces  # FIXME
    faces = []
    for iface in selected_ifaces:
        faces.extend(get_face(igeom, iface))
    return Geom(verts, faces)


def check_iface_export(igeom, iface, bsp_ifaces):  # FIXME
    """
    Check if the face has all its fragments selected
    """
    if iface in bsp_ifaces:
        return True
    children = get_iface_children(igeom, iface)
    if children:
        for child in children:
            if not check_iface_export(igeom, child, bsp_ifaces):
                return False
        return True
    else:
        return False


def get_iface_descendants(igeom, iface):  # FIXME
    """
    Returns all descendants of iface
    """
    descendants = []
    children = get_iface_children(igeom, iface)
    descendants.extend(children)
    for child in children:
        descendants.extend(get_iface_descendants(igeom, child))
    return descendants


def get_all_ifaces_from_bsp(bsp):
    """
    Get recursively all ifaces from bsp and its children
    """
    ifaces = []
    ifaces.extend(bsp.ifaces)
    if bsp.front_bsp:
        ifaces.extend(get_all_ifaces_from_bsp(bsp.front_bsp))
    if bsp.back_bsp:
        ifaces.extend(get_all_ifaces_from_bsp(bsp.back_bsp))
    return ifaces


def build_bsp(igeom, ifaces):
    """
    Build BSP from igeom
    >>> geometry[0] = Geom([-1.0, -1.0, -1.0, -1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -1.0, 1.0, -1.0, 1.0, 1.0, 1.0, 1.0, 1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -1.0, -1.0], [0, 1, 2, 2, 3, 0, 3, 2, 4, 4, 5, 3, 5, 4, 6, 6, 7, 5, 1, 0, 7, 7, 6, 1, 7, 0, 3, 3, 5, 7, 4, 2, 1, 1, 6, 4])  # A cube
    >>> bsp = build_bsp(igeom=0, ifaces=get_ifaces(0))
    """
    # Create new node and append first iface, used as partition plane
    if not ifaces:
        return
    bsp = BSP(igeom)
    bsp.ifaces.append(ifaces[0])
    # Select ifaces for front and back, split them if needed.
    # front and back are lists of ifaces
    if len(ifaces) == 1:
        return bsp
    spl_igeom = igeom
    spl_iface = bsp.ifaces[0]
    front = []
    back = []
    for iface in ifaces[1:]:
        # coplanar front and back polygons go into self.polygons
        new_coplanar_front, new_coplanar_back, new_front, new_back, new_cut_iverts = split_face(
                igeom,
                iface,
                spl_igeom,
                spl_iface,
                )
        front.extend(new_front)
        back.extend(new_back)
        front.extend(new_coplanar_front)
        back.extend(new_coplanar_back)
    # Recursively build the BSP tree and return it
    if len(front) > 0:
        bsp.front_bsp = build_bsp(igeom, ifaces=front)
    if len(back) > 0:
        bsp.back_bsp = build_bsp(igeom, ifaces=back)
    return bsp


def get_inverted_bsp(bsp):  # FIXME
    """ 
    Convert bsp solid space to empty space and empty space to solid space.
    >>> geometry[0] = Geom([-1.0, -1.0, -1.0, -1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -1.0, 1.0, -1.0, 1.0, 1.0, 1.0, 1.0, 1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -1.0, -1.0], [0, 1, 2, 2, 3, 0, 3, 2, 4, 4, 5, 3, 5, 4, 6, 6, 7, 5, 1, 0, 7, 7, 6, 1, 7, 0, 3, 3, 5, 7, 4, 2, 1, 1, 6, 4])  # A cube
    >>> bsp = build_bsp(igeom=0, ifaces=get_ifaces(0))
    >>> bsp = get_inverted_bsp(bsp)
    >>> print(get_face_plane(0, 5))
    (Vector(-1.000, 0.000, 0.000), -1.0)
    """
    # Work on a clone
    bsp = bsp.clone()
    # Flip all face normals
    igeom = bsp.igeom
    for iface in bsp.ifaces:
        flip_iface_normal(igeom, iface)
    if bsp.front_bsp:
        bsp.front_bsp = get_inverted_bsp(bsp.front_bsp)
    if bsp.back_bsp: 
        bsp.back_bsp = get_inverted_bsp(bsp.back_bsp)
    # Swap front and back bsps
    tmp = bsp.front_bsp
    bsp.front_bsp = bsp.back_bsp
    bsp.back_bsp = tmp
    return bsp

def clip_faces(igeom, ifaces, clipping_bsp):  # FIX name, it returns front faces
    """
    Recursively remove all ifaces that are inside the clipping_bsp tree.
    """
    if not clipping_bsp.ifaces:
        return ifaces[:]  # FIXME why a copy?

    front = []
    back = []

    for iface in ifaces:
        new_coplanar_front, new_coplanar_back, new_front, new_back, new_cut_iverts = split_face(
                igeom,
                iface,
                spl_igeom=clipping_bsp.igeom,
                spl_iface=clipping_bsp.ifaces[0],
                )
        front.extend(new_front)
        back.extend(new_back)
        front.extend(new_coplanar_front)
        back.extend(new_coplanar_back)

    if clipping_bsp.front_bsp:
        # recurse on branches, conserve those polygons
        front = clip_faces(igeom, front, clipping_bsp.front_bsp)

    if clipping_bsp.back_bsp:
        # recurse on branches, conserve those polygons
        back = clip_faces(igeom, back, clipping_bsp.back_bsp)
    else:
        back = []  # but remove polygons that are back of the leaves

    # send all non removed polygons, for recursion
    front.extend(back)
    return front


def clip_to(bsp, clipping_bsp):  # FIX name, it returns None
    """
    Remove all polygons in bsp tree that are inside the clipping_bsp tree.
    """

    bsp.ifaces = clip_faces(
            igeom=bsp.igeom,
            ifaces=bsp.ifaces,
            clipping_bsp=clipping_bsp,
            )

    if bsp.front_bsp:
        clip_to(
                bsp=bsp.front_bsp,
                clipping_bsp=clipping_bsp,
                )
    if bsp.back_bsp:
        clip_to(
                bsp=bsp.back_bsp,
                clipping_bsp=clipping_bsp,
                )


def split_face(igeom, iface, spl_igeom, spl_iface):
    """
    Split iface by splitting_iface plane if needed.
    Update or append new verts and new faces to geometry(igeom).
    Return ifaces in the appropriate lists.
    >>> geometry[0] = Geom([-1.0, -1.0, -1.0, -1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -2.0, -2.0, 0.0, 2.0, -2.0, 0.0, 2.0, 2.0, 0.0,], [0,1,2, 3,4,5],)
    >>> print(split_face(igeom=0, iface=0, spl_igeom=0, spl_iface=1))
    ([], [], [2, 3], [4], [6, 7])
    >>> print(geometry[0])
    Geom(
         array('f', [-1.0, -1.0, -1.0, -1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -2.0, -2.0, 0.0, 2.0, -2.0, 0.0, 2.0, 2.0, 0.0, -1.0, -1.0, 0.0, -1.0, 0.0, 0.0]),
         array('i', [0, 1, 2, 3, 4, 5, 6, 1, 2, 6, 2, 7, 0, 6, 7]),
    )
    """
    # Vertices and faces types, collections of ifaces
    COPLANAR = 0  # vertex or face is within EPSILON2 distance from plane
    FRONT = 1     # vertex or face is in front of the plane
    BACK = 2      # vertex or face is at the back of the plane
    SPANNING = 3  # edge is intersected
    coplanar_front, coplanar_back, front, back = [], [], [], []
    cut_iverts = []  # collection of new iverts due to cuts

    # Classify each point as well as the entire polygon
    # into one of the above classes.
    faceType = 0
    vertexTypes = []
    spl_normal, spl_distance = get_face_plane(spl_igeom, spl_iface)
    face = get_face(igeom, iface)
    for ivert in face:
        # Calc the distance between the vertex and the splitting plane
        # then classify the vertex, and update classification of the face
        vert = get_vert(igeom, ivert)
        distance = spl_normal.dot(vert) - spl_distance
        if distance < -EPSILON2:
            vertexType = BACK
        elif distance > EPSILON2:
            vertexType = FRONT
        else:
            vertexType = COPLANAR
        faceType |= vertexType
        vertexTypes.append(vertexType)

    # Put the face in the correct list, splitting it when necessary.
    if faceType == COPLANAR:
        iface_normal, iface_w = get_face_plane(igeom, iface)
        if spl_normal.dot(iface_normal) > 0:
            coplanar_front.append(iface)
        else:
            coplanar_back.append(iface)
    elif faceType == FRONT:
        front.append(iface)
    elif faceType == BACK:
        back.append(iface)
    elif faceType == SPANNING:  # the face is spanning, so cut it
        front_iverts, back_iverts = [], []  # front vertices, back vertices
        for i in range(3):
            j = (i+1) % 3
            ti = vertexTypes[i]  # can be BACK, COPLANAR, FRONT
            tj = vertexTypes[j]
            vi = face[i]
            vj = face[j]
            # the edge is on one side or spanning?
            if ti != BACK:
                front_iverts.append(vi)
            if ti != FRONT:
                if ti != BACK:
                    back_iverts.append(vi)
                else:
                    back_iverts.append(vi)
            if (ti | tj) == SPANNING:
                # interpolation weight at the intersection point
                vi_vert = get_vert(igeom, vi)
                vj_vert = get_vert(igeom, vj)
                t = (spl_distance - spl_normal.dot(vi_vert)) \
                    / spl_normal.dot(vj_vert.minus(vi_vert))
                # intersection point on the plane
                cut_vert = vi_vert.lerp(vj_vert, t)
                cut_ivert = append_vert(igeom, cut_vert)
                front_iverts.append(cut_ivert)
                back_iverts.append(cut_ivert)
                # Record cut_ivert for later fixing of TJunctions
                cut_iverts.append(cut_ivert)

        # Add front cut faces
        if len(front_iverts) > 2:
            new_iface = append_face(igeom, front_iverts[0:3], iface)
            front.append(new_iface)
            if len(front_iverts) == 4:
                new_iface = append_face(
                        igeom,
                        (front_iverts[0], front_iverts[2], front_iverts[3]),
                        iface,
                    )
                front.append(new_iface)
        else:
            raise Exception('Problem with front spanning:', front_iverts)

        # Add back cut faces
        if len(back_iverts) > 2:
            new_iface = append_face(igeom, back_iverts[0:3], iface)
            back.append(new_iface)
            if len(back_iverts) == 4:
                new_iface = append_face(
                        igeom,
                        (back_iverts[0], back_iverts[2], back_iverts[3]),
                        iface,
                    )
                back.append(new_iface)
        else:
            raise Exception('Problem with back spanning:', back_iverts)

    # Return
    return coplanar_front, coplanar_back, front, back, cut_iverts


def geom_union(igeom0, igeom1, name='union'):  # FIXME
    """
    Union of igeom0 and igeom1
    >>> geometry[0] = Geom([-1,-1,0,   1,-1,0,   0,1,0,   0,0,1],   [2,1,0, 0,1,3, 1,2,3, 2,0,3])  # Good tet
    >>> geometry[1] = Geom([-.5,-1,0,  1.5,-1,0, 0.5,1,0, 0.5,0,1], [2,1,0, 0,1,3, 1,2,3, 2,0,3])  # Good tet, move x .5
    >>> geom_union(0, 1)
    Geom(
         array('f', [-1.0, -1.0, 0.0, 1.0, -1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.25, 0.5, 0.0, 0.25, -0.25, 0.75, -0.5, -1.0, 0.0, 1.5, -1.0, 0.0, 0.5, 1.0, 0.0, 0.5, 0.0, 1.0, 0.25, 0.5, 0.0, 0.25, -0.25, 0.75, 1.0, -1.0, 0.0, 0.25, 0.5, 0.0, 1.0, -1.0, 0.0, 0.25, -0.25, 0.75]),
         array('i', [2, 1, 0, 0, 1, 3, 2, 0, 3, 4, 2, 3, 4, 3, 5, 7, 8, 9, 8, 10, 11, 8, 11, 9, 8, 7, 12, 13, 8, 12, 14, 7, 9, 15, 14, 9]),
    )
    """
    a = build_bsp(igeom=igeom0, ifaces=get_ifaces(igeom0))
    b = build_bsp(igeom=igeom1, ifaces=get_ifaces(igeom1))

#    # Send to STL
#    to_STL(igeom0, filename='{}_a.stl'.format(name))
#    to_STL(igeom1, filename='{}_b.stl'.format(name))

    # Clip    
    clip_to(a, b)  # remove everything in a inside b
    clip_to(b, a)  # remove everything in b inside a

#    b = get_inverted_bsp(b)  # FIXME
#    clip_to(b, a)  # remove everything in -b inside a
#    b = get_inverted_bsp(b)

    # Create new geometry
    geometry[igeom0] = get_new_geom_from_bsp(a)
    geometry[igeom1] = get_new_geom_from_bsp(b)

    # Send to STL
    to_STL(igeom0, filename='{}_a_clipped.stl'.format(name))
    to_STL(igeom1, filename='{}_b_clipped.stl'.format(name))

    # Join
    geometry[igeom0] = get_joined_geom(igeom0, igeom1)

    # Send to STL
    to_STL(igeom0, filename='{}_ab.stl'.format(name))

    return geometry[igeom0]

def geom_intersection(igeom0, igeom1, name='inters'):  # FIXME working on this
    """
    Intersection of igeom0 and igeom1
    >>> geometry[0] = Geom([-1,-1,0,   1,-1,0,   0,1,0,   0,0,1],   [2,1,0, 0,1,3, 1,2,3, 2,0,3])  # Good tet
    >>> geometry[1] = Geom([-.5,-1,0,  1.5,-1,0, 0.5,1,0, 0.5,0,1], [2,1,0, 0,1,3, 1,2,3, 2,0,3])  # Good tet, move x .5
    >>> geom_intersection(0, 1)
    """
    a = build_bsp(igeom=igeom0, ifaces=get_ifaces(igeom0))
    b = build_bsp(igeom=igeom1, ifaces=get_ifaces(igeom1))

    # Send to STL
    to_STL(igeom0, filename='{}_a.stl'.format(name))
    to_STL(igeom1, filename='{}_b.stl'.format(name))

    a = get_inverted_bsp(a)
    clip_to(b, a)  # remove everything in b inside -a
    b = get_inverted_bsp(b)
    clip_to(a, b)  # remove everything in -a inside -b
    clip_to(b, a)  # remove everything in -b inside -a

    a = get_inverted_bsp(a)
    b = get_inverted_bsp(b)

    # Create new geometry
    geometry[igeom0] = get_new_geom_from_bsp(a)
    geometry[igeom1] = get_new_geom_from_bsp(b)

    # Send to STL
    to_STL(igeom0, filename='{}_a_clipped.stl'.format(name))
    to_STL(igeom1, filename='{}_b_clipped.stl'.format(name))

    # Join
    geometry[igeom0] = get_joined_geom(igeom0, igeom1)

    # Send to STL
    to_STL(igeom0, filename='{}_ab.stl'.format(name))

    return geometry[igeom0]


if __name__ == "__main__":
#    import doctest
#    doctest.testmod()
    
    print("Test cut: 1,0")
    # Get geometries
    geometry = [None, None,]
    geometry[0] = from_STL(filename='cube_a.stl')
    geometry[1] = from_STL(filename='cube_b.stl')
    geom_union(0, 1, name='cube_union')

#    geometry[0] = from_STL(filename='icosphere_a.stl')
#    geometry[1] = from_STL(filename='icosphere_b.stl')
#    geom_union(0, 1, name='icosphere_union')


#    # Create BSPs, this splits some triangles in the geometry
#    a = build_bsp(igeom=0, ifaces=get_ifaces(0))
#    b = build_bsp(igeom=1, ifaces=get_ifaces(1))
#    # Clip, this splits more triangles in the geometry
#    clip_to(a, b)
#    clip_to(b, a)
#    # Create new geometry
#    geometry.append(get_new_geom_from_bsp(a))
#    geometry.append(get_new_geom_from_bsp(b))
#    # Send to STL
#    to_STL(igeom=2, filename='a_clipped.stl')
#    to_STL(igeom=3, filename='b_clipped.stl')
