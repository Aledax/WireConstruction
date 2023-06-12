import moderngl, pygame
from pygame.locals import *
from array import array

vert_shader = '''
#version 330 core

in vec2 vert;
in vec2 texcoord;
out vec2 uvs;

void main() {
    uvs = texcoord;
    gl_Position = vec4(vert, 0.0, 1.0);
}
'''

frag_shader = '''
#version 330 core

uniform sampler2D tex;
uniform vec2 scale;
uniform vec3 gradientTop;
uniform vec3 gradientBot;

uniform vec2 mousePos;

uniform int hasDepth;

uniform float pulseFactor;

uniform float edgeBrightness;
uniform float glowBrightness;
uniform float edgeRadius;
uniform float edgeAntiAlias;
uniform float glowRadius;
uniform float depthFactor;
uniform float edgeWhitening;

uniform int highlightVertices;
uniform float vertexHighlightRadius;
uniform int hoveringVertex;
uniform int selectedVertex;

uniform int numVertices;
uniform int numEdges;
uniform vec2 screenVertices[256];
uniform float vertexZs[256];
uniform vec2 edgeLinks[256];

in vec2 uvs;
out vec4 f_color;

// Convert from screen coordiantes to a position on a texture of size (1, 1).
vec2 screenToUV(in vec2 sv) {
    return sv / scale;
}

// Calculate d and z.
float distanceToLineSegment(in vec2 p, in int vIndex, in int wIndex, out float d, out float z) {
    vec2 v = screenToUV(screenVertices[vIndex]);
    vec2 w = screenToUV(screenVertices[wIndex]);

    // Algorithm for the distance from a point to a line segment.
    float l2 = pow(v.x - w.x, 2) + pow(v.y - w.y, 2);
    if (l2 == 0.0) return distance(p, v);
    float t = max(0, min(1, dot(p - v, w - v) / l2));
    vec2 proj = v + t * (w - v);
    d = distance(p, proj);

    // The Z coordinate of the point on the line segment closest to p.
    z = vertexZs[vIndex] + t * (vertexZs[wIndex] - vertexZs[vIndex]);
}

// Calculate b.
void brightness(in float minD, in float worldZ, out float b) {

    // "Frontness" ranges from 1 to 2*depthFactor+1, and represents a brightness multiplier.
    float frontness = (hasDepth == 1) ? (-worldZ + 1) * depthFactor + 1 : 2 * depthFactor + 1;

    // On an edge: The brightness should be high.
    if (minD < edgeRadius) b = edgeBrightness * frontness;

    // On the 'edge' of an edge: The brightness should be half. (For anti-aliasing)
    else if (minD < edgeRadius + edgeAntiAlias) b = (edgeBrightness - (minD - edgeRadius) * (edgeBrightness - glowBrightness) / edgeAntiAlias) * frontness;

    // Near an edge: The brightness should gradually scale down until it reaches 1.
    else if (minD < edgeRadius + edgeAntiAlias + glowRadius) b = (1 - sin(3.14 * 0.5 * (minD - edgeRadius - edgeAntiAlias) / glowRadius)) * glowBrightness * frontness;

    // Not near an edge.
    else b = 1;
}

void main() {

    vec3 baseColor = gradientTop + (gradientBot - gradientTop) * uvs.y;

    float d; // The distance from the pixel to a line segment or vertex.
    float z; // The world Z coordinate of the point on a line segment closest to the pixel.
    float b; // The brightness calculated from d and z.

    vec3 maxColor = texture(tex, uvs).rgb; // The brightest color calculated thus far.
    
    // Brightening based on edge proximity.
    for (int i = 0; i < numEdges; i++) {
    
        // Get the distance from the line segment and the corresponding Z coordinate.
        distanceToLineSegment(uvs, int(edgeLinks[i][0]), int(edgeLinks[i][1]), d, z);

        // Calculate the brightness.
        brightness(d, z, b);

        // Calculate the brightened color due to this edge and raise the max if applicable.
        // Case 1: Not on an edge, just multiply by the brightness.
        if (d >= edgeRadius + edgeAntiAlias) maxColor = max(maxColor, baseColor * b);
        // Case 2: On an edge, add some whitening.
        else maxColor = max(maxColor, (baseColor + edgeWhitening) * b);
    }

    // Brightening based on vertex proximity while editing.
    if (highlightVertices != 0) {
        for (int i = 0; i < numVertices; i++) {
            
            // Get the distance squared to the vertex.
            vec2 v = screenToUV(screenVertices[i]);
            float vd = sqrt(pow(v.x - uvs.x, 2) + pow(v.y - uvs.y, 2));

            // Get vertex radius.
            float r = vertexHighlightRadius - vertexZs[i] * 0.0075;

            // Determine the vertex color.
            vec3 c = (i == selectedVertex) ? vec3(1, 0.25, 1) : (i == hoveringVertex) ? vec3(1, 1, 0.25) : (highlightVertices == 1) ? vec3(0.25, 1, 0.25) : vec3(1, 0.25, 0.25);

            // Generate a brightened color.
            if (vd <= r) maxColor = max(maxColor, (baseColor + c * (1 - pow(vd / r, 16))));
        }
    }

    // Crosshair.
    if (hoveringVertex != -1 && hoveringVertex != selectedVertex && (abs(uvs.x - screenToUV(screenVertices[hoveringVertex]).x) <= 0.001 || abs(uvs.y - screenToUV(screenVertices[hoveringVertex]).y) <= 0.001)) maxColor = max(maxColor, baseColor + 0.4);
        
    // Vingette.
    float cornerDistance = min(min(uvs.x, uvs.y), min(1 - uvs.x, 1 - uvs.y));
    if (cornerDistance < 0.0125 && cornerDistance > 0.01) maxColor = (maxColor + 0.1) * 3;
    else maxColor *= min((cornerDistance + 0.25) * 3, 1);

    // Pulse factor.
    maxColor *= pulseFactor;

    // Mouse.
    float mouseD = distance(screenToUV(mousePos), uvs);
    if ((mouseD > 0.006 && mouseD < 0.0075) || mouseD < 0.002) maxColor = 1 - min(maxColor, 1);

    f_color = vec4(maxColor, 1.0);
}
'''

ctx = None
program = None
render_object = None
tex = None

# Call before the frame loop
def initSurface(size):
    global ctx
    global program
    global render_object
    global tex

    surf = pygame.display.set_mode(size, pygame.OPENGL | pygame.DOUBLEBUF)
    ctx = moderngl.create_context()
    quad_buffer = ctx.buffer(data = array('f', [
        -1.0, 1.0, 0.0, 0.0,
        1.0, 1.0, 1.0, 0.0,
        -1.0, -1.0, 0.0, 1.0,
        1.0, -1.0, 1.0, 1.0
    ]))
    program = ctx.program(vertex_shader=vert_shader, fragment_shader=frag_shader)
    render_object = ctx.vertex_array(program, [(quad_buffer, '2f 2f', 'vert', 'texcoord')])

    tex = ctx.texture(size, 4)
    tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    tex.swizzle = 'BGRA'
    tex.use(0)
    program['tex'] = 0

    return surf

# Call every frame, after the surface is done generating
def writeToTexture(surf):
    tex.write(surf.get_view('1'))

# Call whenever you want a uniform to change (e.g. every frame)
def setUniform(name, value):
    program[name] = value

# Call every frame, after writing the texture and settings its uniforms
def renderTexture():
    render_object.render(mode=moderngl.TRIANGLE_STRIP)

# Call upon exiting the program
def freeTextureMemory():
    tex.release()