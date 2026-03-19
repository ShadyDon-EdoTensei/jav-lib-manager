"""配置管理模块"""

import os
import json
from pathlib import Path
from typing import Any, Optional


class Config:
    """配置管理器"""

    DEFAULT_CONFIG = {
        # 数据库配置
        'database_path': 'data/library.db',

        # 图片缓存配置
        'covers_dir': 'data/images/covers',
        'avatars_dir': 'data/images/avatars',

        # 扫描配置
        'scan_recursive': True,
        'supported_formats': ['.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.m4v'],

        # 爬虫配置
        'scraper_delay': 2,         # 请求延迟（秒）
        'scraper_timeout': 30,      # 请求超时（秒）
        'scraper_retries': 3,       # 重试次数
        'scraper_concurrent': 3,    # 并发请求数
        'javdb_url': 'https://javdb571.com',  # JavDB镜像地址

        # GUI配置
        'window_width': 1400,
        'window_height': 900,
        'grid_thumb_size': 200,
        'thumb_size': 150,          # 缩略图大小
        'font_size': 10,            # 字体大小

        # 主题配置
        'theme': 'dark_amber',      # 默认主题

        # 其他
        'last_scan_dir': '',
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，默认为 ~/.javlibrary/config.json
        """
        if config_path is None:
            config_dir = os.path.expanduser('~/.javlibrary')
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, 'config.json')

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # 合并默认配置和加载的配置
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded)
                    return config
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()

    def save(self):
        """保存配置到文件"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """设置配置值"""
        self.config[key] = value
        self.save()

    @property
    def database_path(self) -> str:
        """获取数据库路径（绝对路径）"""
        path = self.get('database_path')
        if not os.path.isabs(path):
            # 相对于应用目录
            app_dir = self.get_app_dir()
            return os.path.join(app_dir, path)
        return path

    @property
    def covers_dir(self) -> str:
        """获取封面目录（绝对路径）"""
        path = self.get('covers_dir')
        if not os.path.isabs(path):
            app_dir = self.get_app_dir()
            return os.path.join(app_dir, path)
        return path

    @property
    def avatars_dir(self) -> str:
        """获取头像目录（绝对路径）"""
        path = self.get('avatars_dir')
        if not os.path.isabs(path):
            app_dir = self.get_app_dir()
            return os.path.join(app_dir, path)
        return path

    def get_app_dir(self) -> str:
        """获取应用目录"""
        # 获取当前脚本所在目录的父目录
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def ensure_directories(self):
        """确保所有需要的目录存在"""
        os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
        os.makedirs(self.covers_dir, exist_ok=True)
        os.makedirs(self.avatars_dir, exist_ok=True)


# 全局实例
_config_instance = None


def get_config() -> Config:
    """获取配置管理器单例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
