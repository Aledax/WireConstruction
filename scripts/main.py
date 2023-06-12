import pygame, sys, time
from pygame.locals import *
from _linalg import *
from _pygameplus import *
from wireframe import wireframeFromPreset, numPresets

# BUGS

# Back shading gets weird after rotating about Z and using the mouse at the same time

# FEATURES FOR 0.3

# Undo
# Orthographic / Perspective toggle
# Options for line thickness, color, dotted
# Light / Dark mode toggle

WINDOW_SIZE = (700, 700)
WINDOW_CENTER = roundV(scaleV(WINDOW_SIZE, 0.5))

WINDOW_SURFACE = pygame.display.set_mode(WINDOW_SIZE)

class App:
    def __init__(self):
        self.clock = pygame.time.Clock()
        self.windowSurface = WINDOW_SURFACE

        self.polyIndex = 3
        self.wireframe = wireframeFromPreset(self.polyIndex)

        # Geometric parameters
        self.keyRotationSpeed = 0.05
        self.mouseRotationSpeed = 0.005
        self.eyePos = (0, 0, -10)
        self.screenZ = -5
        self.zoom = scaleV(WINDOW_SIZE, 0.8)

        # Visual parameters
        self.backgroundColor = (0, 0, 0)
        self.antialias = True
        self.variableBrightness = True
        self.subedgeLength = 0.1
        self.subedgeLengthSquared = self.subedgeLength ** 2
        self.wireframeColor = (255, 255, 255)

        # Mouse input
        self.previousMousePressed = [False, False, False]
        self.previousMousePos = (0, 0)

        # Vertex selection
        self.vertexSelectionRadiusSquared = 20 ** 2
        self.vertexPositions = []
        self.selectedVertex = -1

        self.loop()

    def loop(self):
        while True:
            timer = time.perf_counter()

            # Generating vertex positions

            worldVertices = self.wireframe.getWorldVertices()
            screenVertices = [self.perspectifyVertex(v) for v in worldVertices]

            worldGhosts = self.wireframe.getWorldGhosts()
            screenGhosts = [self.perspectifyVertex(g) for g in worldGhosts]

            # Generating subedges for rendering

            subedges = [] # A subedge consists of (screen endpoint 1, screen endpoint 2, world z midpoint - used for brightness).

            for (v1, v2) in self.wireframe.edgeIndices:

                wv1, wv2 = worldVertices[v1], worldVertices[v2]
                sv1, sv2 = screenVertices[v1], screenVertices[v2]

                if (sv1 == sv2): continue

                worldEdgeLength = distance(wv1, wv2)
                screenEdgeLength = distance(sv1, sv2)
                subedgeCount = worldEdgeLength / self.subedgeLength

                svStep = scaleV(normalize(subV(sv2, sv1)), screenEdgeLength / subedgeCount)
                zStep = (wv2[2] - wv1[2]) / subedgeCount

                svCurrent = sv1
                zCurrent = wv1[2]

                for step in range(int(subedgeCount)):
                    svNew = addV(svCurrent, svStep)
                    subedges.append((svCurrent, svNew, zCurrent + zStep * 0.5))
                    zCurrent += zStep
                    svCurrent = svNew
                
                subedges.append((svCurrent, sv2, (zCurrent + wv2[2]) * 0.5))

            subedges = sorted(subedges, key = lambda subedge: subedge[2], reverse = True)

            # Input

            keys = pygame.key.get_pressed()
            mousePressed = pygame.mouse.get_pressed(3)
            mousePos = pygame.mouse.get_pos()

            # Rotation via keys

            if keys[K_LSHIFT]:
                rotationSpeed = self.keyRotationSpeed / 10
            else:
                rotationSpeed = self.keyRotationSpeed

            if keys[K_w]:
                self.wireframe.rotate((-rotationSpeed, 0, 0))
            if keys[K_s]:
                self.wireframe.rotate((rotationSpeed, 0, 0))
            if keys[K_a]:
                self.wireframe.rotate((0, rotationSpeed, 0))
            if keys[K_d]:
                self.wireframe.rotate((0, -rotationSpeed, 0))
            if keys[K_q]:
                self.wireframe.rotate((0, 0, -rotationSpeed))
            if keys[K_e]:
                self.wireframe.rotate((0, 0, rotationSpeed))

            # Rotation via mouse

            if mousePressed[0] and self.previousMousePressed[0]:
                mouseHorizontal = mousePos[0] - self.previousMousePos[0]
                mouseVertical = mousePos[1] - self.previousMousePos[1]
                self.wireframe.rotate(scaleV((mouseVertical, -mouseHorizontal, 0), self.mouseRotationSpeed))

            # Activating editing modes
            # 1: Adding edges
            # 2: Removing edges
            # 3: Adding / Removing vertices

            if keys[K_1] or keys[K_2] or keys[K_3]:
                closestVertex = -1
                closestDSquared = -1
                for i in range(len(worldVertices)):
                    dSquared = distanceSquared(screenVertices[i], mousePos)
                    if closestVertex != -1:
                        if dSquared < closestDSquared:
                            closestVertex = i
                            closestDSquared = dSquared
                    else:
                        if dSquared < self.vertexSelectionRadiusSquared:
                            closestVertex = i
                            closestDSquared = dSquared

            if not keys[K_1] and not keys[K_2]:
                self.selectedVertex = -1

            if keys[K_3]:
                closestGhost = -1
                for i in range(len(worldGhosts)):
                    dSquared = distanceSquared(screenGhosts[i], mousePos)
                    if closestGhost != -1:
                        if dSquared < closestDSquared:
                            closestGhost = i
                            closestDSquared = dSquared
                    else:
                        if dSquared < self.vertexSelectionRadiusSquared:
                            closestGhost = i
                            closestDSquared = dSquared

            # Events

            for event in pygame.event.get():

                # Exiting, debugging, resetting, switching polyhedra, visual preferences

                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    elif event.key == K_LEFT:
                        self.cyclePolyhedron(-1)
                    elif event.key == K_RIGHT:
                        self.cyclePolyhedron(1)
                    elif event.key == K_SPACE:
                        self.wireframe = wireframeFromPreset(self.polyIndex)
                    if keys[K_LALT]:
                        if event.key == K_1:
                            self.antialias = not self.antialias
                        elif event.key == K_2:
                            self.variableBrightness = not self.variableBrightness

                # Selecting vertices

                elif event.type == MOUSEBUTTONDOWN:
                    if keys[K_1]:
                        if closestVertex != -1 and self.selectedVertex != -1:
                            self.wireframe.addEdge((self.selectedVertex, closestVertex))
                            self.selectedVertex = -1
                        else:
                            self.selectedVertex = closestVertex
                    elif keys[K_2]:
                        if closestVertex != -1 and self.selectedVertex != -1:
                            self.wireframe.removeEdge((self.selectedVertex, closestVertex))
                            self.selectedVertex = -1
                        else:
                            self.selectedVertex = closestVertex
                    elif keys[K_3]:
                        if closestGhost != -1:
                            self.wireframe.materializeGhost(closestGhost)
                        elif closestVertex != -1:
                            self.wireframe.removeVertex(closestVertex)

            # Graphics

            self.windowSurface.fill(self.backgroundColor)

            # Render subedges

            for subedge in subedges:
                if self.antialias:
                    aaLine(self.windowSurface, subedge[0], subedge[1], 2, scaleV(self.wireframeColor, self.calculateBrightness(subedge[2])))
                else:
                    pygame.draw.line(self.windowSurface, scaleV(self.wireframeColor, self.calculateBrightness(subedge[2])), subedge[0], subedge[1], 4)

            # Draw vertices

            for i in range(len(worldVertices)):

                pygameDebug(self.windowSurface, addV(screenVertices[i], (-20, -20)), str(i))

                # Selection highlight

                if i != self.selectedVertex and not keys[K_1] and not keys[K_2] and not keys[K_3]:
                    continue
                
                if i == self.selectedVertex:
                    color = (0, 255, 255)
                elif i == closestVertex:
                    color = (255, 255, 0)
                elif keys[K_1]:
                    color = (0, 255, 0)
                elif keys[K_2]:
                    color = (255, 0, 255)
                else:
                    color = (255, 0, 0)

                pygame.draw.circle(self.windowSurface, color, screenVertices[i], 8)

            if keys[K_3]:
                for i in range(len(worldGhosts)):

                    pygameDebug(self.windowSurface, addV(screenGhosts[i], (-20, -20)), str(i), (255, 255, 0))

                    if i == closestGhost:
                        color = (255, 255, 125)
                    else:
                        color = (125, 125, 125)

                    pygame.draw.circle(self.windowSurface, color, screenGhosts[i], 8)

            self.previousMousePressed = mousePressed
            self.previousMousePos = mousePos

            pygameDebug(self.windowSurface, (10, 10), "Entire frame time: " + str(round((time.perf_counter() - timer) * 60, 2)))

            pygame.display.update()
            self.clock.tick(60)

    def cyclePolyhedron(self, change):
        self.polyIndex = (self.polyIndex + change) % numPresets
        self.wireframe = wireframeFromPreset(self.polyIndex)

    def perspectifyVertex(self, v):
        return addV(mulV(addV(self.eyePos[0:2], scaleV(subV(v[0:2], self.eyePos[0:2]), (self.screenZ - self.eyePos[2]) / (v[2] - self.eyePos[2]))), self.zoom), WINDOW_CENTER)
    
    def calculateBrightness(self, z):
        if not self.variableBrightness: return 1
        return min(max(0.625 - z, 0) + 0.3, 1)


if __name__ == '__main__':
    app = App()