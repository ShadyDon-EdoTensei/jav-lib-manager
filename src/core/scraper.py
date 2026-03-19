"""元数据抓取器 - 从JavDB等站点获取视频元数据"""

import re
import time
import random
import logging
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime
from pathlib import Path

import requests
from lxml import html

from .models import VideoMetadata, SourceType
from .parser import get_parser

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """爬虫基类"""

    BASE_URL = ""
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
        'Accept-Encoding': 'gzip, deflate',  # 移除br，避免返回不同页面
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    def __init__(self, delay_range: tuple = (1, 3)):
        """
        初始化爬虫

        Args:
            delay_range: 请求延迟范围（秒）
        """
        self.delay_range = delay_range
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        self.parser = get_parser()

    @abstractmethod
    def fetch(self, code: str) -> Optional[VideoMetadata]:
        """
        根据番号获取元数据

        Args:
            code: 标准化的番号 (如 "ABC-123")

        Returns:
            VideoMetadata 或 None
        """
        pass

    def _request(self, url: str, timeout: int = 30) -> Optional[requests.Response]:
        """
        发送HTTP请求（带随机延迟）

        Args:
            url: 请求URL
            timeout: 超时时间

        Returns:
            Response 或 None
        """
        try:
            # 随机延迟
            time.sleep(random.uniform(*self.delay_range))
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"请求失败: {url}, 错误: {e}")
            return None

    def _download_image(self, url: str, save_path: str) -> bool:
        """
        下载图片到本地

        Args:
            url: 图片URL
            save_path: 保存路径

        Returns:
            是否成功
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # 确保目录存在
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            print(f"下载图片失败: {url}, 错误: {e}")
            return False


class JavDBScraper(BaseScraper):
    """JavDB爬虫"""

    BASE_URL = "https://javdb.com"

    # 搜索URL格式
    SEARCH_URL = f"{BASE_URL}/search?q={{code}}&f=all"

    def fetch(self, code: str) -> Optional[VideoMetadata]:
        """
        从JavDB抓取元数据

        Args:
            code: 标准化的番号

        Returns:
            VideoMetadata 或 None
        """
        # 先搜索
        search_url = self.SEARCH_URL.format(code=code)
        response = self._request(search_url)
        if not response:
            return None

        # 解析搜索结果页面
        tree = html.fromstring(response.content)

        # 查找第一个搜索结果的链接
        # JavDB的搜索结果中，视频卡片在 .item-list .item 下
        items = tree.cssselect('.item-list .item')
        if not items:
            # 尝试直接访问详情页
            detail_url = f"{self.BASE_URL}/v/{code.lower().replace('-', '')}"
            return self._fetch_detail(detail_url, code)

        # 获取第一个结果的详情页链接
        first_item = items[0]
        link = first_item.cssselect('a')
        if link:
            detail_url = link[0].get('href')
            if detail_url:
                # 处理相对URL
                if detail_url.startswith('/'):
                    detail_url = self.BASE_URL + detail_url
                return self._fetch_detail(detail_url, code)

        return None

    def _fetch_detail(self, url: str, code: str) -> Optional[VideoMetadata]:
        """
        抓取详情页

        Args:
            url: 详情页URL
            code: 番号

        Returns:
            VideoMetadata 或 None
        """
        response = self._request(url)
        if not response:
            return None

        tree = html.fromstring(response.content)

        # 提取标题
        title = self._extract_title(tree)

        # 提取封面
        cover_url = self._extract_cover(tree)

        # 提取演员
        actresses = self._extract_actresses(tree)

        # 提取制作商/发行商
        studio, label = self._extract_studio(tree)

        # 提取系列
        series = self._extract_series(tree)

        # 提取类型标签
        genres = self._extract_genres(tree)

        # 提取发行日期
        release_date = self._extract_release_date(tree)

        # 提取时长
        duration = self._extract_duration(tree)

        return VideoMetadata(
            id=code,
            title=title or code,
            cover_url=cover_url,
            actresses=actresses,
            studio=studio,
            label=label,
            series=series,
            genres=genres,
            release_date=release_date,
            duration=duration,
            source=SourceType.JAVDB
        )

    def _extract_title(self, tree) -> Optional[str]:
        """提取标题"""
        # 标题通常在 h2.title 下
        title_elem = tree.cssselect('h2.title')
        if title_elem:
            return title_elem[0].text_content().strip()

        # 备选: 检查 meta og:title
        og_title = tree.cssselect('meta[property="og:title"]')
        if og_title:
            return og_title[0].get('content')

        return None

    def _extract_cover(self, tree) -> Optional[str]:
        """提取封面URL"""
        # 封面通常在 .column-video-cover .video-cover img 下
        cover_elem = tree.cssselect('.column-video-cover img')
        if cover_elem:
            return cover_elem[0].get('src') or cover_elem[0].get('data-src')

        # 备选: 检查 meta og:image
        og_image = tree.cssselect('meta[property="og:image"]')
        if og_image:
            return og_image[0].get('content')

        return None

    def _extract_actresses(self, tree) -> list[str]:
        """提取演员列表"""
        actresses = []

        # 演员通常在 .panel-block 中，带有 avatar 类
        actress_elems = tree.cssselect('.panel-block')
        for elem in actress_elems:
            # 查找包含演员名的元素
            name_elem = elem.cssselect('.value')
            if name_elem:
                name = name_elem[0].text_content().strip()
                if name and name not in actresses:
                    actresses.append(name)

        # 备选: 查找演员链接
        actress_links = tree.cssselect('a[href*="/actors/"]')
        for link in actress_links:
            name = link.text_content().strip()
            if name and name not in actresses:
                actresses.append(name)

        return actresses

    def _extract_studio(self, tree) -> tuple[Optional[str], Optional[str]]:
        """提取制作商和发行商"""
        studio = None
        label = None

        # 制作商/发行商信息在 .panel-block 中
        panels = tree.cssselect('.panel-block')
        for panel in panels:
            label_elem = panel.cssselect('.label')
            if label_elem:
                label_text = label_elem[0].text_content().strip()
                value_elem = panel.cssselect('.value')
                if value_elem:
                    value_text = value_elem[0].text_content().strip()

                    if '製作商' in label_text or '制作商' in label_text:
                        studio = value_text
                    elif '發行商' in label_text or '发行商' in label_text:
                        label = value_text

        return studio, label

    def _extract_series(self, tree) -> Optional[str]:
        """提取系列名"""
        panels = tree.cssselect('.panel-block')
        for panel in panels:
            label_elem = panel.cssselect('.label')
            if label_elem:
                label_text = label_elem[0].text_content().strip()
                if '系列' in label_text:
                    value_elem = panel.cssselect('.value')
                    if value_elem:
                        return value_elem[0].text_content().strip()
        return None

    def _extract_genres(self, tree) -> list[str]:
        """提取类型标签"""
        genres = []

        # 标签通常在 .panel-block 或 .tags 下
        tag_elems = tree.cssselect('.panel-block')
        for panel in tag_elems:
            label_elem = panel.cssselect('.label')
            if label_elem and '類別' in label_elem[0].text_content():
                # 查找所有标签
                tags = panel.cssselect('.value a')
                for tag in tags:
                    tag_text = tag.text_content().strip()
                    if tag_text and tag_text not in genres:
                        genres.append(tag_text)

        # 备选: 查找所有标签链接
        tag_links = tree.cssselect('a[href*="/tags/"]')
        for link in tag_links:
            tag_text = link.text_content().strip()
            if tag_text and tag_text not in genres:
                genres.append(tag_text)

        return genres

    def _extract_release_date(self, tree) -> Optional[datetime]:
        """提取发行日期"""
        panels = tree.cssselect('.panel-block')
        for panel in panels:
            label_elem = panel.cssselect('.label')
            if label_elem and '日期' in label_elem[0].text_content():
                value_elem = panel.cssselect('.value')
                if value_elem:
                    date_str = value_elem[0].text_content().strip()
                    # 尝试解析日期格式 (如 "2024-01-01")
                    try:
                        return datetime.strptime(date_str, '%Y-%m-%d')
                    except ValueError:
                        pass
        return None

    def _extract_duration(self, tree) -> Optional[int]:
        """提取时长（秒）"""
        panels = tree.cssselect('.panel-block')
        for panel in panels:
            label_elem = panel.cssselect('.label')
            if label_elem and '時長' in label_elem[0].text_content():
                value_elem = panel.cssselect('.value')
                if value_elem:
                    duration_str = value_elem[0].text_content().strip()
                    # 解析时长格式 (如 "120分" 或 "02:00:00")
                    match = re.search(r'(\d+)分', duration_str)
                    if match:
                        return int(match.group(1)) * 60
        return None


class FANZAScraper(BaseScraper):
    """FANZA (DMM) API 爬虫 - 使用官方API"""

    # FANZA商品搜索API (无需认证的公开接口)
    API_URL = "https://api.dmm.com/affiliate/v3/ItemList"

    # 备用URL - 直接爬取FANZA网页
    SITE_URL = "https://www.fanza.jp"

    def __init__(self, api_id: str = "", affiliate_id: str = ""):
        """
        初始化FANZA爬虫

        Args:
            api_id: DMM API ID (可选，用于API访问)
            affiliate_id: DMM Affiliate ID (可选)
        """
        super().__init__(delay_range=(0.5, 2))
        self.api_id = api_id
        self.affiliate_id = affiliate_id

    def fetch(self, code: str) -> Optional[VideoMetadata]:
        """
        从FANZA获取元数据

        Args:
            code: 标准化的番号

        Returns:
            VideoMetadata 或 None
        """
        # 优先使用网页爬取 (更稳定，无需API密钥)
        return self._fetch_from_web(code)

    def _fetch_from_web(self, code: str) -> Optional[VideoMetadata]:
        """从FANZA网页抓取数据"""
        # FANZA搜索URL
        search_url = f"{self.SITE_URL}/search?search_str={code}"

        response = self._request(search_url)
        if not response:
            return None

        tree = html.fromstring(response.content)

        # 尝试从搜索结果中找到匹配的项
        # FANZA的商品链接通常包含cid参数
        product_links = tree.cssselect('a[href*="/product/"]')
        if product_links:
            # 获取第一个产品的详情页
            href = product_links[0].get('href')
            if href:
                if href.startswith('/'):
                    detail_url = self.SITE_URL + href
                else:
                    detail_url = href
                return self._fetch_detail(detail_url, code)

        # 如果搜索失败，尝试直接用番号构建详情页URL
        # FANZA的cid格式通常是 h_123abc 或类似格式
        detail_url = f"{self.SITE_URL}/product?id={code}"
        response = self._request(detail_url)
        if response:
            return self._parse_product_page(response.content, code)

        return None

    def _fetch_detail(self, url: str, code: str) -> Optional[VideoMetadata]:
        """抓取详情页"""
        response = self._request(url)
        if not response:
            return None
        return self._parse_product_page(response.content, code)

    def _parse_product_page(self, content: bytes, code: str) -> Optional[VideoMetadata]:
        """解析FANZA商品页面"""
        tree = html.fromstring(content)

        # 提取标题
        title = None
        title_elem = tree.cssselect('h1.productTitle')
        if title_elem:
            title = title_elem[0].text_content().strip()

        # 提取封面
        cover_url = None
        cover_elem = tree.cssselect('img.productImage')
        if cover_elem:
            cover_url = cover_elem[0].get('src') or cover_elem[0].get('data-src')

        # 提取演员
        actresses = []
        actress_elems = tree.cssselect('a[href*="/ actress/"]')
        for elem in actress_elems:
            name = elem.text_content().strip()
            if name and name not in actresses:
                actresses.append(name)

        # 提取制作商
        studio = None
        maker_elem = tree.cssselect('td:contains("メーカー") + td a')
        if maker_elem:
            studio = maker_elem[0].text_content().strip()

        # 提取类型标签
        genres = []
        genre_elems = tree.cssselect('a[href*="/category/"]')
        for elem in genre_elems:
            genre = elem.text_content().strip()
            if genre and genre not in genres:
                genres.append(genre)

        return VideoMetadata(
            id=code,
            title=title or code,
            cover_url=cover_url,
            actresses=actresses,
            studio=studio,
            label=None,
            series=None,
            genres=genres,
            release_date=None,
            duration=None,
            source=SourceType.JAVDB  # 使用JAVDB作为通用来源标识
        )


class JavBusScraper(BaseScraper):
    """JavBus爬虫 - 支持多个镜像域名"""

    # 已知的JavBus镜像域名列表
    MIRROR_DOMAINS = [
        "javbus.com",
        "javbus.biz",
        "javbus.cc",
        "javbus.life",
        "javbus.work",
        "javbus.one",
        "javbus.best",
    ]

    def __init__(self):
        super().__init__(delay_range=(1, 3))
        self.working_domain = None

    def _get_base_url(self) -> str:
        """获取可用的基础URL"""
        if self.working_domain:
            return f"https://{self.working_domain}"

        # 尝试找到可用的域名
        for domain in self.MIRROR_DOMAINS:
            url = f"https://{domain}"
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    self.working_domain = domain
                    return url
            except:
                continue

        # 默认返回第一个
        return f"https://{self.MIRROR_DOMAINS[0]}"

    def fetch(self, code: str) -> Optional[VideoMetadata]:
        """从JavBus抓取元数据"""
        base_url = self._get_base_url()

        # JavBus的URL格式: /ABC-123
        detail_url = f"{base_url}/{code}"
        return self._fetch_detail(detail_url, code)

    def _fetch_detail(self, url: str, code: str) -> Optional[VideoMetadata]:
        """抓取详情页"""
        response = self._request(url)
        if not response:
            return None

        tree = html.fromstring(response.content)

        # 提取标题
        title = None
        title_elem = tree.cssselect('h3')
        if title_elem:
            title = title_elem[0].text_content().strip()

        # 提取封面
        cover_url = None
        cover_elem = tree.cssselect('a.bigImage img')
        if cover_elem:
            cover_url = cover_elem[0].get('src')

        # 提取演员
        actresses = []
        actress_elems = tree.cssselect('a[href*="/star/"]')
        for elem in actress_elems:
            name = elem.text_content().strip()
            if name and name not in actresses:
                actresses.append(name)

        # 提取制作商
        studio = None
        studio_elem = tree.cssselect('a[href*="/studio/"]')
        if studio_elem:
            studio = studio_elem[0].text_content().strip()

        # 提取类型标签
        genres = []
        genre_elems = tree.cssselect('a[href*="/genre/"]')
        for elem in genre_elems:
            genre = elem.text_content().strip()
            if genre and genre not in genres:
                genres.append(genre)

        return VideoMetadata(
            id=code,
            title=title or code,
            cover_url=cover_url,
            actresses=actresses,
            studio=studio,
            label=None,
            series=None,
            genres=genres,
            release_date=None,
            duration=None,
            source=SourceType.JAVDB
        )


class JavDBMirrorScraper(JavDBScraper):
    """JavDB镜像爬虫 - 支持多个镜像域名"""

    # javdb.vip 是目前最稳定的镜像
    PRIMARY_DOMAIN = "javdb.vip"

    MIRROR_DOMAINS = [
        "javdb.vip",       # 主力 - 已验证可用
        "javdb571.com",    # 备用 - 有403保护
        "javdb365.com",
        "javdb.ir",
        "javdb.com",
        "javdb.re",
    ]

    def __init__(self):
        super().__init__()
        # 直接设置主域名
        self.working_domain = self.PRIMARY_DOMAIN

    def _get_base_url(self) -> str:
        """获取可用的基础URL - 强制使用 javdb.vip"""
        return f"https://{self.PRIMARY_DOMAIN}"

    def fetch(self, code: str) -> Optional[VideoMetadata]:
        """从 javdb.vip 抓取 - 直接访问详情页"""
        base_url = self._get_base_url()

        # javdb 的详情页 URL 格式: /v/MIAA652 (去掉连字符)
        code_no_hyphen = code.replace('-', '').lower()
        detail_url = f"{base_url}/v/{code_no_hyphen}"

        # 先尝试直接访问详情页
        result = self._fetch_detail(detail_url, code)
        if result:
            return result

        # 如果失败，尝试搜索
        self.BASE_URL = base_url
        self.SEARCH_URL = f"{base_url}/search?q={{code}}&f=all"
        search_url = self.SEARCH_URL.format(code=code)
        response = self._request(search_url)
        if not response:
            return None

        tree = html.fromstring(response.content)
        items = tree.cssselect('.item-list .item')
        if not items:
            return None

        first_item = items[0]
        link = first_item.cssselect('a')
        if link:
            detail_url = link[0].get('href')
            if detail_url:
                if detail_url.startswith('/'):
                    detail_url = base_url + detail_url
                return self._fetch_detail(detail_url, code)

        return None

    def fetch(self, code: str) -> Optional[VideoMetadata]:
        """从镜像站点抓取"""
        base_url = self._get_base_url()

        # 更新BASE_URL和SEARCH_URL
        self.BASE_URL = base_url
        self.SEARCH_URL = f"{base_url}/search?q={{code}}&f=all"

        # 调用父类方法
        search_url = self.SEARCH_URL.format(code=code)
        response = self._request(search_url)
        if not response:
            return None

        tree = html.fromstring(response.content)
        items = tree.cssselect('.item-list .item')
        if not items:
            detail_url = f"{base_url}/v/{code.lower().replace('-', '')}"
            return self._fetch_detail(detail_url, code)

        first_item = items[0]
        link = first_item.cssselect('a')
        if link:
            detail_url = link[0].get('href')
            if detail_url:
                if detail_url.startswith('/'):
                    detail_url = base_url + detail_url
                return self._fetch_detail(detail_url, code)

        return None


class JavCLScraper(BaseScraper):
    """JavCL爬虫 - javcl.com (英文JAV站点，可访问)"""

    BASE_URL = "https://javcl.com"

    def fetch(self, code: str) -> Optional[VideoMetadata]:
        """从JavCL抓取元数据"""
        # JavCL的URL格式: /MVSD-458 或 /SSIS-123
        detail_url = f"{self.BASE_URL}/{code}"

        response = self._request(detail_url)
        if not response:
            return None

        return self._parse_page(response, code)

    def _parse_page(self, response: requests.Response, code: str) -> Optional[VideoMetadata]:
        """解析JavCL页面"""
        # 使用response.text而不是content，因为内容可能是br/gzip压缩的
        tree = html.fromstring(response.text)

        # 检查是否是404页面
        if response.status_code == 404:
            return None

        # 提取标题 - 优先使用og:title
        title = code
        og_title = tree.cssselect('meta[property="og:title"]')
        if og_title:
            title_content = og_title[0].get('content', '')
            if title_content:
                title = title_content.split('|')[0].strip()  # 去掉网站名后缀

        # 提取封面
        cover_url = None
        og_image = tree.cssselect('meta[property="og:image"]')
        if og_image:
            cover_url = og_image[0].get('content', '')

        # 提取演员名
        actresses = []
        # 查找演员链接
        actress_links = tree.cssselect('a[href*="/actress/"], a[href*="/star/"]')
        for link in actress_links:
            name = link.text_content().strip()
            # 过滤掉太短或重复的名字
            if name and len(name) >= 2 and name not in actresses:
                actresses.append(name)

        # 提取制作商
        studio = None
        # 从meta description中提取
        og_desc = tree.cssselect('meta[property="og:description"]')
        if og_desc:
            desc_text = og_desc[0].get('content', '')
            # JavCL的描述格式: "...movie product by [Studio] production..."
            import re
            studio_match = re.search(r'product by (.+?) production', desc_text, re.IGNORECASE)
            if studio_match:
                studio = studio_match.group(1).strip()

        return VideoMetadata(
            id=code,
            title=title,
            cover_url=cover_url,
            actresses=actresses,
            studio=studio,
            label=None,
            series=None,
            genres=[],
            release_date=None,
            duration=None,
            source=SourceType.JAVDB
        )


class AVWikiScraper(BaseScraper):
    """AV Wiki爬虫 - av-wiki.net (目前最稳定可访问)"""

    BASE_URL = "https://av-wiki.net"

    def fetch(self, code: str) -> Optional[VideoMetadata]:
        """从AV Wiki抓取元数据"""
        # av-wiki的URL格式: /SSIS-123/ 或 /ABC-123/
        detail_url = f"{self.BASE_URL}/{code}/"

        response = self._request(detail_url)
        if not response:
            # 尝试不带斜杠的格式
            detail_url = f"{self.BASE_URL}/{code}"
            response = self._request(detail_url)
            if not response:
                return None

        return self._parse_page(response, code)

    def _parse_page(self, response: requests.Response, code: str) -> Optional[VideoMetadata]:
        """解析AV Wiki页面"""
        # 使用response.text而不是content，因为内容可能是br/gzip压缩的
        tree = html.fromstring(response.text)

        # 检查是否是404页面
        if response.status_code == 404:
            return None

        # 提取标题 - 优先使用og:title
        title = code
        og_title = tree.cssselect('meta[property="og:title"]')
        if og_title:
            title_content = og_title[0].get('content', '')
            if title_content:
                title = title_content.split('|')[0].strip()  # 去掉网站名后缀

        # 提取封面
        cover_url = None
        og_image = tree.cssselect('meta[property="og:image"]')
        if og_image:
            cover_url = og_image[0].get('content', '')

        # 提取演员名 - AV Wiki 主要功能就是显示演员名
        actresses = []
        # 查找演员链接
        actress_links = tree.cssselect('a[href*="/av-actress/"]')
        for link in actress_links:
            name = link.text_content().strip()
            # 过滤掉太短或重复的名字
            if name and len(name) >= 2 and name not in actresses:
                actresses.append(name)

        # 提取制作商
        studio = None
        og_desc = tree.cssselect('meta[property="og:description"]')
        if og_desc:
            desc_text = og_desc[0].get('content', '')
            # 常见制作商标识
            studios = {
                'エスワン': 'S1',
                'S1': 'S1',
                'プレステージ': 'Prestige',
                'IdeaPocket': 'IdeaPocket',
                'MOODYZ': 'MOODYZ',
                '旦旦旦': '旦旦旦',
                'kawaii': 'kawaii',
                'FALENO': 'FALENO',
                'プレミアム': 'Premium'
            }
            for s_jp, s_en in studios.items():
                if s_jp in desc_text:
                    studio = s_en
                    break

        return VideoMetadata(
            id=code,
            title=title,
            cover_url=cover_url,
            actresses=actresses,
            studio=studio,
            label=None,
            series=None,
            genres=[],
            release_date=None,
            duration=None,
            source=SourceType.JAVDB
        )


class JavDBPlaywrightScraper(BaseScraper):
    """JavDB爬虫 - 使用Playwright绕过反爬虫保护

    专门用于访问 javdb571.com，该站点有反爬虫保护
    """

    BASE_URL = "https://javdb571.com"

    def __init__(self, headless: bool = True):
        """初始化Playwright爬虫

        Args:
            headless: 是否使用无头模式
        """
        super().__init__(delay_range=(0.5, 1.5))
        self.headless = headless
        self._scraper_sync = None
        self._initialized = False

    def _get_scraper(self):
        """获取或创建Playwright爬虫实例"""
        if not self._initialized or self._scraper_sync is None:
            from .javdb_scraper import JavDBScraperSync
            self._scraper_sync = JavDBScraperSync(headless=self.headless)
            self._initialized = True
        return self._scraper_sync

    def fetch(self, code: str) -> Optional[VideoMetadata]:
        """使用Playwright获取元数据"""
        try:
            logger.info(f"[Playwright] 开始获取 {code}")
            scraper = self._get_scraper()
            metadata = scraper.fetch(code)

            if metadata:
                logger.info(f"[Playwright] 成功获取 {code}: {metadata.title[:50]}")
                # 转换为VideoMetadata格式
                return VideoMetadata(
                    id=metadata.id,
                    title=metadata.title,
                    cover_url=metadata.cover_url,
                    actresses=metadata.actresses,
                    studio=metadata.studio,
                    label=metadata.label,
                    series=metadata.series,
                    genres=metadata.genres,
                    release_date=None,  # JavDB返回的是字符串，暂不转换
                    duration=None,      # JavDB返回的是字符串，暂不转换
                    source=SourceType.JAVDB
                )
            else:
                logger.warning(f"[Playwright] 未找到 {code}")
        except ImportError as e:
            logger.error(f"[Playwright] 缺少依赖: {e}")
            logger.error("请运行: pip install playwright && playwright install chromium")
        except Exception as e:
            logger.error(f"[Playwright] 获取 {code} 失败: {e}", exc_info=True)

        return None

    def close(self):
        """关闭爬虫"""
        if self._scraper_sync:
            self._scraper_sync.close()
            self._scraper_sync = None
            self._initialized = False


class ScraperManager:
    """爬虫管理器 - 管理多个数据源"""

    def __init__(self):
        """初始化爬虫管理器"""
        self.scrapers = [
            JavDBPlaywrightScraper(headless=True),  # 优先: JavDB Playwright (javdb571.com)
            JavDBMirrorScraper(),       # 备用: JavDB镜像 (javdb.vip)
            JavDBScraper(),             # 备用: JavDB主站
            JavCLScraper(),             # 备用: JavCL (英文站点)
            AVWikiScraper(),            # 备用: AV Wiki (日文站点)
            JavBusScraper(),            # 备用: JavBus (多镜像)
            FANZAScraper(),             # 备用: FANZA (需要日本IP)
        ]

    def close(self):
        """关闭所有爬虫"""
        for scraper in self.scrapers:
            if hasattr(scraper, 'close'):
                scraper.close()

    def fetch(self, code: str) -> Optional[VideoMetadata]:
        """
        从所有数据源尝试获取元数据

        Args:
            code: 番号

        Returns:
            VideoMetadata 或 None
        """
        for i, scraper in enumerate(self.scrapers, 1):
            try:
                logger.info(f"尝试数据源 {i}/{len(self.scrapers)}: {scraper.__class__.__name__}")
                metadata = scraper.fetch(code)
                if metadata:
                    logger.info(f"✓ 成功从 {scraper.__class__.__name__} 获取 {code}")
                    return metadata
            except Exception as e:
                logger.error(f"✗ {scraper.__class__.__name__} 失败: {e}", exc_info=True)
                continue

        logger.warning(f"所有数据源均未找到: {code}")
        return None


# 全局实例
_scraper_manager = None


def get_scraper() -> ScraperManager:
    """获取爬虫管理器单例"""
    global _scraper_manager
    if _scraper_manager is None:
        _scraper_manager = ScraperManager()
    return _scraper_manager
