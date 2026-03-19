"""JAV Lib Manager - 应用入口"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from gui.main_window import MainWindow
from gui.themes.theme_manager import ThemeManager
from utils.config import get_config
from utils.logger import get_logger


def main():
    """主函数"""
    # 初始化配置和日志
    config = get_config()
    config.ensure_directories()
    logger = get_logger()

    logger.info("=== 启动 JAV Lib Manager ===")

    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("JAV Lib Manager")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("JAVLibrary")

    # 设置全局字体
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)

    # 应用主题
    theme_manager = ThemeManager()
    theme = config.get('theme', 'dark_amber')
    theme_manager.apply_theme(app, theme)
    logger.info(f"应用主题: {theme}")

    # 创建主窗口
    window = MainWindow()
    window.show()

    logger.info("应用启动成功")

    # 运行应用
    exit_code = app.exec()

    logger.info(f"应用退出，退出码: {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
