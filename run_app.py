#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JAV Lib Manager - 应用入口
"""

import sys
import pathlib

# 添加 src 目录到 Python 路径
current_dir = pathlib.Path(__file__).parent.resolve()
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# 导入并启动应用
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow  # type: ignore
from gui.themes.theme_manager import ThemeManager  # type: ignore
from utils.config import get_config  # type: ignore
from utils.logger import get_logger  # type: ignore


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
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("JAVLibrary")

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
