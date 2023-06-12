import pygame, os, math, time
from pygame.locals import *
from pygame import gfxdraw
from _resource import *
from _linalg import *

pygame.mixer.init()

# Loading resources

def loadImage(path: str):
    return pygame.image.load(resourcePath("images/" + path)).convert_alpha()

def loadFont(path: str, size: int):
    return pygame.font.Font(resourcePath("fonts/" + path), size)

def loadSfx(path: str):
    return pygame.mixer.Sound(resourcePath("sounds/sfx/" + path))

def loadMusic(path: str):
    pygame.mixer.music.load(resourcePath("sounds/music/" + path))


# Widgets

def fontSurface(text: str, color: tuple, font: pygame.font.Font, antialias: bool = True):
    return font.render(text, True, color)


# Debug

pygame.font.init()
debugFont = pygame.font.Font(None, 24)

def pygameDebug(surface: pygame.Surface, position: tuple, text: str, color: tuple = (255, 0, 0)):
    label = fontSurface(text, color, debugFont)
    surface.blit(label, position)


# blitPlus

# How to use:
#
# Values is a 4-parameter tuple.
# Parameter 0: X value of the background surface to blit onto
# Parameter 1: Y value of the background surface to blit onto
# Parameter 2: X value of the image surface to blit from
# Parameter 3: Y value of the image surface to blit from
#
# Modes is a 4-parameter tuple. 
# Parameter 0: Mode for translating the background surface X value
# Parameter 1: Mode for translating the background surface Y value
# Parameter 2: Mode for translating the image surface X value
# Parameter 3: Mode for translating the image surface Y value
#
# Each of the modes can be 0, 1, or 2.
# Mode 0: The corresponding value is the distance in pixels from the left/top of the surface.
# Mode 1: The corresponding value is the distance in pixels from the right/bottom of the surface.
# Mode 2: The corresponding value is the percentage across the surfaces width/height span from which to blit.
#
# For example, if you wanted to blit a small box on the bottom right corner of a background with a padding of
# 10 pixels, your modes would be (1, 1, 2, 2), and your values would be (10, 10, 1, 1).
#
# If you wanted to blit an image in the center of a background, your modes would be (2, 2, 2, 2), and your
# values would be (0.5, 0.5, 0.5, 0.5).
#
# Fractional coordinates are rounded.
#
# In the rotated version, all values are still based on the unrotated image's size.

def blitPlus(image: pygame.Surface, background: pygame.Surface, modes: tuple = (0, 0, 0, 0), values: tuple = (0, 0, 0, 0)):
    
    left, top, right, bottom = blitPlusHelper(image, background, modes, values)

    background.blit(image, (round(left - right), round(top - bottom)))

def blitPlusRotate(image: pygame.Surface, background: pygame.Surface, modes: tuple = (0, 0, 0, 0), values: tuple = (0, 0, 0, 0), rotation: float = 0):

    left, top, right, bottom = blitPlusHelper(image, background, modes, values)

    t0 = time.perf_counter()

    rotatedImage = pygame.transform.rotate(image, rotation * 180 / math.pi)

    t1 = time.perf_counter()
    print("Rotozoom took {} seconds.".format(t1 - t0))

    left -= (rotatedImage.get_width() - image.get_width()) / 2
    top -= (rotatedImage.get_height() - image.get_height()) / 2

    t2 = time.perf_counter()
    print("Getting dimensions took {} second.".format(t2 - t1))

    background.blit(rotatedImage, (round(left - right), round(top - bottom)))

    t3 = time.perf_counter()
    print("Blitting took {} seconds.".format(t3 - t2))

def blitPlusHelper(image: pygame.Surface, background: pygame.Surface, modes: tuple = (0, 0, 0, 0), values: tuple = (0, 0, 0, 0)):
    
    left, top, right, bottom = 0, 0, 0, 0

    if modes[0] == 0: left = values[0]
    elif modes[0] == 1: left = background.get_width() - values[0]
    elif modes[0] == 2: left = background.get_width() * values[0]

    if modes[1] == 0: top = values[1]
    elif modes[1] == 1: top = background.get_height() - values[1]
    elif modes[1] == 2: top = background.get_height() * values[1]

    if modes[2] == 0: right = values[2]
    elif modes[2] == 1: right = image.get_width() - values[2]
    elif modes[2] == 2: right = image.get_width() * values[2]

    if modes[3] == 0: bottom = values[3]
    elif modes[3] == 1: bottom = image.get_height() - values[3]
    elif modes[3] == 2: bottom = image.get_height() * values[3]

    return left, top, right, bottom


# Anti-aliased thick lines

# def aaLine(surface, p1, p2, w, color):
#     r = w / 2.0
#     disp = (p2[0] - p1[0], p2[1] - p1[1])
#     vertices = (
#         (p1[0] - disp[1] * r, p1[1] + disp[0] * r),
#         (p1[0] + disp[1] * r, p1[1] - disp[0] * r),
#         (p2[0] + disp[1] * r, p2[1] - disp[0] * r),
#         (p2[0] - disp[1] * r, p2[1] + disp[0] * r)
#     )
#     gfxdraw.aapolygon(surface, vertices, color)
#     gfxdraw.filled_polygon(surface, vertices, color)

def aaLine(surface, p1, p2, r, color):
    if p1 == p2: return
    normal = scaleV(normalize((p1[1] - p2[1], p2[0] - p1[0])), r)
    pygame.draw.aaline(surface, color, addV(p1, normal), addV(p2, normal))
    pygame.draw.aaline(surface, color, subV(p1, normal), subV(p2, normal))
    pygame.draw.line(surface, color, p1, p2, r * 2)
    

# Colors

def colorMultiply(color: tuple, factor: float):
    return tuple([comp * factor for comp in color])

def colorLighten(color: tuple, factor: float):
    return tuple([comp + (255 - comp) * factor for comp in color])


# Widgets

class Button:
    def __init__(self, function, args):
        self.function = function
        self.args = args
    
    def checkHover(self, mousePos):
        return False
    
    def render(self):
        return

    def execute(self):
        self.function(*self.args)

class RectButton(Button):
    def __init__(self, rect, function, args):
        super().__init__(function, args)
        self.rect = rect

    def checkHover(self, mousePos):
        return mousePos[0] >= self.rect[0] and mousePos[1] >= self.rect[1] and mousePos[0] <= self.rect[0] + self.rect[2] and mousePos[1] <= self.rect[1] + self.rect[3]

class CircleButton(Button):
    def __init__(self, x, y, r, function, args):
        super().__init__(function, args)
        self.x, self.y, self.r = x, y, r

    def checkHover(self, mousePos):
        return distanceSquared(mousePos, (self.x, self.y)) <= math.pow(self.r, 2)
    
    @property
    def pos(self):
        return (self.x, self.y)