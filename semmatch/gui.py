import os
import sys
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QAction,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QScrollArea,
    QPushButton,
    QFileDialog,
    QCheckBox,
    QSlider,
    QLineEdit,
    QRubberBand,
    QMessageBox,
    QDoubleSpinBox,
    QComboBox,
)
from PyQt5.QtGui import QImage, QPixmap, QKeySequence, QPainter, QBrush, QColor
from semmatch.core import templateMatch
from semmatch.image import npToQImage, qImgToNp, drawCoords


# popup messages
def popup(parent, message):
    messagebox = QMessageBox(parent)
    messagebox.setText(message)
    messagebox.show()


class ImageViewer(QScrollArea):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.zoom = 1
        self.originalImg = QImage()
        self.activeImg = QImage()

        # need QLabel to setPixmap for images
        self.label = QLabel(self)
        self._refresh()
        self.setWidget(self.label)

    def _refresh(self):
        # save slider values to calculate new positions after zoom
        hBar = self.horizontalScrollBar()
        vBar = self.verticalScrollBar()
        try:
            hBarRatio = hBar.value() / hBar.maximum()
            vBarRatio = vBar.value() / vBar.maximum()
        except ZeroDivisionError:
            hBarRatio = 0
            vBarRatio = 0
        # resize
        img = self.activeImg.scaled(
            self.zoom * self.activeImg.size(), aspectRatioMode=Qt.KeepAspectRatio
        )
        self.label.setPixmap(QPixmap(img))
        self.label.resize(img.size())
        self.label.repaint()
        hBar.setValue(int(hBarRatio * hBar.maximum()))
        vBar.setValue(int(vBarRatio * vBar.maximum()))

    def _setActiveImg(self, img):
        self.activeImg = img
        self._refresh()

    def newImg(self, img):
        self.zoom = 1
        self.originalImg = img
        self._setActiveImg(self.originalImg)

    def zoomIn(self):
        self.zoom *= 1.25
        self._refresh()

    def zoomOut(self):
        self.zoom *= 0.8
        self._refresh()


class ImageViewerCrop(ImageViewer):
    class ColorRubberBand(QRubberBand):
        def __init__(self, shape, parent):
            super().__init__(shape, parent)

        def paintEvent(self, event):
            painter = QPainter()
            painter.begin(self)
            painter.fillRect(self.rect(), QBrush(QColor(255, 0, 0, 128)))
            painter.end()

    def __init__(self):
        super().__init__()
        self.image = None
        self.searchedImg = QImage()

    def loadImage(self, image: "ndarray"):
        self.zoom = 1
        self.image = image
        self.originalImg = npToQImage(image)
        self.parentWidget().sidebar._clearPts()

    def mousePressEvent(self, mouseEvent):
        self.shiftPressed = QApplication.keyboardModifiers() == Qt.ShiftModifier
        self.center = mouseEvent.pos()
        self.rband = self.ColorRubberBand(QRubberBand.Rectangle, self)
        self.rband.setGeometry(QRect(self.center, QSize()))
        self.rband.show()

    def mouseMoveEvent(self, mouseEvent):
        # unnormalized QRect can have negative width/height
        crop = QRect(2 * self.center - mouseEvent.pos(), mouseEvent.pos()).normalized()
        if self.shiftPressed:
            largerSide = max(crop.width(), crop.height())
            self.rband.setGeometry(
                self.center.x() - largerSide // 2,
                self.center.y() - largerSide // 2,
                largerSide,
                largerSide,
            )
        else:
            self.rband.setGeometry(crop)
        self.repaint()

    def mouseReleaseEvent(self, mouseEvent):
        self.rband.hide()
        crop = self.rband.geometry()
        if self.originalImg.isNull():  # no image loaded in
            return
        # handle single click initializing default QRect selecting entire image
        if crop.height() < 10 and crop.width() < 10:
            return
        # calculate X and Y position in original image
        X = int((self.horizontalScrollBar().value() + crop.x()) / self.zoom)
        Y = int((self.verticalScrollBar().value() + crop.y()) / self.zoom)
        origScaleCropWidth = int(crop.width() / self.zoom)
        origScaleCropHeight = int(crop.height() / self.zoom)
        # save crop
        cropQImage = self.originalImg.copy(
            QRect(X, Y, origScaleCropWidth, origScaleCropHeight)
        )
        sidebar = self.parentWidget().sidebar
        sidebar.crop_template.newImg(cropQImage)


class Sidebar(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.width = 230
        self.setFixedWidth(self.width)
        self.sldPrec = 3
        self.thresholdVal = 0.8
        self.pixelSizeNm = 10  # nanometers per pixel
        self.groupPoints = True
        self.groupRadius = 7  # µm
        self.lastGroupSize = 0
        self.lastStartLabel = 0

        # widgets
        self.crop_template = ImageViewer()
        self.crop_template.setFixedHeight(200)
        self.cbBlurTemp = QCheckBox("Blur template")
        self.cbBlurImg = QCheckBox("Blur image")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMaximum(10 ** self.sldPrec)
        self.slider.valueChanged.connect(self._setThreshDisp)
        self.threshDisp = QDoubleSpinBox()
        self.threshDisp.setFixedHeight(40)
        self.threshDisp.setMaximum(1)
        self.threshDisp.setSingleStep(0.01)
        self.threshDisp.setDecimals(self.sldPrec)
        self.threshDisp.valueChanged.connect(self._setThreshSlider)
        self.threshDisp.setValue(0.8)
        buttonSearch = QPushButton("Search")
        buttonSearch.clicked.connect(self._templateSearch)
        buttonPrintCoord = QPushButton("Print Number of Coordinates")
        buttonPrintCoord.resize(buttonPrintCoord.sizeHint())
        buttonPrintCoord.clicked.connect(self.printCoordinates)
        buttonClearPts = QPushButton("Clear Points")
        buttonClearPts.clicked.connect(self._clearPts)
        buttonSaveAndQuit = QPushButton("Save and Quit")
        buttonSaveAndQuit.resize(buttonSaveAndQuit.sizeHint())
        buttonSaveAndQuit.clicked.connect(self.saveAndQuit)

        self.cbAcquire = QCheckBox("Acquire")
        self.cbAcquire.setCheckState(Qt.Checked)
        self.cmboxGroupPts = QComboBox()
        self.cmboxGroupPts.addItem("No Groups")
        self.cmboxGroupPts.addItem("Groups within mesh")
        self.cmboxGroupPts.addItem("Entire mesh as one group")
        self.cmboxGroupPts.currentIndexChanged.connect(self._selectGroupOption)
        self.groupRadiusLabel = QLabel("Group Radius")
        self.groupRadiusLineEdit = QLineEdit()
        self.groupRadiusLineEdit.returnPressed.connect(
            lambda: self._setGroupRadius(self.groupRadiusLineEdit.text())
        )
        self._setGroupRadius(str(self.groupRadius))
        self.groupRadiusLabelµm = QLabel("µm")
        self.pixelSizeLabel = QLabel("Pixel Size")
        self.pixelSizeLineEdit = QLineEdit()
        self.pixelSizeLineEdit.returnPressed.connect(
            lambda: self._setPixelSize(self.pixelSizeLineEdit.text())
        )
        self._setPixelSize(str(self.pixelSizeNm))
        self.pixelSizeLabelnm = QLabel("nm")

        # layout
        vlay = QVBoxLayout()
        vlay.addWidget(self.crop_template)
        vlay.addWidget(self.cbBlurTemp)
        vlay.addWidget(self.cbBlurImg)
        vlay.addWidget(QLabel())
        vlay.addWidget(QLabel("Threshold"))
        vlay.addWidget(self.slider)
        vlay.addWidget(self.threshDisp)
        vlay.addWidget(buttonSearch)
        vlay.addWidget(buttonPrintCoord)
        vlay.addWidget(buttonClearPts)
        vlay.addWidget(QLabel())
        vlay.addWidget(buttonSaveAndQuit)
        vlay.addWidget(self.cbAcquire)
        vlay.addWidget(QLabel("Grouping option"))
        vlay.addWidget(self.cmboxGroupPts)
        self.groupInMeshLay = QGridLayout()
        self.groupInMeshLay.addWidget(self.groupRadiusLabel, 1, 0)
        self.groupInMeshLay.addWidget(self.groupRadiusLineEdit, 1, 1)
        self.groupInMeshLay.addWidget(self.groupRadiusLabelµm, 1, 2)
        self.groupInMeshLay.addWidget(self.pixelSizeLabel, 2, 0)
        self.groupInMeshLay.addWidget(self.pixelSizeLineEdit, 2, 1)
        self.groupInMeshLay.addWidget(self.pixelSizeLabelnm, 2, 2)
        vlay.addLayout(self.groupInMeshLay)
        self.cmboxGroupPts.setCurrentIndex(2)  # entire mesh as one group
        vlay.addStretch(1)
        self.setLayout(vlay)

    def _setThreshDisp(self, i: int):
        self.threshDisp.setValue(i / 10 ** self.sldPrec)

    def _setThreshSlider(self, val: float):
        try:
            self.slider.setValue(int(10 ** self.sldPrec * val))
            self.thresholdVal = val
        except ValueError:
            pass

    def _templateSearch(self):
        template = self.crop_template.originalImg
        image = self.parentWidget().viewer.originalImg
        if image.isNull() or template.isNull():
            popup(self, "either image or template missing")
            return

        global pts
        pts = templateMatch(
            qImgToNp(image),
            qImgToNp(template),
            self.thresholdVal,
            blurImage=self.cbBlurImg.isChecked(),
            blurTemplate=self.cbBlurTemp.isChecked(),
        )

        viewer = self.parentWidget().viewer
        viewer.searchedImg = drawCoords(viewer.originalImg, pts)
        viewer._setActiveImg(viewer.searchedImg)
        self.repaint()

    def printCoordinates(self):
        global pts
        print(len(pts))

    def _clearPts(self):
        global pts
        pts = []
        viewer = self.parentWidget().viewer
        viewer._setActiveImg(viewer.originalImg)
        viewer.searchedImg = QImage()
        viewer._refresh()

    def saveAndQuit(self):
        QApplication.quit()

    def _setGroupRadius(self, s: str):
        try:
            self.groupRadius = float("{:.1f}".format(float(s)))
            self.groupRadiusLineEdit.setText(str(self.groupRadius))
        except:
            pass

    def _setPixelSize(self, s: str):
        try:
            self.pixelSizeNm = float("{:.1f}".format(float(s)))
            self.pixelSizeLineEdit.setText(str(self.pixelSizeNm))
        except:
            pass

    def _selectGroupOption(self, i):
        if i == 1:  # groups within mesh
            self.groupRadiusLabel.show()
            self.groupRadiusLineEdit.show()
            self.groupRadiusLabelµm.show()
            self.pixelSizeLabel.show()
            self.pixelSizeLineEdit.show()
            self.pixelSizeLabelnm.show()
        else:
            self.groupRadiusLabel.hide()
            self.groupRadiusLineEdit.hide()
            self.groupRadiusLabelµm.hide()
            self.pixelSizeLabel.hide()
            self.pixelSizeLineEdit.hide()
            self.pixelSizeLabelnm.hide()
        self.repaint()


class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.sidebar = Sidebar()
        self.viewer = ImageViewerCrop()

        grid = QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(self.sidebar, 1, 0, 1, 1)
        grid.addWidget(self.viewer, 1, 1, 5, 5)
        self.setLayout(grid)

    def openImage(self, image):
        self.viewer.loadImage(image)

    def setTemplate(self, template):
        if os.path.isfile(template):
            self.sidebar.crop_template.newImg(QImage(template))
        else:
            popup(self, "template image %s not found" % template)

    def setThreshold(self, threshold):
        self.sidebar.threshDisp.setValue(threshold)

    def setGroupOption(self, option, radius=None, pixelSize=None):
        self.sidebar.cmboxGroupPts.setCurrentIndex(option)
        self.sidebar._selectGroupOption(option)
        if option == 1:
            self.sidebar._setGroupRadius(str(radius))
            self.sidebar._setPixelSize(str(pixelSize))

    def setAcquire(self, acquire):
        self.sidebar.cbAcquire.setCheckState(Qt.Checked if acquire else Qt.Unchecked)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.root = MainWidget()
        self.setCentralWidget(self.root)
        self.statusBar()
        self.initUI()

    def initUI(self):
        menubar = self.menuBar()
        fileMenu = menubar.addMenu("File")
        viewMenu = menubar.addMenu("View")

        zoomIn = QAction("Zoom In", self)
        zoomIn.setShortcut(Qt.Key_Equal)
        zoomIn.triggered.connect(self.root.viewer.zoomIn)
        zoomOut = QAction("Zoom Out", self)
        zoomOut.setShortcut(Qt.Key_Minus)
        zoomOut.triggered.connect(self.root.viewer.zoomOut)
        viewMenu.addAction(zoomIn)
        viewMenu.addAction(zoomOut)

        self.setGeometry(300, 300, 1000, 1000)
        self.show()

    def openImage(self, image):
        self.root.openImage(image)

    def setTemplate(self, template):
        self.root.setTemplate(template)

    def setThreshold(self, threshold):
        self.root.setThreshold(threshold)

    def setGroupOption(self, option, radius=None, pixelSize=None):
        self.root.setGroupOption(option, radius, pixelSize)

    def setAcquire(self, acquire):
        self.root.setAcquire(acquire)


def main(image, template, threshold, options: "NavOptions"):

    global pts
    pts = []

    app = QApplication([])
    w = MainWindow()
    w.openImage(image)

    app.exec_()

    return pts, options
