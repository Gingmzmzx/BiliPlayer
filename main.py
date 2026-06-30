import sys
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QApplication,
    QLabel, QWidget
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from BiliPlayer import run
from BiliPlayer.config import Config


class SetupDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BiliPlayer 初始化")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setMinimumHeight(260)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.config = config

        font = QFont()
        font.setPixelSize(14)
        QApplication.setFont(font)
        label_font = QFont()
        label_font.setPixelSize(14)
        label_font.setBold(True)
        label_font.setBold(True)

        self.main_widget = QWidget()
        self.main_widget.setObjectName("mainWidget")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16); shadow.setXOffset(0); shadow.setYOffset(4)
        shadow.setColor(Qt.GlobalColor.gray)
        self.main_widget.setGraphicsEffect(shadow)

        form = QFormLayout(self.main_widget)
        form.setContentsMargins(28, 28, 28, 28)
        form.setVerticalSpacing(14)
        form.setHorizontalSpacing(16)

        self.fields = {}
        defaults = [
            ("uid", "用户UID：", str(config.get("uid", ""))),
            ("favName", "收藏夹名：", str(config.get("favName", ""))),
            ("defaultVolume", "默认音量：", str(config.get("Player.defaultVolume", 30))),
            ("webPort", "Web端口：", str(config.get("Player.webPort", 58000))),
        ]
        for key, label_text, default_val in defaults:
            edit = QLineEdit(default_val)
            edit.setFixedHeight(36)
            edit.setPlaceholderText("请填写内容")
            lab = QLabel(label_text)
            lab.setFont(label_font)
            form.addRow(lab, edit)
            self.fields[key] = edit

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.layout().setSpacing(12)
        buttons.setContentsMargins(0, 12, 0, 0)
        form.addWidget(buttons)

        root = QFormLayout()
        root.setContentsMargins(16, 16, 16, 16)
        root.addWidget(self.main_widget)
        self.setLayout(root)

        self.setStyleSheet("""
        #mainWidget { background-color: #ffffff; border-radius: 12px; }
        QLabel { color: #222222; }
        QLineEdit { border: 1px solid #d0d7e3; border-radius: 8px; padding: 0 12px; background: #fafbfd; color: #222; }
        QLineEdit:focus { border: 1px solid #409eff; background: #ffffff; }
        QLineEdit:hover { border: 1px solid #a8b4cc; }
        QDialogButtonBox QPushButton { height: 38px; border-radius: 8px; padding: 0 22px; border: none; }
        QDialogButtonBox QPushButton[text="OK"] { background-color: #409eff; color: white; }
        QDialogButtonBox QPushButton[text="OK"]:hover { background-color: #337ecc; }
        QDialogButtonBox QPushButton[text="Cancel"] { background-color: #e5e6eb; color: #333333; }
        QDialogButtonBox QPushButton[text="Cancel"]:hover { background-color: #dcdde0; }
        """)

    def getResults(self):
        return {key: edit.text().strip() for key, edit in self.fields.items()}

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


if __name__ == "__main__":
    if sys.platform == "darwin":
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_PluginApplication, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)

    config = Config()
    config.autoComplete()

    uid = config.get("uid", "")
    favName = config.get("favName", "")

    # 第一次启动（未配置过）弹出配置窗口
    if not config.get("configured", False):
        dlg = SetupDialog(config)
        screen = app.primaryScreen().geometry()
        dlg_rect = dlg.frameGeometry()
        dlg_rect.moveCenter(screen.center())
        dlg.move(dlg_rect.topLeft())
        if dlg.exec():
            r = dlg.getResults()
            uid = r["uid"]
            favName = r["favName"]
            config.set("uid", uid)
            config.set("favName", favName)
            config.set("Player.defaultVolume", int(r["defaultVolume"] or 30))
            config.set("Player.webPort", int(r["webPort"] or 58000))
            config.set("configured", True)
            config.save()
        else:
            sys.exit(0)

    run.run(app, uid, favName)
