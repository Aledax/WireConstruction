import math


# Classes

class Line:
    def __init__(self, point: tuple, direction: tuple):
        self.point, self.direction = point, direction


# Vector component-wise operations

def addV(v1: tuple, v2: tuple):
    return tuple([v1[i] + v2[i] for i in range(len(v1))])
def subV(v1: tuple, v2: tuple):
    return tuple([v1[i] - v2[i] for i in range(len(v1))])
def mulV(v1: tuple, v2: tuple):
    return tuple([v1[i] * v2[i] for i in range(len(v1))])
def divV(v1: tuple, v2: tuple):
    return tuple([v1[i] / v2[i] for i in range(len(v1))])
def modV(v1: tuple, v2: tuple):
    return tuple([v1[i] % v2[i] for i in range(len(v1))])

def scaleV(v: tuple, s: float):
    return tuple([c * s for c in v])

def intV(v: tuple):
    return tuple([int(c) for c in v])
def floorV(v: tuple):
    return tuple([math.floor(c) for c in v])
def ceilV(v: tuple):
    return tuple([math.ceil(c) for c in v])
def roundV(v: tuple, digits: int = 0):
    if digits == 0: return tuple([int(round(c, digits)) for c in v])
    return tuple([round(c, digits) for c in v])

def lerpV(v: tuple, v_dest: tuple, factor: float):
    return tuple([v[i] + (v_dest[i] - v[i]) * factor for i in range(len(v))])

def vOfConstants(s: float, size: int):
    return tuple([s for i in range(size)])


# Basic linear algebra

def normalize(v: tuple):
    return scaleV(v, 1 / magnitude(v))

def magnitude(v: tuple):
    return math.sqrt(sum([c ** 2 for c in v]))
def magnitudeSquared(v: tuple):
    return sum([c ** 2 for c in v])

def dot(v1: tuple, v2: tuple):
    return sum([v1[i] * v2[i] for i in range(len(v1))])
def cross3(v1: tuple, v2: tuple):
    return (
        v1[1] * v2[2] - v1[2] * v2[1],
        v1[2] * v2[0] - v1[0] * v2[2],
        v1[0] * v2[1] - v1[1] * v2[0]
    )

def vectorProj(v: tuple, v_onto: tuple):
    return scaleV(v, dot(v, v_onto) / magnitude(v_onto) ** 2)
def scalarProj(v: tuple, v_onto: tuple):
    return magnitude(vectorProj(v, v_onto))

def distance(p1: tuple, p2: tuple):
    return magnitude(subV(p1, p2))
def distanceSquared(p1: tuple, p2: tuple):
    return sum([(p1[i] - p2[i]) ** 2 for i in range(len(p1))])


# 0: Not parallel
# 1: Parallel, but in opposite directions
# 2: Parallel, and in the same direction
def testParallel(v1: tuple, v2: tuple, tolerance: float = 0.01):
    print("Parallel test result: ", 1 - abs(dot(normalize(v1), normalize(v2))))
    if 1 - abs(dot(normalize(v1), normalize(v2))) <= tolerance:
        if all(v1[i] * v2[i] >= 0 for i in range(len(v1))):
            return 2
        else:
            return 1
    return 0

# More specific functions

def pointToLineDist(p: tuple, l: Line):
    return math.sqrt(magnitude(subV(p, l.point)) ** 2 - scalarProj(subV(p, l.point), l.direction) ** 2)

def midpoint(p1: tuple, p2: tuple):
    return scaleV(addV(p1, p2), 0.5)


# Functions to do with angles

def angleToVector2(theta: float, magnitude: float = 1):
    return (magnitude * math.cos(theta), magnitude * math.sin(theta))
def vector2ToAngle(v: tuple):
    if v[0] > 0: return (math.atan(v[1] / v[0]) + 2 * math.pi) % (2 * math.pi)
    if v[0] < 0: return math.atan(v[1] / v[0]) + math.pi
    if v[1] > 0: return math.pi / 2
    return 3 * math.pi / 2

def rotateVector2(v: tuple, theta: float):
    return (v[0] * math.cos(theta) - v[1] * math.sin(theta),
            v[0] * math.sin(theta) + v[1] * math.cos(theta))
def rotateVector3Axis(v: tuple, theta: float, axis: int): # Axis should be 0 (x), 1 (y), or 2 (z)
    newV = [None, None, None]
    newV[axis] = v[axis]
    newV[(axis + 1) % 3] = v[(axis + 1) % 3] * math.cos(theta) - v[(axis + 2) % 3] * math.sin(theta)
    newV[(axis + 2) % 3] = v[(axis + 1) % 3] * math.sin(theta) + v[(axis + 2) % 3] * math.cos(theta)
    return newV

def lerpAngle(a: float, a_dest: float, factor: float):
    a = a % (2 * math.pi)
    a_dest = a_dest % (2 * math.pi)
    if a_dest - a <= math.pi or a_dest + (math.pi * 2) - a <= 180:
        return a + (a_dest - a) * factor
    return a - (a - a_dest) * factor

# Other

def lerpFloat(f: float, f_dest: float, factor: float):
    return f + (f - f_dest) * factor