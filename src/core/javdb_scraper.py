# JavDB scraper using Playwright to bypass anti-bot protection

import asyncio
import random
from dataclasses import dataclass
from typing import Optional, List
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import logging

logger = logging.getLogger(__name__)


def _normalize_image_url(url: Optional[str], base_url: str) -> str:
    """Normalize image URLs from JavDB pages."""
    if not url:
        return ""

    url = url.strip()
    if not url:
        return ""

    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return f"{base_url.rstrip('/')}{url}"
    return url

@dataclass
class JavDBMetadata:
    """JavDB视频元数据"""
    id: str                    # 番号 (e.g., "SSIS-123")
    title: str                 # 标题
    cover_url: str             # 封面图URL
    release_date: str          # 发布日期
    duration: str              # 时长
    director: Optional[str]    # 导演
    studio: str                # 片商
    label: Optional[str]       # 厂牌
    series: Optional[str]      # 系列
    actresses: List[str]       # 演员列表
    genres: List[str]          # 类型/标签
    sample_images: List[str]   # 样本截图


class JavDBScraper:
    """JavDB爬虫 - 使用Playwright绕过反爬虫"""

    BASE_URL = "https://javdb571.com"

    # 反检测的浏览器启动参数
    BROWSER_ARGS = [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-site-isolation-trials',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-infobars',
        '--window-size=1920,1080',
        '--start-maximized',
    ]

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None

    async def _init(self):
        """初始化浏览器（增强反检测）"""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=self.BROWSER_ARGS
            )

            # 创建浏览器上下文（更真实的浏览环境）
            self._context = await self._browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
            )

            # 创建页面
            self._page = await self._context.new_page()

            # 注入反检测脚本
            await self._page.add_init_script("""
                // 隐藏webdriver特征
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // 伪装plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // 伪装languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en-US', 'en']
                });
            """)

            # 设置默认超时
            self._page.set_default_timeout(60000)
            self._page.set_default_navigation_timeout(60000)

    async def _get_page(self) -> Page:
        """获取或创建页面"""
        if self._page is None:
            await self._init()
        assert self._page is not None
        return self._page

    async def close(self):
        """关闭浏览器"""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def fetch(self, video_id: str, max_retries: int = 3) -> Optional[JavDBMetadata]:
        """
        获取视频元数据（带重试机制）

        Args:
            video_id: 番号 (e.g., "SSIS-123")
            max_retries: 最大重试次数

        Returns:
            JavDBMetadata or None
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # 随机延迟，避免模式识别
                if attempt > 0:
                    wait_time = (attempt + 1) * random.uniform(3, 8)
                    logger.info(f"第{attempt + 1}次尝试获取 {video_id}，延迟{wait_time:.1f}秒")
                    await asyncio.sleep(wait_time)
                else:
                    await asyncio.sleep(random.uniform(2, 5))

                result = await self._fetch_once(video_id)
                if result:
                    return result

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"第{attempt + 1}次尝试失败: {e}")
                else:
                    logger.error(f"所有重试均失败: {video_id}, 错误: {e}")

        logger.error(f"获取 {video_id} 失败: {last_error}")
        return None

    async def _fetch_once(self, video_id: str) -> Optional[JavDBMetadata]:
        """执行单次获取"""
        page = await self._get_page()

        # 构建搜索URL
        search_url = f"{self.BASE_URL}/search?q={video_id}&f=all"
        logger.debug(f"搜索: {search_url}")

        # 访问搜索页面
        await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)

        # 等待搜索结果加载 - 尝试多个选择器
        await self._wait_for_search_results(page)

        # 获取搜索结果
        link, link_text = await self._get_first_search_result(page, video_id)

        if not link:
            logger.warning(f"未找到 {video_id} 的搜索结果")
            return None

        # 验证搜索结果是否匹配
        if not self._validate_search_result(video_id, link_text):
            logger.warning(f"搜索结果不匹配: 期望{video_id}, 得到{link_text}")
            return None

        href = await link.get_attribute('href')
        if not href:
            logger.warning(f"无法获取链接")
            return None

        if href.startswith('/'):
            detail_url = self.BASE_URL + href
        else:
            detail_url = href

        logger.debug(f"访问详情页: {detail_url}")

        # 访问详情页
        await page.goto(detail_url, wait_until='domcontentloaded', timeout=60000)

        # 等待主要内容加载
        try:
            await page.wait_for_selector('.container', timeout=30000)
        except:
            logger.warning(f"详情页加载超时，尝试继续解析")

        # 提取元数据
        return await self._parse_metadata(page, video_id)

    async def _wait_for_search_results(self, page: Page):
        """等待搜索结果加载（尝试多个选择器）"""
        selectors = ['.item', '.video-item', '.list-item']

        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=30000)
                return
            except:
                continue

        logger.error("搜索结果加载失败，所有选择器都超时")

    async def _get_first_search_result(self, page: Page, video_id: str):
        """获取第一个搜索结果"""
        # 尝试多个选择器
        selectors = ['.item a', '.video-item a', '.list-item a']

        for selector in selectors:
            link = await page.query_selector(selector)
            if link:
                link_text = await link.inner_text()
                return link, link_text

        return None, None

    def _validate_search_result(self, video_id: str, link_text: str) -> bool:
        """验证搜索结果是否匹配目标番号"""
        if not link_text:
            return False

        # 移除连字符和空格后比较
        normalized_id = video_id.upper().replace('-', '')
        normalized_text = link_text.upper().replace('-', '').replace(' ', '')

        return normalized_id in normalized_text

    async def _parse_metadata(self, page: Page, video_id: str) -> Optional[JavDBMetadata]:
        """解析页面元数据"""
        try:
            # 标题
            title_elem = await page.query_selector('h2.title')
            title = await title_elem.inner_text() if title_elem else video_id

            # 封面图，兼容多种页面结构
            cover_url = ""
            cover_selectors = [
                '.column-video-cover img',
                '.video-cover img',
                'a.bigImage img',
                '.tile-images img',
            ]
            for selector in cover_selectors:
                cover_elem = await page.query_selector(selector)
                if not cover_elem:
                    continue

                src = await cover_elem.get_attribute('src')
                data_src = await cover_elem.get_attribute('data-src')
                fancybox_src = await cover_elem.get_attribute('data-fancybox')
                cover_url = _normalize_image_url(data_src or src or fancybox_src, self.BASE_URL)
                if cover_url:
                    break

            if not cover_url:
                og_image = await page.query_selector('meta[property="og:image"]')
                if og_image:
                    og_content = await og_image.get_attribute('content')
                    cover_url = _normalize_image_url(og_content, self.BASE_URL)

            # 解析元数据面板
            blocks = await page.query_selector_all('.panel .panel-block')

            release_date = ""
            duration = ""
            director = None
            studio = ""
            label = None
            series = None
            actresses = []
            genres = []

            for block in blocks:
                text = await block.inner_text()
                text_lower = text.lower()

                # 发布日期
                if '日期' in text or 'date' in text_lower:
                    parts = text.split('\n')
                    if len(parts) > 1:
                        release_date = parts[-1].strip()

                # 时长
                elif '時長' in text or '时长' in text or 'length' in text_lower:
                    parts = text.split('\n')
                    if len(parts) > 1:
                        duration = parts[-1].strip()

                # 导演
                elif '導演' in text or '导演' in text or 'director' in text_lower:
                    parts = text.split('\n')
                    if len(parts) > 1:
                        director = parts[-1].strip()

                # 片商
                elif '片商' in text or 'studio' in text_lower:
                    parts = text.split('\n')
                    if len(parts) > 1:
                        studio = parts[-1].strip()

                # 厂牌
                elif '廠牌' in text or '厂牌' in text or 'label' in text_lower:
                    parts = text.split('\n')
                    if len(parts) > 1:
                        label = parts[-1].strip()

                # 系列
                elif '系列' in text or 'series' in text_lower:
                    parts = text.split('\n')
                    if len(parts) > 1:
                        series = parts[-1].strip()

                # 演员列表
                elif '演員' in text or '演员' in text or 'actress' in text_lower or 'star' in text_lower:
                    links = await block.query_selector_all('a')
                    for link in links:
                        name = await link.inner_text()
                        if name and name.strip():
                            # 移除性别符号后添加
                            clean_name = name.replace('♀', '').strip()
                            if clean_name and clean_name not in actresses:
                                actresses.append(clean_name)

                # 类型/标签
                elif '類別' in text or '类别' in text or 'category' in text_lower or 'genre' in text_lower or 'tag' in text_lower:
                    links = await block.query_selector_all('a')
                    for link in links:
                        name = await link.inner_text()
                        if name and name.strip() and name.strip() not in genres:
                            genres.append(name.strip())

            # 样本截图
            sample_images = []
            try:
                sample_selectors = [
                    '.tile-images .tile-item img',
                    '.sample-images img',
                    '.preview-images img',
                    'img.fancybox',
                ]
                for selector in sample_selectors:
                    sample_elems = await page.query_selector_all(selector)
                    if sample_elems:
                        for elem in sample_elems[:10]:
                            url = await elem.get_attribute('data-src') or await elem.get_attribute('src')
                            if url:
                                sample_images.append(url)
                        break
            except:
                pass

            logger.info(f"成功解析 {video_id}: {title[:50]}")

            return JavDBMetadata(
                id=video_id,
                title=title,
                cover_url=cover_url,
                release_date=release_date,
                duration=duration,
                director=director,
                studio=studio,
                label=label,
                series=series,
                actresses=actresses,
                genres=genres,
                sample_images=sample_images
            )

        except Exception as e:
            logger.error(f"解析元数据失败: {e}")
            return None


class JavDBScraperSync:
    """同步版本的JavDB爬虫"""

    def __init__(self, headless: bool = True):
        self._scraper = JavDBScraper(headless=headless)
        self._loop = None
        self._loop_owner = False

    def _get_loop(self):
        """获取或创建事件循环（确保使用同一个循环）"""
        if self._loop is None:
            try:
                self._loop = asyncio.get_event_loop()
                if self._loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                self._loop_owner = True
        return self._loop

    def fetch(self, video_id: str, max_retries: int = 3) -> Optional[JavDBMetadata]:
        """同步获取视频元数据"""
        loop = self._get_loop()
        try:
            return loop.run_until_complete(self._scraper.fetch(video_id, max_retries))
        except Exception as e:
            logger.error(f"获取 {video_id} 失败: {e}")
            return None

    def close(self):
        """关闭爬虫"""
        if self._loop and not self._loop.is_closed():
            try:
                self._loop.run_until_complete(self._scraper.close())
            except Exception as e:
                logger.warning(f"关闭爬虫时出错: {e}")
            finally:
                if self._loop_owner:
                    self._loop.close()
                self._loop = None


# 测试
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s'
    )

    if len(sys.argv) < 2:
        print("用法: python javdb_scraper.py <番号>")
        sys.exit(1)

    video_id = sys.argv[1]

    scraper = JavDBScraperSync(headless=False)

    try:
        print(f"正在获取 {video_id} 的信息...")
        metadata = scraper.fetch(video_id)

        if metadata:
            print(f"\n=== {metadata.id} ===")
            print(f"标题: {metadata.title}")
            print(f"发布日期: {metadata.release_date}")
            print(f"时长: {metadata.duration}")
            print(f"导演: {metadata.director}")
            print(f"片商: {metadata.studio}")
            print(f"厂牌: {metadata.label}")
            print(f"系列: {metadata.series}")
            print(f"演员: {', '.join(metadata.actresses)}")
            print(f"类型: {', '.join(metadata.genres[:5])}")
            print(f"封面: {metadata.cover_url}")
            print(f"截图: {len(metadata.sample_images)} 张")
        else:
            print(f"未找到 {video_id}")

    finally:
        scraper.close()
