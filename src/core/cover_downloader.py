# 封面下载器 - 下载并缓存视频封面

import logging
import os
import time
from pathlib import Path
from typing import Optional, Dict, Callable
import threading
import requests

logger = logging.getLogger(__name__)


class CoverDownloader:
    """封面下载器 - 同步批量下载"""

    def __init__(self, config=None):
        if config:
            self.covers_dir = Path(config.covers_dir)
        else:
            # 默认路径
            self.covers_dir = Path("data/images/covers")
        self.covers_dir.mkdir(parents=True, exist_ok=True)

        # 转换为绝对路径
        self.covers_dir = self.covers_dir.resolve()

        # 下载会话
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://javdb571.com/',
        })

    def get_cover_path(self, video_id: str) -> str:
        """获取封面本地路径"""
        return str(self.covers_dir / f"{video_id}.jpg")

    def download_one(self, video_id: str, url: str, retries: int = 3) -> Optional[str]:
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

        # 重试下载
        for attempt in range(retries):
            try:
                logger.info(f"下载封面: {video_id} <- {url} (尝试 {attempt + 1}/{retries})")
                response = self.session.get(url, timeout=15)
                response.raise_for_status()  # 检查HTTP错误

                # 确保目录存在
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                with open(local_path, 'wb') as f:
                    f.write(response.content)

                logger.info(f"封面下载成功: {video_id}")
                return local_path

            except requests.RequestException as e:
                logger.error(f"下载失败(尝试{attempt+1}/{retries}): {video_id} - {type(e).__name__}: {e}")
                if attempt < retries - 1:
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
