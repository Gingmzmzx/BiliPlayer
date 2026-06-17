import asyncio
import random
from playwright.async_api import Browser, Page
from .config import DEBUG_FLG
from .utils import prt


with open("BiliPlayer/anti_pause.js", "r", encoding="utf-8") as f:
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
                 bv_list: list[str],
                 default_volume: int,
                 sep_page: bool,
                 preferrence=None,
                 on_timeupdate = lambda cur, total: None,
                 on_ended = lambda: None,
                 on_play = lambda: None
                 ) -> None:
        if preferrence is None:
            preferrence = dict()
        self.bv_list: list[str] = bv_list
        self.current_title: str = str()
        self.current_bv: str = str()
        self.browser: Browser = browser
        self.page = None
        self.callback_timeupdate = on_timeupdate
        self.callback_ended = on_ended
        self.callback_play = on_play
        self.state: PlayState = PlayState()
        self.default_volume: int = int(default_volume)
        self.preferrence: dict = preferrence
        self.duration: float = 0
        self.cur: float = 0
        self.sep_page = sep_page

    def get_random_next(self) -> str:
        available = [bv for bv in self.bv_list if bv != self.current_bv]
        return random.choice(available if available else self.bv_list)

    def _on_timeupdate(self, cur, total):
        # prt(f"Time update: {cur:.2f} / {total:.2f}")
        self.cur = cur
        endTime = self.preferrence.get(self.current_bv, {}).get("endTime", -1)
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
        await self.page.evaluate(f"$('video')[0].currentTime = {progress}")

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
            self.page: Page = await self.browser.new_page()
            prt("Page Created")
            await self.page.expose_function("biliMusic_on_timeupdate", self._on_timeupdate)
            await self.page.expose_function("biliMusic_on_ended", self._on_ended)

        bvid = self.get_random_next() if bvid is None else bvid
        pref = self.preferrence.get(bvid, {})
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
                await self.play(self.get_random_next())
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
        headless=not DEBUG_FLG,
        ignore_default_args=["--mute-audio"],
        args=["--autoplay-policy=no-user-gesture-required", "--no-sandbox"]
    )
    BV_LIST = ["BVxxxxxxxxxxx"]
    biliMusic = BiliMusicPlayer(browser=browser, bv_list=BV_LIST, on_timeupdate=show_progress, on_play=func_on_play)

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

    await biliMusic.run()
    await biliMusic.play()

    await browser.close()
    await p.stop()

if __name__ == '__main__':
    asyncio.run(test())
