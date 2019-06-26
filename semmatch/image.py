import io
import cv2
import imageio
import numpy as np
import PIL
import PIL.ImageQt
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QBuffer
import scipy.misc

# Unset PIL max size
PIL.Image.MAX_IMAGE_PIXELS = None


def npToQImage(ndArr):
    pilImageQt = PIL.ImageQt.ImageQt(PIL.Image.fromarray(ndArr))
    return QPixmap.fromImage(pilImageQt).toImage()


def qImgToPilRGBA(qimg):
    buf = QBuffer()
    buf.open(QBuffer.ReadWrite)
    qimg.save(buf, "PNG")
    return PIL.Image.open(io.BytesIO(buf.data().data())).convert("RGBA")


def qImgToNp(qimg):
    return np.array(qImgToPilRGBA(qimg))


def drawCross(img: "ndarray", x, y):
    red = (255, 0, 0, 255)
    thickness = 2
    cv2.line(img, (x - 15, y), (x + 15, y), red, thickness)
    cv2.line(img, (x, y - 15), (x, y + 15), red, thickness)


def drawCrosses(img: "ndarray", coords):
    img = np.flip(img, 0).copy()
    for x, y in coords:
        drawCross(img, x, y)
    return np.flip(img, 0).copy()


def drawCoords(qimg, coords):
    return npToQImage(drawCrosses(qImgToNp(qimg), coords))


class ImageHandler:

    MAX_DIM_BEFORE_DOWNSCALE = 2000

    def __init__(self, filename):
        data = imageio.imread(filename)
        max_dimension = max(data.shape)
        if max_dimension > self.MAX_DIM_BEFORE_DOWNSCALE:
            self.downscale = float(max_dimension / self.MAX_DIM_BEFORE_DOWNSCALE)
            self.downscaled_data = scipy.misc.imresize(data, 1 / self.downscale)
        else:
            self.downscale = 1
            self.downscaled_data = data

    def getData(self):
        return self.downscaled_data

    def toQImage(self):
        return npToQImage(self.downscaled_data)

    def toOrigCoord(self, pt: "(x,y)"):
        """return full scale coordinate"""
        return (int(self.downscale * pt[0]), int(self.downscale * pt[1]))
