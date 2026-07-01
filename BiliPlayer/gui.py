import sys

from PyQt6.QtWidgets import QApplication, QWidget, QSlider, QLabel
from PyQt6.QtCore import Qt, QPoint, QRect
from .config import _resource


class CustomSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.on_handle_click = lambda value: None
        self.on_mouse_release = lambda value: None
        self.on_handle_enter = lambda value: None
        self.on_handle_leave = lambda value: None
        self._is_hover_handle = False
        self.handle_size = 18
        self.offset_size = 9
        self._is_mouse_pressed = False
        self.setMouseTracking(True)

    def _is_mouse_on_handle(self, pos: QPoint) -> bool:
        if self.orientation() != Qt.Orientation.Vertical:
            return False
        pos_x = pos.x()
        pos_y = pos.y()
        # X: must be within slider width (with small margin)
        if pos_x < -10 or pos_x > self.width() + 10:
            return False
        slider_h = self.height()
        val = self.value()
        min_val = self.minimum()
        max_val = self.maximum()
        total_range = max_val - min_val

        if total_range == 0:
            handle_center_y = slider_h / 2
        else:
            ratio = (val - min_val) / total_range
            handle_center_y = slider_h * (1 - ratio)
        return abs(pos_y - handle_center_y) <= ((self.handle_size / 2) + self.offset_size)

    def get_handle_center_pos(self) -> QPoint:
        if self.orientation() != Qt.Orientation.Vertical:
            return self.mapToGlobal(self.rect().center())
        slider_h = self.height()
        val = self.value()
        min_val = self.minimum()
        max_val = self.maximum()
        total_range = max_val - min_val

        if total_range == 0:
            handle_center_y = slider_h / 2
        else:
            ratio = (val - min_val) / total_range
            handle_center_y = slider_h * (1 - ratio)
        local_pos = QPoint(int(self.width() / 2), int(handle_center_y))
        return self.mapToGlobal(local_pos)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        current_on = self._is_mouse_on_handle(event.pos())
        if current_on and not self._is_hover_handle:
            self._is_hover_handle = True
            if self.on_handle_enter:
                self.on_handle_enter(self.value())
        elif not current_on and self._is_hover_handle:
            self._is_hover_handle = False
            if self.on_handle_leave:
                self.on_handle_leave(self.value())

    def enterEvent(self, event):
        super().enterEvent(event)
        if self._is_mouse_on_handle(self.mapFromGlobal(self.cursor().pos())):
            self._is_hover_handle = True
            if self.on_handle_enter:
                self.on_handle_enter(self.value())

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if self._is_hover_handle:
            self._is_hover_handle = False
            if self.on_handle_leave:
                self.on_handle_leave(self.value())

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.orientation() == Qt.Orientation.Vertical:
            pos_y = event.pos().y()
            slider_h = self.height()
            val = self.value()
            total_range = self.maximum() - self.minimum()
            if total_range == 0:
                return
            self._is_mouse_pressed = True
            ratio = (val - self.minimum()) / total_range
            handle_center_y = slider_h * (1 - ratio)
            if abs(pos_y - handle_center_y) <= self.handle_size / 2:
                if self.on_handle_click:
                    self.on_handle_click(val)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._is_mouse_pressed = False
        if self.on_mouse_release:
            self.on_mouse_release(self.value())

    def getIfMosuePressed(self):
        return self._is_mouse_pressed


class RightSideProgress(QWidget):
    def __init__(self,
                 on_mouse_click = lambda value: None,
                 on_mouse_release = lambda value: None,
                 on_handle_enter = lambda value: None,
                 on_handle_leave = lambda value: None,
                 on_progress_change = lambda value: None):
        super().__init__()

        self.callback_on_mouse_click = on_mouse_click
        self.callback_on_mouse_release = on_mouse_release
        self.callback_on_handle_enter = on_handle_enter
        self.callback_on_handle_leave = on_handle_leave
        self.callback_on_progress_change = on_progress_change

        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        if sys.platform != "darwin":
            flags |= Qt.WindowType.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        screen = QApplication.primaryScreen().availableGeometry()
        scr_w = screen.width()
        scr_h = screen.height()
        win_width = 40
        win_height = scr_h
        win_x = scr_w - win_width
        win_y = screen.top()
        self.setGeometry(win_x, win_y, win_width, win_height)

        # 滑块
        self.slider = CustomSlider(Qt.Orientation.Vertical, self)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.setFixedSize(win_width, win_height)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.prevProgress = -1

        # Tooltip 窗口配置
        self.tooltip = QLabel()
        self.tooltip.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.ToolTip
            | Qt.WindowType.WindowStaysOnTopHint
        )

        # ========== 美化后的 Tooltip 样式 ==========
        self.tooltip.setStyleSheet("""
        QLabel {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                        stop:0 rgba(45, 45, 48, 0.96), 
                                        stop:1 rgba(28, 28, 30, 0.96));
            color: #f0f0f0;
            font-family: -apple-system, "Microsoft YaHei", sans-serif;
            padding: 10px 14px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            /* 外阴影 */
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.45);
        }
        """)

        self.tooltip.setText("100%\nBVID: asdasdasdas\ntitle: asdasdasdfdgsfd")
        self.tooltip.adjustSize()
        self.tooltip.hide()

        # 信号绑定
        self.slider.on_handle_click = self.on_slider_click
        self.slider.on_mouse_release = self.on_mouse_up
        self.slider.valueChanged.connect(self.on_progress_change)

        # ---- 定时轮询 tooltip（macOS 上 mouseMoveEvent 失焦不触发） ----
        from PyQt6.QtCore import QTimer
        self._hover_timer = QTimer(self)
        self._hover_timer.timeout.connect(self._poll_hover)
        self._hover_timer.start(120)
        self._was_hover = False

        # 滑块样式（使用绝对路径，Windows 需用反斜杠转正斜杠）
        def _url(p):
            return _resource(p).replace("\\", "/")
        tv  = _url("BiliPlayer/resources/bilitv.png")
        tvh = _url("BiliPlayer/resources/bilitv_hover.png")
        tvp = _url("BiliPlayer/resources/bilitv_pressed.png")
        self.slider.setStyleSheet(f"""
        QSlider::groove:vertical {{
            background: #444444;
            width: 6px;
            border-radius: 3px;
            margin: 0px;
            padding: 0px;
            subcontrol-position: right center;
        }}
        QSlider::sub-page:vertical {{
            background: #ff99cc;
            width: 6px;
            border-radius: 3px;
            margin: 0px;
            padding: 0px;
        }}
        QSlider::handle:vertical {{
            image: url({tv});
            width: 20px;
            height: 18px;
            border-radius: 10px;
            margin: 0 0 0 -11px;
            padding: 0px;
            background: transparent;
        }}
        QSlider::handle:vertical:hover {{
            image: url({tvh});
        }}
        QSlider::handle:vertical:pressed {{
            image: url({tvp});
        }}
        """)

    def _update_tooltip(self, _: int):
        handle_pos = self.slider.get_handle_center_pos()

        # 基础坐标：手柄左侧 + 间距
        tip_x = handle_pos.x() - self.tooltip.width() - 10
        tip_y = handle_pos.y() - (self.tooltip.height() / 2)

        # 获取屏幕完整区域
        screen_rect: QRect = QApplication.primaryScreen().availableGeometry()
        tip_h = self.tooltip.height()

        # 顶部越界：贴屏幕顶部，留出少量边距
        if tip_y < screen_rect.top():
            tip_y = screen_rect.top() + 6
        # 底部越界：贴屏幕底部，留出少量边距
        elif tip_y + tip_h > screen_rect.bottom():
            tip_y = screen_rect.bottom() - tip_h - 6

        self.tooltip.move(int(tip_x), int(tip_y))

    def on_progress_change(self, value: int):
        if self.tooltip.isVisible():
            self._update_tooltip(value)
        self.callback_on_progress_change(value)

    def on_slider_click(self, value: int):
        print(f"点击滑块，进度: {value}%")
        self.callback_on_mouse_click(value)

    def on_mouse_up(self, value: int):
        print(f"鼠标松开，最终进度: {value}%")
        self.callback_on_mouse_release(value)

    def on_handle_enter(self, value: int):
        self._update_tooltip(value)
        self.callback_on_handle_enter(value)
        self.tooltip.show()

    def on_handle_leave(self, value: int):
        self.tooltip.hide()
        self.callback_on_handle_leave(value)

    def _poll_hover(self):
        """Timer-based hover detection (works even when window is unfocused on macOS)."""
        from PyQt6.QtGui import QCursor
        gp = QCursor.pos()
        lp = self.slider.mapFromGlobal(gp)
        on_handle = self.slider._is_mouse_on_handle(lp)
        if on_handle and not self._was_hover:
            self._was_hover = True
            self.on_handle_enter(self.slider.value())
        elif not on_handle and self._was_hover:
            self._was_hover = False
            self.on_handle_leave(self.slider.value())

    def change_progress(self, value: int):
        if self.slider.getIfMosuePressed():
            return
        val = max(0, min(100, value))
        self.slider.setValue(val)

