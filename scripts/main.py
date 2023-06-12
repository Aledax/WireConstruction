import pygame, sys, time
from pygame.locals import *
from _linalg import *
from _pygameplus import *
from wireframe import polyhedra

WINDOW_SIZE = (700, 700)
WINDOW_CENTER = roundV(scaleV(WINDOW_SIZE, 0.5))

WINDOW_SURFACE = pygame.display.set_mode(WINDOW_SIZE)

class App:
    def __init__(self):
        self.clock = pygame.time.Clock()
        self.windowSurface = WINDOW_SURFACE

        self.polyhedronIndex = 0
        self.polyhedron = polyhedra[0]

        # Geometric parameters
        self.keyRotationSpeed = 0.05
        self.mouseRotationSpeed = 0.005
        self.eyePos = (0, 0, -10)
        self.screenZ = -5
        self.zoom = scaleV(WINDOW_SIZE, 0.8)

        # Visual parameters
        self.backgroundColor = (0, 0, 0)
        self.antialias = False
        self.variableBrightness = True
        self.subedgeLength = 0.1
        self.wireframeColor = (125, 255, 255)

        # Mouse input
        self.previousMousePressed = [False, False, False]
        self.previousMousePos = (0, 0)

        # Vertex selection
        self.vertexSelectionRadiusSquared = 400
        self.vertexPositions = []
        self.selectedVertex = -1

        self.loop()

    def loop(self):
        while True:
            timer = time.perf_counter()

            keys = pygame.key.get_pressed()
            mousePressed = pygame.mouse.get_pressed(3)
            mousePos = pygame.mouse.get_pos()

            # Rotation via keys

            if keys[K_LSHIFT]:
                rotationSpeed = self.keyRotationSpeed / 10
            else:
                rotationSpeed = self.keyRotationSpeed

            if keys[K_w]:
                self.polyhedron.rotate((-rotationSpeed, 0, 0))
            if keys[K_s]:
                self.polyhedron.rotate((rotationSpeed, 0, 0))
            if keys[K_a]:
                self.polyhedron.rotate((0, rotationSpeed, 0))
            if keys[K_d]:
                self.polyhedron.rotate((0, -rotationSpeed, 0))
            if keys[K_q]:
                self.polyhedron.rotate((0, 0, -rotationSpeed))
            if keys[K_e]:
                self.polyhedron.rotate((0, 0, rotationSpeed))

            # Rotation via mouse

            if mousePressed[0] and self.previousMousePressed[0]:
                mouseHorizontal = mousePos[0] - self.previousMousePos[0]
                mouseVertical = mousePos[1] - self.previousMousePos[1]
                self.polyhedron.rotate(scaleV((mouseVertical, -mouseHorizontal, 0), self.mouseRotationSpeed))

            # Enabling selection

            if keys[K_LCTRL]:
                closestVertex = -1
                closestDSquared = -1
                for i in range(len(self.polyhedron.absoluteVertices)):
                    dSquared = distanceSquared(self.perspectifyVertex(self.polyhedron.absoluteVertices[i]), mousePos)
                    if closestVertex != -1:
                        if dSquared < closestDSquared:
                            closestVertex = i
                            closestDSquared = dSquared
                    else:
                        if dSquared < self.vertexSelectionRadiusSquared:
                            closestVertex = i
                            closestDSquared = dSquared

            # Events

            for event in pygame.event.get():

                # Exiting, resetting, switching polyhedra, visual preferences

                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    elif event.key == K_LEFT:
                        self.cyclePolyhedron(self.polyhedronIndex - 1)
                    elif event.key == K_RIGHT:
                        self.cyclePolyhedron(self.polyhedronIndex + 1)
                    elif event.key == K_SPACE:
                        self.polyhedron.reset()
                    if keys[K_LALT]:
                        if event.key == K_1:
                            self.antialias = not self.antialias
                        elif event.key == K_2:
                            self.variableBrightness = not self.variableBrightness

                # Selecting vertices

                elif event.type == MOUSEBUTTONDOWN and keys[K_LCTRL]:
                    if closestVertex != -1:
                        if self.selectedVertex != -1:
                            self.polyhedron.toggleEdge(self.selectedVertex, closestVertex)
                            self.selectedVertex = -1
                        else:
                            self.selectedVertex = closestVertex

            # Graphics

            self.windowSurface.fill(self.backgroundColor)
            self.renderWireframe(self.polyhedron)

            # Draw vertices

            for i in range(len(self.polyhedron.absoluteVertices)):
                if i != self.selectedVertex and not keys[K_LCTRL]:
                    continue
                color = (255, 0, 0) if i == self.selectedVertex else (0, 255, 0) if i == closestVertex else (255, 255, 0)
                pygame.draw.circle(self.windowSurface, color, self.perspectifyVertex(self.polyhedron.absoluteVertices[i]), 8)

            self.previousMousePressed = mousePressed
            self.previousMousePos = mousePos

            pygameDebug(self.windowSurface, (10, 90), "Entire frame time: " + str(round((time.perf_counter() - timer) * 60, 2)))

            pygame.display.update()
            self.clock.tick(60)

    def cyclePolyhedron(self, index):
        self.polyhedronIndex = (index + len(polyhedra)) % len(polyhedra)
        self.polyhedron = polyhedra[self.polyhedronIndex]

    def perspectifyVertex(self, v):
        return addV(mulV(addV(self.eyePos[0:2], scaleV(subV(v[0:2], self.eyePos[0:2]), (self.screenZ - self.eyePos[2]) / (v[2] - self.eyePos[2]))), self.zoom), WINDOW_CENTER)
    
    def renderWireframe(self, w):

        # For each subedge:
        # Calculate the absolute subedge's vertex positions.
        # Create a 2D subedge object by pespectifying the absolute subedge.
        # Calculate the tint based on the subedge vertices and include it in the 2D subedge object.
        # Add the 2D subedge to the array.

        timer0 = time.perf_counter()
        timerSum = 0

        newEdges = []

        for e in w.absoluteEdges:

            currentVertex = e[0]
            edgeDirection = normalize(subV(e[1], e[0]))

            while currentVertex != e[1]:
                if magnitude(subV(e[1], currentVertex)) < self.subedgeLength:
                    newVertex = e[1]
                else:
                    newVertex = addV(currentVertex, scaleV(edgeDirection, self.subedgeLength))

                timerSum0 = time.perf_counter()

                v1 = self.perspectifyVertex(currentVertex)
                v2 = self.perspectifyVertex(newVertex)
                b = min(max((0.625 - midpoint(currentVertex, newVertex)[2]), 0) + 0.3, 1) if self.variableBrightness else 1

                timerSum += time.perf_counter() - timerSum0

                newEdges.append({"v1": v1,
                                 "v2": v2,
                                 "brightness": b})

                currentVertex = newVertex
        
        timer1 = time.perf_counter()

        sortedEdges = sorted(newEdges, key=lambda e: e["brightness"])

        timer2 = time.perf_counter()

        for e in sortedEdges:
            if self.antialias:
                pygame.draw.aaline(self.windowSurface, intV(scaleV(self.wireframeColor, e["brightness"])), e["v1"], e["v2"])
            else:
                pygame.draw.line(self.windowSurface, intV(scaleV(self.wireframeColor, e["brightness"])), e["v1"], e["v2"], 4)
        
        timer3 = time.perf_counter()

        pygameDebug(self.windowSurface, (10, 10), "Time to calculate: " + str(round((timer1 - timer0) * 60, 2)))
        pygameDebug(self.windowSurface, (10, 30), "Fraction of calculate: " + str(round(timerSum / (timer1 - timer0), 2)))
        pygameDebug(self.windowSurface, (10, 50), "Time to sort: " + str(round((timer2 - timer1) * 60, 2)))
        pygameDebug(self.windowSurface, (10, 70), "Time to draw: " + str(round((timer3 - timer2) * 60, 2)))

if __name__ == '__main__':
    app = App()