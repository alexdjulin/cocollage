from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog
from PyQt5.QtGui import QIcon
from PIL import Image, ImageDraw, ImageFont
from core import *
import sys
from datetime import datetime
from random import randint
import re
import json
from time import sleep
import re

# local paths
data_json_path = 'save.json'
settings_json_path = 'settings.json'


class LiveModeWorker(QObject):
    """" Live Mode worker Class processing collages on a different thread """

    finished = pyqtSignal()
    progress = pyqtSignal(int)
    
    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui

    def run(self):
        ''' Thread function running at start '''

        # The loop will only run in LiveMode and with a valid root folder
        while self.ui.current_mode == 'live_mode' and os.path.isdir(self.ui.root_path_lineEdit.text()):
            
            # get list of available folders in root, ignore starting with '_'
            dir_list = [dir for dir in os.listdir(self.ui.root_path_lineEdit.text()) if not dir.startswith('_')]

            # if new folder available, update folder list and set latest one as active folder
            if len(dir_list) > self.ui.active_folder_comboBox.count():
                
                # find new folder that is not part of the active_folder list
                new_dir = ""
                for dir in dir_list:
                    if self.ui.active_folder_comboBox.findText(dir) == -1:
                        new_dir = dir
                        break
                
                self.ui.update_folders()
                self.ui.active_folder_comboBox.setCurrentText(new_dir)

                # timer to ensure that all pictures have entered
                sleep(3)
                self.progress.emit(f"New folder found: Creating Collage for {new_dir}")
                self.ui.create_collage_image()
            
            # update comboBox in case a folder is deleted
            elif len(dir_list) < self.ui.active_folder_comboBox.count():
                self.ui.update_folders(self)
            
            # timer to wait before checking for a new folder
            sleep(3)
        
        self.finished.emit()

        
class CocoUI(QDialog):
    """ Main UI dialog """

    def __init__(self, app, parent=None):
        super(CocoUI, self).__init__(parent)
        self.app = app
        self.root_path_label = QtWidgets.QLabel(self)
        self.root_path_lineEdit = QtWidgets.QLineEdit(self)
        self.active_folder_label = QtWidgets.QLabel(self)
        self.titel_label = QtWidgets.QLabel(self)
        self.titel_lineEdit = QtWidgets.QLineEdit(self)
        self.subtitle_label = QtWidgets.QLabel(self)
        self.subtitle_lineEdit = QtWidgets.QLineEdit(self)
        self.time_label = QtWidgets.QLabel(self)
        self.time_lineEdit = QtWidgets.QLineEdit(self)
        self.notes_label = QtWidgets.QLabel(self)
        self.notes_lineEdit = QtWidgets.QTextEdit(self)
        self.export_folder_label = QtWidgets.QLabel(self)
        self.export_folder_lineEdit = QtWidgets.QLineEdit(self)                   
        self.export_picture_label = QtWidgets.QLabel(self)
        self.export_picture_lineEdit = QtWidgets.QLineEdit(self)
        self.selected_folders_label = QtWidgets.QLabel(self)
        self.selected_folders_textEdit = QtWidgets.QTextEdit(self)
        self.selected_pictures_label = QtWidgets.QLabel(self)
        self.selected_pictures_textEdit = QtWidgets.QTextEdit(self)
        self.edit_collage_checkBox = QtWidgets.QCheckBox(self)
        self.open_collage_checkBox = QtWidgets.QCheckBox(self)
        self.display_description_checkBox = QtWidgets.QCheckBox(self)
        self.display_logo_checkbox = QtWidgets.QCheckBox(self)
        # BUTTONS
        self.root_browse_button = QtWidgets.QPushButton(self)
        self.update_button = QtWidgets.QPushButton(self)
        self.help_button = QtWidgets.QPushButton(self)
        self.settings_button = QtWidgets.QPushButton(self)
        self.now_button = QtWidgets.QPushButton(self)
        self.save_ui_button = QtWidgets.QPushButton(self)
        self.load_ui_button = QtWidgets.QPushButton(self)
        self.create_button = QtWidgets.QPushButton(self)
        self.mode_button = QtWidgets.QPushButton(self)
        # COMBO BOXES
        self.active_folder_comboBox = QtWidgets.QComboBox(self)
        self.templates_comboBox = QtWidgets.QComboBox(self)
        # PIXMAP IMAGES
        self.template_label = QLabel(self)
        self.template_pixmap = QPixmap()
        self.logo_label = QLabel(self)
        self.logo_pixmap = QPixmap()

        # CLASS variables required to keep track of current state
        self.active_path = str()
        self.processed_folders_list = list()
        self.current_mode = ""
        self.export_folder = ""
        
        self.setup_ui()

    def update_ui_elements(self):
        """ Updating the UI layout based on mode """

        # Default UI color
        bkg_color = 'rgb(50, 50, 50)'   # dark grey
        text_color = 'rgb(255, 255, 255)'
        self.setStyleSheet(f"QDialog {{ background-color: {bkg_color}; color: white;}}")
        
        # Label colors
        self.root_path_label.setStyleSheet(f"QLabel {{ color: {text_color}}}")
        self.active_folder_label.setStyleSheet(f"QLabel {{ color: {text_color}}}")
        self.titel_label.setStyleSheet(f"QLabel {{ color: {text_color}}}")
        self.subtitle_label.setStyleSheet(f"QLabel {{ color: {text_color}}}")
        self.time_label.setStyleSheet(f"QLabel {{ color: {text_color}}}")
        self.notes_label.setStyleSheet(f"QLabel {{ color: {text_color}}}")
        self.export_folder_label.setStyleSheet(f"QLabel {{ color: {text_color}}}")
        self.export_picture_label.setStyleSheet(f"QLabel {{ color: {text_color}}}")
        self.selected_pictures_label.setStyleSheet(f"QLabel {{ color: {text_color}}}")
        self.selected_folders_label.setStyleSheet(f"QLabel {{ color: {text_color}}}")
        self.edit_collage_checkBox.setStyleSheet(f"QCheckBox {{ color: {text_color}}}")
        self.display_logo_checkbox.setStyleSheet(f"QCheckBox {{ color: {text_color}}}")
        self.open_collage_checkBox.setStyleSheet(f"QCheckBox {{ color: {text_color}}}")
        self.display_description_checkBox.setStyleSheet(f"QCheckBox {{ color: {text_color}}}")

        # Update Mode
        folder_color = 'rgb(100, 200, 255)'
        batch_color = 'rgb(159, 255, 140)'
        live_color = 'rgb(255, 106, 106)'

        if self.current_mode == 'folder_mode':
            self.selected_pictures_textEdit.setGeometry(QtCore.QRect(20, 330, 360, 140))
            self.selected_folders_label.setVisible(False)
            self.selected_folders_textEdit.setVisible(False)
            self.mode_button.setStyleSheet(f"QPushButton {{ background-color: {folder_color}}}")
            self.mode_button.setText("Folder\nMode")
            self.edit_collage_checkBox.setEnabled(True)
            self.edit_collage_checkBox.setChecked(True)
            self.open_collage_checkBox.setEnabled(False)
            self.open_collage_checkBox.setChecked(True)
            self.create_button.setEnabled(True)

        elif self.current_mode == 'batch_mode':
            self.selected_pictures_textEdit.setGeometry(QtCore.QRect(20, 330, 170, 140))
            self.selected_folders_label.setVisible(True)
            self.selected_folders_textEdit.setVisible(True)
            self.mode_button.setStyleSheet(f"QPushButton {{ background-color: {batch_color}}}")
            self.mode_button.setText("Batch\nMode")
            self.edit_collage_checkBox.setEnabled(False)
            self.edit_collage_checkBox.setChecked(False)
            self.open_collage_checkBox.setEnabled(True)
            self.create_button.setEnabled(True)

        elif self.current_mode == 'live_mode':
            self.selected_pictures_textEdit.setGeometry(QtCore.QRect(20, 330, 360, 140))
            self.selected_folders_label.setVisible(False)
            self.selected_folders_textEdit.setVisible(False)
            self.mode_button.setStyleSheet(f"QPushButton {{ background-color: {live_color}}}")
            self.mode_button.setText("Live\nMode")
            self.edit_collage_checkBox.setEnabled(False)
            self.edit_collage_checkBox.setChecked(False)
            self.open_collage_checkBox.setEnabled(True)
            self.create_button.setEnabled(False)
        
        self.update_ui_checkboxes()
    

    def update_ui_checkboxes(self):
        """ update checkboxes to grey out the disabled ones """

        text_color = 'rgb(255, 255, 255)'
        text_disabled_color = 'rgb(150, 150, 150)'

        if self.edit_collage_checkBox.isEnabled():
            self.edit_collage_checkBox.setStyleSheet(f"QCheckBox {{ color: {text_color}}}")
        else:
            self.edit_collage_checkBox.setStyleSheet(f"QCheckBox {{ color: {text_disabled_color}}}")

        if self.open_collage_checkBox.isEnabled():
            self.open_collage_checkBox.setStyleSheet(f"QCheckBox {{ color: {text_color}}}")
        else:
            self.open_collage_checkBox.setStyleSheet(f"QCheckBox {{ color: {text_disabled_color}}}")


    def setup_ui(self):

        self.setObjectName("self")
        self.resize(980, 490)

        self.update_ui_elements()

        # ROOT PATH
        self.root_path_label.setGeometry(QtCore.QRect(20, 20, 80, 13))
        self.root_path_lineEdit.setGeometry(QtCore.QRect(120, 20, 225, 20))
        self.root_path_lineEdit.setObjectName("RootPathLineEdit")
        self.root_browse_button.setGeometry(QtCore.QRect(350, 19, 30, 22))
        self.root_browse_button.setObjectName("BrowseButton")

        # ACTIVE FOLDER / LIVE BUTTON
        self.active_folder_label.setGeometry(QtCore.QRect(20, 50, 80, 13))
        self.active_folder_comboBox.setGeometry(QtCore.QRect(120, 50, 225, 20))
        self.update_button.setGeometry(QtCore.QRect(350, 50, 30, 21))
        self.update_button.setObjectName("UpdateButton")

        # TITLE
        self.titel_label.setGeometry(QtCore.QRect(20, 80, 80, 13))
        self.titel_label.setObjectName("TitleLabel")
        self.titel_lineEdit.setGeometry(QtCore.QRect(120, 80, 260, 20))
        self.titel_lineEdit.setObjectName("TitleLineEdit")  

        # SUBTITLE
        self.subtitle_label.setGeometry(QtCore.QRect(20, 110, 80, 13))
        self.subtitle_label.setObjectName("SubtitleLabel")
        self.subtitle_lineEdit.setGeometry(QtCore.QRect(120, 110, 260, 20))
        self.subtitle_lineEdit.setObjectName("SubtitleLineEdit")

        # TIME
        self.time_label.setGeometry(QtCore.QRect(20, 140, 80, 13))
        self.time_label.setObjectName("TimeLabel")
        self.time_lineEdit.setGeometry(QtCore.QRect(120, 140, 225, 20))
        self.time_lineEdit.setObjectName("TimeLineEdit")
        self.now_button.setGeometry(QtCore.QRect(350, 139, 30, 22))
        self.now_button.setObjectName("NowButton")

        # NOTES
        self.notes_label.setGeometry(QtCore.QRect(20, 170, 80, 13))
        self.notes_label.setObjectName("NotesLabel")
        self.notes_lineEdit.setGeometry(QtCore.QRect(120, 170, 260, 50))
        self.notes_lineEdit.setObjectName("NotesTextEdit")
        
        # EXPORT FOLDER AND PICTURE NAME
        self.export_folder_label.setGeometry(QtCore.QRect(20, 240, 100, 17))
        self.export_folder_label.setObjectName("ExportFolderLabel")
        self.export_folder_lineEdit.setGeometry(QtCore.QRect(120, 240, 261, 20))
        self.export_folder_lineEdit.setObjectName("ExportFolderLineEdit")        
        self.export_picture_label.setGeometry(QtCore.QRect(20, 270, 100, 17))
        self.export_picture_label.setObjectName("ExportPictureLabel")
        self.export_picture_lineEdit.setGeometry(QtCore.QRect(120, 270, 261, 20))
        self.export_picture_lineEdit.setObjectName("ExportPictureLineEdit")

        # SELECTED FOLDERS
        self.selected_pictures_label.setGeometry(QtCore.QRect(20, 310, 170, 13))
        self.selected_pictures_label.setObjectName("SelectedPicturesLabel")        
        self.selected_pictures_textEdit.setGeometry(QtCore.QRect(20, 330, 360, 140))
        self.selected_pictures_textEdit.setObjectName("SelectedPicturesTextEdit")    

        # SELECTED PICTURES
        self.selected_folders_label.setGeometry(QtCore.QRect(210, 310, 170, 13))
        self.selected_folders_label.setObjectName("SelectedFoldersLabel")
        self.selected_folders_textEdit.setGeometry(QtCore.QRect(210, 330, 170, 140))
        self.selected_folders_textEdit.setObjectName("SelectedFoldersTextEdit")

        # OPTIONS
        self.edit_collage_checkBox.setGeometry(QtCore.QRect(620, 390, 100, 17))
        self.edit_collage_checkBox.setObjectName("EditCollageCheckBox")
        self.open_collage_checkBox.setGeometry(QtCore.QRect(620, 410, 100, 17))
        self.open_collage_checkBox.setObjectName("OpenCollageCheckBox")
        self.display_description_checkBox.setGeometry(QtCore.QRect(620, 430, 100, 17))
        self.display_description_checkBox.setObjectName("DisplayDescriptionCheckBox")
        self.display_logo_checkbox.setGeometry(QtCore.QRect(620, 450, 100, 17))
        self.display_logo_checkbox.setObjectName("DisplayLogoCheckBox")        
        
        # MODE BUTTON
        self.mode_button.setGeometry(QtCore.QRect(725, 390, 75, 75))
        self.mode_button.setObjectName("ModeButton")

        # HELP / SETTINGS BUTTONS
        self.help_button.setGeometry(QtCore.QRect(805, 390, 35, 35))
        self.help_button.setObjectName("HelpButton")
        self.help_button.setIcon(QIcon('data/help_icon.png'))       
        self.help_button.setIconSize(QtCore.QSize(self.help_button.width(),self.help_button.height())) 
        self.settings_button.setGeometry(QtCore.QRect(845, 390, 35, 35))
        self.settings_button.setObjectName("SettingsButton")
        self.settings_button.setIcon(QIcon('data/settings_icon.png'))       
        self.settings_button.setIconSize(QtCore.QSize(self.settings_button.width(),self.settings_button.height()))

        # SAVE UI / LOAD UI BUTTONS
        self.save_ui_button.setGeometry(QtCore.QRect(805, 430, 35, 35))
        self.save_ui_button.setObjectName("SaveUIButton")     
        self.save_ui_button.setIcon(QIcon('data/save_icon.png'))       
        self.save_ui_button.setIconSize(QtCore.QSize(self.save_ui_button.width(),self.save_ui_button.height()))
        self.load_ui_button.setObjectName("LoadUIButton")
        self.load_ui_button.setGeometry(QtCore.QRect(845, 430, 35, 35))
        self.load_ui_button.setIcon(QIcon('data/load_icon.png'))       
        self.load_ui_button.setIconSize(QtCore.QSize(self.load_ui_button.width(),self.load_ui_button.height()))   

        # CREATE BUTTON
        self.create_button.setGeometry(QtCore.QRect(885, 390, 75, 75))
        self.create_button.setObjectName("CreateButton")
        self.create_button.setIcon(QIcon('data/create_icon.png'))       
        self.create_button.setIconSize(QtCore.QSize(self.create_button.width(),self.create_button.height()))   

        # TEMPLATES
        self.template_folder = os.path.join(sys.path[0], SETTINGS['TEMPLATE_DIR'])
        self.template_files = [t for t in os.listdir(self.template_folder) if t.lower().endswith('.json')]
        self.template_previews = [t for t in os.listdir(self.template_folder) if t.lower().endswith('.png') or t.lower().endswith('.jpg')]
        self.templates_comboBox.setGeometry(QtCore.QRect(420, 330, 540, 25))
        self.template_label.setGeometry(QtCore.QRect(420, 20, 540, 300)) # template picture
        self.init_template()

        # LOGO
        logo_path = os.path.join(sys.path[0], SETTINGS['UI_LOGO'])
        self.logo_label.setGeometry(QtCore.QRect(410, 365, 170, 117))
        self.logo_pixmap.load(logo_path)
        self.logo_pixmap = self.logo_pixmap.scaled(self.logo_label.width(), self.logo_label.height())
        self.logo_label.setPixmap(self.logo_pixmap)

        # TABULATION ORDER
        self.retranslate_ui()
        QtCore.QMetaObject.connectSlotsByName(self)
        CocoUI.setTabOrder(self.titel_lineEdit, self.subtitle_lineEdit)
        CocoUI.setTabOrder(self.subtitle_lineEdit, self.time_lineEdit)
        CocoUI.setTabOrder(self.time_lineEdit, self.notes_lineEdit)
        CocoUI.setTabOrder(self.notes_lineEdit, self.export_folder_lineEdit)
        CocoUI.setTabOrder(self.export_folder_lineEdit, self.export_picture_lineEdit)
        CocoUI.setTabOrder(self.export_picture_lineEdit, self.titel_lineEdit)

        # INIT STATES OF UI ELEMENTS
        self.root_path_lineEdit.setEnabled(False)
        self.update_button.setEnabled(False)
        self.titel_lineEdit.setEnabled(False)
        self.subtitle_lineEdit.setEnabled(False)
        self.now_button.setEnabled(False)
        self.time_lineEdit.setEnabled(False)
        self.notes_lineEdit.setEnabled(False)
        self.export_folder_lineEdit.setEnabled(False)
        self.export_picture_lineEdit.setEnabled(False)
        self.selected_folders_label.setVisible(False)
        self.selected_folders_textEdit.setVisible(False)
        self.selected_pictures_textEdit.setEnabled(False)
        self.edit_collage_checkBox.setEnabled(True)
        self.edit_collage_checkBox.setChecked(True)
        self.open_collage_checkBox.setEnabled(False)
        self.open_collage_checkBox.setChecked(True)
        self.display_description_checkBox.setChecked(True)
        self.display_logo_checkbox.setChecked(True)
        self.mode_button.setEnabled(False)
        self.update_ui_checkboxes()

        # CONNECTIONS
        self.root_browse_button.clicked.connect(self.set_root_path)
        self.update_button.clicked.connect(self.update_folders)
        self.now_button.clicked.connect(self.set_time_now)
        self.save_ui_button.clicked.connect(self.save_ui_data)
        self.load_ui_button.clicked.connect(self.load_ui_data)
        self.create_button.clicked.connect(self.create_image_collage)
        self.mode_button.clicked.connect(self.switch_mode)
        self.edit_collage_checkBox.clicked.connect(self.activate_edit_collage)
        self.templates_comboBox.activated[str].connect(self.update_template)
        self.help_button.clicked.connect(self.open_documentation)
        self.settings_button.clicked.connect(self.open_settings)

        # save current scan settings
        self.store_current_values()

        # show the UI
        self.show()

    
    def retranslate_ui(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("CocoUI", "Cocollage - v1.0"))
        self.root_path_label.setText(_translate("CocoUI", "Root Path"))
        self.root_browse_button.setText(_translate("CocoUI", "..."))
        self.update_button.setText(_translate("CocoUI", "↻"))
        self.active_folder_label.setText(_translate("CocoUI", "Active Folder"))
        self.titel_label.setText(_translate("CocoUI", "Title"))
        self.subtitle_label.setText(_translate("CocoUI", "Subtitle"))
        self.time_label.setText(_translate("CocoUI", "Time"))
        self.now_button.setText(_translate("CocoUI", "Now"))
        self.notes_label.setText(_translate("CocoUI", "Notes"))
        self.export_folder_label.setText(_translate("CocoUI", "Export Folder"))
        self.export_picture_label.setText(_translate("CocoUI", "Picture Name"))
        self.selected_folders_label.setText(_translate("CocoUI", "Batch Folders"))
        self.selected_pictures_label.setText(_translate("CocoUI", "Pictures"))
        self.edit_collage_checkBox.setText(_translate("CocoUI", "Edit Collage"))
        self.open_collage_checkBox.setText(_translate("CocoUI", "Open Collage"))
        self.display_description_checkBox.setText(_translate("CocoUI", "Description"))
        self.display_logo_checkbox.setText(_translate("CocoUI", "Logo"))
        self.help_button.setText(_translate("CocoUI", ""))
        self.settings_button.setText(_translate("CocoUI", ""))
        self.save_ui_button.setText(_translate("CocoUI", ""))
        self.load_ui_button.setText(_translate("CocoUI", ""))
        self.create_button.setText(_translate("CocoUI", ""))
        self.mode_button.setText(_translate("CocoUI", "Folder\nMode"))


    def set_time_now(self):
        """ Set today's date when clicking the Today button """
        time_now = datetime.now().strftime("%d.%m.%Y, %H:%M:%S")
        self.time_lineEdit.setText(time_now)


    def set_root_path(self, root_path = None, update_ui = True):
        """ set path to root folder, browse for it if None """
        
        # if not passed, get root folder from user
        if not root_path:
            # read default folder from settings. Use script folder if empty
            current_dir = os.path.normpath(SETTINGS['DEFAULT_ROOT_FOLDER'])
            if not current_dir:
                current_dir = os.path.dirname(os.path.realpath(__file__))
            root_path = QFileDialog.getExistingDirectory(self, 'Browse to a Root folder containing at least one subfolder', current_dir)
            if not os.path.isdir(root_path):
                self.print_to_log("Root path invalid")
                return

        # load all subfolders which dont start with an underscore
        self.active_folders = [folder for folder in sorted(os.listdir(root_path)) if not folder.startswith('_')]
        
        # check if there is at least one session folder
        if not self.active_folders:
            self.print_to_log("No subfolder found, update root folder")
            return
       
        # empty and list all available subfolders and set first one as default
        self.active_folder_comboBox.clear()
        for session in self.active_folders:
            self.active_folder_comboBox.addItem(session)
        self.active_folder_comboBox.setCurrentIndex(0)

        # update UI if new root path loaded
        if update_ui:
            self.update_button.setEnabled(True)
            self.titel_lineEdit.setEnabled(True)
            self.subtitle_lineEdit.setEnabled(True)
            self.now_button.setEnabled(True)
            self.time_lineEdit.setEnabled(True)
            self.notes_lineEdit.setEnabled(True)
            self.export_folder_lineEdit.setEnabled(True)
            self.export_picture_lineEdit.setEnabled(True)
            self.selected_pictures_textEdit.setEnabled(True)
            self.mode_button.setEnabled(True)
            self.current_mode = 'folder_mode'
            self.update_ui_elements()

        # load contents of the session
        self.root_path_lineEdit.setText(root_path)


    def update_folders(self):
        """ Update folders from root path """
        active_folder = self.active_folder_comboBox.currentText()
        self.set_root_path(root_path = self.root_path_lineEdit.text(), update_ui = False)
        # reset to current folder if still existing
        if self.active_folder_comboBox.findText(active_folder) != -1:
            self.active_folder_comboBox.setCurrentText(active_folder)


    def open_documentation(self):
        """ Opens documentation webpage when clicking the Help button """
        import webbrowser
        webbrowser.open("https://github.com/alexdjulin/cocollage/", new=2)    


    def open_settings(self):
        """ Opens settings.json when clicking the Settings button """
        os.startfile("settings.json")
    

    def init_template(self):
        """ init the templates combo box and set up the default one at startup """

        for template in self.template_files:
            self.templates_comboBox.addItem(f"{template}  |  Images: {int(template.split('_')[1])}  |  Template: {int(template.split('_')[2][:-5])}")
        
        self.current_template = SETTINGS['TEMPLATE_DEFAULT']
        self.templates_comboBox.setCurrentIndex(self.templates_comboBox.findText(self.current_template, QtCore.Qt.MatchStartsWith))

        self.display_template()


    def update_template(self):
        """ update the current template combo box and image """

        # reads template from combobox in form T_XX_XX withoug the json extension
        self.current_template = self.templates_comboBox.currentText().split(' ')[0][:-5]
        self.templates_comboBox.setCurrentIndex(self.templates_comboBox.findText(self.current_template, QtCore.Qt.MatchStartsWith))
        self.display_template()


    def store_current_values(self):
        """ save the current ui state to class variables"""

        self.title = self.titel_lineEdit.text()
        self.subtitle = self.subtitle_lineEdit.text()
        self.time = self.time_lineEdit.text()          
        self.notes = self.notes_lineEdit.toPlainText()          


    def display_template(self):
        """ display an imate of the current template based on the combo box"""

        template_path = os.path.join(self.template_folder, f'{self.current_template}.jpg')

        # if no template preview, create one
        if not os.path.isfile(template_path):
            template_path = self.create_template_preview()

        self.template_pixmap.load(template_path)
        self.template_pixmap = self.template_pixmap.scaled(self.template_label.width(), self.template_label.height())
        self.template_label.setPixmap(self.template_pixmap)


    def create_template_preview(self):
        """ generate a preview of the current template """

        # load template file contents and store information
        with open(f"{os.path.join(SETTINGS['TEMPLATE_DIR'], self.current_template)}.json") as f:
            template_layout = json.load(f)
        template_layout['Description'] = template_layout['Description'][:-1]

        # create empty picture
        template_img_width = SETTINGS['COLLAGE_WIDTH']
        template_img_height = SETTINGS['COLLAGE_HEIGHT']
        template_img = Image.new(mode="RGB", size=(template_img_width, template_img_height), color=tuple(SETTINGS['BKG_COLOR']))

        # draw pictures/description/logo positions
        for key, value in template_layout.items():
            # data missing or not specified
            if not (key and value):
                continue
            
            pic_x, pic_y, pic_w, pic_h = value[0:4]
            grey_value = randint(0, 128)  # get random grey value btw 0 and 128 (dark)
            pic_clr = grey_value, grey_value, grey_value  # convert to RGB
            frame_color = 255, 255, 255
            frame_width = 3

            sub_img = Image.new(mode="RGBA", size=(pic_w, pic_h), color=pic_clr)
            template_img.paste(sub_img, box=(pic_x, pic_y), mask=sub_img)
            # add white frame
            border = ImageDraw.Draw(template_img)
            border.rectangle([pic_x, pic_y, pic_x + pic_w, pic_y + pic_h], fill=None, outline=frame_color, width=frame_width)
            # add pic number
            description = ImageDraw.Draw(template_img)
            description.text((pic_x + 10, pic_y + 10), key, font=ImageFont.truetype(SETTINGS['TEXT_FONT'], 50), fill=tuple(SETTINGS['TEXT_COLOR']))
        
        # draw picture frame
        border = ImageDraw.Draw(template_img)
        border.rectangle([0,0,template_img_width - frame_width, template_img_height - frame_width], fill=None, outline=frame_color, width=frame_width)

        # resize and save picture
        size = self.template_label.width(), self.template_label.height()
        template_img.thumbnail(size, Image.ANTIALIAS)
        template_img_path = f"{os.path.join(SETTINGS['TEMPLATE_DIR'], self.current_template)}.jpg"
        template_img.save(template_img_path)

        return template_img_path


    def load_ui_data(self):
        """ load data from data.json and set corresponding fields"""
        
        try:
            # read file
            with open(data_json_path, 'r') as d:
                DATA = json.load(d)

            # load data
            root_path = DATA['ROOT_PATH'] if 'ROOT_PATH' in DATA.keys() else ''
            active_folder = DATA['ACTIVE_FOLDER'] if 'ACTIVE_FOLDER' in DATA.keys() else ''
            current_mode  = DATA['CURRENT_MODE'] if 'CURRENT_MODE' in DATA.keys() else ''
            title = DATA['TITLE'] if 'TITLE' in DATA.keys() else ''
            subtitle = DATA['SUBTITLE'] if 'SUBTITLE' in DATA.keys() else ''
            Time = DATA['TIME'] if 'TIME' in DATA.keys() else ''
            description = DATA['NOTES'] if 'NOTES' in DATA.keys() else ''
            export_folder = DATA['EXPORT_FOLDER'] if 'EXPORT_FOLDER' in DATA.keys() else ''
            picture_name = DATA['PICTURE_NAME'] if 'PICTURE_NAME' in DATA.keys() else ''
            template = DATA['TEMPLATE'] if 'TEMPLATE' in DATA.keys() else ''
            selected_folders = '\n'.join(DATA['SELECTED_FOLDERS']) if 'SELECTED_FOLDERS' in DATA.keys() else ''
            selected_pictures = '\n'.join(DATA['SELECTED_PICTURES']) if 'SELECTED_PICTURES' in DATA.keys() else ''

            self.set_root_path(root_path)
            self.active_folder_comboBox.setCurrentIndex(self.active_folder_comboBox.findText(active_folder))
            self.titel_lineEdit.setText(title)
            self.subtitle_lineEdit.setText(subtitle)
            self.time_lineEdit.setText(Time)
            self.notes_lineEdit.setText(description) 
            self.export_folder_lineEdit.setText(export_folder)
            self.export_picture_lineEdit.setText(picture_name)
            self.selected_folders_textEdit.setText(selected_folders)
            self.selected_pictures_textEdit.setText(selected_pictures)

            # load template
            if template:
                template_index = self.templates_comboBox.findText(template)
                if template_index != -1:
                    self.templates_comboBox.setCurrentIndex(template_index)
                    self.update_template()
            
            # load options
            if self.edit_collage_checkBox.isEnabled():
                self.edit_collage_checkBox.setChecked(bool(DATA['EDIT_COLLAGE_BOX']))
            if self.open_collage_checkBox.isEnabled():
                self.open_collage_checkBox.setChecked(bool(DATA['OPEN_COLLAGE_BOX']))
            if self.display_description_checkBox.isEnabled():
                self.display_description_checkBox.setChecked(bool(DATA['DESCRIPTION_BOX']))
            if self.display_logo_checkbox.isEnabled():
                self.display_logo_checkbox.setChecked(bool(DATA['LOGO_BOX']))
            
            self.mode_button.setEnabled(True)

            # set current mode
            if current_mode:
                self.current_mode = current_mode
                if current_mode == 'live_mode':
                    self.start_live_mode()

            self.update_ui_elements()

        except:
            self.print_to_log("Error loading the data")

        else:
            self.store_current_values()
            self.print_to_log("Data loaded successfully")


    def save_ui_data(self):
        ''' save current values in data.json to restore them at next startup '''

        try:
            new_settings = dict()

            new_settings['ROOT_PATH'] = self.root_path_lineEdit.text()
            new_settings['ACTIVE_FOLDER'] = self.active_folder_comboBox.currentText()
            new_settings['CURRENT_MODE'] = self.current_mode
            new_settings['TITLE'] = self.titel_lineEdit.text()
            new_settings['SUBTITLE'] = self.subtitle_lineEdit.text()
            new_settings['TIME'] = self.time_lineEdit.text()
            new_settings['NOTES'] = self.notes_lineEdit.toPlainText()
            new_settings['EXPORT_FOLDER'] = self.export_folder_lineEdit.text()
            new_settings['PICTURE_NAME'] = self.export_picture_lineEdit.text()
            new_settings['SELECTED_FOLDERS'] = [os.path.basename(folder) for folder in self.selected_folders_textEdit.toPlainText().replace('file:///', '').split('\n') if folder != '']
            new_settings['SELECTED_PICTURES'] = [os.path.split(pic)[-1] for pic in self.selected_pictures_textEdit.toPlainText().replace('file:///', '').split('\n') if pic != '']
            new_settings['TEMPLATE'] = self.templates_comboBox.currentText()
            new_settings['EDIT_COLLAGE_BOX'] = 1 if self.edit_collage_checkBox.isChecked() else 0
            new_settings['OPEN_COLLAGE_BOX'] = 1 if self.open_collage_checkBox.isChecked() else 0
            new_settings['DESCRIPTION_BOX'] = 1 if self.display_description_checkBox.isChecked() else 0
            new_settings['LOGO_BOX'] = 1 if self.display_logo_checkbox.isChecked() else 0

            with open(data_json_path, 'w') as outfile:
                json.dump(new_settings, outfile, indent=4)
        
        except:
            self.print_to_log("Error saving the contents to data.json", sys.exc_info()[0])
            
        else:
            self.print_to_log("Data saved successfully")


    def activate_edit_collage(self):
        """ Toogle Edit Collage option """

        if self.edit_collage_checkBox.isChecked():
            self.open_collage_checkBox.setChecked(True)
            self.open_collage_checkBox.setEnabled(False)
        else:
            self.open_collage_checkBox.setEnabled(True)
        
        # update ui
        self.update_ui_checkboxes()


    def switch_mode(self):
        """ Switch between Active/Batch/Live Modes """

        if self.current_mode == 'folder_mode':
            self.current_mode = 'batch_mode'
        elif self.current_mode == 'batch_mode':
            self.current_mode = 'live_mode'
            self.start_live_mode()
        else:
            self.current_mode = 'folder_mode'
        
        self.update_ui_elements()

    
    def start_live_mode(self):
        """ start thread handling live mode """

        # Create a QThread object
        self.thread = QThread()

        # Create a LiveModeWorker object
        self.live_mode_worker = LiveModeWorker(self)

        # Move worker to the thread
        self.live_mode_worker.moveToThread(self.thread)

        # Connect signals and slots
        self.thread.started.connect(self.live_mode_worker.run)
        self.live_mode_worker.finished.connect(self.thread.quit)
        self.live_mode_worker.finished.connect(self.live_mode_worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.live_mode_worker.progress.connect(self.lm_thread_reportProgress)

        # Start the thread
        self.thread.start()


    def lm_thread_reportProgress(self, n):
        """ add here any report progress from the liveMode thread """
        pass


    def get_export_folder(self):
        """" returns the path to the export folder, sets up a default one if invalid or missing """

        # read export dir and replace FOLDER keyword
        export_dir = self.export_folder_lineEdit.text().replace('[FOLDER]', self.active_path)

        # specify default one if not passed
        if not export_dir:
            export_dir = os.path.join(self.active_path, '_out')
            self.print_to_log("Export folder not specified. Using _out subfolder")

        # try to create it if it does not exist. If not possible, use windows Picture folder
        if not os.path.isdir(export_dir):
            try:
                os.mkdir(export_dir)
            except:
                self.print_to_log("Export folder not valid or not found. Using [Pictures]")
                export_dir = os.path.join(os.environ['USERPROFILE'], 'Pictures')

        self.export_folder = export_dir
        return os.path.normpath(export_dir)


    def get_picture_name(self):
        """ returns target picture name, sets up a default one if missing """

        # reads picture name
        pic_name = self.export_picture_lineEdit.text()
        
        # sets up default name if not specified
        if not pic_name: 
            pic_name = f'collage_{datetime.now().strftime("%d.%m.%Y, %H:%M:%S")}'
        else:
            pic_name = pic_name.replace('[TITLE]', self.titel_lineEdit.text())
            pic_name = pic_name.replace('[SUBTITLE]', self.subtitle_lineEdit.text())
            pic_name = pic_name.replace('[TIME]', self.time_lineEdit.text())
            pic_name = pic_name.replace('[NOTES]', self.notes_lineEdit.toPlainText())
        
        # make picture name valid
        pic_name = re.sub('[^\w_.)( -]', '_', pic_name)

        # make sure picture is unique
        if os.path.isfile(os.path.join(self.export_folder, f'{pic_name}.png')):
            pic_name = f'{pic_name}_{datetime.now().strftime("%d.%m.%Y, %H:%M:%S")}'
        
        return pic_name
    

    def get_options(self):
        """ returns the different options """

        # get Edit Mode option if enabled
        edit_mode = self.edit_collage_checkBox.isChecked() if self.edit_collage_checkBox.isEnabled() else False
        # get Open Collage option
        open_collage = self.open_collage_checkBox.isChecked() if self.open_collage_checkBox.isEnabled() else False
        # get Add Description option
        add_description = self.display_description_checkBox.isChecked() if self.display_description_checkBox.isEnabled() else False
        # get Add Logo option
        add_logo = self.display_logo_checkbox.isChecked() if self.display_logo_checkbox.isEnabled() else False

        return edit_mode, open_collage, add_description, add_logo
    

    def get_pictures_list(self):
        """ return pictures list, full path if no folder is found """

        pictures_list = []
        pictures_path = []
        active_path = os.path.join(self.root_path_lineEdit.text(), self.active_folder_comboBox.currentText())
        
        # get specified pictures or all pictures from active path
        if self.selected_pictures_textEdit.toPlainText():
            pictures_list = [os.path.split(pic)[-1] for pic in self.selected_pictures_textEdit.toPlainText().splitlines() if pic]
        else:
            pictures_list = [os.path.split(pic)[-1] for pic in os.listdir(active_path) if pic.lower()[-4:] in SETTINGS['PIC_EXTENSION']]

        # make list of valid pictures path
        for picture in pictures_list:
            picture_path = os.path.normpath(os.path.join(active_path, picture))
            if os.path.isfile(picture_path):
                pictures_path.append(picture_path)
            else:
                self.print_to_log(f"{picture} not valid > Removed from list.")

        return pictures_path


    def create_image_collage(self):
        ''' generates collage when we click on Create '''
        
        processed_folders = []
        
        # To create a collage we need at least to specify a valid root and active folders
        if not os.path.isdir(self.root_path_lineEdit.text()) and not self.active_folder_comboBox.currentText():
            self.print_to_log("Error. Please specify a root path containing subfolders with pictures")
            return

        # BATCH FOLDERS MODE
        if self.current_mode == 'batch_mode' and self.selected_folders_textEdit.toPlainText():

            updated_field = str()

            # retrieve all batches from the field
            folders_list = [os.path.basename(folder) for folder in self.selected_folders_textEdit.toPlainText().splitlines() if folder]
            
            # if folder path is valid, store path to process
            for folder in folders_list:
                folder_path = os.path.normpath(os.path.join(self.root_path_lineEdit.text(), folder))
                if os.path.isdir(folder_path):
                    processed_folders.append(folder_path)
                    updated_field += f"{folder}\n"
                # if invalid, skip batch
                else:
                    self.print_to_log(f"ERROR: {folder} not a valid folder > Removed from list.")

            # update Selected Folders field
            self.selected_folders_textEdit.setText(updated_field)

        # ACTIVE / LIVE MODES
        else:
            
            active_folder = os.path.normpath(os.path.join(self.root_path_lineEdit.text(), self.active_folder_comboBox.currentText()))
            if os.path.isdir(active_folder):
                processed_folders.append(active_folder)
        
        # ALL MODSES / Process folder(s)
        for folder in processed_folders:

            self.active_path = folder
            active_folder = os.path.basename(folder)
            self.active_folder_comboBox.setCurrentIndex(self.active_folder_comboBox.findText(active_folder))

            # get pictures for current batch
            processed_pictures = self.get_pictures_list()
            if not processed_pictures:
                self.print_to_log(f"Pictures not found for batch {active_folder}")
                continue

            # collects fields content, replace keywords if any
            time_now =  datetime.now().strftime("%d.%m.%Y, %H:%M:%S")
            title = self.titel_lineEdit.text().replace('[PATH]', folder).replace('[FOLDER]', active_folder).replace('[NOW]', time_now)
            subtitle = self.subtitle_lineEdit.text().replace('[PATH]', folder).replace('[FOLDER]', active_folder).replace('[NOW]', time_now)
            Time = self.time_lineEdit.text().replace('[PATH]', folder).replace('[FOLDER]', active_folder).replace('[NOW]', time_now)
            notes = self.notes_lineEdit.toPlainText().replace('[PATH]', folder).replace('[FOLDER]', active_folder).replace('[NOW]', time_now)
            export_dir = self.get_export_folder()
            pic_name = self.get_picture_name()

            # get options
            edit_mode, open_collage, add_description, add_logo = self.get_options()

            # creates new collage
            new_collage = Collage(root='', title=title, subtitle=subtitle, Time=Time, notes=notes, path=self.active_path, pic_list=processed_pictures)

            # generates template. Will raise an error if a matching template is not found (exit function in that case)
            try:
                new_collage_dic = new_collage.generate_template(self.current_template)
            except:
                self.print_to_log(f"ERROR: Could not find a matching template for {len(processed_pictures)} pictures, please create one")
                return

            # creates and save picture (passing the mainWindow as argument to populate it in the UI file)
            self.mainWindow = Window()
            new_collage.create_collage(self.app, self.mainWindow, pic_dic=new_collage_dic, ui=edit_mode, dir = export_dir, name = pic_name, show = open_collage, desc=add_description, logo=add_logo)


    def print_to_log(self, string):
        ''' log message to console with time information '''
        print(f'{datetime.now().strftime("%d.%m.%Y, %H:%M:%S")} >> {string}')


def coco_ui():
    app = QApplication(sys.argv)
    myUI = CocoUI(app)
    sys.exit(app.exec_())
