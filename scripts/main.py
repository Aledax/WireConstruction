import pygame, sys, time, copy
from pygame.locals import *
from _linalg import *
from _pygameplus import *
from wireframe import wireframeFromPreset, numPresets

# BUGS

# Back shading gets weird after rotating about Z and using the mouse at the same time
# (Sometimes, ghost vertex detection fails (division by zero in normalize))

# FEATURES FOR 0.3 (Bracket when done)

# (Undo)
# (Orthographic / Perspective toggle)
# (Light / Dark mode toggle)
# (Debug information toggle)
# (Vertex depth)

# FEATURES FOR 0.4

# Initial preset rotation
# Allow creation of vertices at edge midpoints
# Options for line thickness, color, dotted
# Ability to save and load models as files
# Menu UI for loading a preset or a model file

WINDOW_SIZE = (700, 700)
WINDOW_CENTER = roundV(scaleV(WINDOW_SIZE, 0.5))

WINDOW_SURFACE = pygame.display.set_mode(WINDOW_SIZE)

# Keybinds

EDIT_SET_EDGE = K_1
EDIT_FILL = K_2
EDIT_DEL_EDGE = K_3

EDIT_GHOST_VERTEX = K_4
EDIT_MID_VERTEX = K_5
EDIT_DEL_VERTEX = K_6

COMMAND = K_LCTRL

class App:

    class Subedge:
        def __init__(self, screenV1, screenV2, worldZ, color, radius):
            self.screenV1, self.screenV2, self.worldZ, self.color, self.radius = screenV1, screenV2, worldZ, color, radius

    def __init__(self):
        self.clock = pygame.time.Clock()
        self.windowSurface = WINDOW_SURFACE

        # Geometric parameters
        self.keyRotationSpeed = 0.05
        self.mouseRotationSpeed = 0.005
        self.eyePos = (0, 0, -10)
        self.screenZ = -5
        self.perspectiveZoom = scaleV(WINDOW_SIZE, 0.8)
        self.orthogonalZoom = scaleV(WINDOW_SIZE, 0.4)

        # Visual parameters
        self.backgroundColor = (0, 0, 0)
        self.subedgeLength = 0.05
        self.subedgeLengthSquared = self.subedgeLength ** 2

        # Toggleables
        self.antialias = True
        self.variableBrightness = True
        self.perspective = True
        self.darkMode = True
        self.enableDebug = True

        # Mouse input
        self.previousMousePressed = [False, False, False]
        self.previousMousePos = (0, 0)

        # Edge styling
        self.setEdgeColor = (255, 255, 255)
        self.setEdgeRadius = 2
        self.setEdgeDotted = False

        # Vertex selection
        self.vertexSelectionRadiusSquared = 30 ** 2
        self.vertexPositions = []
        self.selectedVertex = -1

        # Wireframe
        self.wireframeUnitVectors = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        self.polyIndex = 3
        self.wireframeStack = [wireframeFromPreset(self.polyIndex)]
        self.maxUndos = 10

        self.loop()

    def loop(self):
        while True:
            timer = time.perf_counter()

            wireframe = copy.deepcopy(self.wireframeStack[-1])

            # Generating vertex positions

            worldVertices = wireframe.getWorldVertices(self.wireframeUnitVectors)
            screenVertices = [self.worldToScreen(v) for v in worldVertices]

            worldGhosts = wireframe.getWorldGhosts(self.wireframeUnitVectors)
            screenGhosts = [self.worldToScreen(g) for g in worldGhosts]

            # Generating Subedges for rendering

            subedges = []

            for edge in wireframe.edges:

                v1, v2 = edge.v1, edge.v2
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
                    if not edge.dotted or step % 2 == 0:
                        subedges.append(App.Subedge(svCurrent, svNew, zCurrent + zStep * 0.5, edge.color, edge.radius))
                    zCurrent += zStep
                    svCurrent = svNew
                
                subedges.append(App.Subedge(svCurrent, sv2, (zCurrent + wv2[2]) * 0.5, edge.color, edge.radius))

            subedges = sorted(subedges, key = lambda subedge: subedge.worldZ, reverse = True)

            # Input

            keys = pygame.key.get_pressed()
            mousePressed = pygame.mouse.get_pressed(3)
            mousePos = pygame.mouse.get_pos()

            # Rotation via keys

            if keys[COMMAND]:
                rotationSpeed = 0
            elif keys[K_LSHIFT]:
                rotationSpeed = self.keyRotationSpeed / 10
            else:
                rotationSpeed = self.keyRotationSpeed

            if keys[K_w]:
                self.rotate((-rotationSpeed, 0, 0))
            if keys[K_s]:
                self.rotate((rotationSpeed, 0, 0))
            if keys[K_a]:
                self.rotate((0, rotationSpeed, 0))
            if keys[K_d]:
                self.rotate((0, -rotationSpeed, 0))
            if keys[K_q]:
                self.rotate((0, 0, -rotationSpeed))
            if keys[K_e]:
                self.rotate((0, 0, rotationSpeed))

            # Rotation via mouse

            if mousePressed[0] and self.previousMousePressed[0]:
                mouseHorizontal = mousePos[0] - self.previousMousePos[0]
                mouseVertical = mousePos[1] - self.previousMousePos[1]
                self.rotate(scaleV((mouseVertical, -mouseHorizontal, 0), self.mouseRotationSpeed))

            # ACTIVATING EDITING MODES

            # 1: Setting edges (including modifying existing ones)
            # 3: Modifying ALL edges
            # 2: Removing edges

            # 4: Creating ghost vertices
            # 5: Creating midpoint vertices (not implemented)
            # 6: Removing vertices

            # Get the closest vertex to the mouse
            if keys[EDIT_SET_EDGE] or keys[EDIT_DEL_EDGE] or keys[EDIT_DEL_VERTEX]:
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

            # Enable selecting a second vertex?
            if not keys[EDIT_SET_EDGE] and not keys[EDIT_DEL_EDGE]:
                self.selectedVertex = -1

            # Get the closest ghost vertex to the mouse
            if keys[EDIT_GHOST_VERTEX]:
                closestGhost = -1
                closestDSquared = -1
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

                # Commands

                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if keys[COMMAND]:
                        if event.key == K_a:
                            self.antialias = not self.antialias
                        elif event.key == K_b:
                            self.variableBrightness = not self.variableBrightness
                        elif event.key == K_p:
                            self.perspective = not self.perspective
                        elif event.key == K_l:
                            self.darkMode = not self.darkMode
                        elif event.key == K_d:
                            self.enableDebug = not self.enableDebug
                        elif event.key == K_z:
                            self.undo()
                        elif event.key == K_r:
                            self.updateWireframe(wireframeFromPreset(self.polyIndex))
                        elif event.key == K_LEFT:
                            self.cyclePolyhedron(-1)
                        elif event.key == K_RIGHT:
                            self.cyclePolyhedron(1)

                # Selecting vertices

                elif event.type == MOUSEBUTTONDOWN:
                    if keys[EDIT_SET_EDGE]:
                        if closestVertex != -1 and self.selectedVertex != -1:
                            wireframe.addEdge((self.selectedVertex, closestVertex))
                            self.updateWireframe(wireframe)
                            self.selectedVertex = -1
                        else:
                            self.selectedVertex = closestVertex
                    elif keys[EDIT_DEL_EDGE]:
                        if closestVertex != -1 and self.selectedVertex != -1:
                            wireframe.removeEdge((self.selectedVertex, closestVertex))
                            self.updateWireframe(wireframe)
                            self.selectedVertex = -1
                        else:
                            self.selectedVertex = closestVertex
                    elif keys[EDIT_GHOST_VERTEX]:
                        if closestGhost != -1:
                            wireframe.materializeGhost(closestGhost)
                            self.updateWireframe(wireframe)
                    elif keys[EDIT_DEL_VERTEX]:
                        if closestVertex != -1:
                            wireframe.removeVertex(closestVertex)
                            self.updateWireframe(wireframe)

            # Graphics

            self.windowSurface.fill(self.flipColor(self.backgroundColor))

            # Draw subedges

            for subedge in subedges:
                if self.antialias:
                    aaLine(self.windowSurface, subedge.screenV1, subedge.screenV2, subedge.radius, self.flipColor(scaleV(subedge.color, self.edgeBrightness(subedge.worldZ))))
                else:
                    pygame.draw.line(self.windowSurface, self.flipColor(scaleV(subedge.color, self.edgeBrightness(subedge.worldZ))), subedge.screenV1, subedge.screenV2, 2 * subedge.radius)

            # Draw vertices

            # Normal vertices
            if keys[EDIT_SET_EDGE] or keys[EDIT_DEL_EDGE] or keys[EDIT_DEL_VERTEX]:
                for i in range(len(worldVertices)):

                    if self.enableDebug: pygameDebug(self.windowSurface, addV(screenVertices[i], (-20, -20)), str(i))

                    # Selection highlight
                    
                    if i == closestVertex:
                        color = (255, 255, 0)
                    elif keys[EDIT_SET_EDGE]:
                        color = (0, 255, 0)
                    elif keys[EDIT_DEL_EDGE]:
                        color = (255, 0, 255)
                    elif keys[EDIT_DEL_VERTEX]:
                        color = (255, 0, 0)

                    pygame.draw.circle(self.windowSurface, color, screenVertices[i], self.vertexRadius(worldVertices[i][2]))

            # Ghost veretices
            if keys[EDIT_GHOST_VERTEX]:
                for i in range(len(worldGhosts)):

                    if self.enableDebug: pygameDebug(self.windowSurface, addV(screenGhosts[i], (-20, -20)), str(i), (255, 255, 0))

                    if i == closestGhost:
                        color = (255, 255, 125)
                    else:
                        color = (125, 125, 125)

                    pygame.draw.circle(self.windowSurface, color, screenGhosts[i], self.vertexRadius(worldGhosts[i][2]))

            # Selected vertex
            if self.selectedVertex != -1:
                pygame.draw.circle(self.windowSurface, (0, 255, 255), screenVertices[self.selectedVertex], self.vertexRadius(worldVertices[self.selectedVertex][2]))

            # Previous input
            self.previousMousePressed = mousePressed
            self.previousMousePos = mousePos

            if self.enableDebug: pygameDebug(self.windowSurface, (10, 10), "Entire frame time: " + str(round((time.perf_counter() - timer) * 60, 2)))

            pygame.display.update()
            self.clock.tick(60)

    def rotate(self, rotation):
        for worldAxis in range(3):
            for localAxis in range(3):
                self.wireframeUnitVectors[localAxis] = rotateVector3Axis(self.wireframeUnitVectors[localAxis], rotation[worldAxis], worldAxis)

    def updateWireframe(self, newWireframe):
        if len(self.wireframeStack) == self.maxUndos + 1: self.wireframeStack.pop(0)
        self.wireframeStack.append(newWireframe)

    def undo(self):
        if len(self.wireframeStack) > 1: self.wireframeStack.pop(-1)

    def cyclePolyhedron(self, change):
        self.polyIndex = (self.polyIndex + change) % numPresets
        self.updateWireframe(wireframeFromPreset(self.polyIndex))

    def worldToScreen(self, v):
        if self.perspective:
            return addV(mulV(addV(self.eyePos[0:2], scaleV(subV(v[0:2], self.eyePos[0:2]), (self.screenZ - self.eyePos[2]) / (v[2] - self.eyePos[2]))), self.perspectiveZoom), WINDOW_CENTER)
        else:
            return addV(mulV(addV(self.eyePos[0:2], v[0:2]), self.orthogonalZoom), WINDOW_CENTER)

    def edgeBrightness(self, z):
        if not self.variableBrightness: return 1
        return min(max(0.625 - z, 0) + 0.3, 1)
    
    def vertexRadius(self, z):
        return 10 - z * 5
    
    def flipColor(self, color):
        if self.darkMode: return color
        return subV((255, 255, 255), color)


if __name__ == '__main__':
    app = App()