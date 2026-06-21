import sys
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QApplication,
    QLabel, QWidget
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from BiliPlayer import run


UID = 227711953
FAVNAME = "豪听"


class TwoInputDialog(QDialog):
    def __init__(self, title="请输入", label1="输入1：", label2="输入2：", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setMinimumHeight(180)
        # 无边框圆角弹窗
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 字体设置
        self.global_font = QFont("Microsoft YaHei", 11)
        self.label_font = QFont("Microsoft YaHei", 11)
        self.label_font.setBold(True)
        QApplication.setFont(self.global_font)

        # 主圆角容器
        self.main_widget = QWidget()
        self.main_widget.setObjectName("mainWidget")
        # 阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(Qt.GlobalColor.gray)
        self.main_widget.setGraphicsEffect(shadow)

        # 输入框
        self.edit1 = QLineEdit(str(UID))
        self.edit2 = QLineEdit(FAVNAME)
        for edit in [self.edit1, self.edit2]:
            edit.setFixedHeight(36)
            edit.setPlaceholderText("请填写内容")

        # 表单布局
        form_layout = QFormLayout(self.main_widget)
        form_layout.setContentsMargins(28, 28, 28, 28)
        form_layout.setVerticalSpacing(18)
        form_layout.setHorizontalSpacing(16)

        # 修复：改用QLabel而不是QWidget
        lab1 = QLabel(label1)
        lab1.setFont(self.label_font)
        lab2 = QLabel(label2)
        lab2.setFont(self.label_font)
        form_layout.addRow(lab1, self.edit1)
        form_layout.addRow(lab2, self.edit2)

        # 确定+取消按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.layout().setSpacing(12)
        buttons.setContentsMargins(0, 12, 0, 0)
        form_layout.addWidget(buttons)

        # 外层布局
        root_layout = QFormLayout()
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.addWidget(self.main_widget)
        self.setLayout(root_layout)

        # 美化样式表
        self.setStyleSheet("""
        #mainWidget {
            background-color: #ffffff;
            border-radius: 12px;
        }
        QLabel {
            color: #222222;
        }
        QLineEdit {
            border: 1px solid #d0d7e3;
            border-radius: 8px;
            padding: 0 12px;
            background: #fafbfd;
        }
        QLineEdit:focus {
            border: 1px solid #409eff;
            background: #ffffff;
        }
        QLineEdit:hover {
            border: 1px solid #a8b4cc;
        }
        QDialogButtonBox QPushButton {
            height: 38px;
            border-radius: 8px;
            padding: 0 22px;
            border: none;
        }
        QDialogButtonBox QPushButton[text="OK"] {
            background-color: #409eff;
            color: white;
        }
        QDialogButtonBox QPushButton[text="OK"]:hover {
            background-color: #337ecc;
        }
        QDialogButtonBox QPushButton[text="Cancel"] {
            background-color: #e5e6eb;
            color: #333333;
        }
        QDialogButtonBox QPushButton[text="Cancel"]:hover {
            background-color: #dcdde0;
        }
        """)

    def getInputs(self):
        return self.edit1.text().strip(), self.edit2.text().strip()

    # 窗口拖拽
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


if __name__ == "__main__":
    # macOS：隐藏 Dock 图标（必须在 QApplication 创建之前设置）
    if sys.platform == "darwin":
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_PluginApplication, True)
    app = QApplication(sys.argv)
    dlg = TwoInputDialog(
        title="BiliPlayer初始化",
        label1="用户UID：",
        label2="收藏夹名："
    )
    # 窗口居中
    screen = app.primaryScreen().geometry()
    dlg_rect = dlg.frameGeometry()
    dlg_rect.moveCenter(screen.center())
    dlg.move(dlg_rect.topLeft())

    if dlg.exec():
        UID, FAVNAME = dlg.getInputs()
        print(f"输入UID: {UID}, 收藏夹: {FAVNAME}")
        run.run(app, UID, FAVNAME)
