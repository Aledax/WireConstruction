import os

def resourcePath(path):
    return os.path.join(os.path.dirname(__file__), "..", "resources", path)

def loadFile(path):
    try:
        f = open(resourcePath(path))
        return f
    except:
        return None

def loadFileLines(path):
    f = loadFile(path)
    if f:
        return list(f.read().splitlines())
    return None

def loadFileGrid(path):
    f = loadFile(path)
    if f:
        return [[*s] for s in f.read().splitlines()]
    return None

def newFile(path):
    return open(resourcePath(path), 'a')

def writeTextFile(path, text):
    newFile(path).write(text)