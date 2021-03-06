from Point import dist, Pointf
from Cope import getMidPoint, debugged, invertColor
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import QLine
from PyQt5.QtWidgets import QLabel

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    from OpenGL.GLUT import *
except ImportError:
    app = QApplication(sys.argv)
    QMessageBox.critical(None, "OpenGL hellogl", "PyOpenGL must be installed to run this example.")
    exit(1)

from Cope import DIR, reprise, getTime, timeFunc, clampColor, debug
# import os; DIR = os.path.dirname(__file__) + '/../'

import numpy as np
from typing import Union

@reprise
class Line:
    vboSize = 4
    def __init__(self, vboIndex: int, start, end=None, color: Union[list, tuple]=None, hidden=False):
        self.start = start
        if end == None:
            self.end = start
        else:
            self.end = end

        self.color = color if len(color) == 4 else (*color, 255)
        self.hidden = hidden
        self.index = vboIndex
        self.label = None

    def finish(self, loc, width, height, vbo, colorVbo, lines, color=None):
        if not self.color:
            self.color = color

        self.end = loc

        # vbo.bind()
        # tell OpenGL that the VBO contains an array of vertices
        # glEnableClientState(GL_VERTEX_ARRAY)
        # these vertices contain 2 single precision coordinates
        # glVertexPointer(2, GL_FLOAT, 0, vbo)
        # draw "count" points from the VBO
        # glDrawArrays(GL_POINTS, 0, len(self.dots))
        # glBufferSubData(GL_ARRAY_BUFFER, self.index, self.vboSize * 32, self.data(width, height))
        # vbo.write(self.index, self.data(width, height), self.vboSize)

        # // bind then map the VBO
        # glBindBuffer(GL_ARRAY_BUFFER, vboId)
        # vbo.bind()
        # data = glMapBuffer(GL_ARRAY_BUFFER, GL_WRITE_ONLY)
        # assert data
        # # // if the pointer is valid(mapped), update VBO
        # data.
        # updateMyVBO(ptr, ...)

        # glUnmapBuffer(GL_ARRAY_BUFFER)

        lineData  = ()
        colorData = ()
        for i in lines:
            lineData += i.data(width, height)
            colorData += clampColor(i.color)

        debug(colorData, minItems=10)

        vbo.bind()

        # glEnableClientState(GL_VERTEX_ARRAY)

        #* BufferSubData
        # glBufferSubData(GL_ARRAY_BUFFER, 12, 8 * 32, newData)

        #* MapBuffer
        # data = glMapBuffer(GL_ARRAY_BUFFER, GL_READ_WRITE)
        # debug(pointer(data))
        # debug(data)

        #* BufferData
        glBufferData(GL_ARRAY_BUFFER, np.asarray(lineData + self.data(width, height), np.float32), GL_DYNAMIC_DRAW)

        glDisableClientState(GL_VERTEX_ARRAY)
        vbo.unbind()

        colorVbo.bind()

        # glEnableClientState(GL_COLOR_ARRAY)

        glBufferData(GL_ARRAY_BUFFER, np.asarray(colorData + clampColor(self.color)), GL_DYNAMIC_DRAW)



    def isFinished(self):
        return self.end != None

    def draw(self, width, height):
        """ This must be run from within glBegin/glEnd
        """
        # if self.color is None:
            # assert(not 'No color was specified for a line')

        if not self.hidden:
            # display.setPen(self.color)
            # display.drawLine(self.QLine())
            glColor(*clampColor(self.color))

            # debug(f'drawing a line between {clampPoint(tlOriginToCenterOrigin(self.start, width, height), width, height)} and {clampPoint(tlOriginToCenterOrigin(self.end, width, height), width, height)}')

            # glVertex(*clampPoint(tlOriginToCenterOrigin(self.start, width, height), width, height).dataf())
            # glVertex(*clampPoint(tlOriginToCenterOrigin(self.end,   width, height), width, height).dataf())

            glVertex(*self.start.asGL(width, height).data())
            glVertex(*self.end.asGL(width, height).data())

    def hide(self):
        self.hidden = True

    def show(self):
        self.hidden = False

    # def QLine(self):
    #     return QLine(*self.start.datai(), *self.end.datai())

    def createLabel(self, parent, dotSpread, dotSpreadMeasure, dotSpreadUnit, backgroundColor):
        if self.label is None:
            self.label = QLabel(f'{round(self.getLen(dotSpread, dotSpreadMeasure), 1)} {dotSpreadUnit}', parent)
            self.label.font().setBold(False)
            self.label.font().setFamily('Times')
            # self.label.setStyleSheet(f"color:rgba{invertColor(backgroundColor)}")
            self.label.setStyleSheet(f"color:rgba{self.color}")
            self.label.setGeometry(*self.getLenLoc().asTL().data(), self.label.width(), self.label.height())
        return self.label

    def getDist(self):
        return dist(self.start.asTL(), self.end.asTL())

    def data(self, width, height):
        return self.start.asGL(width, height).data() + self.end.asGL(width, height).data() # + clampColor(self.color)

    def getLen(self, dotSpread, multiplier):
        return (self.getDist() / dotSpread) * multiplier

    def getLenLoc(self):
        return getMidPoint(self.start.asTL(), self.end.asTL())

    def __str__(self):
        return f'Line[{self.start}, {self.end}, color={self.color}]'

    def __eq__(self, a):
        try:
            return self.start == a.start and self.end == a.end
        except:
            return False