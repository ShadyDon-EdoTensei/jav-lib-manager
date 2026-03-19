"""日志模块"""

import logging
import os
from datetime import datetime
from pathlib import Path


class Logger:
    """日志管理器"""

    def __init__(self, name: str = "javlibrary", log_dir: str = None):
        """
        初始化日志管理器

        Args:
            name: 日志名称
            log_dir: 日志目录，默认为 ~/.javlibrary/logs
        """
        if log_dir is None:
            log_dir = os.path.expanduser('~/.javlibrary/logs')

        os.makedirs(log_dir, exist_ok=True)

        # 创建logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 清除已有的处理器
        self.logger.handlers.clear()

        # 文件处理器
        log_file = os.path.join(log_dir, f"{name}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def debug(self, message: str):
        """调试日志"""
        self.logger.debug(message)

    def info(self, message: str):
        """信息日志"""
        self.logger.info(message)

    def warning(self, message: str):
        """警告日志"""
        self.logger.warning(message)

    def error(self, message: str):
        """错误日志"""
        self.logger.error(message)

    def critical(self, message: str):
        """严重错误日志"""
        self.logger.critical(message)


# 全局实例
_logger_instance = None


def get_logger() -> Logger:
    """获取日志管理器单例"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = Logger()
    return _logger_instance
