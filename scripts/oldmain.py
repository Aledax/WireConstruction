import pygame, sys, math
from pygame.locals import *
from _linalg import *
from _pygameplus import *

WINDOW_SIZE = (700, 700)
WINDOW_CENTER = roundV(scaleV(WINDOW_SIZE, 0.5))

WINDOW_SURFACE = pygame.display.set_mode(WINDOW_SIZE)

class Vertex:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

        self.screenPos = (0, 0)

    @property
    def pos(self):
        return (self.x, self.y, self.z)

    def rotateXZ(self, center, angle):
        relX = self.x - center[0]
        relZ = self.z - center[2]
        newX = relX * math.cos(angle) - relZ * math.sin(angle)
        newZ = relX * math.sin(angle) + relZ * math.cos(angle)
        self.x = newX + center[0]
        self.z = newZ + center[2]

    def rotateYZ(self, center, angle):
        relY = self.y - center[1]
        relZ = self.z - center[2]
        newY = relY * math.cos(angle) - relZ * math.sin(angle)
        newZ = relY * math.sin(angle) + relZ * math.cos(angle)
        self.y = newY + center[1]
        self.z = newZ + center[2]

    def rotateXY(self, center, angle):
        relX = self.x - center[0]
        relY = self.y - center[1]
        newX = relX * math.cos(angle) - relY * math.sin(angle)
        newY = relX * math.sin(angle) + relY * math.cos(angle)
        self.x = newX + center[0]
        self.y = newY + center[1]

    def setScreenPos(self, wireframeCenter, eyePos): # Assumes the screen is the plane z = 0
        worldPos = addV(self.pos, wireframeCenter)
        displacement = subV(eyePos, worldPos)
        self.screenPos = addV(worldPos, scaleV(displacement, worldPos[2] / displacement[2]))[0:2]

class Edge:
    def __init__(self, v1, v2):
        self.v1, self.v2 = v1, v2

    def render(self, surface, color):
        pygame.draw.aaline(surface, color, addV(self.v1.screenPos, WINDOW_CENTER), addV(self.v2.screenPos, WINDOW_CENTER))

class Face:
    def __init__(self, vertices):
        self.vertices = vertices

    @property
    def normal(self):
        return 

class Wireframe:
    def __init__(self, center, vertices, edges):
        self.center, self.vertices, self.edges = center, vertices, edges

    def rotateXZ(self, angle):
        for v in self.vertices:
            v.rotateXZ(self.center, angle)

    def rotateYZ(self, angle):
        for v in self.vertices:
            v.rotateYZ(self.center, angle)

    def rotateXY(self, angle):
        for v in self.vertices:
            v.rotateXY(self.center, angle)

    def render(self, surface, color):
        for e in self.edges:
            e.render(surface, color)

class Solid:
    def __init__(self, center, vertices, edges, faces):
        self.center, self.vertices, self.edges, self.faces = center, vertices, edges, faces

vPositions = [
    # (-300, 0, 0), # Left
    # (300, 0, 0),  # Right
    # (0, -300, 0), # Top
    # (0, 300, 0),  # Bottom
    # (0, 0, -300), # Front
    # (0, 0, 300)   # Back
    (212, 212, 0),
    (0, 212, -212),
    (-212, 212, 0),
    (0, 212, 212),

    (212, -212, 0),
    (0, -212, -212),
    (-212, -212, 0),
    (0, -212, 212),
    
    (212, 0, -212),
    (-212, 0, -212),
    (-212, 0, 212),
    (212, 0, 212)
]

eIndices = [
    # (0, 2),
    # (0, 3),
    # (0, 4),
    # (0, 5),
    # (1, 2),
    # (1, 3),
    # (1, 4),
    # (1, 5),
    # (2, 4),
    # (3, 4),
    # (5, 3),
    # (5, 2)
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 8), (0, 11), (4, 8), (4, 11),
    (1, 8), (1, 9), (5, 8), (5, 9),
    (2, 9), (2, 10), (6, 9), (6, 10),
    (3, 10), (3, 11), (7, 10), (7, 11)
]

fIndices = [
    (0, 2, 4),
    (0, 4, 3),
    (0, 3, 5),
    (0, 5, 2),
    (1, 4, 2),
    (1, 3, 4),
    (1, 5, 3),
    (1, 2, 5)
]

class App:
    def __init__(self):
        self.clock = pygame.time.Clock()

        self.windowSurface = WINDOW_SURFACE

        self.backgroundColor = (255, 255, 255)
        self.gridlineColor = (0, 0, 0)

        self.vertices = []
        self.edges = []

        for v in vPositions:
            self.vertices.append(Vertex(v[0], v[1], v[2]))
        for e in eIndices:
            self.edges.append(Edge(self.vertices[e[0]], self.vertices[e[1]]))
        self.octahedron = Wireframe((0, 0, 500), self.vertices, self.edges)

        self.eyePosition = (0, 0, -100)
        self.movementSpeed = 2
        self.rotationSpeed = 0.05

        self.loop()

    @property
    def convergePosition(self):
        return (self.windowPosition[0], self.windowPosition[1], self.windowPosition[2] + self.convergeOffset)

    def loop(self):
        while True:
            keys = pygame.key.get_pressed()

            if keys[K_a]:
                self.octahedron.rotateXZ(-self.rotationSpeed)
            if keys[K_d]:
                self.octahedron.rotateXZ(self.rotationSpeed)
            if keys[K_w]:
                self.octahedron.rotateYZ(-self.rotationSpeed)
            if keys[K_s]:
                self.octahedron.rotateYZ(self.rotationSpeed)
            if keys[K_q]:
                self.octahedron.rotateXY(-self.rotationSpeed)
            if keys[K_e]:
                self.octahedron.rotateXY(self.rotationSpeed)


            for event in pygame.event.get():
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        pygame.quit()
                        sys.exit()

            self.windowSurface.fill(self.backgroundColor)

            for v in self.vertices:
                v.setScreenPos(self.octahedron.center, self.eyePosition)
            for e in self.edges:
                e.render(self.windowSurface, self.gridlineColor)

            pygame.display.update()
            self.clock.tick(60)

if __name__ == '__main__':
    app = App()