import asyncio
import sys
import threading

from playwright.async_api import async_playwright
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QFont

from .player import BiliMusicPlayer
from .user import User
from .utils import prt
from .gui import RightSideProgress
from .config import Config, DEBUG_FLG
from .web_state import SharedState
from .web_server import start_web_server


# ===================== 全局信号类 =====================
class AppSignal(QObject):
    progress_update = pyqtSignal(float, float, str, str)  # 播放进度UI
    loading_close = pyqtSignal()                          # 关闭Loading信号

app_sig = AppSignal()
config  = Config()

# 跨线程指令队列：存放需要跳转的进度百分比 (0~100)
seek_val = -1
toggle_pause = False
# 全局运行标记
TASK_RUNNING = True

# 全局Loading窗口实例
loading_window = None

# ===================== 共享状态（web ↔ player 桥梁） =====================
shared_state = SharedState()


# ===================== 美观 Loading 窗口 =====================
class LoadingWindow(QWidget):
    def __init__(self, uid, favName):
        super().__init__()
        self.info_label = None
        self.load_label = None
        self.bg_panel = None
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
        # macOS: AA_PluginApplication 已隐藏 Dock，不加 Tool（Tool 创建 NSPanel 会引入拖拽问题）
        # Windows: 加 Tool 以隐藏任务栏图标
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        if sys.platform != "darwin":
            flags |= Qt.WindowType.Tool
        self.setWindowFlags(flags)
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
    global TASK_RUNNING, seek_val, shared_state
    p = await async_playwright().start()
    browser = await p.chromium.launch(
        channel="chrome",
        headless=not DEBUG_FLG,
        ignore_default_args=["--mute-audio"],
        args=[
            "--autoplay-policy=no-user-gesture-required",
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--disable-features=TranslateUI",
            "--disable-component-extensions-with-background-pages",
            "--disable-client-side-phishing-detection",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-sync",
            "--metrics-recording-only",
            "--no-default-browser-check",
            "--no-first-run",
        ]
    )

    shared_state.uid = int(uid)
    shared_state.fav_name = favName
    shared_state.play_mode = config.get("Player.playMode")
    shared_state.volume = config.get("Player.defaultVolume")

    favList = await User(browser=browser).get_favlist(uid=uid, favName=favName)
    bv_ids = [it['bvid'] for it in favList]
    titles = {it['bvid']: it['title'] for it in favList}
    shared_state.set_playlist(bv_ids, titles)

    biliPlayer = BiliMusicPlayer(
        browser=browser,
        bv_list=bv_ids,
        preference=config.get("Player.preference"),
        sep_page=config.get("Player.sepPage"),
        default_volume=config.get("Player.defaultVolume"),
        shared_state=shared_state,
        play_mode=shared_state.play_mode,
    )

    def timeupdate(cur, total):
        app_sig.progress_update.emit(cur, total, biliPlayer.current_title, biliPlayer.current_bv)
        shared_state.update_playback(cur, total, biliPlayer.current_bv, biliPlayer.current_title)

    biliPlayer.callback_timeupdate = timeupdate

    prt("biliPlayer实例化完成，关闭Loading...")
    app_sig.loading_close.emit()

    async def seek_monitor():
        global seek_val
        while TASK_RUNNING:
            if seek_val != -1:
                print("收到跳转指令", seek_val)
                seek = biliPlayer.duration * (seek_val / 100)
                if abs(seek - biliPlayer.cur) >= 3:
                    biliPlayer.set_progress(seek)
                else:
                    print("toggle_pause")
                    biliPlayer.toggle_pause()
                seek_val = -1
            await asyncio.sleep(0.1)

    async def reload_monitor():
        nonlocal biliPlayer
        while TASK_RUNNING:
            if shared_state.needs_reload():
                try:
                    new_list = await User(browser=browser).get_favlist(
                        uid=shared_state.uid, favName=shared_state.fav_name
                    )
                    bv_ids = [it['bvid'] for it in new_list]
                    titles = {it['bvid']: it['title'] for it in new_list}
                    shared_state.set_playlist(bv_ids, titles)
                    biliPlayer.bv_list = bv_ids
                    if biliPlayer.current_bv in bv_ids:
                        biliPlayer.random_cur = bv_ids.index(biliPlayer.current_bv)
                except Exception as e:
                    pass
            await asyncio.sleep(1.0)

    seek_task = asyncio.create_task(seek_monitor())
    reload_task = asyncio.create_task(reload_monitor())

    try:
        while TASK_RUNNING:
            await biliPlayer.play()
            if biliPlayer._needs_reload:
                try:
                    new_list = await User(browser=browser).get_favlist(
                        uid=shared_state.uid, favName=shared_state.fav_name
                    )
                    bv_ids = [it['bvid'] for it in new_list]
                    titles = {it['bvid']: it['title'] for it in new_list}
                    shared_state.set_playlist(bv_ids, titles)
                    biliPlayer.bv_list = bv_ids
                    biliPlayer._needs_reload = False
                except Exception as e:
                    pass
                    biliPlayer._needs_reload = False
            if biliPlayer.state.quit:
                TASK_RUNNING = False
                break
    except Exception as e:
        print(f"[play_main] 播放任务异常: {e}", flush=True)
        import traceback; traceback.print_exc()
    finally:
        TASK_RUNNING = False
        seek_task.cancel()
        reload_task.cancel()

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
        print(f"[async_worker] 播放任务异常: {e}", flush=True)
        import traceback; traceback.print_exc()
    finally:
        loop.close()


# ===================== UI 主线程 =====================
def main(app, uid, favName):
    global TASK_RUNNING, seek_val, loading_window, shared_state
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    # 初始化 Loading 窗口并显示
    loading_window = LoadingWindow(uid, favName)
    loading_window.show()

    def close_loading():
        if loading_window and loading_window.isVisible():
            loading_window.close()

    app_sig.loading_close.connect(close_loading)

    # ---- 启动 Web 控制服务器 ----
    web_port = config.get("Player.webPort")
    start_web_server(shared_state, config, port=web_port)
    print(f"Web 控制面板已启动: http://localhost:{web_port}", flush=True)

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

