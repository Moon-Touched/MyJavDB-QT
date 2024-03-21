from PyQt6 import uic, QtWidgets
from PyQt6.QtCore import QTimer, QRectF, Qt, QPropertyAnimation, QPointF
from PyQt6.QtGui import QBrush, QColor, QPixmap, QPen
from tasks import *
import sys, pymongo


class MatchInfoDialouge(QtWidgets.QDialog):
    def __init__(self, db):
        super().__init__()
        ui = uic.loadUi("./MatchInfoDialouge.ui", self)
        self.go_btn: QtWidgets.QPushButton = ui.go_btn
        self.log_area: QtWidgets.QTextBrowser = ui.log_area
        self.capture_path_btn: QtWidgets.QPushButton = ui.capture_path_btn
        self.movie_path_btn: QtWidgets.QPushButton = ui.movie_path_btn
        self.capture_path_label: QtWidgets.QLabel = ui.capture_path_label
        self.movie_path_label: QtWidgets.QLabel = ui.movie_path_label

        self.db = db
        self.capture_path = ""
        self.movie_path = ""
        self.go_btn.clicked.connect(self.run)
        self.capture_path_btn.clicked.connect(self.select_capture_path)
        self.movie_path_btn.clicked.connect(self.select_movie_path)

    def run(self):
        if self.movie_path == "" or self.capture_path == "":
            self.log_area.append("请选择路径")
            return
        self.go_btn.setEnabled(False)
        self.log_area.setText("")
        self.task = MatchInfoTask(db=self.db, capture_path=self.capture_path, movie_path=self.movie_path, time_interval=1)

        self.task.log_signal.connect(self.update_log)
        self.task.finished_signal.connect(self.enable_btn)
        self.task.start()

    def update_log(self, message):
        self.log_area.append(message)

    def enable_btn(self):
        self.go_btn.setEnabled(True)

    def select_capture_path(self):
        # 弹出对话框让用户选择目录
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "选择路径")
        if directory:  # 检查用户是否选择了路径
            self.capture_path_label.setText(f"选定路径: {directory}")
            self.capture_path = directory

    def select_movie_path(self):
        # 弹出对话框让用户选择目录
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "选择路径")
        if directory:  # 检查用户是否选择了路径
            self.movie_path_label.setText(f"选定路径: {directory}")
            self.movie_path = directory


class MagnetDialouge(QtWidgets.QDialog):
    def __init__(self, db):
        super().__init__()
        ui = uic.loadUi("./MagnetDialouge.ui", self)
        self.go_btn: QtWidgets.QPushButton = ui.go_btn
        self.log_area: QtWidgets.QTextBrowser = ui.log_area
        self.actor_list: QtWidgets.QComboBox = ui.actor_list
        self.code_input_box: QtWidgets.QLineEdit = ui.code_input_box
        self.save_to_Pikpak_check: QtWidgets.QCheckBox = ui.save_to_Pikpak_check

        self.db = db
        actor_collection = self.db["actor"].find()
        for a in actor_collection:
            self.actor_list.addItem(a["name"])

        self.go_btn.clicked.connect(self.run)

    def run(self):
        self.go_btn.setEnabled(False)
        self.log_area.setText("")
        actor_name = self.actor_list.currentText()
        code = self.code_input_box.text()
        save_to_pikpak = self.save_to_Pikpak_check.isChecked()
        self.task = MagnetTask(db=self.db, actor_name=actor_name, code=code, save_to_pikpak=save_to_pikpak, time_interval=1)

        self.task.log_signal.connect(self.update_log)
        self.task.finished_signal.connect(self.enable_btn)
        self.task.start()

    def update_log(self, message):
        self.log_area.append(message)

    def enable_btn(self):
        self.go_btn.setEnabled(True)


class OneActorAllMovieDialouge(QtWidgets.QDialog):
    def __init__(self, db):
        super().__init__()
        ui = uic.loadUi("./OneActorAllMovieDialouge.ui", self)
        self.go_btn: QtWidgets.QPushButton = ui.go_btn
        self.log_area: QtWidgets.QTextBrowser = ui.log_area
        self.actor_list: QtWidgets.QComboBox = ui.actor_list

        self.db = db
        actor_collection = self.db["actor"].find()
        for a in actor_collection:
            self.actor_list.addItem(a["name"])

        self.go_btn.clicked.connect(self.run)

    def run(self):
        self.go_btn.setEnabled(False)
        self.log_area.setText("")
        actor_name = self.actor_list.currentText()
        self.task = OneActorAllMovieTask(actor_name=actor_name, time_interval=1, db=self.db)

        self.task.log_signal.connect(self.update_log)
        self.task.finished_signal.connect(self.enable_btn)
        self.task.start()

    def update_log(self, message):
        self.log_area.append(message)

    def enable_btn(self):
        self.go_btn.setEnabled(True)


class FavouriteActorDialouge(QtWidgets.QDialog):
    def __init__(self, db):
        super().__init__()
        ui = uic.loadUi("./FavouriteActorDialouge.ui", self)
        self.go_btn: QtWidgets.QPushButton = ui.go_btn
        self.log_area: QtWidgets.QTextBrowser = ui.log_area

        self.db = db

        self.go_btn.clicked.connect(self.run)

    def run(self):
        self.go_btn.setEnabled(False)
        self.log_area.setText("")

        self.task = FavouriteActorTask(time_interval=1, db=self.db)

        self.task.log_signal.connect(self.update_log)
        self.task.finished_signal.connect(self.enable_btn)
        self.task.start()

    def update_log(self, message):
        self.log_area.append(message)

    def enable_btn(self):
        self.go_btn.setEnabled(True)


class OneActorInfoDialouge(QtWidgets.QDialog):
    def __init__(self, db):
        super().__init__()
        ui = uic.loadUi("./OneActorInfoDialouge.ui", self)
        self.go_btn: QtWidgets.QPushButton = ui.go_btn
        self.url_input_box: QtWidgets.QLineEdit = ui.url_input_box
        self.log_area: QtWidgets.QTextBrowser = ui.log_area
        self.update_check: QtWidgets.QCheckBox = ui.update_check

        self.db = db

        self.go_btn.clicked.connect(self.run)

    def run(self):
        self.go_btn.setEnabled(False)
        self.log_area.setText("")

        actor_url = self.url_input_box.text()
        update = self.update_check.isChecked()
        self.task = OneActorInfoTask(time_interval=0, actor_url=actor_url, db=self.db, update=update)

        self.task.log_signal.connect(self.update_log)
        self.task.finished_signal.connect(self.enable_btn)
        self.task.start()

    def update_log(self, message):
        self.log_area.append(message)

    def enable_btn(self):
        self.go_btn.setEnabled(True)


class OneMovieInfoDialouge(QtWidgets.QDialog):
    def __init__(self, db):
        super().__init__()
        ui = uic.loadUi("./OneMovieInfoDialouge.ui", self)
        self.go_btn: QtWidgets.QPushButton = ui.go_btn
        self.url_input_box: QtWidgets.QLineEdit = ui.url_input_box
        self.log_area: QtWidgets.QTextBrowser = ui.log_area
        self.uncensored_check: QtWidgets.QCheckBox = ui.uncensored_check

        self.db = db

        self.go_btn.clicked.connect(self.run)

    def run(self):
        self.go_btn.setEnabled(False)
        self.log_area.setText("")

        movie_url = self.url_input_box.text()
        uncensored = self.uncensored_check.isChecked()
        self.task = OneMovieInfoTask(time_interval=0, movie_url=movie_url, db=self.db, uncensored=uncensored)

        self.task.log_signal.connect(self.update_log)
        self.task.finished_signal.connect(self.enable_btn)
        movie_info = self.task.start()

    def update_log(self, message):
        self.log_area.append(message)

    def enable_btn(self):
        self.go_btn.setEnabled(True)


class StartPage(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.client = pymongo.MongoClient("mongodb://localhost:27017/")
        self.db = self.client["MyJavDB"]

        ui = uic.loadUi("./start_page.ui", self)
        self.one_movie_btn: QtWidgets.QPushButton = ui.one_movie_btn
        self.actor_all_movie_btn: QtWidgets.QPushButton = ui.actor_all_movie_btn
        self.favourit_actor_button: QtWidgets.QPushButton = ui.favourit_actor_button
        self.one_actor_button: QtWidgets.QPushButton = ui.one_actor_button
        self.magnet_btn: QtWidgets.QPushButton = ui.magnet_btn
        self.match_btn: QtWidgets.QPushButton = ui.match_btn

        self.one_movie_btn.clicked.connect(self.open_one_movie_dialogue)
        self.one_actor_button.clicked.connect(self.open_one_actor_dialogue)
        self.favourit_actor_button.clicked.connect(self.open_favourite_actor_dialogue)
        self.actor_all_movie_btn.clicked.connect(self.open_one_actor_all_movie_dialogue)
        self.magnet_btn.clicked.connect(self.open_magnet_dialogue)
        self.match_btn.clicked.connect(self.open_match_info_dialogue)

    def open_one_movie_dialogue(self):
        self.dialog = OneMovieInfoDialouge(db=self.db)
        self.dialog.setModal(True)
        self.dialog.exec()

    def open_one_actor_dialogue(self):
        self.dialog = OneActorInfoDialouge(db=self.db)
        self.dialog.setModal(True)
        self.dialog.exec()

    def open_favourite_actor_dialogue(self):
        self.dialog = FavouriteActorDialouge(db=self.db)
        self.dialog.setModal(True)
        self.dialog.exec()

    def open_one_actor_all_movie_dialogue(self):
        self.dialog = OneActorAllMovieDialouge(db=self.db)
        self.dialog.setModal(True)
        self.dialog.exec()

    def open_magnet_dialogue(self):
        self.dialog = MagnetDialouge(db=self.db)
        self.dialog.setModal(True)
        self.dialog.exec()

    def open_match_info_dialogue(self):
        self.dialog = MatchInfoDialouge(db=self.db)
        self.dialog.setModal(True)
        self.dialog.exec()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = StartPage()
    win.show()
    sys.exit(app.exec())
