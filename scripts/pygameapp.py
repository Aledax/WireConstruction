from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame, sys, time, copy, jsonpickle
from pygame.locals import *
from _resource import *
from _linalg import *
from _pygameplus import *
from wireframe import *
import shaders

# FEATURES FOR 0.8

# (Use ModernGL to render the scene)
# (Fixed edge flashing by separating rendering and events)
# - Always try to keep your state unmodified through the whole rendering process!
# (Reorganize the shader:)
# 1. Define all graphics constants here and pass them into the shader
# 2. Make the shader's functionality more readable
# Fix the segmentation fault bug
# Fix the division by zero bug (nested pentagons)
# (Depth option)

# FEATURES FOR THE FUTURE

# Enterbox widget
# Separate game screen from the app
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

KEY_GOAL = K_TAB

KEY_ADDEDGE = K_1
KEY_REMEDGE = K_2
KEY_EDTEDGE = K_3

KEY_REMVERTEX = K_4

KEY_COMMAND = K_LCTRL

KEY_TOG_DEPTH = K_d
KEY_TOG_VIEW = K_v
KEY_TOG_DEBUG = K_0

KEY_RESET = K_r
KEY_UNDO = K_z
KEY_SAVE = K_s
KEY_OPEN = K_o

KEY_QUIT = K_q

class App:

    def __init__(self):
        self.clock = pygame.time.Clock()
        self.display = shaders.initSurface(WINDOW_SIZE)
        self.windowSurface = pygame.Surface(WINDOW_SIZE)

        # Shader parameters
        shaders.setUniform('scale', WINDOW_SIZE)

        shaders.setUniform('gradientTop', (0, 0, 0.25))
        shaders.setUniform('gradientBot', (0.16, 0, 0.2))

        shaders.setUniform('edgeBrightness', 2)
        shaders.setUniform('glowBrightness', 0.3)
        shaders.setUniform('edgeRadius', 0.00)
        shaders.setUniform('edgeAntiAlias', 0.004)
        shaders.setUniform('glowRadius', 0.03)
        shaders.setUniform('depthFactor', 4)
        shaders.setUniform('edgeWhitening', 0.075)
        shaders.setUniform('vertexHighlightRadius', 0.015)

        self.actionPulseFactor = 1
        self.placePulse = 1.25
        self.winPulse = 5

        # Video settings
        self.edgeDepth = True
        self.perspective = True
        self.enableDebug = False

        # Previous mouse state
        pygame.mouse.set_visible(False)
        self.previousMousePos = (0, 0)
        self.previousClosestV = -1

        # For selecting an edge (via two vertices)
        self.selectedV = -1
        self.dragSelect = True
        self.panning = False

        # Edge styling
        self.edgeStyle = copy.deepcopy(Wireframe.defaultStyle)

        # Buttons
        self.buttonEdgeWhite = CircleButton(30, 200, 20, self.setEdgeStyle, ("color", (255, 255, 255)))
        self.buttonEdgeRed = CircleButton(30, 260, 20, self.setEdgeStyle, ("color", (255, 0, 0)))
        self.buttonEdgeYellow = CircleButton(30, 320, 20, self.setEdgeStyle, ("color", (255, 255, 0)))
        self.buttonEdgeBlue = CircleButton(30, 380, 20, self.setEdgeStyle, ("color", (0, 125, 255)))
        self.buttonEdgeSolid = CircleButton(30, 440, 20, self.setEdgeStyle, ("dotted", False))
        self.buttonEdgeDotted = CircleButton(30, 500, 20, self.setEdgeStyle, ("dotted", True))
        self.buttons = [self.buttonEdgeWhite, self.buttonEdgeRed, self.buttonEdgeYellow, self.buttonEdgeBlue, self.buttonEdgeSolid, self.buttonEdgeDotted]

        # For rotation
        self.wireframeUnitVectors = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

        # Wireframe objects
        self.wireframeStack = [wireframeFromPreset(1)]
        self.goalWireframe = wireframeFromPreset(1)

        # Music and Sfx
        loadMusic("Beauty.mp3")
        pygame.mixer.music.set_volume(0.375)
        pygame.mixer.music.play(-1)

        # Music colors:
        # Opulence - Red
        # Intrigue - Gray
        # Beauty - Blue
        # Traditions - Purple
        # The Alchemist - Yellow
        # Transmutation Engine - Green

        self.showVertexSound = loadSfx("tick.wav")
        self.hideVertexSound = loadSfx("tick2.wav")
        self.hoverVertexSound = loadSfx("bike.wav")
        self.clickVertexSound = loadSfx("click.wav")
        self.breakSound = loadSfx("pop.wav")
        self.placeSound = loadSfx("glasstap2.wav")
        self.goalViewSound = loadSfx("sheet2.wav")
        self.goalHideSound = loadSfx("sheet3.wav")
        self.undoSound = loadSfx("undo.wav")
        self.winSound = loadSfx("win.wav")

        while True: self.loop()

    def setEdgeStyle(self, parameter, value):
        self.edgeStyle[parameter] = value

    def worldToScreen(self, vertex):
        if self.perspective:
            return addV(mulV(scaleV(vertex[0:2], (WORLD_SCREEN_Z - WORLD_EYE_Z) / (vertex[2] - WORLD_EYE_Z)), ZOOM_PERSPECTIVE), WINDOW_CENTER)
        else:
            return addV(mulV(vertex[0:2], ZOOM_ORTHOGONAL), WINDOW_CENTER)
        
    def rotateWireframeUnitVectors(self, rotation):
        for worldAxis in range(3):
            for localAxis in range(3):
                self.wireframeUnitVectors[localAxis] = rotateVector3Axis(self.wireframeUnitVectors[localAxis], rotation[worldAxis], worldAxis)
    
    def vertexRadius(self, worldZ):
        return 10 - worldZ * 5
    
    def quit(self):
        shaders.freeTextureMemory()
        pygame.quit()
        sys.exit()

    def loop(self):
        timer = time.perf_counter()
        self.windowSurface.fill((0, 0, 0))

        # Input

        keys = pygame.key.get_pressed()
        mousePressed = pygame.mouse.get_pressed(3)
        mousePos = pygame.mouse.get_pos()

        # Wireframe

        if keys[KEY_GOAL]:
            wireframe = copy.deepcopy(self.goalWireframe)
        else:
            wireframe = copy.deepcopy(self.wireframeStack[-1])

        # Generating additional vertex and subedge data

        worldVertices = wireframe.getWorldVertices(self.wireframeUnitVectors)
        screenVertices = [self.worldToScreen(vertex) for vertex in worldVertices]

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

        if mousePressed[0] and self.panning:
            (mouseH, mouseV) = subV(mousePos, self.previousMousePos)
            self.rotateWireframeUnitVectors(scaleV((mouseV, -mouseH, 0), ROT_SPEED_MOUSE))

        # Closest vertex

        closestV = -1
        if not keys[KEY_GOAL] and (keys[KEY_ADDEDGE] or keys[KEY_REMEDGE] or keys[KEY_REMVERTEX] or keys[KEY_EDTEDGE]) and not self.panning:
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
        if closestV != -1 and self.previousClosestV != closestV and self.selectedV != closestV: self.hoverVertexSound.play()

        # Drop selected vertex

        if not (keys[KEY_ADDEDGE] or keys[KEY_REMEDGE] or keys[KEY_EDTEDGE]):
            self.selectedV = -1

        # Draw dragging edge

        if mousePressed[0] and self.selectedV != -1 and not self.panning:
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
            
            aaLine(self.windowSurface, screenVertices[self.selectedV], pos, radius, color)

        if self.enableDebug:
            for v in range(len(worldVertices)):
                pygameDebug(self.windowSurface, addV(screenVertices[v], (-30, -30)), str(v))

        # Draw buttons

        # pygame.draw.circle(self.windowSurface, (255, 255, 255), self.buttonEdgeWhite.pos, 20)
        # pygame.draw.circle(self.windowSurface, (255, 0, 0), self.buttonEdgeRed.pos, 20)
        # pygame.draw.circle(self.windowSurface, (255, 255, 0), self.buttonEdgeYellow.pos, 20)
        # pygame.draw.circle(self.windowSurface, (0, 125, 255), self.buttonEdgeBlue.pos, 20)

        # Final rendering
        hv = 0
        if keys[KEY_ADDEDGE] or keys[KEY_EDTEDGE]:
            hv = 1
        elif keys[KEY_REMEDGE] or keys[KEY_REMVERTEX]:
            hv = 2

        shaders.writeToTexture(self.windowSurface)
        shaders.setUniform('mousePos', mousePos)
        shaders.setUniform('hasDepth', self.edgeDepth)
        shaders.setUniform('pulseFactor', self.actionPulseFactor)
        shaders.setUniform('highlightVertices', hv)
        shaders.setUniform('hoveringVertex', closestV)
        shaders.setUniform('selectedVertex', self.selectedV)
        shaders.setUniform('numVertices', len(wireframe.vertices))
        shaders.setUniform('numEdges', len(wireframe.edges))
        shaders.setUniform('screenVertices', screenVertices[:256])
        shaders.setUniform('vertexZs', [v[2] for v in worldVertices[:256]])
        shaders.setUniform('edgeLinks', [tuple(e) for e in wireframe.edgeLinks[:256]])
        shaders.renderTexture()

        self.actionPulseFactor = lerpFloat(self.actionPulseFactor, 1, 0.2)

        # Events (Modification of wireframe can only happen after this point)

        for event in pygame.event.get():

            if event.type == QUIT:
                self.quit()

            # Commands

            if event.type == KEYDOWN and keys[KEY_COMMAND]:
                if event.key == KEY_QUIT:
                    self.quit()
                elif event.key == KEY_TOG_DEPTH:
                    self.edgeDepth = not self.edgeDepth
                elif event.key == KEY_TOG_VIEW:
                    self.perspective = not self.perspective
                elif event.key == KEY_TOG_DEBUG:
                    self.enableDebug = not self.enableDebug
                elif event.key == KEY_RESET and not keys[KEY_GOAL]:
                    self.wireframeStack.append(wireframeFromPreset(self.goalWireframe.preset))
                    self.goalViewSound.play()
                elif event.key == KEY_UNDO and not keys[KEY_GOAL]:
                    if len(self.wireframeStack) > 1:
                        self.undoSound.play()
                        self.wireframeStack.pop(-1)
                elif event.key == KEY_SAVE and not keys[KEY_GOAL]:
                    name = input("Wireframe name: ")
                    writeTextFile("wireframes/custom/" + name + ".txt", jsonpickle.encode(wireframe))
                elif event.key == KEY_OPEN:
                    name = input("Wireframe name: ")
                    f = loadFile("wireframes/custom/" + name + ".txt")
                    if f:
                        self.goalWireframe = jsonpickle.decode(f.read())
                        self.wireframeStack = [wireframeFromPreset(self.goalWireframe.preset)]
                    else:
                        print("No wireframe named " + name)

            # Vertex sounds

            elif not keys[KEY_GOAL] and event.type == KEYDOWN and event.key in [KEY_ADDEDGE, KEY_REMEDGE, KEY_REMVERTEX, KEY_EDTEDGE]:
                self.showVertexSound.play()
            elif not keys[KEY_GOAL] and event.type == KEYUP and event.key in [KEY_ADDEDGE, KEY_REMEDGE, KEY_REMVERTEX, KEY_EDTEDGE]:
                self.hideVertexSound.play()
            elif event.type == KEYDOWN and event.key == KEY_GOAL:
                self.goalViewSound.play()
            elif event.type == KEYUP and event.key == KEY_GOAL:
                self.goalHideSound.play()
            
            # Vertex Selection and Button Presses

            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                if closestV == -1:
                    self.panning = True
                elif (keys[KEY_ADDEDGE] or keys[KEY_REMEDGE] or keys[KEY_EDTEDGE]) and self.selectedV == -1 and closestV != -1 and not keys[KEY_GOAL]:
                    self.selectedV = closestV
                    self.clickVertexSound.play()

                # for button in self.buttons:
                #     if button.checkHover(mousePos):
                #         button.execute()
            
            elif event.type == MOUSEBUTTONUP and event.button == 1 and not keys[KEY_GOAL]:
                if self.panning:
                    self.panning = False
                elif (keys[KEY_ADDEDGE] or keys[KEY_REMEDGE] or keys[KEY_EDTEDGE]):

                    success = False

                    if self.dragSelect:
                        if self.selectedV != -1:
                            if closestV != -1 and closestV != self.selectedV:
                                success = True
                            elif closestV == self.selectedV:
                                self.dragSelect = False
                            else:
                                self.selectedV = -1
                    else:
                        if closestV != -1 and closestV != self.selectedV:
                            success = True
                            self.dragSelect = True
                        else:
                            self.selectedV = -1
                            self.dragSelect = True

                    if success:
                        if keys[KEY_ADDEDGE]:
                            pygame.mixer.Sound.play(self.placeSound)
                            self.actionPulseFactor = self.placePulse
                            wireframe.addEdge(self.selectedV, closestV, self.edgeStyle)
                            self.wireframeStack.append(wireframe)
                            if wireframeEquality(wireframe, self.goalWireframe):
                                self.actionPulseFactor = self.winPulse
                                self.winSound.play()
                        elif keys[KEY_REMEDGE]:
                            pygame.mixer.Sound.play(self.breakSound)
                            wireframe.removeEdge({self.selectedV, closestV})
                            self.wireframeStack.append(wireframe)
                            if wireframeEquality(wireframe, self.goalWireframe):
                                self.actionPulseFactor = self.winPulse
                                self.winSound.play()
                        elif keys[KEY_EDTEDGE]:
                            pygame.mixer.Sound.play(self.placeSound)
                            wireframe.editEdge({self.selectedV, closestV}, self.edgeStyle)
                            self.wireframeStack.append(wireframe)
                        self.selectedV = -1

                elif keys[KEY_REMVERTEX]:
                    if closestV != -1:
                        pygame.mixer.Sound.play(self.breakSound)
                        wireframe.clearVertex(closestV)
                        self.wireframeStack.append(wireframe)
                        self.selectedV = -1
                        if wireframeEquality(wireframe, self.goalWireframe):
                            self.actionPulseFactor = self.winPulse
                            self.winSound.play()

        # Cap undos

        if len(self.wireframeStack) > MAX_UNDOS:
            self.wireframeStack.pop(0)

        # Frame data

        self.previousMousePos = mousePos
        self.previousClosestV = closestV

        if self.enableDebug: pygameDebug(self.windowSurface, (10, 10), "Entire frame time: " + str(round((time.perf_counter() - timer) * 60, 2)))

        pygame.display.flip()

        self.clock.tick(60)