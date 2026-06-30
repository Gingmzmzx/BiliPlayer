from __future__ import annotations

import json
from playwright.async_api import Browser
from .utils import prt
from .config import STEALTH_JS


class User:
    def __init__(self, browser: Browser):
        self.browser: Browser = browser
        self.page = None
        self.context = None

    async def get_favlist(self, uid: int, favName: str) -> list[dict]:
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

        raw = await self.page.evaluate("""
            (() => {
                const seen = new Set();
                const result = [];
                for (const card of document.querySelectorAll('.bili-video-card')) {
                    // Title from .bili-video-card__title a
                    const titleA = card.querySelector('.bili-video-card__title a');
                    if (!titleA) continue;
                    const href = titleA.href || '';
                    const m = href.match(/\\/video\\/([^/?]+)/);
                    if (!m) continue;
                    const bvid = m[1];
                    if (seen.has(bvid)) continue;
                    seen.add(bvid);
                    const title = (titleA.textContent || '').trim();
                    // Cover from .b-img__inner
                    const img = card.querySelector('.b-img__inner');
                    let cover = '';
                    if (img) {
                        cover = (img.src || '').trim();
                        if (cover.startsWith('//')) cover = 'https:' + cover;
                    }
                    result.push({bvid: bvid, title: title || bvid, cover: cover});
                }
                return JSON.stringify(result);
            })()
        """)
        favList = json.loads(raw)

        await self.page.close()
        if self.context:
            await self.context.close()
            self.context = None
        return favList
