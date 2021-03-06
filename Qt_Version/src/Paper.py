# from PIL import Image, ImageDraw, ImageColor
import json
import math
import os
import pickle
import sys
from copy import deepcopy
from os.path import join
from typing import Any, Callable, Iterable, Optional, Union
# from array import array

from OpenGL.arrays.vbo import *
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtCore import QEvent, QFile, QLine, QLineF, QRect, QRectF, Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QFileDialog, QMainWindow, QWidget

from Cope import (DIR, clampColor, debug, debugged, displayAllFiles,
                  displayAllLinks, getTime, invertColor, timeFunc, todo,
                  translate)
from Geometry import *
from Line import Line
from Point import CoordPoint, GLPoint, InfPoint, Pointf, TLPoint, dist

try:
    from OpenGL.GL import *
    # from OpenGL.GLU import *
    # from OpenGL.GLUT import *
    from PyQt5.QtOpenGL import *
    from PyQt5._QOpenGLFunctions_4_1_Core import *
    from PyQt5._QOpenGLFunctions_2_1 import *
    from PyQt5._QOpenGLFunctions_2_0 import *
except ImportError:
    QApplication([])
    crash("PyOpenGL must be installed to run this example.")

def crash(errMsg):
    # QApplication([])
    QMessageBox.critical(None, "GeoDoodle Error", errMsg)
    exit(1)



import numpy as np

from Pattern import Pattern


displayAllFiles(True)


def toQPoint(p):
    return QPoint(p.x, p.y)


#* Cool events worth looking into:
    # QEvent.MouseTrackingChange, QEvent.Move, QEvent.Paint, QEvent.Resize, QEvent.Scroll, QEvent.Show,
    # QEvent.Shortcut, QEvent.ShortcutOverride, QEvent.StyleChange, QEvent.UpdateRequest, QEvent.Wheel,
    # QEvent.DragEnter, QEvent.DragLeave, QEvent.DragMove, QEvent.Drop, QEvent.Enter, QEvent.FileOpen,
    # QEvent.Gesture, QEvent.GrabKeyboard, QEvent.GrabMouse, QEvent.HoverEnter, QEvent.HoverLeave,
    # QEvent.HoverMove, QEvent.Leave, QEvent.MouseButtonDblClick

class Paper(QOpenGLWidget):
#* Static Settings
    # offscreenAmount = 0
    dotSpread = 16
    dotSize = 1
    focusRadius = 0.015
    dragDelay = 7
    exportThickness = 2
    aaSamples = 4

    background = (200, 160, 100, 255)
    # background = '/home/marvin/Media/Pictures/quiched my room meme.png'
    # background = Qt.transparent
    dotColor = (0, 0, 0, 255)
    focusColor = (0, 0, 255, 255)
    boundsColor = (30, 30, 30, 255)
    boundsLineColor = mirrorLineColor = (32, 45, 57, 255)
    # currentLineColor = (150, 44, 44)

    dotSpreadMeasure = 1
    dotSpreadUnit = 'dots'

    includeHalfsies = True
    overlap = (0, 0)

    rowSkip = 1
    rowSkipAmount = 0
    columnSkip = 1
    columnSkipAmount = 0

    flipRow = 1
    flipRowOrientation = 'Vertically'
    flipColumn = 1
    flipColumnOrientation = 'Vertically'


    savePath   = "~/.GeoDoodle/saves/"
    exportPath = "~/.GeoDoodle/images/"
    loadDir    = savePath

    mirroringStates = (0, 1, 2, 4) # 1 is horizontal line only

    # _image = None



#* Init functions
    def __init__(self, parent=None):
        super(Paper, self).__init__(parent)
        # QOpenGLFunctions_4_1_Core.__init__(self)

        # self.reset(width, height)
        self.doReset = True

        # mouseLoc is the 'normal' location of the cursor, focusLoc is the openGL location of the adjusted cursor.
        self.focusLoc = None # GLPoint(self.width, self.height-1, -1)
        self.mouseLoc = None # TLPoint(0, 0)

        self.dragButtons = [False] * 32

        self.lines = []
        self.lineColors = []

        self.setMouseTracking(True)
        self.installEventFilter(self)

        # self.setMinimumSize(100, 100)
        # self.getSize = lambda: (self.window().width(), self.window().height())

        # self.startingPoint = Pointi(self.width / 2, self.height / 2)
        # self.qp = QPainter()

        self.showLen = False

        self.lineVboIndex = 0

        # self.qp.pen().setWidth(1)

        # self.qp.font().setFamily('Times')
        # self.qp.font().setBold(False)
        # self.qp.font().setPointSize(40)

        # self.setStyleSheet("background-color: rgba(0,0,0,0)")
        # self.setWindowFlags(Qt.FramelessWindowHint)
        # self.setAttribute(Qt.WA_NoSystemBackground)
        # self.setAttribute(Qt.WA_TranslucentBackground)
        # self.setAttribute(Qt.WA_TransparentForMouseEvents)


        fmt = QSurfaceFormat()
        fmt.setSamples(self.aaSamples)
        # # fmt.setStereo(True)
        # fmt.setRenderableType(QSurfaceFormat.OpenGLES)
        # # fmt.setAlphaBufferSize(0)
        self.setFormat(fmt)


    def reset(self):
        self.doReset = False

        self.width = self.size().width()
        self.height = self.size().height()

        #* Because I'm reeeeeally lazy
        self.s = self.width, self.height

        self.focusLoc = GLPoint(-1, -1, self.width, self.height)
        self.mouseLoc = TLPoint(0, 0, self.width, self.height)

        # debug(self.geometry(), color=2)

        # Vertex Buffered
        self.dots = genDotArrayPoints((self.width, self.height), self.dotSpread)
                                    #    startPoint=Pointi(-self.width / 2, -self.height / 2))
        self.centerPoint = TLPoint(min(self.dots, key=lambda p: dist(p, Pointf(self.width / 2, self.height / 2))), None, self.width, self.height)

        # TLPoint(self.dots[0], None, self.width, self.height)
        # debug(self.centerPoint)

        # Not Vertex Buffered
        self.metaLines = []
        self.bounds = set()
        self.currentLine = None
        # An ordered list of Lines or tuples of Lines that hold the last lines to be added/removed
        #   Previously deleted and not drawn lines are included in this.
        #   Should have a limiter to stop it from getting too big.
        self.undoBuffer = []

        self.specificEraseBuffer = None

        # self.lineVboIndex = 0

        for line in self.lines:
            if line.label:
                line.label.hide()
                line.label = None

        self.currentDrawColor = (0, 0, 0)

        self.initializeGL()

        # self.resetLineVbo()

        self.update()

        # self.boundsMode = False


    def initializeGL(self):
        # super().initializeGL()
        # glClearColor(*clampColor(*self.backgroundColor), 1)
        # self.initializeOpenGLFunctions()

        # self.context = QOpenGLContext(self)
        # assert self.context.create()
        # assert self.conte ().create() # QOpenGLContext(self)
        # debug(self.context().format())

        # npDots = np.array([np.array(i.start, i.end) for i in self.dots], dtype=np.float32)
        # self.dotCount = npDots.shape[0]
        # create a VBO, data is a Nx2 Numpy array
        # self.dotVbo = VBO(npDots)

        self.adjDots = [TLPoint(i, None, self.width, self.height).asGL().data() for i in genDotArrayPoints((self.width, self.height), self.dotSpread)]
        # debug(self.adjDots)

        self.dotVbo  = VBO(np.asarray(self.adjDots, dtype=np.float32))
        # self.lineVbo = VBO(np.array(self.lines, np.float32), size=16384)

        # s = self.width, self.height
        # self.lines = [Line(0, TLPoint(20, 20, *s), TLPoint(30, 35, *s), (0, 0, 255)),
        #               Line(0, TLPoint(30, 20, *s), TLPoint(30, 55, *s), (0, 255, 0)),
        #               Line(0, TLPoint(80, 50, *s), TLPoint(30, 35, *s), (255, 0, 0))]
        # lineData = ()
        # for i in self.lines:
        #     lineData += i.start.asGL(self.width, self.height).data() + i.end.asGL(self.width, self.height).data()

        self.lineVbo  = VBO(np.asarray([], np.float32))
        self.colorVbo = VBO(np.asarray([], np.float32))
        # GLPoint(-1, -1, *s).data() * 600

        # debug(self.lineVbo.data)

        # self.lineVbo.bind()

        # newData = TLPoint(34, 511, *s).asGL().data() + \
        #           TLPoint(73, 471, *s).asGL().data() + \
        #           TLPoint(769, 513, *s).asGL().data() + \
        #           TLPoint(714, 472, *s).asGL().data()


        # glEnableClientState(GL_VERTEX_ARRAY)

        # #* BufferSubData
        # # glBufferSubData(GL_ARRAY_BUFFER, 12, 8 * 32, newData)

        # #* MapBuffer
        # # data = glMapBuffer(GL_ARRAY_BUFFER, GL_READ_WRITE)
        # # debug(pointer(data))
        # # debug(data)

        # #* BufferData
        # glBufferData(GL_ARRAY_BUFFER, np.asarray(lineData + newData, np.float32), GL_DYNAMIC_DRAW)

        # self.lines.append(Line(0, TLPoint(25, 275, *s), TLPoint(775, 275, *s), (0, 255, 0)))
        # self.lines.append(Line(0, TLPoint(25, 295, *s), TLPoint(775, 295, *s), (0, 255, 0)))

        # debug(self.lineVbo.data)

        # point = None
        # pointer = glGetBufferPointerv(GL_ARRAY_BUFFER, GL_BUFFER_MAP_POINTER, point)

        # debug(pointer)


        # self.lineVbo = None
        # self.lineVbo = QOpenGLBuffer()
        # assert self.lineVbo.create()
        # self.lineVbo.setUsagePattern(QOpenGLBuffer.DynamicDraw)
        # self.lineVbo.allocate(2048 ** 8)

        # self.lineVbo = VBO(np.asarray(self.lines, dtype=np.float32))
        # self.lineColorVbo = VBO(np.asarray(self.lineColors, dtype=np.float32))

        # glShadeModel(GL_SMOOTH)
        # glMatrixMode(GL_PROJECTION)
        # glLoadIdentity()
        # gluPerspective(45, -1.33, 1, 1)
        # glMatrixMode(GL_MODELVIEW)



#* Update Functions
    def updateFocus(self):
        self.focusLoc = GLPoint(min(self.adjDots, key=lambda p:abs(p[0] - self.mouseLoc.asGL().x))[0],
                                min(self.adjDots, key=lambda p:abs(p[1] - self.mouseLoc.asGL().y))[1],
                                self.width, self.height)


    def updateMouse(self, event):
        self.mouseLoc = TLPoint(event.pos(), None, self.width, self.height)
        self.updateFocus()
        if self.currentLine:
            self.currentLine.end = self.focusLoc



#* Event Functions
    def eventFilter(self, target, event):
        #* For some reason, this is the first point after initialization that the width/height are correct
        if self.doReset and self.size().width() != 100 and self.size().height() != 30:
            debug(showFunc=True)
            self.reset()

        if target == self:
            if event.type() in (QEvent.MouseMove, QEvent.DragMove, QEvent.HoverMove):
                self.updateMouse(event)
                self.dragButtons[int(event.buttons())] = True
                self.update()

            if event.type() == QEvent.MouseButtonPress:
                if int(event.buttons()) == Qt.LeftButton:
                    self.createLine()

                elif int(event.buttons()) == Qt.RightButton:
                    self.createLine(True)

                elif int(event.buttons()) == Qt.MiddleButton:
                    self.deleteLine()
                    debug(self.mouseLoc, color=2)

            if event.type() == QEvent.MouseButtonRelease:
                if self.dragButtons[int(event.button())]:
                    self.dragButtons[int(event.button())] = False
                    if event.button() & (Qt.RightButton | Qt.LeftButton):
                        self.createLine(linkAnother=int(event.button()) == Qt.RightButton)

            if event.type() == QEvent.MouseButtonDblClick:
                if int(event.buttons()) == Qt.LeftButton:
                    self.createLine(True)

                elif int(event.buttons()) == Qt.RightButton:
                    self.createLine(True)
        return super().eventFilter(target, event)


    def keyPressed(self, event):
        if   event.key() == Qt.Key_Up or event.key() == Qt.Key_W:
            self.moveY(-1)

        elif event.key() == Qt.Key_Down or event.key() == Qt.Key_S:
            self.moveY(1)

        elif event.key() == Qt.Key_Left or event.key() == Qt.Key_A:
            self.moveX(-1)

        elif event.key() == Qt.Key_Right or event.key() == Qt.Key_D:
            self.moveX(1)

        elif event.key() == Qt.Key_Space:
            self.createLine()
            # self.update()

        elif event.key() == Qt.Key_C:
            self.createLine(True)
            # self.update()

        elif event.key() == Qt.Key_B:
            self.update()

        elif event.key() == Qt.Key_Q:
            self.deleteLine()

        else:
            event.ignore()
            return

        event.accept()


         # if event.key == 264 or event.key == pygame.K_HOME: # numpad up
        #     DOTSPREAD += 1
        #     self.dots = genDotArrayPoints((self.width, self.height), OFFSCREEN_AMOUNT, DOTSPREAD)
        # if event.key == 258 or event.key == pygame.K_END: # numpad down
        #     DOTSPREAD -= 1
            # self.dots = genDotArrayPoints((self.width, self.height), OFFSCREEN_AMOUNT, DOTSPREAD)


    def specificErase(self):
        todo('specificErase')
        # If there's nothing there, don't do anything
        if self.focusLoc in [i.end for i in self.lines] + [i.start for i in self.lines]:
            if self.specificEraseBuffer == None:
                self.specificEraseBuffer = self.focusLoc
            else:
                assert(type(self.specificEraseBuffer) == Pointi)
                for index, i in enumerate(self.lines):
                    if (i.start == self.focusLoc and i.end == self.specificEraseBuffer) or \
                    (i.start == self.specificEraseBuffer and i.end == self.focusLoc):
                        del self.lines[index]
                self.specificEraseBuffer = None
        else:
            self.specificEraseBuffer = None


    def fileDropped(self, event):
        with open(event.file, 'r') as f:
            self.lines = pickle.load(f)


    def moveX(self, dots):
        # I would think you should divide this by self.width instead, but that doesn't seem to work
        self.focusLoc.x += (self.dotSpread / (self.width / 2)) * dots
        if self.currentLine is not None:
            self.currentLine.end = self.focusLoc
            #* If the cursor is inside the window, move the cursor as well,
            #   That way, when you move it again, it goes from where it shows it is
        if self.window().rect().contains(toQPoint(self.focusLoc.asTL()), proper=True):
            self.cursor().setPos(self.mapToGlobal(toQPoint(self.focusLoc.asTL())))
        self.update()


    def moveY(self, dots):
        self.focusLoc.y += (self.dotSpread / (self.height / 2)) * dots
        if self.currentLine is not None:
            self.currentLine.end = self.focusLoc
            #* If the cursor is inside the window, move the cursor as well,
            #   That way, when you move it again, it goes from where it shows it is
        if self.window().rect().contains(toQPoint(self.focusLoc.asTL()), proper=True):
            self.cursor().setPos(self.mapToGlobal(toQPoint(self.focusLoc.asTL())))
        self.update()



#* Draw Functions
    def paintGL(self):
        if self.doReset:# and not (self.size().width() == 100 and self.size().width() == 30):
            debug(showFunc=True)
            self.reset()
        # debug(self.size(), name='paper size', color=3)
        # Reset the background color
        # glClear(GL_COLOR_BUFFER_BIT)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


        # debug(self.lines, showFile=True)

        # debug(self.focusLoc, self.lines, self.dots)
        self.drawBackground()
        self.drawDots()
        self.drawBounds()
        self.drawLines()
        self.drawCurrentLine()
        self.drawFocus()

        # glColor(*clampColor(self.boundsColor))
        # self.drawCircle(self.centerPoint.asGL(), self.focusRadius)

        #* Resets the current matrix
        # glLoadIdentity()
        glFlush()


    def paintEvent(self, event):

        # self.drawBackground()

        for line in self.lines:
            if self.showLen:
                line.createLabel(self, self.dotSpread, self.dotSpreadMeasure, self.dotSpreadUnit, self.background).show()
            elif line.label:
                line.label.hide()

        return super().paintEvent(event)


    def drawBackground(self):
        # self.qp.begin(self)
        # self.qp.setPen(QColor(255, 0, 0, 255))

        # self.qp.drawEllipse(*self.centerPoint.asTL().data(), 6, 6)
        # debug(self.background)
        if type(self.background) is tuple:
            # self.qp.fillRect(0, 0, self.width, self.height, QColor(*self.background))
            # return
            glColor(*clampColor(*self.background))
            glBegin(GL_QUADS)
            glVertex2f(1,1)
            glVertex2f(1,-1)
            glVertex2f(-1,-1)
            glVertex2f(-1,1)
            glEnd()

        elif type(self.background) is str:
            # if not self._image:
            # self._image = QLabel(self)
            # self._image.setPixmap(QPixmap(self.background))
            # self._image.setPixmap(QPixmap(QColor(255, 255, 255, 0)))
            # pixmap = QPixmap(self.background) #, 'Format_ARGB32_Premultiplied')
            image = QImage(self.background).mirrored() #, 'Format_ARGB32_Premultiplied')
            texture = QOpenGLTexture(image)
            texture.bind()
            glDrawArrays(GL_TRIANGLE_FAN, 0, 4)

            # texture.bind()
            # for k, v in kwparams.items():
            # gl.glTexParameteri(gl.GL_TEXTURE_2D, getattr(gl, k), v)
            # texture.release()


            # qp = QPainter(pixmap)
            # qp.fillRect(pixmap.rect(), QColor(0, 0, 0, 150))
            # qp.end()
            # pixmap.transformed(QTransform())
            # self.window()._image.setPixmap(pixmap)

            # else:
            #     self._image.show()


            # self.imageimage = QImage(self.background)

            # QPainter painter(this)
            # self.qp.drawPixmap(0, 0, pixmap)

        elif type(self.background) is QGradient:
            todo('Drawing QGradient')

        elif type(self.background) is QImage:
            self.qp.drawImage(0, 0, self.background)

        # self.qp.end()


    def drawLines(self):
        # glColor(*clampColor(self.dotColor))
        # # Bind the VBO




        # lineData = ()
        # for i in self.lines:
        #     lineData += i.start.asGL(self.width, self.height).data() + i.end.asGL(self.width, self.height).data()
        # # lineData = np.asarray([i.data(self.width, self.height) for i in self.lines])
        # debug(lineData)
        # # self.lineVbo.set_array(lineData)
        # # self.lineVbo.bind()
        # # # tell OpenGL that the VBO contains an array of vertices
        # glEnableClientState(GL_VERTEX_ARRAY)
        # # # these vertices contain 2 single precision coordinates

        # # glVertexPointer(2, GL_FLOAT, 0, self.lineVbo)
        # glVertexPointer(2, GL_FLOAT, 0, np.asarray(lineData, np.float32))
        # # # draw "count" points from the VBO
        # glDrawArrays(GL_LINES, 0, len(self.lines) * 2)

        # glColor(*clampColor(self.dotColor))
        # bind the VBO
        self.lineVbo.bind()
        # self.colorVbo.bind()
        # tell OpenGL that the VBO contains an array of vertices
        glEnableClientState(GL_VERTEX_ARRAY)
        # glEnableClientState(GL_COLOR_ARRAY)
        # these vertices contain 2 single precision coordinates
        glVertexPointer(2, GL_FLOAT, 0, self.lineVbo)
        # glColorPointer(4, GL_FLOAT, 0, self.colorVbo)
        # glVertexPointer(2, GL_FLOAT, 2, self.lineVbo + 2)
        # draw "count" points from the VBO
        glDrawArrays(GL_LINES, 0, len(self.lines)*2)


        # glBegin(GL_LINES)

        # for line in self.lines:
        #     line.draw(self.width, self.height)

        # glEnd()

        # glDrawArrays(GL_LINES, 0, len(self.lines) * 2)


    def drawCurrentLine(self):
        if self.currentLine is not None:
            glBegin(GL_LINES)
            # glColor(*clampColor(self.currentLineColor))
            glColor(*clampColor(self.currentDrawColor))
            glVertex(*self.currentLine.start.asGL().data())
            glVertex(*self.focusLoc.asGL().data())
            glEnd()


    def drawDots(self):
        glColor(*clampColor(self.dotColor))
        # bind the VBO
        self.dotVbo.bind()
        # tell OpenGL that the VBO contains an array of vertices
        glEnableClientState(GL_VERTEX_ARRAY)
        # these vertices contain 2 single precision coordinates
        glVertexPointer(2, GL_FLOAT, 0, self.dotVbo)
        # draw "count" points from the VBO
        glDrawArrays(GL_POINTS, 0, len(self.dots))


    def drawCircle(self, center, radius, filled=False, vertexCount=10):
        #* Create a buffer for vertex data
        # buffer = [] # = new float[vertexCount*2] # (x,y) for each vertex
        # buffer = np.array([0]*vertexCount*2, np.float32)
        glBegin(GL_LINE_LOOP)
        #* Center vertex for triangle fan
        # buffer.append(center.x)
        # buffer.append(center.y)

        #* Outer vertices of the circle
        outerVertexCount = vertexCount-1

        for i in range(outerVertexCount):
            percent = i / (outerVertexCount-1)
            rad = percent * 2 * math.pi

            #* Vertex position
            outer_x = center.x + radius * math.cos(rad)
            outer_y = center.y + radius * math.sin(rad) * 1.5

            glVertex(outer_x, outer_y)

        glEnd()

        #     buffer.append(outer_x)
        #     buffer.append(outer_y)

        # #* Create VBO from buffer with glBufferData()
        # if filled:
        #     glDrawArrays(GL_TRIANGLE_FAN, 0, vertexCount)
        # else:
        #     glDrawArrays(GL_LINE_LOOP, 2, debugged(outerVertexCount))


    def drawFocus(self):
        # self.qp.setPen(QColor(*self.focusColor))
        # self.qp.drawEllipse(*(self.focusLoc-6).datai(), self.focusRadius, self.focusRadius)

        glBegin(GL_LINES)

        glColor(*clampColor(self.focusColor))

        glVertex(self.focusLoc.x - self.focusRadius, self.focusLoc.y             )
        glVertex(self.focusLoc.x + self.focusRadius, self.focusLoc.y             )
        # I'm not sure why this direction is shorter than the other.
        glVertex(self.focusLoc.x,        self.focusLoc.y - self.focusRadius * 1.5)
        glVertex(self.focusLoc.x,        self.focusLoc.y + self.focusRadius * 1.5)

        # for offset in ((-2, -2), (2, 2), (-2, 2), (2, -2)):
        #     self.drawPoint(self.focusLoc + offset)

        glEnd()
         # self.drawCircle(self.focusLoc, self.focusRadius)


    def drawBounds(self):
        # Just for optimization's sake
        if len(self.bounds):
            glColor(*clampColor(self.boundsColor))
            for i in self.bounds:
                self.drawCircle(i, self.focusRadius * .75)

            if len(self.bounds) >= 2:
                glColor(*clampColor(self.boundsLineColor))
                # glBegin(GL_QUADS)
                glBegin(GL_LINE_LOOP)
                bounds = getLargestRect(self.bounds)
                glVertex(*Pointf(bounds.topLeft()).dataf())
                glVertex(*Pointf(bounds.topRight()).dataf())
                glVertex(*Pointf(bounds.bottomRight()).dataf())
                glVertex(*Pointf(bounds.bottomLeft()).dataf())
                glEnd()


    def drawMirroring(self):
        todo('mirroring')
        #* Add mirroring
        for i in self.lineBuffer:
            #* Check if there's already a line there (so it doesn't get bolder (because of anti-aliasing))
            dontDraw = False
            for k in self.lines:
                if i == k or (i.start == k.end and i.end == k.start):
                    dontDraw = True

            #* Check if the start and end are the same (no line would be drawn)
            if i.start != i.end and not dontDraw:
                self.lines.append(i)

            if self.mirroringStates[self.currentMirrorState] in [1, 4]:
                starty = self.startingPoint.y + (self.startingPoint.y - i.start.y) + 2
                endy   = self.startingPoint.y + (self.startingPoint.y - i.end.y) + 2
                vertStart = Pointi(i.start.x, starty)
                vertEnd   = Pointi(i.end.x,   endy)
                self.lines.append(Line(vertStart, vertEnd, i.color))


            if self.mirroringStates[self.currentMirrorState] >= 2:
                # self.startingPoint = Point(min(self.dots, key=lambda i:abs(i.x - (self.width / 2))).x + 1, min(self.dots, key=lambda i:abs(i.y - (self.height / 2))).y + 1)

                startx = self.startingPoint.x + (self.startingPoint.x - i.start.x) + 2
                endx   = self.startingPoint.x + (self.startingPoint.x - i.end.x) + 2
                horStart = Pointi(startx, i.start.y)
                horEnd   = Pointi(endx,   i.end.y)
                self.lines.append(Line(horStart, horEnd, i.color))

                if self.mirroringStates[self.currentMirrorState] >= 4:
                    corStart = Pointi(startx, starty)
                    corEnd   = Pointi(endx,   endy)
                    self.lines.append(Line(corStart, corEnd, i.color))

        self.lineBuffer = []

        #* Add mirrored current line
        if self.currentLine is not None and self.mirroringStates[self.currentMirrorState] in [1, 4]:
            curStarty = self.startingPoint.y + (self.startingPoint.y - self.currentLine.start.y) + 2
            curEndy   = self.startingPoint.y + (self.startingPoint.y - self.currentLine.end.y) + 2
            Line(Pointi(self.currentLine.start.x, curStarty), Pointi(self.currentLine.end.x, curEndy), self.currentLine.color).draw(self.mainSurface)

        if self.currentLine is not None and self.mirroringStates[self.currentMirrorState] >= 2:
            curStartx = self.startingPoint.x + (self.startingPoint.x - self.currentLine.start.x) + 2
            curEndx   = self.startingPoint.x + (self.startingPoint.x - self.currentLine.end.x) + 2
            Line(Pointi(curStartx, self.currentLine.start.y), Pointi(curEndx, self.currentLine.end.y), self.currentLine.color).draw(self.mainSurface)

            if self.currentLine is not None and self.mirroringStates[self.currentMirrorState] >= 4:
                Line(Pointi(curStartx, curStarty), Pointi(curEndx, curEndy), self.currentLine.color).draw(self.mainSurface)


    def resetLineVbo(self):
        lineData = ()
        for i in self.lines:
            lineData += i.data(self.width, self.height)

        self.lineVbo.bind()

        glEnableClientState(GL_VERTEX_ARRAY)

        #* BufferSubData
        # glBufferSubData(GL_ARRAY_BUFFER, 12, 8 * 32, newData)

        #* MapBuffer
        # data = glMapBuffer(GL_ARRAY_BUFFER, GL_READ_WRITE)
        # debug(pointer(data))
        # debug(data)

        #* BufferData
        glBufferData(GL_ARRAY_BUFFER, np.asarray(lineData, np.float32), GL_DYNAMIC_DRAW)


#* File Functions
    def save(self):
        file = self.getFile(True)
        if len(file):
            with open(file, 'wb') as f:
                pickle.dump(self.lines, f)
            print('File Saved!')


    def saveAs(self):
        todo('saveAs')


    def open(self):
        file = self.getFile(False)
        if len(file):
            with open(file, 'rb') as f:
                self.lines = pickle.load(f)


    def export(self):
        image = Image.new('RGB', (self.width, self.height), color=tuple(self.background))
        draw = ImageDraw.Draw(image)
        for line in self.lines:
            draw.line(line.start.data() + line.end.data(), fill=tuple(line.color), width=self.exportLineThickness)

        image.save(self.getFile(True))
        print('File Saved!')


    def new_(self):
        todo('_new')


    def getFile(self, save: bool):
        return QFileDialog.getSaveFileName()[0] if save else QFileDialog.getOpenFileName()[0]



#* Repeat Functions
    def repeatPattern(self, pattern):
        self.lines = pattern.repeat((Sizei(*self.s) / self.dotSpread) + 1,
                                     self.centerPoint,
                                    #  self.dotSpread / (self.height / 2),
                                     self.dotSpread,
                                     #  self.dots[0] % self.dotSpread,
                                     self.overlap,
                                     self.rowSkip,
                                     self.rowSkipAmount,
                                     self.columnSkip,
                                     self.columnSkipAmount,
                                     self.flipRow,
                                     self.flipRowOrientation,
                                     self.flipColumn,
                                     self.flipColumnOrientation,
                                     self.includeHalfsies)

        #* This does help, but not enough to make it worth it, I think
        # debug(self.lines)
        # for i, line in enumerate(self.lines):
        #     for point in (line.start, line.end):
        #         delete = False
        #         if not collidePoint(Pointf(-1, -1), (2, 2), point.asGL(*self.s)):
        #             delete = True
        #     if delete:
        #         del self.lines[i]
        # debug(self.lines)

        self.resetLineVbo()
        self.bounds = set()


    def getLinesWithinRect(self, bounds: QRectF):
        lines = []
        halfLines = []

        # debug(self.lines, color=3, showFile=True)

        for l in self.lines:
            #* You suck
            if bounds.contains(*l.start.asTL(*self.s).data()) and bounds.contains(*l.end.asTL(*self.s).data()):
            # if collidePoint(Pointf(bounds.topLeft()), (bounds.width(), bounds.height()), l.start) and \
            #    collidePoint(Pointf(bounds.topLeft()), (bounds.width(), bounds.height()), l.end):
                lines.append(l)
            elif bounds.contains(*l.start.asTL(*self.s).data()) or bounds.contains(*l.end.asTL(*self.s).data()):
                halfLines.append(l)

        return lines, halfLines


    def getPattern(self):
        if len(self.bounds) < 2:
            raise UserWarning('I\'m sorry Dave, but I can\'t do that.')

        bounds = getLargestRect([b.asTL(*self.s) for b in self.bounds])
        # return debugged(Pattern(self.getLinesWithinRect(bounds), self.getHalfLinesWithinRect(bounds), self.dotSpread / (self.height / 2), bounds))
        return Pattern(*self.getLinesWithinRect(bounds), self.dotSpread, self.centerPoint, bounds)



#* Other Functions
    def createLine(self, linkAnother=False):
        if self.currentLine is None:
            self.currentLine = Line(self.lineVboIndex, deepcopy(self.focusLoc), color=self.currentDrawColor)
            self.lineVboIndex += Line.vboSize
        else:
            if self.currentLine.start == self.focusLoc:
                self.currentLine = None
            else:
                self.currentLine.finish(self.focusLoc.copy(), self.width, self.height, self.lineVbo, self.colorVbo, self.lines)
                self.lines.append(self.currentLine)
                self.currentLine = Line(self.lineVboIndex, deepcopy(self.focusLoc), color=self.currentDrawColor) if linkAnother else None
                self.lineVboIndex += Line.vboSize


    def deleteLine(self, at=None):
        todo('optimize deleteLine with glBufferSubData()')

        if at is None:
            at = self.focusLoc.asGL(*self.s)

        #* If there's a bound there, don't delete all the lines under it as well
        removedBound = False

        # You can't change the size of a set while iterating through it for some reason
        #   Hence, copy().
        for i in self.bounds.copy():
            if i == at:
                self.bounds.remove(i)
                removedBound = True


        if not removedBound:
            #* This should not be nessicarry, I have no idea why the 3 lines don't work by themselves.
            linesStillAtFocus = True
            while linesStillAtFocus:
                linesStillAtFocus = False

                for i in self.lines:
                    if i.start == at or i.end == at:
                        self.lines.remove(i)

                for i in self.lines:
                    if i.start == at or i.end == at:
                        linesStillAtFocus = True

        self.currentLine = None

        self.resetLineVbo()
        self.update()


    def resizeGL(self, width, height):
        """Called upon window resizing: reinitialize the viewport.
        """
        # update the window size
        # self.width, self.height = width, height
        # paint within the whole window
        glViewport(0, 0, width, height)
        # set orthographic projection (2D only)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        # the window corner OpenGL coordinates are (-+1, -+1)
        glOrtho(-1, 1, 1, -1, -1, 1)

        # side = min(width, height)
        # glViewport((width - side) / 2, (height - side) / 2, side, side)


    def mirror(self):
        self.metaLines = []

        self.currentMirrorState += 1
        if self.currentMirrorState >= len(self.mirroringStates):
            self.currentMirrorState = 0

        # print(self.mirroringStates[self.currentMirrorState])

        if self.mirroringStates[self.currentMirrorState] in [1, 4]:
            starth = Pointi(-self.offScreenAmount, self.startingPoint.y)
            endh   = Pointi(self.width + self.offScreenAmount, self.startingPoint.y)
            self.metaLines.append(Line(starth, endh, MIRROR_LINE_COLOR))

        if self.mirroringStates[self.currentMirrorState] >= 2:
            startv = Pointi(self.startingPoint.x, -self.offScreenAmount)
            endv   = Pointi(self.startingPoint.x, self.height + self.offScreenAmount)
            self.metaLines.append(Line(startv, endv, MIRROR_LINE_COLOR))


    def toggleBoundsMode(self):
        # todo('toggleBoundsMode')
        # self.boundsMode = not self.boundsMode
        self.addBound()


    def undo(self):
        todo('undo')
        if self.currentLine == None and len(self.lines) > 0:
            del self.lines[-1]
            if self.mirroringStates[self.currentMirrorState] >= 2 and len(self.lines) > 0:
                self.lines.pop()
                if self.mirroringStates[self.currentMirrorState] >= 4 and len(self.lines) > 0:
                    self.lines.pop()
                    if len(self.lines) > 1:
                        self.lines.pop()
        elif self.currentLine != None:
            self.currentLine = None


    def redo(self):
        todo('redo')


    def clearAll(self):
        self.lines = []
        self.bounds = set()
        self.currentLine = None
        self.metaLines = []


    def addBound(self):
        self.bounds.add(self.focusLoc.copy())
        self.update()


    def updateSettings(self, settings):
        # keyRepeatDelay
        # keyIntervalDealy

        # shortcutBox
        # shortcutSelect
        # setShortcut

        self.dotSpread = settings.dotSpread.value()
        self.dotSpreadMeasure = settings.dotSpreadMeasure.value()
        self.dotSpreadUnit = settings.dotSpreadUnit.text()

        self.background = settings.backgroundColor.getColor()
        self.dotColor = settings.dotColor.getColor()
        self.focusColor = settings.focusColor.getColor()

        self.exportThickness = settings.exportThickness.value()
        self.savePath = settings.savePath.text()
        self.exportPath = settings.exportPath.text()

        self.doReset = True
        # glClearColor(*clampColor(*self.backgroundColor), 1)
        # debug(glGetFloatv(GL_COLOR_CLEAR_VALUE), name='background color', color=2)
        self.update()


    def setCurrentDrawColor(self, color):
        self.currentDrawColor = color


    def setShowLen(self, val):
        self.showLen = val
        self.update()


    def exit(self):
        self.close()
