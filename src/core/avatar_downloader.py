"""女优头像下载器"""

import json
import logging
import os
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class AvatarDownloader:
    """女优头像下载与缓存管理"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # 自动定位到项目根目录下的 data/
            app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(app_dir, "data")
        self.data_dir = Path(data_dir)
        self.avatars_dir = self.data_dir / "images" / "avatars"
        self.avatars_dir.mkdir(parents=True, exist_ok=True)
        self.actress_data_path = self.data_dir / "actress_data.json"
        self._data: Optional[List[Dict]] = None

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/*,*/*;q=0.8',
        })
        self._setup_http_adapter()

    def _setup_http_adapter(self):
        retry = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def load_actress_data(self) -> List[Dict]:
        """加载女优数据"""
        if self._data is not None:
            return self._data

        if not self.actress_data_path.exists():
            logger.warning("女优数据文件不存在")
            return []

        with open(self.actress_data_path, 'r', encoding='utf-8') as f:
            self._data = json.load(f)
        return self._data

    def get_avatar_path(self, name: str) -> Optional[str]:
        """获取女优头像本地路径"""
        # 用名字的 hash 作为文件名，避免特殊字符问题
        name_hash = hashlib.md5(name.encode('utf-8')).hexdigest()[:12]
        for ext in ('.jpg', '.png', '.webp'):
            path = self.avatars_dir / f"{name_hash}{ext}"
            if path.exists():
                return str(path)
        return None

    def get_avatar_url(self, name: str) -> Optional[str]:
        """根据女优名字查找头像URL"""
        data = self.load_actress_data()
        for actress in data:
            if actress['name'] == name:
                return actress.get('avatar_url')
        return None

    def get_actress_info(self, name: str) -> Optional[Dict]:
        """获取女优完整信息"""
        data = self.load_actress_data()
        for actress in data:
            if actress['name'] == name:
                return actress
        return None

    def get_all_actress_info(self) -> List[Dict]:
        """获取所有女优信息，附带本地头像路径"""
        data = self.load_actress_data()
        for actress in data:
            actress['avatar_path'] = self.get_avatar_path(actress['name'])
        return data

    def download_avatar(self, name: str, url: str) -> Optional[str]:
        """下载单个女优头像"""
        local_path = self.get_avatar_path(name)
        if local_path:
            return local_path

        name_hash = hashlib.md5(name.encode('utf-8')).hexdigest()[:12]
        local_path = str(self.avatars_dir / f"{name_hash}.jpg")

        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()

            content_type = resp.headers.get('Content-Type', '')
            if content_type and 'image/' not in content_type.lower():
                logger.warning(f"头像响应不是图片: {name}")
                return None

            with open(local_path, 'wb') as f:
                f.write(resp.content)

            if os.path.getsize(local_path) == 0:
                os.remove(local_path)
                return None

            logger.info(f"头像下载成功: {name}")
            return local_path
        except Exception as e:
            logger.error(f"头像下载失败: {name} - {e}")
            return None

    def download_missing_avatars(self, callback=None) -> Dict[str, str]:
        """下载所有缺失的头像"""
        data = self.load_actress_data()
        results = {}

        for i, actress in enumerate(data):
            name = actress['name']
            url = actress.get('avatar_url', '')

            if not url or 'actor_unknow' in url:
                continue

            if self.get_avatar_path(name):
                continue

            path = self.download_avatar(name, url)
            if path:
                results[name] = path

            if callback:
                callback(i + 1, len(data), name, path is not None)

            time.sleep(0.3)

        logger.info(f"头像批量下载完成: {len(results)}")
        return results

    def close(self):
        self.session.close()
