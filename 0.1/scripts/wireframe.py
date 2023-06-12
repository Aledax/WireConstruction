import math
from _linalg import *
from shapedata import *

class Wireframe:
    def __init__(self, center, vertices, edges, scale):
        self.center = center
        self.originalCenter = center
        
        self.scale = scale

        # Relative vertices are constant, and are relative to wireframe's center.
        self.relativeVertices = vertices # Tuple3 list (coordinates)
        self.edgeIndices = edges # Tuple2 list (vertex indices)
        self.extraEdges = [] # Tuple2 list (vertex indices)
        self.omittedEdges = [] # Tuple2 list (vertex indices)

        # Wireframe's local i, j, k in terms of world coordinates
        self.unitVectors = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

        # Absolute vertices are the vertices' actual world-position coordinates.
        self.absoluteVertices = [] # Tuple2 list (coordinates)
        self.absoluteEdges = [] # Tuple2 list (absolute vertices)

        self.calculateAbsolutes()

    def reset(self):
        self.center = self.originalCenter
        self.rotation = (0, 0, 0)
        self.extraEdges = []
        self.omittedEdges = []
        self.calculateAbsolutes()

    def move(self, displacement):
        self.center = addV(self.center, displacement)
        self.calculateAbsolutes()

    def rotate(self, rotation):
        for worldAxis in range(3):
            for localAxis in range(3):
                self.unitVectors[localAxis] = rotateVector3Axis(self.unitVectors[localAxis], rotation[worldAxis], worldAxis)
        self.calculateAbsolutes()

    def toggleEdge(self, vIndex1, vIndex2):
        if vIndex1 == vIndex2: return
        if (vIndex1, vIndex2) in self.omittedEdges or (vIndex2, vIndex1) in self.omittedEdges:
            if (vIndex2, vIndex1) in self.omittedEdges: self.omittedEdges.remove((vIndex2, vIndex1))
            else: self.omittedEdges.remove((vIndex1, vIndex2))
        elif (vIndex1, vIndex2) in self.extraEdges or (vIndex2, vIndex1) in self.extraEdges:
            if (vIndex2, vIndex1) in self.extraEdges: self.extraEdges.remove((vIndex2, vIndex1))
            else: self.extraEdges.remove((vIndex1, vIndex2))
        elif (vIndex1, vIndex2) in self.edgeIndices or (vIndex2, vIndex1) in self.edgeIndices:
            self.omittedEdges.append((vIndex1, vIndex2))
        else:
            self.extraEdges.append((vIndex1, vIndex2))

    def calculateAbsolutes(self):
        self.absoluteVertices = []
        for rV in self.relativeVertices:
            aV = [None, None, None]

            # Rotation matrix product
            for axis in range(3):
                aV[axis] = sum(self.unitVectors[i][axis] * rV[i] for i in range(3))

            self.absoluteVertices.append(addV(self.center, scaleV(aV, self.scale)))
        
        self.absoluteEdges = []
        for e in self.edgeIndices + self.extraEdges:
            if e in self.omittedEdges or (e[1], e[0]) in self.omittedEdges: continue
            self.absoluteEdges.append((self.absoluteVertices[e[0]], self.absoluteVertices[e[1]]))

commonCenter = (0, 0, 0)
commonRadius = 1

tetrahedron = Wireframe(commonCenter, tetrahedronVertices, tetrahedronEdges, commonRadius / math.sqrt(3))
cube = Wireframe(commonCenter, cubeVertices, cubeEdges, commonRadius / math.sqrt(3))
octahedron = Wireframe(commonCenter, octahedronVertices, octahedronEdges, commonRadius)

polyhedra = (
    tetrahedron, cube, octahedron
)