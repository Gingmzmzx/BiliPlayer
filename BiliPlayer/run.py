import asyncio
import threading

from playwright.async_api import async_playwright
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QFont

from .player import BiliMusicPlayer
from .user import User
from . import config
from .utils import prt
from .gui import RightSideProgress


# ===================== 全局信号类 =====================
class AppSignal(QObject):
    progress_update = pyqtSignal(float, float, str, str)  # 播放进度UI
    loading_close = pyqtSignal()                          # 关闭Loading信号

app_sig = AppSignal()

# 跨线程指令队列：存放需要跳转的进度百分比 (0~100)
seek_val = -1
toggle_pause = False
# 全局运行标记
TASK_RUNNING = True

# 全局Loading窗口实例
loading_window = None


# ===================== 美观 Loading 窗口 =====================
class LoadingWindow(QWidget):
    def __init__(self, uid, favName):
        super().__init__()
        self.uid = uid
        self.favName = favName
        self.init_ui()
        # 文字动画定时器
        self.dot_count = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_loading_text)
        self.timer.start(400)

    def init_ui(self):
        # 窗口基础设置：置顶、无边框、居中、磨砂深色风格
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(280, 120)

        # 主布局
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(20, 20, 20, 20)

        # 背景面板（模拟磨砂黑）
        self.bg_panel = QWidget(self)
        self.bg_panel.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 30, 0.9);
                border-radius: 8px;
                border: 1px solid rgba(80, 80, 120, 0.6);
            }
        """)
        bg_layout = QVBoxLayout(self.bg_panel)
        bg_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 加载文字
        self.load_label = QLabel("BiliPlayer Loading")
        self.load_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.load_label.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        self.load_label.setStyleSheet("color: #e0e0ff;")
        self.info_label = QLabel(f"UID: {self.uid} FavName: {self.favName}")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.info_label.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Light))
        self.info_label.setStyleSheet("color: #e0e0ff;")
        bg_layout.addWidget(self.load_label)
        bg_layout.addWidget(self.info_label)

        layout.addWidget(self.bg_panel)
        self.setLayout(layout)

        # 屏幕居中
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def update_loading_text(self):
        """动态点点动画 Loading... → Loading...."""
        self.dot_count = (self.dot_count + 1) % 4
        text = "BiliPlayer Loading" + "." * self.dot_count
        self.load_label.setText(text)

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)


# ===================== 异步播放主协程 =====================
async def play_main(uid, favName):
    global TASK_RUNNING, seek_val
    p = await async_playwright().start()
    browser = await p.chromium.launch(
        headless=not config.DEBUG_FLG,
        ignore_default_args=["--mute-audio"],
        args=["--autoplay-policy=no-user-gesture-required", "--no-sandbox"]
    )

    favList = await User(browser=browser).get_favlist(uid=uid, favName=favName)
    prt(favList)
    biliPlayer = BiliMusicPlayer(browser=browser, bv_list=favList, preferrence=config.PREFERRENCE)

    # 播放进度回调 → 更新UI
    def timeupdate(cur, total):
        app_sig.progress_update.emit(cur, total, biliPlayer.current_title, biliPlayer.current_bv)

    biliPlayer.callback_timeupdate = timeupdate

    # ========== 关键：执行 run() 前Loading已显示，执行完发送关闭信号 ==========
    prt("开始执行 biliPlayer.run()，Loading 生效中...")
    await biliPlayer.run()
    prt("biliPlayer.run() 执行完毕，关闭 Loading")
    app_sig.loading_close.emit()  # 通知UI线程关闭Loading

    # 1. 播放主协程（长驻）
    async def play_task():
        await biliPlayer.play()

    # 2. 进度跳转监听协程
    async def seek_monitor():
        global seek_val, toggle_pause
        while TASK_RUNNING:
            if seek_val != -1:
                print("收到跳转指令", seek_val)
                seek = biliPlayer.duration * (seek_val / 100)
                if abs(seek-biliPlayer.cur) >= 3:
                    biliPlayer.set_progress(seek)
                else:
                    print("toggle_pause")
                    biliPlayer.toggle_pause()
                seek_val = -1
            await asyncio.sleep(0.1)

    # 两个协程并行运行
    try:
        await asyncio.gather(play_task(), seek_monitor())
    except Exception as e:
        QMessageBox.warning(None, "Runtime Error", f"并行任务异常\n{e}")

    # 资源释放
    prt("开始释放资源...")
    await browser.close()
    await p.stop()
    prt("资源释放完成")


# ===================== 异步子线程入口 =====================
def async_worker(uid, favName):
    global TASK_RUNNING
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(play_main(uid, favName))
    except Exception as e:
        QMessageBox.warning(None, "Runtime Error", f"播放任务异常\n{e}")
    finally:
        loop.close()


# ===================== UI 主线程 =====================
def main(app, uid, favName):
    global TASK_RUNNING, seek_val, loading_window
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # 初始化 Loading 窗口并显示
    loading_window = LoadingWindow(uid, favName)
    loading_window.show()

    # 绑定关闭Loading信号（主线程内执行，安全）
    def close_loading():
        if loading_window and loading_window.isVisible():
            loading_window.close()

    app_sig.loading_close.connect(close_loading)

    handle_click_val = -1
    def ui_on_mouse_release(percent):
        prt(f"UI 拖拽完成，发送进度: {percent}%")
        global seek_val
        seek_val = percent

    def ui_on_handle_click(val):
        global handle_click_val
        handle_click_val = val

    # 初始化主窗口
    window = RightSideProgress(on_mouse_release=ui_on_mouse_release, on_mouse_click=ui_on_handle_click)

    def parse_time(t: float) -> str:
        total = int(t)
        minute = total // 60
        second = total % 60
        return f"{minute:02d}:{second:02d}"

    def change_progress(cur, total, title, bv):
        try:
            window.change_progress(int((cur/total)*100))
            window.tooltip.setText(
                f"<b style='font-size:14px; color:#ffffff;'>{parse_time(cur)}/{parse_time(total)}</b><br>"
                f"<span style='font-size:11px; color:#cccccc;'>标题: {title}</span><br>"
                f"<span style='font-size:11px; color:#cccccc;'>BV号: {bv}</span>"
            )
            window.tooltip.adjustSize()
        except ValueError as e:
            # QMessageBox.warning(window, "Runtime Error", "An ValueError has occoured in main.change_progress\n"+str(e)+"\nClick OK to switch to the next song.")
            prt("change_progress", e)
            pass

    # 进度信号绑定
    app_sig.progress_update.connect(change_progress)

    # 窗口退出逻辑
    def on_app_quit():
        global TASK_RUNNING
        TASK_RUNNING = False
        prt("窗口关闭，通知播放任务退出")
        # 退出时强制关闭Loading
        if loading_window and loading_window.isVisible():
            loading_window.close()

    app.aboutToQuit.connect(on_app_quit)

    # 启动播放子线程
    work_thread = threading.Thread(target=async_worker, args=(uid, favName,), daemon=False)
    work_thread.start()

    window.show()
    app.exec()

    # 等待子线程资源释放完毕
    work_thread.join()
    prt("程序完全退出")

def run(app, uid, favName):
    try:
        main(app, uid, favName)
    except Exception as e:
        QMessageBox.critical(None, "Runtime Error", f"Program has exited caused by\n{e}\nPlease restart. If this issue persists, contact the developer.")

