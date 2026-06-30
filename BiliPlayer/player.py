from __future__ import annotations

import asyncio
import random
from playwright.async_api import Browser

from .config import DEBUG_FLG, STEALTH_JS
from .utils import prt


with open("BiliPlayer/resources/anti_pause.js", "r", encoding="utf-8") as f:
    JS_CONTENT = f.read()


class PlayState:
    def __init__(self):
        self.next_song: bool = False
        self.toggle_pause: bool = False
        self.volume: int = -1
        self.quit: bool = False
        self.progress: int = -1


class BiliMusicPlayer:
    def __init__(self,
                 browser: Browser,
                 bv_list: list,
                 default_volume: int,
                 sep_page: bool,
                 preference=None,
                 shared_state=None,
                 play_mode: str = "shuffle",
                 on_timeupdate = lambda cur, total: None,
                 on_ended = lambda: None,
                 on_play = lambda: None
                 ) -> None:
        if preference is None:
            preference = dict()
        self.bv_list: list = bv_list
        self.current_title: str = str()
        self.current_bv: str = str()
        self.browser: Browser = browser
        self.page = None
        self.callback_timeupdate = on_timeupdate
        self.callback_ended = on_ended
        self.callback_play = on_play
        self.state: PlayState = PlayState()
        self.default_volume: int = int(default_volume)
        self.preference: dict = preference
        self.duration: float = 0
        self.cur: float = 0
        self.sep_page = sep_page
        self.random_cur = 0
        self.context = None
        self.shared_state = shared_state
        self.play_mode: str = play_mode
        self._pending_bvid: str | None = None
        self._needs_reload: bool = False

    def get_random_next(self) -> str:
        if self.random_cur < len(self.bv_list):
            self.random_cur += 1
            return self.bv_list[self.random_cur-1]
        random.shuffle(self.bv_list)
        while self.bv_list[0] == self.current_bv:
            random.shuffle(self.bv_list)
        self.random_cur = 1
        return self.bv_list[0]

    def get_next(self) -> str:
        """Return the next BV based on play_mode ('sequential'|'shuffle'|'repeat_one')."""
        print(f"[get_next] _pending_bvid={self._pending_bvid}, bv_list len={len(self.bv_list)}, current_bv={self.current_bv}, mode={self.play_mode}", flush=True)

        if self._pending_bvid is not None:
            bv = self._pending_bvid
            self._pending_bvid = None
            if bv in self.bv_list:
                self.random_cur = self.bv_list.index(bv)
            print(f"[get_next] pending → {bv}", flush=True)
            return bv

        if self.shared_state is not None:
            web_pl = self.shared_state.get_playlist()
            print(f"[get_next] shared_state playlist len={len(web_pl)}", flush=True)
            if web_pl and web_pl != self.bv_list:
                print(f"[get_next] sync bv_list from shared_state", flush=True)
                self.bv_list = web_pl
                if self.current_bv in web_pl:
                    self.random_cur = web_pl.index(self.current_bv)
            self.play_mode = self.shared_state.play_mode

        # Fallback: if local list is empty but shared_state has items, use those
        if not self.bv_list and self.shared_state is not None:
            fb = self.shared_state.get_playlist()
            print(f"[get_next] fallback: shared_state playlist len={len(fb)}", flush=True)
            if fb:
                self.bv_list = fb
                self.random_cur = 0

        if not self.bv_list:
            print(f"[get_next] bv_list empty, returning '{self.current_bv or ''}'", flush=True)
            return self.current_bv or ""

        if self.play_mode == "repeat_one" and self.current_bv:
            print(f"[get_next] repeat_one → {self.current_bv}", flush=True)
            return self.current_bv

        if self.play_mode == "sequential":
            if self.current_bv in self.bv_list:
                idx = self.bv_list.index(self.current_bv)
                next_idx = (idx + 1) % len(self.bv_list)
                self.random_cur = next_idx
                print(f"[get_next] sequential → {self.bv_list[next_idx]}", flush=True)
                return self.bv_list[next_idx]
            self.random_cur = 0
            print(f"[get_next] sequential(first) → {self.bv_list[0]}", flush=True)
            return self.bv_list[0]

        result = self.get_random_next()
        print(f"[get_next] shuffle → {result}", flush=True)
        return result

    def _on_timeupdate(self, cur, total):
        # prt(f"Time update: {cur:.2f} / {total:.2f}")
        self.cur = cur
        endTime = self.preference.get(self.current_bv, {}).get("endTime", -1)
        if endTime != -1 and cur >= endTime:
            self.next_song()
        self.callback_timeupdate(cur, total)

    async def _on_ended(self):
        prt("Video ended, playing next...")
        self.state.next_song = True
        self.callback_ended()

    def _on_play(self):
        prt("Video started")
        self.callback_play()

    async def _toggle_pause(self):
        is_video_paused = await self.page.evaluate("document.querySelector('video').paused")
        if is_video_paused:
            await self.page.evaluate("document.querySelector('video').play()")
        else:
            await self.page.evaluate("document.querySelector('video').pause()")

    async def _set_volume(self, vol):
        await self.page.evaluate(f"document.querySelector('video').volume = {int(vol) / 100}")

    async def _set_progress(self, progress):
        prt("_set_progress", progress)
        await self.page.evaluate(f"document.querySelector('video').currentTime = {progress}")

    def set_progress(self, progress):
        self.state.progress = progress

    def next_song(self):
        self.state.next_song = True
    
    def toggle_pause(self):
        self.state.toggle_pause = True

    def set_volume(self, vol):
        self.state.volume = vol

    async def play(self, bvid=None):
        # Init page
        if self.sep_page:
            if not self.context:
                self.context = await self.browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1920, "height": 1080},
                    locale="zh-CN",
                )
            self.page = await self.context.new_page()
            # 注入 stealth 脚本（在每个新 document 创建前执行）
            await self.page.add_init_script(STEALTH_JS)
            prt("Page Created")
            await self.page.expose_function("biliMusic_on_timeupdate", self._on_timeupdate)
            await self.page.expose_function("biliMusic_on_ended", self._on_ended)

        bvid = self.get_next() if bvid is None else bvid
        print(f"[play] bvid={repr(bvid)}, current_bv={self.current_bv}", flush=True)
        pref = self.preference.get(bvid, {})
        self.current_bv = bvid
        url = f"https://www.bilibili.com/video/{bvid}"
        if pref.get("p"):
            url += f"?p={pref.get('p')}"
        prt("Going to", url)
        await self.page.goto(url, timeout=80000)
        await self.page.wait_for_selector("video", timeout=40000)
        prt("Video Loaded")

        # 标题
        title = await self.page.evaluate('document.querySelector("h1")?.innerText || "未知标题"')
        self.current_title = title
        self.duration = await self.page.evaluate("window.player.getDuration()")
        await self.page.evaluate("""
                    const v = document.querySelector('video');
                    v.muted = false;
                    v.volume = {0};
                """.format(self.default_volume / 100))
        await self.page.evaluate(JS_CONTENT)

        # 播放
        if pref.get("beginTime"):
            await self._set_progress(int(pref.get("beginTime", 0)))

        # 获取时长
        prt(f"Playing: {title} ({bvid})")
        self._on_play()

        while True:
            if self.state.next_song:
                self.state.next_song = False
                if self.sep_page:
                    await self.page.close()
                    prt("Close Page")
                await self.play()
                break
            if self.state.toggle_pause:
                self.state.toggle_pause = False
                await self._toggle_pause()
            if self.state.volume != -1:
                await self._set_volume(self.state.volume)
                self.state.volume = -1
            if self.state.progress != -1:
                await self._set_progress(self.state.progress)
                self.state.progress = -1
            if self.state.quit:
                break

            if self.shared_state is not None:
                cmd = self.shared_state.get_command()
                if cmd is not None:
                    cmd_name, cmd_val = cmd
                    if cmd_name == "next":
                        self.next_song()
                    elif cmd_name == "pause":
                        self.toggle_pause()
                    elif cmd_name == "seek":
                        if cmd_val is not None:
                            self.set_progress(self.duration * (cmd_val / 100))
                    elif cmd_name == "volume":
                        if cmd_val is not None:
                            self.set_volume(cmd_val)
                            self.shared_state.volume = cmd_val
                    elif cmd_name == "play_index":
                        if cmd_val is not None:
                            pl = self.shared_state.get_playlist()
                            if 0 <= cmd_val < len(pl):
                                self._pending_bvid = pl[cmd_val]
                                self.next_song()
                    elif cmd_name == "reload_playlist":
                        self._needs_reload = True
                        self.next_song()
                    elif cmd_name == "quit":
                        self.quit()

            await asyncio.sleep(.5)

        await self.page.close()

    def quit(self):
        self.state.quit = True


# Testing...
async def test():
    def show_progress(cur, total):
        # 以一个进度条形式显示进度
        bar_length = 30
        filled_length = int(bar_length * cur // total)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f"\rProgress: |{bar}| {cur:.2f}/{total:.2f} seconds", end='')
    
    def func_on_play():
        print(f"\nPlaying {biliMusic.current_title} ({biliMusic.current_bv})")

    from playwright.async_api import async_playwright
    p = await async_playwright().start()
    browser = await p.chromium.launch(
        channel="chrome",
        headless=not DEBUG_FLG,
        ignore_default_args=["--mute-audio"],
        args=["--autoplay-policy=no-user-gesture-required", "--no-sandbox"]
    )
    BV_LIST = ["BVxxxxxxxxxxx"]
    biliMusic = BiliMusicPlayer(
        browser=browser,
        bv_list=BV_LIST,
        on_timeupdate=show_progress,
        on_play=func_on_play,
        default_volume=30,
        sep_page=True
    )

    def cmdctl():
        while True:
            cmd = input("Enter command (n: next, p: pause/play, v[0-100]: set volume, t[int]: set progress, q: quit): \n").strip().lower()
            print("debug", cmd)
            if cmd == 'n':
                biliMusic.next_song()
            elif cmd == 'p':
                biliMusic.toggle_pause()
            elif cmd.startswith('v'):
                try:
                    vol = int(cmd.replace("v", ""))
                    if 0 <= vol <= 100:
                        biliMusic.set_volume(vol)
                    else:
                        print("Volume must be between 0 and 100.")
                except ValueError:
                    print("Invalid volume value.")
            elif cmd.startswith('t'):
                try:
                    vol = int(cmd.replace("t", ""))
                    biliMusic.set_progress(vol)
                except ValueError:
                    print("Invalid progress value.")
            elif cmd == 'q':
                biliMusic.quit()
                break
            else:
                print("Unknown command.")

    import threading
    cmd_thread = threading.Thread(target=cmdctl)
    cmd_thread.start()

    await biliMusic.play()

    await browser.close()
    await p.stop()

if __name__ == '__main__':
    asyncio.run(test())
