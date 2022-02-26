from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QMessageBox, QMainWindow
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QTransform, QScreen
import os  # file management
import json  # json file management
import time  # insert date_str and time in file names
import pyperclip  # copy path to clipboard
import piexif # for picture orientation infos
import sys # for exception handling


def load_settings():
    """ load current settings """
    try:
        # load settings
        with open('settings.json') as f:
            data = json.load(f)
    except:
        print("Error loading the settings", sys.exc_info()[0])
    else:
        return data

SETTINGS = load_settings()

def get_exif_rotation_angle(path):
    """" Reads rotation value from exif and returns rotation value required to display picture correctly """

    img_supported = ['.jpg', '.tif']

    if path.lower()[-4:] in img_supported:
        exif_dict = piexif.load(path)
        if piexif.ImageIFD.Orientation in exif_dict["0th"]:
            orientation = exif_dict["0th"].pop(piexif.ImageIFD.Orientation)
            if orientation == 3:
                return 180
            elif orientation == 6:
                return 90
            elif orientation == 8:
                return -90

    # returns 0 (no rotation) for all other values of if img is not supported
    return 0

class PictureFrame(QtWidgets.QGraphicsView):
    """ Frame displaying a picture or a description and offering zoom/pan/click events """

    def __init__(self, parent):
        super(PictureFrame, self).__init__(parent)
        self._picturePath = None
        self._scene = QtWidgets.QGraphicsScene(self)
        self._photo = QtWidgets.QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        self.setScene(self._scene)
        self._zoom = 0
        self._empty = True
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(*SETTINGS['BKG_COLOR'])))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.installEventFilter(self)
        self.layout = QVBoxLayout()
        self.label = QLabel("Description")
        self.setLayout(self.layout)

    def hasPhoto(self):
        """ Checks if frame contains a photo """
        return not self._empty

    def fitInView(self, scale=True):
        """ Fit current photo in frame"""
        rect = QtCore.QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                # only scale pictures down
                if factor < 1:
                    self.scale(factor, factor)
            self._zoom = 0

    def setPhoto(self, path, settings):
        """ Display photo inside a frame """
        self._zoom = 0
        if path and settings:
            self._picturePath = path
            self._empty = False
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.setGeometry(*settings)
            transform = QTransform().rotate(get_exif_rotation_angle(path))
            pixmap = QPixmap(path).transformed(transform)
            self._photo.setPixmap(pixmap)
        else:
            self._empty = True
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self._photo.setPixmap(QtGui.QPixmap())

    def setDescription(self, settings):
        """ Display description inside a frame """
        if settings:
            self._empty = False
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.setGeometry(*settings[0:4])
            self._scene.addText(settings[-1], QtGui.QFont(SETTINGS['TEXT_FONT'], SETTINGS['TEXT_SIZE'], QtGui.QFont.Light)).setDefaultTextColor(QtGui.QColor.fromRgb(*SETTINGS['TEXT_COLOR']))

    def wheelEvent(self, event):
        """ mouse wheel event to zoom in/out on frame """
        if self.hasPhoto():
            if event.angleDelta().y() > 0:
                factor = 1.25
                self._zoom += 1
            else:
                factor = 0.8
                self._zoom -= 1
            # allow zooming in and out of picture
            if self._zoom > 0 or self._zoom < 0:
                self.scale(factor, factor)
            elif self._zoom == 0:
                self.fitInView()
            # else:
            #     self._zoom = 0

    # overriding drag mode
    def toggleDragMode(self):
        """ toggle pan picture inside frame on and off """
        if self.dragMode() == QtWidgets.QGraphicsView.ScrollHandDrag:
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        elif not self._photo.pixmap().isNull():
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

    def eventFilter(self, obj, event):
        """ capture right mouse click event to fit photo to frame"""
        if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.RightButton:
            self.fitInView()
        return super(PictureFrame, self).eventFilter(obj, event)


class Window(QMainWindow):
    """ Define the main window """

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)
        # create window
        self.setGeometry(0, 0, SETTINGS['COLLAGE_WIDTH'], SETTINGS['COLLAGE_HEIGHT'])
        self.setWindowTitle("Review Pic")
        # hide window bar
        self.setWindowFlag(Qt.FramelessWindowHint)
        # set background color
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: rgb{tuple(SETTINGS['BKG_COLOR'])}")
        self.picture_frames = []    # list of pictures inside the main window
        self.installEventFilter(self)
        self.batch_dir = None
        self._borders = False
        self.export_dir = ''
        self.picture_name = ''

    def populate_window(self, app, pic_dic, export_dir, picture_name):
        """ Populate main window with frames """
        
        self.picture_frames = []
        self.export_dir = export_dir
        self.picture_name = picture_name
        self.app = app

        for path, settings in pic_dic.items():
            if path:
                print(path, settings)
                new_frame = PictureFrame(self)
                if path[-4:].lower() in SETTINGS['PIC_EXTENSION']:
                    new_frame.setPhoto(path, settings)
                elif path == "Description":
                    new_frame.setDescription(settings)
                self.picture_frames.append(new_frame)
                if not self.batch_dir:
                    self.batch_dir = os.path.dirname(path)

    def update_pictures(self):
        """" Fit pictures to frame at startup """
        for picture in self.picture_frames:
            picture.fitInView()

    def save_collage(self):
        """ Take screenshot of the main full screen """
        
        # export directory
        if not self.export_dir:
            self.export_dir = os.path.join(self.batch_dir, "_export")

        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)

        # screenshot title and path
        if not self.picture_name:
            self.picture_name = f"collage_{time.strftime('%Y%m%d_%H%M%S')}"
        save_path = os.path.join(self.export_dir, f"{self.picture_name}.png")
        print(save_path)
        # grab and savescreenshot
        QScreen.grabWindow(self.app.primaryScreen(), QApplication.desktop().winId()).save(save_path, 'png')

        # Messagebox to confirm export and path
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Collage image exported")
        msg.setText(f"Path to image:\n{save_path}\nPath copied to clipboard.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        # add path to clipboard and print result
        pyperclip.copy(save_path)
        print(f"Screenshot saved here:\n{save_path}. Path copied to clipboard. Have a good day :)")

    def toggle_borders(self):
        """ Add borders around frames, settings in settings.json """

        for picture in self.picture_frames:
            if self._borders:
                picture.setStyleSheet("border-width: 0px;")
            else:
                picture.setStyleSheet(f"border-width: {SETTINGS['BORDER_WIDTH']}; border-style: solid; border-color: rgb{tuple(SETTINGS['BORDER_COLOR'])}")

        self._borders = not self._borders

    def eventFilter(self, obj, event):
        """ Capture mouse or keyboard events """
                
        if event.type() == QtCore.QEvent.MouseButtonDblClick:
            self.save_collage()
        # elif event.key() == Qt.Key.Key_S:
        #     self.save_collage()
        elif event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.MiddleButton:
            self.toggle_borders()
        # elif event.type() == QtCore.QEvent.KeyPress and event.button() == QtCore.Qt.Key.Key_B:
        #     self.toggle_borders()
        elif event.type() == QtCore.QEvent.KeyPress:
            print("Image closed")
            self.close()
        return super(Window, self).eventFilter(obj, event)





