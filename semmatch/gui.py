import os
import sys
import time
from PyQt5.QtCore import Qt, QRect, QSize, QPoint, QSettings
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
    QSpinBox,
    QSizePolicy,
)
from PyQt5.QtGui import QImage, QPixmap, QKeySequence, QPainter, QBrush, QColor
from semmatch.core import NavOptions, templateMatch
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
        hbar = self.horizontalScrollBar()
        vbar = self.verticalScrollBar()

        try:
            hbarRatio = hbar.value() / hbar.maximum()
        except ZeroDivisionError:
            hbarRatio = 0.5
        try:
            vbarRatio = vbar.value() / vbar.maximum()
        except ZeroDivisionError:
            vbarRatio = 0.5

        # resize
        img = self.activeImg.scaled(
            self.zoom * self.activeImg.size(), aspectRatioMode=Qt.KeepAspectRatio
        )
        self.label.setPixmap(QPixmap(img))
        self.label.resize(img.size())
        self.label.repaint()

        hbar.setValue(int(hbarRatio * hbar.maximum()))
        vbar.setValue(int(vbarRatio * vbar.maximum()))

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

        self.zoom = 1
        hsb = self.horizontalScrollBar()
        vsb = self.verticalScrollBar()
        hsb.setValue((hsb.minimum() + hsb.maximum()) // 2)
        vsb.setValue((vsb.minimum() + vsb.maximum()) // 2)
        self._refresh()

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

        # widgets
        self.crop_template = ImageViewer()
        self.crop_template.setFixedHeight(200)
        self.cbBlurTemp = QCheckBox("Blur template")
        self.cbBlurImg = QCheckBox("Blur image")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMaximum(10 ** self.sldPrec)
        self.slider.valueChanged.connect(self._setThreshDisp)
        self.slider.setFixedHeight(25)
        self.threshDisp = QDoubleSpinBox()
        self.threshDisp.setFixedHeight(40)
        self.threshDisp.setMaximum(1)
        self.threshDisp.setSingleStep(0.01)
        self.threshDisp.setDecimals(self.sldPrec)
        self.threshDisp.valueChanged.connect(self._setThreshSlider)
        buttonSearch = QPushButton("Search")
        buttonSearch.clicked.connect(self._templateSearch)
        buttonSearch.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.MinimumExpanding)
        self.searchLay = QGridLayout()
        self.searchLay.addWidget(self.slider, 0, 0, 1, 3)
        self.searchLay.addWidget(self.threshDisp, 1, 0, 1, 2)
        self.searchLay.addWidget(buttonSearch, 1, 2)
        buttonClearPts = QPushButton("Clear Points")
        buttonClearPts.clicked.connect(self._clearPts)

        self.cbAcquire = QCheckBox("Acquire")
        self.cmboxGroupPts = QComboBox()
        self.cmboxGroupPts.addItem("No Groups")
        self.cmboxGroupPts.addItem("Groups by radius")
        self.cmboxGroupPts.addItem("Entire mesh as one group")
        self.cmboxGroupPts.addItem("Number of Groups")
        self.cmboxGroupPts.addItem("Number of Points per Group")
        self.cmboxGroupPts.currentIndexChanged.connect(self._selectGroupOption)
        self.groupRadiusLabel = QLabel("Group Radius")
        self.groupRadiusLineEdit = QLineEdit()
        self.groupRadiusLineEdit.returnPressed.connect(
            lambda: self._setGroupRadius(self.groupRadiusLineEdit.text())
        )
        global navOptions
        if navOptions.groupRadius is not None:
            self._setGroupRadius(str(navOptions.groupRadius))
        self.groupRadiusLabelµm = QLabel("µm")
        self.pixelSizeLabel = QLabel("Pixel Size")
        self.pixelSizeLineEdit = QLineEdit()
        self.pixelSizeLineEdit.returnPressed.connect(
            lambda: self._setPixelSize(self.pixelSizeLineEdit.text())
        )
        if navOptions.pixelSize is not None:
            self._setPixelSize(str(navOptions.pixelSize))
        self.pixelSizeLabelnm = QLabel("nm")

        self.numGroupsLabel = QLabel("Number of groups")
        self.numGroupsSB = QSpinBox()
        self.numGroupsSB.setMinimum(1)
        self.numGroupsSB.setMaximum(20)
        self.numGroupsSB.setValue(navOptions.numGroups)
        self.numGroupsSB.valueChanged.connect(
            lambda: self._setNumGroups(self.numGroupsSB.value())
        )

        self.ptsPerGroupLabel = QLabel("Points per group")
        self.ptsPerGroupSB = QSpinBox()
        self.ptsPerGroupSB.setMinimum(1)
        self.ptsPerGroupSB.setMaximum(20)
        self.ptsPerGroupSB.setValue(navOptions.ptsPerGroup)
        self.ptsPerGroupSB.valueChanged.connect(
            lambda: self._setPtsPerGroup(self.ptsPerGroupSB.value())
        )

        buttonSaveAndQuit = QPushButton("\nSave and Quit\n")
        buttonSaveAndQuit.resize(buttonSaveAndQuit.sizeHint())
        buttonSaveAndQuit.clicked.connect(self.saveAndQuit)

        # layout
        vlay = QVBoxLayout()
        vlay.addWidget(self.crop_template)
        vlay.addWidget(self.cbBlurTemp)
        vlay.addWidget(self.cbBlurImg)
        vlay.addWidget(QLabel())
        vlay.addLayout(self.searchLay)
        vlay.addWidget(buttonClearPts)
        vlay.addWidget(QLabel())
        vlay.addWidget(self.cbAcquire)
        vlay.addWidget(QLabel("Grouping option"))
        vlay.addWidget(self.cmboxGroupPts)
        self.groupByRadiusLay = QGridLayout()
        self.groupByRadiusLay.addWidget(self.groupRadiusLabel, 1, 0)
        self.groupByRadiusLay.addWidget(self.groupRadiusLineEdit, 1, 1)
        self.groupByRadiusLay.addWidget(self.groupRadiusLabelµm, 1, 2)
        self.groupByRadiusLay.addWidget(self.pixelSizeLabel, 2, 0)
        self.groupByRadiusLay.addWidget(self.pixelSizeLineEdit, 2, 1)
        self.groupByRadiusLay.addWidget(self.pixelSizeLabelnm, 2, 2)
        vlay.addLayout(self.groupByRadiusLay)
        self.numGroupsLayout = QGridLayout()
        self.numGroupsLayout.addWidget(self.numGroupsLabel, 1, 0)
        self.numGroupsLayout.addWidget(self.numGroupsSB, 1, 2)
        vlay.addLayout(self.numGroupsLayout)
        self.ptsPerGroupLayout = QGridLayout()
        self.ptsPerGroupLayout.addWidget(self.ptsPerGroupLabel, 1, 0)
        self.ptsPerGroupLayout.addWidget(self.ptsPerGroupSB, 1, 2)
        vlay.addLayout(self.ptsPerGroupLayout)
        vlay.addWidget(QLabel())
        vlay.addWidget(buttonSaveAndQuit)

        self.cmboxGroupPts.setCurrentIndex(navOptions.groupOption)
        self._selectGroupOption(navOptions.groupOption)
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

        self.parentWidget().parentWidget().statusBar().showMessage("searching...")
        startTime = time.time()
        global pts
        pts = templateMatch(
            qImgToNp(image),
            qImgToNp(template),
            self.thresholdVal,
            blurImage=self.cbBlurImg.isChecked(),
            blurTemplate=self.cbBlurTemp.isChecked(),
        )
        endTime = time.time()

        viewer = self.parentWidget().viewer
        viewer.searchedImg = drawCoords(viewer.originalImg, pts)
        viewer._setActiveImg(viewer.searchedImg)

        self.parentWidget().parentWidget().statusBar().showMessage(
            "%d matches found in %.2f sec" % (len(pts), endTime - startTime)
        )

        self.repaint()

    def _clearPts(self):
        global pts
        pts = []
        viewer = self.parentWidget().viewer
        viewer._setActiveImg(viewer.originalImg)
        viewer.searchedImg = QImage()
        viewer._refresh()
        self.parentWidget().parentWidget().statusBar().clearMessage()

    def saveAndQuit(self):
        global navOptions
        navOptions = NavOptions(
            navOptions.groupOption,
            navOptions.groupRadius,
            navOptions.pixelSize,
            navOptions.numGroups,
            navOptions.ptsPerGroup,
            int(self.cbAcquire.isChecked()),
        )
        global pts
        global finalPts
        finalPts = pts
        self.parentWidget().parentWidget().writeSettings()
        QApplication.quit()

    def _setGroupRadius(self, s: str):
        try:
            groupRadius = float("{:.1f}".format(float(s)))
            self.groupRadiusLineEdit.setText(str(groupRadius))
        except Exception as e:
            print("_setGroupRadius exception")
            print(e)
            groupRadius = None

        global navOptions
        navOptions = NavOptions(
            navOptions.groupOption,
            groupRadius,
            navOptions.pixelSize,
            navOptions.numGroups,
            navOptions.ptsPerGroup,
            navOptions.acquire,
        )

    def _setPixelSize(self, s: str):
        try:
            pixelSize = float("{:.1f}".format(float(s)))  # in nm
            self.pixelSizeLineEdit.setText(str(pixelSize))
        except Exception as e:
            print("_setPixelSize exception")
            print(e)
            pixelSize = None

        global navOptions
        navOptions = NavOptions(
            navOptions.groupOption,
            navOptions.groupRadius,
            pixelSize,
            navOptions.numGroups,
            navOptions.ptsPerGroup,
            navOptions.acquire,
        )

    def _setNumGroups(self, numGroups):
        global navOptions
        navOptions = NavOptions(
            navOptions.groupOption,
            navOptions.groupRadius,
            navOptions.pixelSize,
            numGroups,
            navOptions.ptsPerGroup,
            navOptions.acquire,
        )
        self.numGroupsSB.setValue(navOptions.numGroups)

    def _setPtsPerGroup(self, ptsPerGroup):
        global navOptions
        navOptions = NavOptions(
            navOptions.groupOption,
            navOptions.groupRadius,
            navOptions.pixelSize,
            navOptions.numGroups,
            ptsPerGroup,
            navOptions.acquire,
        )
        self.ptsPerGroupSB.setValue(navOptions.ptsPerGroup)

    def _selectGroupOption(self, groupOption):
        global navOptions
        navOptions = NavOptions(
            groupOption,
            navOptions.groupRadius,
            navOptions.pixelSize,
            navOptions.numGroups,
            navOptions.ptsPerGroup,
            navOptions.acquire,
        )
        if groupOption == 1:  # groups by radius
            self.groupRadiusLabel.show()
            self.groupRadiusLineEdit.show()
            self.groupRadiusLabelµm.show()
            self.pixelSizeLabel.show()
            self.pixelSizeLineEdit.show()
            self.pixelSizeLabelnm.show()
            self.numGroupsLabel.hide()
            self.numGroupsSB.hide()
            self.ptsPerGroupLabel.hide()
            self.ptsPerGroupSB.hide()
        elif groupOption == 3:  # numGroups
            self.groupRadiusLabel.hide()
            self.groupRadiusLineEdit.hide()
            self.groupRadiusLabelµm.hide()
            self.pixelSizeLabel.hide()
            self.pixelSizeLineEdit.hide()
            self.pixelSizeLabelnm.hide()
            self.numGroupsLabel.show()
            self.numGroupsSB.show()
            self.ptsPerGroupLabel.hide()
            self.ptsPerGroupSB.hide()
        elif groupOption == 4:  # ptsPerGroup
            self.groupRadiusLabel.hide()
            self.groupRadiusLineEdit.hide()
            self.groupRadiusLabelµm.hide()
            self.pixelSizeLabel.hide()
            self.pixelSizeLineEdit.hide()
            self.pixelSizeLabelnm.hide()
            self.numGroupsLabel.hide()
            self.numGroupsSB.hide()
            self.ptsPerGroupLabel.show()
            self.ptsPerGroupSB.show()
        else:
            self.groupRadiusLabel.hide()
            self.groupRadiusLineEdit.hide()
            self.groupRadiusLabelµm.hide()
            self.pixelSizeLabel.hide()
            self.pixelSizeLineEdit.hide()
            self.pixelSizeLabelnm.hide()
            self.numGroupsLabel.hide()
            self.numGroupsSB.hide()
            self.ptsPerGroupLabel.hide()
            self.ptsPerGroupSB.hide()
        self.repaint()

    def _refreshNavOptions(self):
        global navOptions
        self._setGroupRadius(navOptions.groupRadius)
        self._setPixelSize(navOptions.pixelSize)
        self._setNumGroups(navOptions.numGroups)
        self._setPtsPerGroup(navOptions.ptsPerGroup)
        self._selectGroupOption(navOptions.groupOption)
        self.cmboxGroupPts.setCurrentIndex(navOptions.groupOption)
        self.parentWidget().setAcquire(navOptions.acquire)


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
        self.sidebar.crop_template.newImg(npToQImage(template))

    def setBlurImage(self, blur: bool):
        self.sidebar.cbBlurImg.setChecked(blur)

    def setBlurTemplate(self, blur: bool):
        self.sidebar.cbBlurTemp.setChecked(blur)

    def setAcquire(self, acquire: bool):
        self.sidebar.cbAcquire.setChecked(acquire)

    def setThreshold(self, theshold):
        self.sidebar.threshDisp.setValue(theshold)

    def search(self):
        self.sidebar._templateSearch()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.root = MainWidget()
        self.setCentralWidget(self.root)
        self.statusBar()
        self.initUI()
        self.readSettings()

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

        self.showMaximized()

    def openImage(self, image):
        self.root.openImage(image)

    def setTemplate(self, template):
        self.root.setTemplate(template)

    def setBlurImage(self, blur: bool):
        self.root.setBlurImage(blur)

    def setBlurTemplate(self, blur: bool):
        self.root.setBlurTemplate(blur)

    def setAcquire(self, acquire: bool):
        self.root.setAcquire(acquire)

    def getThreshold(self):
        return self.root.sidebar.thresholdVal

    def setThreshold(self, theshold):
        self.root.setThreshold(theshold)

    def setGroupOption(self, option):
        self.root.sidebar._selectGroupOption(option)
        self.root.sidebar.cmboxGroupPts.setCurrentIndex(option)

    def search(self):
        self.root.search()

    def writeSettings(self):
        settings = QSettings(
            "University of Massachusetts Medical School CryoEM", "semmatch"
        )
        settings.beginGroup("MainWindow")
        settings.setValue("size", self.size())
        settings.setValue("pos", self.pos())
        settings.setValue("threshold", self.getThreshold())
        settings.setValue("blurImage", self.root.sidebar.cbBlurImg.isChecked())
        settings.setValue("blurTemplate", self.root.sidebar.cbBlurTemp.isChecked())
        global navOptions
        settings.setValue("navOptions", navOptions)
        settings.endGroup()

    def readSettings(self):
        settings = QSettings(
            "University of Massachusetts Medical School CryoEM", "semmatch"
        )
        settings.beginGroup("MainWindow")
        self.resize(settings.value("size", QSize(400, 400)))
        self.move(settings.value("pos", QPoint(200, 200)))
        global inputThreshold
        self.setThreshold(float(settings.value("threshold", inputThreshold)))
        global navOptions
        navOptions = settings.value("navOptions", navOptions)
        self.root.sidebar._refreshNavOptions()
        self.setBlurImage(settings.value("blurImage") == "true")
        self.setBlurTemplate(settings.value("blurTemplate") == "true")
        settings.endGroup()


def main(
    image, template, threshold, options: "NavOptions", blurImage=True, blurTemplate=True
):
    global inputThreshold
    inputThreshold = threshold

    global navOptions
    navOptions = options

    global pts
    pts = []

    global finalPts
    finalPts = []

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication([])
    w = MainWindow()
    w.openImage(image)
    if template is not None:
        w.setTemplate(template)
        w.search()

    app.exec_()

    return finalPts, navOptions
