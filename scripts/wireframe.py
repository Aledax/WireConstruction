import math, copy, numpy
from _linalg import *

class Edge:

    defaultColor = (255, 255, 255)
    defaultRadius = 2
    defaultDotted = False

    def __init__(self, v1, v2, color = defaultColor, radius = defaultRadius, dotted = defaultDotted):
        self.v1, self.v2 = v1, v2 # Vertex INDICES, not coordinates
        self.color, self.radius, self.dotted = color, radius, dotted

class Wireframe:

    def __init__(self, vertices, edgeIndices, scale = 1):
        self.scale = scale

        # Relative vertices are constant, and are relative to wireframe's center.
        self.localVertices = vertices # Tuple3 list (coordinates)
        self.edges = [Edge(e[0], e[1]) for e in edgeIndices] # Edge list

        # A "ghost vertex" is one that does not technically exist in the localVertices array but may be
        # created by the user.
        # It is defined by 2 attributes: (world position, list of edges it touches)
        self.ghostVertices = []

    @property
    def edgeIndices(self):
        return [(e.v1, e.v2) for e in self.edges]
    
    def removeEdgeByIndices(self, v1, v2):
        for e in self.edges:
            if (e.v1 == v1 and e.v2 == v2) or (e.v1 == v2 and e.v2 == v1):
                self.edges.remove(e)
                return

    def reset(self):
        self.unitVectors = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

    def addEdge(self, edge):
        if edge[0] == edge[1]: return
        reversedEdge = (edge[1], edge[0])
        if edge in self.edgeIndices or reversedEdge in self.edgeIndices: return

        # Check if the edge would pass through an existing vertex, in which case call recursively
        for i in range(len(self.localVertices)):
            if i in edge: continue
            v = self.localVertices[i]
            if testParallel(subV(v, self.localVertices[edge[0]]), subV(v, self.localVertices[edge[1]])) == 1:
                self.addEdge((edge[0], i))
                self.addEdge((edge[1], i))
                return

        # Check if the edge would pass through an existing ghost
        for ghost in self.ghostVertices:
            if testParallel(subV(ghost[0], self.localVertices[edge[0]]), subV(ghost[0], self.localVertices[edge[1]])) == 1:
                ghost[1].append(edge)

        # If line segments intersect, then traversing between alternating endpoints (e1[0] -> e2[0] -> e1[1] -> e2[1]) will create a valid quadrilateral.
        # i.e. The 2 cross products obtained by traversing these endpoints will all be parallel and will point in the same direction.
        for otherEdge in self.edgeIndices:
            
            # Ghost edge is impossible unless all four vertices are distinct
            if edge[0] in otherEdge or edge[1] in otherEdge: continue

            path = [self.localVertices[i] for i in [edge[0], otherEdge[0], edge[1], otherEdge[1]]]
            c1 = cross3(subV(path[1], path[0]), subV(path[2], path[1]))
            c2 = cross3(subV(path[2], path[1]), subV(path[3], path[2]))
            c3 = cross3(subV(path[3], path[2]), subV(path[0], path[3]))

            # Make sure all paths are linearly independent
            if magnitude(c1) == 0 or magnitude(c2) == 0 or magnitude(c3) == 0:
                continue

            if testParallel(c1, c2) == 2 and testParallel(c2, c3) == 2:

                # Calculate edge intersection position
                p1, p2 = path[0], path[1]
                v1, v2 = subV(path[2], path[0]), subV(path[3], path[1])

                try:
                    s, t = numpy.linalg.solve([[v1[0], -v2[0]], [v1[1], -v2[1]]], [p2[0] - p1[0], p2[1] - p1[1]])
                except:
                    try:
                        s, t = numpy.linalg.solve([[v1[0], -v2[0]], [v1[2], -v2[2]]], [p2[0] - p1[0], p2[2] - p1[2]])
                    except:
                        s, t = numpy.linalg.solve([[v1[1], -v2[1]], [v1[2], -v2[2]]], [p2[1] - p1[1], p2[2] - p1[2]])

                p3 = addV(p1, scaleV(v1, s))

                # Check if a ghost with the same position already exists
                if any(p3 == ghost[0] for ghost in self.ghostVertices): continue
                
                # Check if intersection actually lies on the edges (and not just the lines they lie on)
                if testParallel(subV(p3, path[0]), subV(p3, path[2])) != 1 or testParallel(subV(p3, path[1]), subV(p3, path[3])) != 1: continue

                self.ghostVertices.append((p3, [edge, otherEdge]))

        self.edges.append(Edge(*edge))

    def removeEdge(self, edge):
        reversedEdge = (edge[1], edge[0])
        if edge in self.edgeIndices:
            self.removeEdgeByIndices(*edge)
        elif reversedEdge in self.edgeIndices:
            self.removeEdgeByIndices(*edge)

        # Delete edge data from ghosts that the edge crosses, remove ghosts if necessary
        newGhosts = []
        for ghost in self.ghostVertices:
            if edge in ghost[1]:
                ghost[1].remove(edge)
            elif reversedEdge in ghost[1]:
                ghost[1].remove(reversedEdge)
            if len(ghost[1]) >= 2:
                newGhosts.append(ghost)
        self.ghostVertices = newGhosts

    def materializeGhost(self, gId):
        ghost = self.ghostVertices[gId]
        newVertexId = len(self.localVertices)
        self.localVertices.append(ghost[0])

        newEdges = []

        # Delete the edges that are getting split
        for e in self.edges:
            indices, rindices = (e.v1, e.v2), (e.v2, e.v1)
            if indices not in ghost[1] and rindices not in ghost[1]:
                newEdges.append(e)
            # Update the edges of any other ghosts that have this edge
            else:
                for otherG in self.ghostVertices:
                    if otherG != ghost and (indices in otherG[1] or rindices in otherG[1]):
                        if indices in otherG[1]: otherG[1].remove(indices)
                        elif rindices in otherG[1]: otherG[1].remove(rindices)

                        if testParallel(subV(otherG[0], ghost[0]), subV(otherG[0], self.localVertices[e.v1])) == 1:
                            otherG[1].append((e.v1, newVertexId))
                        else:
                            otherG[1].append((e.v2, newVertexId))

        # Add the new halved edges
        for e in ghost[1]:
            newEdges.append(Edge(e[0], newVertexId))
            newEdges.append(Edge(e[1], newVertexId))

        self.edges = newEdges
        self.ghostVertices.pop(gId)

    def removeVertex(self, vId):

        # Delete edges connected to the vertex
        for i in range(len(self.edges) - 1, -1, -1):
            if vId == self.edges[i].v1 or vId == self.edges[i].v2:
                self.edges.pop(i)
        
        # Remove the vertex
        self.localVertices.pop(vId)

        # Shift the edge indices that are greater than vertex by -1
        for e in self.edges:
            e.v1 = e.v1 - 1 if e.v1 > vId else e.v1
            e.v2 = e.v2 - 1 if e.v2 > vId else e.v2

    def getWorldVertices(self, unitVectors):
        return [[sum(unitVectors[i][axis] * localV[i] for i in range(3)) * self.scale for axis in range(3)] for localV in self.localVertices]
    
    def getWorldGhosts(self, unitVectors):
        return [[sum(unitVectors[i][axis] * ghost[0][i] for i in range(3)) * self.scale for axis in range(3)] for ghost in self.ghostVertices]

globalScale = 1

tetrahedronVertices = [
    (1, 1, 1),
    (-1, -1, 1),
    (1, -1, -1),
    (-1, 1, -1),
]
tetrahedronEdges = [
    (0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)
]

cubeVertices = [
    (1, 1, 1),
    (-1, 1, 1),
    (-1, -1, 1),
    (1, -1, 1),
    (1, 1, -1),
    (-1, 1, -1),
    (-1, -1, -1),
    (1, -1, -1)
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
    (tetrahedronVertices, tetrahedronEdges, 1 / math.sqrt(3)),
    (cubeVertices, cubeEdges, 1 / math.sqrt(3)),
    (octahedronVertices, octahedronEdges, 1),
    (dodecahedronVertices, dodecahedronEdges, 1)
)
numPresets = len(presets)

def wireframeFromPreset(id):
    return Wireframe(copy.deepcopy(presets[id][0]), copy.deepcopy(presets[id][1]), copy.deepcopy(presets[id][2]) * globalScale)