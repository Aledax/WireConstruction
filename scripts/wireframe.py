import math, copy
from _linalg import *

class Wireframe:

    tolerance = 0.0001

    defaultStyle = {
        "radius": 2,
        "color": (255, 255, 255),
        "dotted": False
    }

    class Vertex:
        def __init__(self, id, localPosition):
            self.id = id # Int
            self.localPosition = localPosition # Float Vector3

    class Edge:
        def __init__(self, id, style):
            self.id = id # Int
            self.style = style # Dict

    def __init__(self, vertexLocalPositions, edgeVertexConnections):
        
        # The lengths of vertices and vertexLinks should always be the same.
        # The lengths of edges and edgeLinks should always be the same.

        self.preset = -1

        self.vertices = [] # Vertex Array
        self.edges = [] # Edge Array

        self.vertexLinks = [] # Int Set Array (Which edges are each vertex connected to?)
        self.edgeLinks = [] # Int Set Array (Which vertices are each edge connected to?)

        for v in range(len(vertexLocalPositions)):
            self.vertices.append(Wireframe.Vertex(v, vertexLocalPositions[v]))
            self.vertexLinks.append(set())
        for e in range(len(edgeVertexConnections)):
            self.edges.append(Wireframe.Edge(e, Wireframe.defaultStyle))
            self.vertexLinks[edgeVertexConnections[e][0]].add(e)
            self.vertexLinks[edgeVertexConnections[e][1]].add(e)
            self.edgeLinks.append({*edgeVertexConnections[e]})

    def getWorldVertices(self, unitVectors):
        return [[sum(unitVectors[i][axis] * v.localPosition[i] for i in range(3)) for axis in range(3)] for v in self.vertices]

    # Returns True if they cross and False otherwise
    def vertexEdgeCrossCheck(self, v, evs):
        # Vertex cannot be one of the edge's vertices
        if v in evs: return False

        # Parallel check
        vp, ev1p, ev2p = (self.vertices[thisV].localPosition for thisV in [v] + list(evs))
        return testParallel(subV(vp, ev1p), subV(vp, ev2p), Wireframe.tolerance) == 1

    # Returns the point of intersection if they cross and None otherwise
    def edgeEdgeCrossCheck(self, evs1, evs2):
        # Vertices must be unique
        if not evs1.isdisjoint(evs2): return False

        # Calculate cross products
        levs1, levs2 = list(evs1), list(evs2)
        path = [self.vertices[v].localPosition for v in [levs1[0], levs2[0], levs1[1], levs2[1]]]
        c1 = cross3(subV(path[1], path[0]), subV(path[2], path[1]))
        c2 = cross3(subV(path[3], path[2]), subV(path[0], path[3]))
        
        # Cancel if linearly dependent
        if magnitudeSquared(c1) < Wireframe.tolerance or magnitudeSquared(c2) < Wireframe.tolerance: return None

        #print("Edges", evs1, "and", evs2, "are linearly dependent - calculating coplanar")

        # Cancel if 4 points are not coplanar
        if testParallel(c1, c2, Wireframe.tolerance) != 2:
            #print("Edges", evs1, "and", evs2, "are not coplanar, the result of the test is", testParallel(c1, c2))
            return None
        
        #print("Edges", evs1, "and", evs2, "are coplanar - calculating intersection")

        # Calculate intersection
        ap, bp, ar, br = path[0], path[1], subV(path[2], path[0]), subV(path[3], path[1])
        denominator = ar[0]*br[1]-br[0]*ar[1]
        #print("First denominator:", denominator)
        if abs(denominator) > Wireframe.tolerance:
            s = ((ap[1]-bp[1])*br[0]-(ap[0]-bp[0])*br[1])/denominator
        else:
            denominator = ar[1]*br[2]-br[1]*ar[2]
            #print("Second denominator:", denominator)
            if abs(denominator) > Wireframe.tolerance:
                s = ((ap[2]-bp[2])*br[1]-(ap[1]-bp[1])*br[2])/denominator
            else:
                denominator = ar[2]*br[0]-br[2]*ar[0]
                #print("Third denominator:", denominator)
                s = ((ap[0]-bp[0])*br[2]-(ap[2]-bp[2])*br[0])/denominator
        intersection = addV(ap, scaleV(ar, s))
        
        # Cancel if intersection doesn't lie on both edges
        result1, result2 = testParallel(subV(intersection, path[0]), subV(intersection, path[2]), Wireframe.tolerance), testParallel(subV(intersection, path[1]), subV(intersection, path[3]), Wireframe.tolerance)
        if result1 != 1 or result2 != 1: return None

        #print("Edges", evs1, "and", evs2, "are confirmed to have an intersection")
        
        # Confirmed intersection
        return intersection

    # Mimicks overloading by using the argument type:
    # Int: Edge id.
    # Set: Edge vertex links.
    def removeEdge(self, e):
        # Check e's type
        if isinstance(e, set):
            #print("Preparing to remove edge ", tuple(e))
            # e is a set; Check if evs actually exists
            evs = e
            if evs not in self.edgeLinks:
                # e does not exist; Check for vertex crossings
                for v in range(len(self.vertices)):
                    if self.vertexEdgeCrossCheck(v, evs):
                        # Crosses a vertex; Recursive call
                        #print("Found intersecting vertex ", v)
                        for thisV in evs:
                            self.removeEdge(thisV, v)
                        return
                return
            else:
                # e exists; set e to its edge index instead of its vertex links
                e = self.edgeLinks.index(e)

        # e exists.
        #print("Removing edge ", tuple(self.edgeLinks[e]))
        # Remove edge links from linked vertices
        for v in self.edgeLinks[e]:
            self.vertexLinks[v].discard(e)
        
        # Delete edge
        self.edges.pop(e)
        self.edgeLinks.pop(e)
        
        # Shift edge ids
        for v in range(len(self.vertices)):
            self.vertexLinks[v] = {otherE - 1 if otherE > e else otherE for otherE in self.vertexLinks[v]}
        for otherE in range(e, len(self.edges)):
            self.edges[otherE].id -= 1

    def clearVertex(self, v):
        delete = not self.vertexLinks[v]

        # Remove edges
        for e in sorted(self.vertexLinks[v], key = lambda e: e, reverse = True):
            self.removeEdge(e)
        
        if delete:
            # Delete vertex
            self.vertices.pop(v)
            self.vertexLinks.pop(v)
            
            # Shift vertex ids
            for otherV in range(v, len(self.vertices)):
                self.vertices[otherV].id -= 1
            for e in range(len(self.edges)):
                self.edgeLinks[e] = {otherV - 1 if otherV > v else otherV for otherV in self.edgeLinks[e]}

    def addEdge(self, v1, v2, style, checkCross = True):
        # Can't have an edge between two of the same vertex
        if v1 == v2: return
        # Can't make a duplicate edge
        if {v1, v2} in self.edgeLinks: return

        #print("Preparing to add edge ", (v1, v2))

        # Intersection check:
        # 1. If the edge crosses a vertex, call this function recursively
        # 2. Otherwise, if the edge crosses an edge, create a new vertex, and call this function recursively

        if checkCross:
            for v in range(len(self.vertices)):
                # Cross check
                if self.vertexEdgeCrossCheck(v, {v1, v2}):
                    # If True: Recursive call, return
                    #print("Found intersection with vertex ", v)
                    self.addEdge(v, v1, style)
                    self.addEdge(v, v2, style)
                    return
            
            for e in range(len(self.edges)):
                # "evs": Edge's vertices
                evs = self.edgeLinks[e]
                # Cross check
                intersection = self.edgeEdgeCrossCheck(evs, {v1, v2})
                if intersection:
                    #print("Found intersection with edge ", tuple(evs))
                    # If True:
                    # Remove crossing edge
                    otherStyle = self.edges[e].style
                    self.removeEdge(e)
                    # Create new vertex
                    newV = len(self.vertices)
                    self.vertices.append(Wireframe.Vertex(newV, intersection))
                    self.vertexLinks.append(set())
                    # Create 4 new edges
                    for otherV in evs:
                        self.addEdge(otherV, newV, otherStyle, False)
                    for thisV in {v1, v2}:
                        self.addEdge(thisV, newV, style)
                    return
            
        # No crosses at all
        #print("Adding edge ", (v1, v2))
        newE = len(self.edges)
        self.edges.append(Wireframe.Edge(newE, copy.deepcopy(style)))
        self.edgeLinks.append({v1, v2})
        for v in {v1, v2}:
            self.vertexLinks[v].add(newE)

    def editEdge(self, e, style):
        if (isinstance(e, set)):
            e = self.edgeLinks.index(e)
        self.edges[e].style = copy.deepcopy(style)

d1 = 1 / math.sqrt(3)
tetrahedronVertices = [
    (d1, d1, d1),
    (-d1, -d1, d1),
    (d1, -d1, -d1),
    (-d1, d1, -d1),
]
tetrahedronEdges = [
    (0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)
]

cubeVertices = [
    (-d1, d1, d1),
    (d1, d1, d1),
    (d1, -d1, d1),
    (-d1, -d1, d1),
    (-d1, d1, -d1),
    (d1, d1, -d1),
    (d1, -d1, -d1),
    (-d1, -d1, -d1)
]
cubeEdges = [
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7)
]

octahedronVertices = [
    (1, 0, 0),
    (-1, 0, 0),
    (0, 1, 0),
    (0, -1, 0),
    (0, 0, 1),
    (0, 0, -1)
]
octahedronEdges = [
    (0, 2), (0, 3), (0, 4), (0, 5),
    (1, 2), (1, 3), (1, 4), (1, 5),
    (2, 4), (3, 4), (3, 5), (5, 2)
]

gr = (1 + math.sqrt(5)) / 2 # Golden Ratio
d1 = 1 / math.sqrt(3)
d2 = 1 / (gr * math.sqrt(3))
d3 = math.sqrt(1 - d2 ** 2)

dodecahedronVertices = [
    (0, d2, d3),
    (0, -d2, d3),
    (0, -d2, -d3),
    (0, d2, -d3),
    (d3, 0, d2),
    (d3, 0, -d2),
    (-d3, 0, -d2),
    (-d3, 0, d2),
    (d2, d3, 0),
    (-d2, d3, 0),
    (-d2, -d3, 0),
    (d2, -d3, 0),

    (d1, d1, d1),
    (-d1, d1, d1),
    (d1, -d1, d1),
    (-d1, -d1, d1),
    (d1, d1, -d1),
    (-d1, d1, -d1),
    (d1, -d1, -d1),
    (-d1, -d1, -d1)
]
dodecahedronEdges = [
    (0, 1), (2, 3), (4, 5), (6, 7), (8, 9), (10, 11),

    (12, 0), (12, 4), (12, 8),
    (13, 0), (13, 7), (13, 9),
    (14, 1), (14, 4), (14, 11),
    (15, 1), (15, 7), (15, 10),
    (16, 3), (16, 5), (16, 8),
    (17, 3), (17, 6), (17, 9),
    (18, 2), (18, 5), (18, 11),
    (19, 2), (19, 6), (19, 10)
]

presets = (
    (tetrahedronVertices, tetrahedronEdges),
    (cubeVertices, cubeEdges),
    (octahedronVertices, octahedronEdges),
    (dodecahedronVertices, dodecahedronEdges)
)
numPresets = len(presets)

def wireframeFromPreset(id):
    w = Wireframe(*copy.deepcopy(presets[id]))
    w.preset = id
    return w

def wireframeEquality(w1, w2):
    if len(w1.vertices) != len(w2.vertices) or len(w1.edges) != len(w2.edges):
        return False

    vMappings = {}
    for v1 in range(len(w1.vertices)):
        found = False
        for v2 in range(len(w2.vertices)):
            if all(abs(c) <= Wireframe.tolerance for c in subV(w1.vertices[v1].localPosition, w2.vertices[v2].localPosition)):
                vMappings[v1] = v2
                #print("Current wireframe", v1, "= Goal wireframe", v2)
                found = True
                break
        if not found:
            #print("Bad vertex")
            return False
        
    for e1 in range(len(w1.edges)):
        if {vMappings[v] for v in w1.edgeLinks[e1]} not in w2.edgeLinks:
            #print("Bad edge: ", {vMappings[v] for v in w1.edgeLinks[e1]})
            return False
        
    return True