import pygame, sys, time, copy
from pygame.locals import *
from _linalg import *
from _pygameplus import *
from wireframe import *

# BUGS

# Parallel test is weird for the dodecahedron
# Rarely get divisions by zero in parallel test

# FEATURES FOR 0.5

# Highlight edges to be deleted when clearing a vertex
# Functionality for saving and loading wireframes as files
# More aesthetically pleasing background

# Window options

WINDOW_SIZE = (700, 700)
WINDOW_CENTER = roundV(scaleV(WINDOW_SIZE, 0.5))

# World geometry

WORLD_EYE_Z = -10
WORLD_SCREEN_Z = -5
ZOOM_PERSPECTIVE = scaleV(WINDOW_SIZE, 0.8)
ZOOM_ORTHOGONAL = scaleV(WINDOW_SIZE, 0.4)
WORLD_SUBEDGE_LENGTH = 0.05

# Control

ROT_SPEED_KEY = 0.05
ROT_SPEED_KEYSLOW = 0.005
ROT_SPEED_MOUSE = 0.005

MAX_UNDOS = 10

VERTEX_RADIUS_SQUARED = math.pow(30, 2)

# Keybinds

KEY_LEFT = K_a
KEY_RIGHT = K_d
KEY_UP = K_w
KEY_DOWN = K_s
KEY_CCW = K_q
KEY_CW = K_e
KEY_SLOWROT = K_LSHIFT

KEY_PRESET = K_TAB

KEY_COMMAND = K_LCTRL

KEY_ADDEDGE = K_1
KEY_REMEDGE = K_2

KEY_CLRVERTEX = K_3
KEY_REMVERTEX = K_4

KEY_EDGESTYLE = K_5
KEY_FILLSTYLE = K_6

KEY_TOG_AA = K_a
KEY_TOG_DEPTH = K_d
KEY_TOG_VIEW = K_v
KEY_TOG_LIGHT = K_l
KEY_TOG_DEBUG = K_0

KEY_UNDO = K_z

KEY_QUIT = K_q

class App:

    class Subedge:
        def __init__(self, sv1, sv2, wz, color, radius):
            self.sv1, self.sv2, self.wz, self.color, self.radius = sv1, sv2, wz, color, radius

    def __init__(self):
        self.clock = pygame.time.Clock()
        self.windowSurface = pygame.display.set_mode(WINDOW_SIZE)

        # Video settings
        self.antialias = True
        self.edgeDepth = True
        self.perspective = True
        self.darkTheme = True
        self.enableDebug = True

        # Previous mouse state
        self.previousMousePos = (0, 0)

        # For selecting an edge (via two vertices)
        self.selectedV = -1

        # For adding edges
        self.edgeStyle = Wireframe.defaultStyle

        # For rotation
        self.wireframeUnitVectors = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

        # For undos
        self.wireframeStack = [wireframeFromPreset(1)]

        while True: self.loop()

    def worldToScreen(self, vertex):
        if self.perspective:
            return addV(mulV(scaleV(vertex[0:2], (WORLD_SCREEN_Z - WORLD_EYE_Z) / (vertex[2] - WORLD_EYE_Z)), ZOOM_PERSPECTIVE), WINDOW_CENTER)
        else:
            return addV(mulV(vertex.localPosition[0:2], ZOOM_ORTHOGONAL), WINDOW_CENTER)

    def generateSubedges(self, wireframe, worldVertices, screenVertices):

        subedges = []

        for e in range(len(wireframe.edges)):

            color = wireframe.edges[e].style["color"]
            radius = wireframe.edges[e].style["radius"]

            evs = list(wireframe.edgeLinks[e])     # Edge vertices
            wvs = [worldVertices[v] for v in evs]  # World vertex positions
            svs = [screenVertices[v] for v in evs] # Screen vertex positions

            if (svs[0] == svs[1]): continue

            wel = distance(wvs[0], wvs[1])   # World edge distance
            sel = distance(svs[0], svs[1])   # Screen edge distance
            sbc = wel / WORLD_SUBEDGE_LENGTH # Number of subedges

            # Subedge vector and z-step
            sbStep = scaleV(normalize(subV(svs[1], svs[0])), sel / sbc)
            zStep = (wvs[1][2] - wvs[0][2]) / sbc

            sbCurrent = svs[0]
            zCurrent = wvs[0][2]

            for step in range(int(sbc)):
                sbNew = addV(sbCurrent, sbStep)
                if not wireframe.edges[e].style["dotted"] or step % 2 == 0:
                    subedges.append(App.Subedge(sbCurrent, sbNew, zCurrent + zStep, color, radius))
                zCurrent += zStep
                sbCurrent = sbNew
        
            subedges.append(App.Subedge(sbCurrent, svs[1], (zCurrent + wvs[1][2]) * 0.5, color, radius))

        subedges = sorted(subedges, key = lambda sb: sb.wz, reverse = True)
        return subedges
    
    def rotateWireframeUnitVectors(self, rotation):
        for worldAxis in range(3):
            for localAxis in range(3):
                self.wireframeUnitVectors[localAxis] = rotateVector3Axis(self.wireframeUnitVectors[localAxis], rotation[worldAxis], worldAxis)

    def subedgeBrightness(self, worldZ):
        if not self.edgeDepth: return 1
        return min(max(0.625 - worldZ, 0) + 0.3, 1)
    
    def vertexRadius(self, worldZ):
        return 10 - worldZ * 5
    
    def flipColor(self, color):
        if self.darkTheme: return color
        return subV((255, 255, 255), color)

    def loop(self):
        timer = time.perf_counter()

        wireframe = copy.deepcopy(self.wireframeStack[-1])

        # Generating additional vertex and subedge data

        worldVertices = wireframe.getWorldVertices(self.wireframeUnitVectors)
        screenVertices = [self.worldToScreen(vertex) for vertex in worldVertices]
        subedges = self.generateSubedges(wireframe, worldVertices, screenVertices)

        # Input

        keys = pygame.key.get_pressed()
        mousePressed = pygame.mouse.get_pressed(3)
        mousePos = pygame.mouse.get_pos()

        # Rotation control

        if keys[KEY_COMMAND]:
            rotationSpeed = 0
        elif keys[KEY_SLOWROT]:
            rotationSpeed = ROT_SPEED_KEYSLOW
        else:
            rotationSpeed = ROT_SPEED_KEY

        if keys[KEY_UP]:
            self.rotateWireframeUnitVectors((-rotationSpeed, 0, 0))
        if keys[KEY_DOWN]:
            self.rotateWireframeUnitVectors((rotationSpeed, 0, 0))
        if keys[KEY_LEFT]:
            self.rotateWireframeUnitVectors((0, rotationSpeed, 0))
        if keys[KEY_RIGHT]:
            self.rotateWireframeUnitVectors((0, -rotationSpeed, 0))
        if keys[KEY_CCW]:
            self.rotateWireframeUnitVectors((0, 0, -rotationSpeed))
        if keys[KEY_CW]:
            self.rotateWireframeUnitVectors((0, 0, rotationSpeed))

        if mousePressed[0] and self.selectedV == -1:
            (mouseH, mouseV) = subV(mousePos, self.previousMousePos)
            self.rotateWireframeUnitVectors(scaleV((mouseV, -mouseH, 0), ROT_SPEED_MOUSE))

        # Closest vertex

        if keys[KEY_ADDEDGE] or keys[KEY_REMEDGE] or keys[KEY_REMVERTEX]:
            closestV = -1  # Closest vertex so far
            closestDS = -1 # Shortest distance squared so far
            
            for i in range(len(worldVertices)):

                # Ignore conditions
                if i == self.selectedV: continue
                if self.selectedV != -1:
                    if keys[KEY_ADDEDGE] and {self.selectedV, i} in wireframe.edgeLinks: continue
                    elif keys[KEY_REMEDGE] and {self.selectedV, i} not in wireframe.edgeLinks: continue

                # Calculate distance
                ds = distanceSquared(screenVertices[i], mousePos)
                if closestV != -1:
                    if ds < closestDS:
                        closestV = i
                        closestDS = ds
                else:
                    if ds < VERTEX_RADIUS_SQUARED:
                        closestV = i
                        closestDS = ds

        if not (keys[KEY_ADDEDGE] or keys[KEY_REMEDGE]):
            self.selectedV = -1

        # Events

        for event in pygame.event.get():

            # Commands

            if event.type == KEYDOWN and keys[KEY_COMMAND]:
                if event.key == KEY_QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.key == KEY_TOG_AA:
                    self.antialias = not self.antialias
                elif event.key == KEY_TOG_DEPTH:
                    self.edgeDepth = not self.edgeDepth
                elif event.key == KEY_TOG_VIEW:
                    self.perspective = not self.perspective
                elif event.key == KEY_TOG_LIGHT:
                    self.darkTheme = not self.darkTheme
                elif event.key == KEY_TOG_DEBUG:
                    self.enableDebug = not self.enableDebug
                elif event.key == KEY_UNDO:
                    if len(self.wireframeStack) > 1: self.wireframeStack.pop(-1)
            
            # Presets

            elif event.type == KEYDOWN and keys[KEY_PRESET]:
                if event.unicode.isdigit():
                    i = int(event.unicode)
                    if i >= 0 and i < numPresets:
                        self.wireframeStack.append(wireframeFromPreset(i))
            
            # Vertex Selection

            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                if keys[KEY_ADDEDGE] or keys[KEY_REMEDGE]:
                    self.selectedV = closestV
            
            elif event.type == MOUSEBUTTONUP and event.button == 1:
                if keys[KEY_ADDEDGE] and self.selectedV != -1 and closestV != -1:
                    wireframe.addEdge(self.selectedV, closestV, self.edgeStyle)
                    self.wireframeStack.append(wireframe)
                elif keys[KEY_REMEDGE] and self.selectedV != -1 and closestV != -1:
                    wireframe.removeEdge({self.selectedV, closestV})
                    self.wireframeStack.append(wireframe)
                elif keys[KEY_REMVERTEX] and closestV != -1:
                    wireframe.clearVertex(closestV)
                    self.wireframeStack.append(wireframe)
                self.selectedV = -1

        # Cap undos

        if len(self.wireframeStack) > MAX_UNDOS:
            self.wireframeStack.pop(0)

        # Background

        self.windowSurface.fill(self.flipColor((0, 0, 0)))

        # Draw subedges

        if self.antialias:
            for sb in subedges: aaLine(self.windowSurface, sb.sv1, sb.sv2, sb.radius, self.flipColor(scaleV(sb.color, self.subedgeBrightness(sb.wz))))
        else:
            for sb in subedges: pygame.draw.line(self.windowSurface, self.flipColor(scaleV(sb.color, self.subedgeBrightness(sb.wz))), sb.sv1, sb.sv2, 2 * sb.radius)

        # Draw dragging edge

        if mousePressed[0] and self.selectedV != -1:
            if closestV != -1:
                pos = screenVertices[closestV]
                if keys[KEY_ADDEDGE]:
                    color = (0, 255, 0)
                    radius = 1
                elif keys[KEY_REMEDGE]:
                    color = (255, 0, 0)
                    radius = 2
            else:
                pos = mousePos
                if keys[KEY_ADDEDGE]:
                    color = (200, 255, 200)
                elif keys[KEY_REMEDGE]:
                    color = (255, 200, 200)
                radius = 1
            
            if self.antialias: aaLine(self.windowSurface, screenVertices[self.selectedV], pos, radius, color)
            else: pygame.draw.line(self.windowSurface, color, screenVertices[self.selectedV], pos, 2 * radius)

        # Draw vertices

        for v in range(len(worldVertices)):
            if v == self.selectedV:
                pygame.draw.circle(self.windowSurface, (255, 0, 255), screenVertices[v], self.vertexRadius(worldVertices[v][2]))
            elif keys[KEY_ADDEDGE] or keys[KEY_REMEDGE] or keys[KEY_REMVERTEX]:
                if v == closestV: color = (255, 255, 0)
                elif keys[KEY_ADDEDGE]: color = (0, 255, 0)
                elif keys[KEY_REMEDGE]: color = (255, 0, 255)
                elif keys[KEY_REMVERTEX]: color = (255, 0, 0)

                pygame.draw.circle(self.windowSurface, color, screenVertices[v], self.vertexRadius(worldVertices[v][2]))

        if self.enableDebug:
            for v in range(len(worldVertices)):
                pygameDebug(self.windowSurface, addV(screenVertices[v], (-30, -30)), str(v))

        # Frame data

        self.previousMousePos = mousePos

        if self.enableDebug: pygameDebug(self.windowSurface, (10, 10), "Entire frame time: " + str(round((time.perf_counter() - timer) * 60, 2)))

        pygame.display.update()
        self.clock.tick(60)