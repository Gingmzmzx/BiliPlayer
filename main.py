import sys
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QApplication
)
from BiliPlayer import run


UID = 227711953
FAVNAME = "豪听"


class TwoInputDialog(QDialog):
    def __init__(self, title="请输入", label1="输入1：", label2="输入2：", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(300)

        # 两个输入框
        self.edit1 = QLineEdit(str(UID))
        self.edit2 = QLineEdit(FAVNAME)

        # 表单布局（整齐好看）
        layout = QFormLayout()
        layout.addRow(label1, self.edit1)
        layout.addRow(label2, self.edit2)

        # 确定 + 取消按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)
        self.setLayout(layout)

    def getInputs(self):
        """返回 (text1, text2)"""
        return self.edit1.text().strip(), self.edit2.text().strip()

app = QApplication(sys.argv)
if __name__ == "__main__":
    dlg = TwoInputDialog(
        title="BiliPlayer初始化",
        label1="用户UID：",
        label2="收藏夹名："
    )
    if dlg.exec():
        UID, FAVNAME = dlg.getInputs()
        run.run(app, UID, FAVNAME)
