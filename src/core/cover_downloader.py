# 封面下载器 - 下载并缓存视频封面

import logging
import os
import time
from pathlib import Path
from typing import Optional, Dict, Callable
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class CoverDownloader:
    """封面下载器 - 同步批量下载"""

    def __init__(self, config=None):
        if config:
            self.covers_dir = Path(config.covers_dir)
            self.request_timeout = max(5, int(config.get('scraper_timeout', 30)))
            self.request_retries = max(1, int(config.get('scraper_retries', 3)))
        else:
            # 默认路径
            self.covers_dir = Path("data/images/covers")
            self.request_timeout = 30
            self.request_retries = 3
        self.covers_dir.mkdir(parents=True, exist_ok=True)

        # 转换为绝对路径
        self.covers_dir = self.covers_dir.resolve()

        # 下载会话
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Referer': 'https://javdb571.com/',
        })
        self._setup_http_adapter()

    def _build_referer_candidates(self, url: str) -> list[str]:
        """Build referer candidates to avoid cross-mirror hotlink failures."""
        parsed = urlparse(url)
        candidates = [
            'https://javdb571.com/',
            'https://javdb.vip/',
            'https://javdb.com/',
        ]

        if parsed.scheme and parsed.netloc:
            candidates.insert(0, f"{parsed.scheme}://{parsed.netloc}/")

        # De-duplicate while preserving order
        seen = set()
        result = []
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                result.append(candidate)
        return result

    def _setup_http_adapter(self):
        retry_kwargs = dict(
            total=self.request_retries,
            connect=self.request_retries,
            read=self.request_retries,
            status=self.request_retries,
            backoff_factor=0.8,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )
        try:
            retry = Retry(allowed_methods=frozenset(["GET", "HEAD"]), **retry_kwargs)
        except TypeError:
            retry = Retry(method_whitelist=frozenset(["GET", "HEAD"]), **retry_kwargs)

        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get_cover_path(self, video_id: str) -> str:
        """获取封面本地路径"""
        return str(self.covers_dir / f"{video_id}.jpg")

    def download_one(self, video_id: str, url: str, retries: Optional[int] = None) -> Optional[str]:
        """下载单个封面，支持重试

        Args:
            video_id: 番号
            url: 封面URL
            retries: 重试次数，默认3次

        Returns:
            本地文件路径，失败返回None
        """
        # 检查 URL
        if not url or url == "":
            logger.warning(f"封面URL为空: {video_id}")
            return None

        local_path = self.get_cover_path(video_id)

        # 如果已存在，跳过
        if os.path.exists(local_path):
            logger.debug(f"封面已存在: {video_id}")
            return local_path

        max_retries = retries if retries is not None else self.request_retries

        referer_candidates = self._build_referer_candidates(url)

        # 重试下载
        for attempt in range(max_retries):
            try:
                for referer in referer_candidates:
                    logger.info(f"下载封面: {video_id} <- {url} (尝试 {attempt + 1}/{max_retries}, Referer={referer})")
                    headers = {'Referer': referer}
                    with self.session.get(url, timeout=(5, self.request_timeout), stream=True, headers=headers) as response:
                        response.raise_for_status()  # 检查HTTP错误

                        content_type = response.headers.get('Content-Type', '').lower()
                        if content_type and not content_type.startswith('image/'):
                            logger.warning(f"封面响应不是图片类型: {video_id}, Content-Type={content_type}, Referer={referer}")
                            continue

                        # 确保目录存在
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)

                        with open(local_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)

                    if os.path.getsize(local_path) == 0:
                        logger.warning(f"封面下载结果为空文件: {video_id}, Referer={referer}")
                        continue

                    logger.info(f"封面下载成功: {video_id}")
                    return local_path

            except requests.RequestException as e:
                logger.error(f"下载失败(尝试{attempt+1}/{max_retries}): {video_id} - {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    # 指数退避：1秒、2秒、4秒
                    wait_time = 2 ** attempt
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"下载失败，已达最大重试次数: {video_id}")
                    return None
            except Exception as e:
                logger.error(f"下载失败(非网络错误): {video_id} - {type(e).__name__}: {e}")
                return None  # 非网络错误不重试

    def download_batch(
        self,
        covers: Dict[str, str],
        callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, str]:
        """批量下载封面

        Args:
            covers: {video_id: cover_url}
            callback: 下载完成回调 (video_id, local_path)

        Returns:
            {video_id: local_path}
        """
        results = {}

        for i, (video_id, url) in enumerate(covers.items(), 1):
            logger.info(f"下载进度: {i}/{len(covers)}")

            local_path = self.download_one(video_id, url)
            if local_path:
                results[video_id] = local_path

            if callback:
                callback(video_id, local_path)

            # 延迟，避免请求过快
            if i < len(covers):
                import time
                time.sleep(0.5)

        logger.info(f"批量下载完成: {len(results)}/{len(covers)}")
        return results

    def close(self):
        """关闭会话"""
        self.session.close()
