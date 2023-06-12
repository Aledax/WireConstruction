import pygame, sys, time, copy, jsonpickle
from pygame.locals import *
from _resource import *
from _linalg import *
from _pygameplus import *
from wireframe import *

# BUGS

# (Parallel test is weird for the dodecahedron)
# - LESSONS:
#  - DO NOT try to equate weird calculations to zero. Instead, check if they are below a very low TOLERANCE.
#  - Checking whether two line segments intersect or not only requires the calculation of TWO path cross products.
#  - Instead of getting numpy to solve a system of linear equations entirely, you only need one of the constants, which
#    can easily be computed algebraically, with a bit of hand-written work first.

# FEATURES FOR 0.6

# (Toggle fancy background)
# (Custom edges)
# (Editing existing edges)
# (Two modes of edge selection)
# (Button widget)

# FEATURES FOR 0.7

# Enterbox widget
# Main menu screen
# Loading wireframe screen (preset or file)

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

VERTEX_RADIUS_SQUARED = math.pow(40, 2)

# Keybinds

KEY_LEFT = K_a
KEY_RIGHT = K_d
KEY_UP = K_w
KEY_DOWN = K_s
KEY_CCW = K_q
KEY_CW = K_e
KEY_SLOWROT = K_LSHIFT

KEY_PRESET = K_TAB

KEY_ADDEDGE = K_1
KEY_REMEDGE = K_2
KEY_EDTEDGE = K_3

KEY_REMVERTEX = K_4

KEY_COMMAND = K_LCTRL

KEY_TOG_AA = K_a
KEY_TOG_DEPTH = K_d
KEY_TOG_VIEW = K_v
KEY_TOG_LIGHT = K_l
KEY_TOG_GRADIENT = K_g
KEY_TOG_DEBUG = K_0

KEY_UNDO = K_z
KEY_SAVE = K_s
KEY_OPEN = K_o

KEY_QUIT = K_q

class App:

    class Subedge:
        def __init__(self, e, sv1, sv2, wz, color, radius):
            self.e, self.sv1, self.sv2, self.wz, self.color, self.radius = e, sv1, sv2, wz, color, radius

    def __init__(self):
        self.clock = pygame.time.Clock()
        self.windowSurface = pygame.display.set_mode(WINDOW_SIZE)

        # Video settings
        self.antialias = True
        self.edgeDepth = True
        self.perspective = True
        self.darkTheme = True
        self.gradientBG = True
        self.enableDebug = False

        # Background
        self.backgroundSurfaces = [
            [
                pygame.Surface(WINDOW_SIZE),
                pygame.Surface(WINDOW_SIZE)
            ],
            [
                self.verticalGradient(WINDOW_SIZE, (255, 255, 255), (255, 245, 230)),
                self.verticalGradient(WINDOW_SIZE, (0, 0, 51), (19, 0, 26))
            ]
        ]
        self.backgroundSurfaces[0][0].fill((255, 255, 255))
        self.backgroundSurfaces[0][1].fill((0, 0, 0))

        # Previous mouse state
        self.previousMousePos = (0, 0)

        # For selecting an edge (via two vertices)
        self.selectedV = -1
        self.dragSelect = True
        self.panning = False

        # For adding edges
        self.edgeStyle = copy.deepcopy(Wireframe.defaultStyle)

        # Buttons
        self.buttonEdgeWhite = CircleButton(30, 200, 20, self.setEdgeStyle, ("color", (255, 255, 255)))
        self.buttonEdgeRed = CircleButton(30, 260, 20, self.setEdgeStyle, ("color", (255, 0, 0)))
        self.buttonEdgeYellow = CircleButton(30, 320, 20, self.setEdgeStyle, ("color", (255, 255, 0)))
        self.buttonEdgeBlue = CircleButton(30, 380, 20, self.setEdgeStyle, ("color", (0, 0, 255)))
        self.buttonEdgeSolid = CircleButton(30, 440, 20, self.setEdgeStyle, ("dotted", False))
        self.buttonEdgeDotted = CircleButton(30, 500, 20, self.setEdgeStyle, ("dotted", True))
        self.buttons = [self.buttonEdgeWhite, self.buttonEdgeRed, self.buttonEdgeYellow, self.buttonEdgeBlue, self.buttonEdgeSolid, self.buttonEdgeDotted]

        # For rotation
        self.wireframeUnitVectors = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

        # For undos
        self.wireframeStack = [wireframeFromPreset(1)]

        while True: self.loop()

    def setEdgeStyle(self, parameter, value):
        self.edgeStyle[parameter] = value

    def verticalGradient(self, size, colorTop, colorBot):
        surface = pygame.Surface(size)
        for row in range(size[1]):
            color = roundV(lerpV(colorTop, colorBot, row / size[1]))
            pygame.draw.rect(surface, color, (0, row, size[0], 1))
        return surface

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
                    subedges.append(App.Subedge(e, sbCurrent, sbNew, zCurrent + zStep, color, radius))
                zCurrent += zStep
                sbCurrent = sbNew
        
            subedges.append(App.Subedge(e, sbCurrent, svs[1], (zCurrent + wvs[1][2]) * 0.5, color, radius))

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

        closestV = -1
        if (keys[KEY_ADDEDGE] or keys[KEY_REMEDGE] or keys[KEY_REMVERTEX] or keys[KEY_EDTEDGE]) and not self.panning:
            closestDS = -1 # Shortest distance squared so far
            
            for i in range(len(worldVertices)):

                # Ignore conditions
                if self.selectedV != -1:
                    if keys[KEY_ADDEDGE] and {self.selectedV, i} in wireframe.edgeLinks: continue
                    elif (keys[KEY_REMEDGE] or keys[KEY_EDTEDGE]) and {self.selectedV, i} not in wireframe.edgeLinks: continue

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

        # Drop selected vertex

        if not (keys[KEY_ADDEDGE] or keys[KEY_REMEDGE] or keys[KEY_EDTEDGE]):
            self.selectedV = -1

        # Background

        self.windowSurface.blit(self.backgroundSurfaces[self.gradientBG][self.darkTheme], (0, 0))

        # Draw subedges

        if self.antialias:
            for sb in subedges:
                color = sb.color if not (not keys[KEY_PRESET] and keys[KEY_REMVERTEX] and closestV != -1 and sb.e in wireframe.vertexLinks[closestV]) else (255, 0, 0)
                aaLine(self.windowSurface, sb.sv1, sb.sv2, sb.radius, self.flipColor(scaleV(color, self.subedgeBrightness(sb.wz))))
        else:
            for sb in subedges:
                color = sb.color if not (not keys[KEY_PRESET] and keys[KEY_REMVERTEX] and closestV != -1 and sb.e in wireframe.vertexLinks[closestV]) else (255, 0, 0)
                pygame.draw.line(self.windowSurface, self.flipColor(scaleV(color, self.subedgeBrightness(sb.wz))), sb.sv1, sb.sv2, 2 * sb.radius)

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
                elif keys[KEY_EDTEDGE]:
                    color = (255, 255, 0)
                    radius = 2
            else:
                pos = mousePos
                if keys[KEY_ADDEDGE]:
                    color = (200, 255, 200)
                elif keys[KEY_REMEDGE]:
                    color = (255, 200, 200)
                elif keys[KEY_EDTEDGE]:
                    color = (255, 255, 200)
                radius = 1
            
            if self.antialias: aaLine(self.windowSurface, screenVertices[self.selectedV], pos, radius, color)
            else: pygame.draw.line(self.windowSurface, color, screenVertices[self.selectedV], pos, 2 * radius)

        # Draw vertices

        if not keys[KEY_PRESET]:
            for v in sorted(range(len(worldVertices)), key = lambda v: worldVertices[v][2], reverse = True):
                if v != self.selectedV and (keys[KEY_ADDEDGE] or keys[KEY_REMEDGE] or keys[KEY_REMVERTEX] or keys[KEY_EDTEDGE]):
                    if v == closestV: color = (255, 255, 0)
                    elif keys[KEY_ADDEDGE]: color = (0, 255, 0)
                    elif keys[KEY_REMEDGE]: color = (255, 0, 255)
                    elif keys[KEY_REMVERTEX]: color = (255, 0, 0)
                    elif keys[KEY_EDTEDGE]: color = (255, 125, 0)
                    pygame.draw.circle(self.windowSurface, color, screenVertices[v], self.vertexRadius(worldVertices[v][2]))
            if self.selectedV != -1:
                pygame.draw.circle(self.windowSurface, (255, 0, 255), screenVertices[self.selectedV], self.vertexRadius(worldVertices[self.selectedV][2]))

        if self.enableDebug:
            for v in range(len(worldVertices)):
                pygameDebug(self.windowSurface, addV(screenVertices[v], (-30, -30)), str(v))

        # Draw buttons

        pygame.draw.circle(self.windowSurface, (255, 255, 255), self.buttonEdgeWhite.pos, 20)
        pygame.draw.circle(self.windowSurface, (255, 0, 0), self.buttonEdgeRed.pos, 20)
        pygame.draw.circle(self.windowSurface, (255, 255, 0), self.buttonEdgeYellow.pos, 20)
        pygame.draw.circle(self.windowSurface, (0, 0, 255), self.buttonEdgeBlue.pos, 20)

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
                elif event.key == KEY_TOG_GRADIENT:
                    self.gradientBG = not self.gradientBG
                elif event.key == KEY_TOG_DEBUG:
                    self.enableDebug = not self.enableDebug
                elif event.key == KEY_UNDO:
                    if len(self.wireframeStack) > 1: self.wireframeStack.pop(-1)
                elif event.key == KEY_SAVE:
                    name = input("Wireframe name: ")
                    writeTextFile("wireframes/custom/" + name + ".txt", jsonpickle.encode(wireframe))
                elif event.key == KEY_OPEN:
                    name = input("Wireframe name: ")
                    f = loadFile("wireframes/custom/" + name + ".txt")
                    if f:
                        self.wireframeStack.append(jsonpickle.decode(f.read()))
                    else:
                        print("No wireframe named " + name)
            
            # Presets

            elif event.type == KEYDOWN and keys[KEY_PRESET]:
                if event.unicode.isdigit():
                    i = int(event.unicode)
                    if i > 0 and i <= numPresets:
                        self.wireframeStack.append(wireframeFromPreset(i - 1))
            
            # Vertex Selection and Button Presses

            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                if closestV == -1:
                    self.panning = True
                if (keys[KEY_ADDEDGE] or keys[KEY_REMEDGE] or keys[KEY_EDTEDGE]) and self.selectedV == -1:
                    if closestV != -1:
                        self.selectedV = closestV
                        self.draggingV = True

                for button in self.buttons:
                    if button.checkHover(mousePos):
                        button.execute()
            
            elif event.type == MOUSEBUTTONUP and event.button == 1:
                if self.panning:
                    self.panning = False
                elif (keys[KEY_ADDEDGE] or keys[KEY_REMEDGE] or keys[KEY_EDTEDGE]):

                    success = False

                    if self.dragSelect:
                        if self.selectedV != -1:
                            if closestV != -1 and closestV != self.selectedV:
                                success = True
                            else:
                                self.dragSelect = True
                    else:
                        if closestV != -1 and closestV != self.selectedV:
                            success = True
                            self.dragSelect = True
                        else:
                            self.selectedV = -1
                            self.dragSelect = True

                    if success:
                        if keys[KEY_ADDEDGE]:
                            wireframe.addEdge(self.selectedV, closestV, self.edgeStyle)
                            self.wireframeStack.append(wireframe)
                        elif keys[KEY_REMEDGE]:
                            wireframe.removeEdge({self.selectedV, closestV})
                            self.wireframeStack.append(wireframe)
                        elif keys[KEY_EDTEDGE]:
                            wireframe.editEdge({self.selectedV, closestV}, self.edgeStyle)
                            self.wireframeStack.append(wireframe)
                        self.selectedV = -1

                elif keys[KEY_REMVERTEX]:
                    if closestV != -1:
                        wireframe.clearVertex(closestV)
                        self.wireframeStack.append(wireframe)
                        self.selectedV = -1

        # Cap undos

        if len(self.wireframeStack) > MAX_UNDOS:
            self.wireframeStack.pop(0)

        # Frame data

        self.previousMousePos = mousePos

        if self.enableDebug: pygameDebug(self.windowSurface, (10, 10), "Entire frame time: " + str(round((time.perf_counter() - timer) * 60, 2)))

        pygame.display.update()
        self.clock.tick(60)