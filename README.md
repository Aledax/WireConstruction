# Wire Construction

A unique and challenging puzzle game born from my passion for puzzle games and geometry. I created this purely for fun.

To play the game, make sure you have Python 3, PyGame, and ModernGL installed, and run `main.py` from `0.9\scripts`. Controls are listed at the bottom of this document.

## Overview

The goal of each level is to construct a specific wireframe shape out of a starting wireframe, using only the ability to create and delete edges between existing vertices. What gives these puzzles so much potential is that new vertices can be brought into existence by creating edges that intersect. These new vertices can then be used to make new edges.

The images below show an example of the start and finish of a level, the start being a regular dodecahedron (left) and the finish being a decagonal bipyramid (right):

&nbsp;  

<img src="https://github.com/Aledax/WireConstruction/assets/89650652/7d102db6-2969-4774-8dca-c8c77316b420" width="300" height="300">
<img src="https://github.com/Aledax/WireConstruction/assets/89650652/90a4a217-d168-4bcc-89fa-9da723a326d2" width="300" height="300">

&nbsp;  

It can take a lot of geometric intuition and experimentation to work out how the geometries of the end product relate to the starting shape and how to actually construct the vertices and edges required. During the process of creating levels and experimenting myself, I discovered lots of unexpected patterns and symmetries within the platonic solids (like the dodecahedron) that I could only have easily recognized using an interactive tool such as this.

This makes it not just a game to me, but a tool to explore the beautiful symmetries of shapes I am already passionate about in a way not easily replicable in real life.

## Development Notes

This project was created using PyGame and ModernGL.

Some useful experience I gained in this project:
- Using linear algebra for both rendering and game logic
- Writing GLSL shaders and connecting it to PyGame
- Designing a responsive, intuitive, and visually pleasing UI
- Designing satisfying sound effects with Audacity

## Controls

Basic controls:
- Rotate the wireframe at a constant speed using `WASDQE`. Hold `LShift` for slow rotation. Alternatively, click and drag across the screen to rotate.
- Hold `TAB` to view your end goal.
- Hold `1` to go into 'add edge' mode. Click two vertices, or drag from one vertex to another to create an edge between them.
- Hold `2` to go into 'remove edge' mode. Click two vertices, or drag from one vertex to another to remove the edge between them.
- Hold `4` to go into 'remove vertex' mode. Click a vertex to destroy it and all of its connected edges. NOTE: Unused vertices must be removed in order to 'win' a level.

Commands (hold `LCtrl` and press):
- `d`: Toggle whether edges in the back appear dimmer than the edges in the front
- `v`: Switch between perspective and orthogonal views (orthogonal view can be very useful for recognizing symmetries!)
- `0`: Toggle debug mode, where you can see framerate and vertex IDs
- `r`: Reset the current level
- `z`: Undo (up to 10 times)
- `s`: Save what you currently have as a new level (enter name in command prompt)
- `o`: Open an existing level (enter name in command prompt)
- `q`: Quit the application
