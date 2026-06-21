from playwright.async_api import Browser
from .utils import prt
from .config import STEALTH_JS


class User:
    def __init__(self, browser: Browser):
        self.browser: Browser = browser
        self.page = None
        self.context = None

    async def get_favlist(self, uid: int, favName: str) -> list:
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
        await self.page.add_init_script(STEALTH_JS)
        await self.page.goto(f"https://space.bilibili.com/{uid}/favlist?ftype=create", timeout=80000)
        await self.page.wait_for_selector(".items", timeout=40000)
        prt("Favlist Page Loaded.")

        await self.page.click(f".fav-sidebar-item[title='{favName}']")
        await self.page.wait_for_selector(f".favlist-info-detail__title-row div.vui_ellipsis.multi-mode:text('{favName}')")

        favList = await self.page.evaluate("""
                                 let aaadata=[];
                                 aaadata = Array.from(new Set(aaadata.concat(Array.from(document.querySelectorAll('a')).filter(el => el.href.includes('www.bilibili.com/video')).map(el => el.origin + el.pathname))));
                                 aaadata.join(' ');
                                """)
        favList = str(favList).split(" ")
        favList = [i.replace("https://www.bilibili.com/video/", "") for i in favList]
        prt(favList)

        await self.page.close()
        return favList
