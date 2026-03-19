"""设置对话框"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QWidget, QLineEdit, QSpinBox, QCheckBox,
    QComboBox, QPushButton, QFileDialog, QGroupBox, QLabel,
    QScrollArea, QRadioButton, QButtonGroup, QGridLayout
)
from PyQt6.QtCore import Qt

from gui.themes.theme_manager import ThemeManager
import qtawesome


class BasicSettingsTab(QWidget):
    """基础设置标签页"""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout()

        # 数据库路径
        db_layout = QHBoxLayout()
        self.db_path_edit = QLineEdit(self.config.get('database_path', 'data/videos.db'))
        self.db_path_edit.setReadOnly(True)
        db_browse_btn = QPushButton("浏览...")
        try:
            db_browse_btn.setIcon(qtawesome.icon('fa5s.folder'))
        except:
            pass
        db_browse_btn.clicked.connect(self._browse_database)
        db_layout.addWidget(self.db_path_edit, 1)
        db_layout.addWidget(db_browse_btn)
        layout.addRow("数据库路径:", db_layout)

        # 封面目录
        cover_layout = QHBoxLayout()
        self.cover_dir_edit = QLineEdit(self.config.get('covers_dir', 'data/images/covers'))
        self.cover_dir_edit.setReadOnly(True)
        cover_browse_btn = QPushButton("浏览...")
        try:
            cover_browse_btn.setIcon(qtawesome.icon('fa5s.folder'))
        except:
            pass
        cover_browse_btn.clicked.connect(self._browse_cover_dir)
        cover_layout.addWidget(self.cover_dir_edit, 1)
        cover_layout.addWidget(cover_browse_btn)
        layout.addRow("封面目录:", cover_layout)

        # 递归扫描
        self.recursive_check = QCheckBox("递归扫描子目录")
        recursive_val = self.config.get('scan_recursive', True)
        self.recursive_check.setChecked(bool(recursive_val) if not isinstance(recursive_val, list) else True)
        layout.addRow("", self.recursive_check)

        # 支持的格式
        format_group = QGroupBox("支持的视频格式")
        format_layout = QGridLayout()

        self.mp4_check = QCheckBox("MP4")
        self.mp4_check.setChecked('.mp4' in self.config.get('video_formats', ['.mp4', '.mkv', '.avi']))

        self.mkv_check = QCheckBox("MKV")
        self.mkv_check.setChecked('.mkv' in self.config.get('video_formats', ['.mp4', '.mkv', '.avi']))

        self.avi_check = QCheckBox("AVI")
        self.avi_check.setChecked('.avi' in self.config.get('video_formats', ['.mp4', '.mkv', '.avi']))

        self.wmv_check = QCheckBox("WMV")
        self.wmv_check.setChecked('.wmv' in self.config.get('video_formats', []))

        self.flv_check = QCheckBox("FLV")
        self.flv_check.setChecked('.flv' in self.config.get('video_formats', []))

        format_layout.addWidget(self.mp4_check, 0, 0)
        format_layout.addWidget(self.mkv_check, 0, 1)
        format_layout.addWidget(self.avi_check, 0, 2)
        format_layout.addWidget(self.wmv_check, 1, 0)
        format_layout.addWidget(self.flv_check, 1, 1)

        format_group.setLayout(format_layout)
        layout.addRow(format_group)

        self.setLayout(layout)

    def _browse_database(self):
        """浏览数据库路径"""
        path, _ = QFileDialog.getSaveFileName(
            self, "选择数据库文件", self.db_path_edit.text(), "SQLite Database (*.db)"
        )
        if path:
            self.db_path_edit.setText(path)

    def _browse_cover_dir(self):
        """浏览封面目录"""
        path = QFileDialog.getExistingDirectory(
            self, "选择封面目录", self.cover_dir_edit.text()
        )
        if path:
            self.cover_dir_edit.setText(path)

    def get_settings(self):
        """获取设置"""
        formats = []
        if self.mp4_check.isChecked():
            formats.append('.mp4')
        if self.mkv_check.isChecked():
            formats.append('.mkv')
        if self.avi_check.isChecked():
            formats.append('.avi')
        if self.wmv_check.isChecked():
            formats.append('.wmv')
        if self.flv_check.isChecked():
            formats.append('.flv')

        return {
            'database_path': self.db_path_edit.text(),
            'covers_dir': self.cover_dir_edit.text(),
            'scan_recursive': self.recursive_check.isChecked(),
            'video_formats': formats,
        }


class ScraperSettingsTab(QWidget):
    """爬虫设置标签页"""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout()

        # JavDB URL
        self.javdb_url_edit = QLineEdit(
            self.config.get('javdb_url', 'https://javdb571.com')
        )
        layout.addRow("JavDB 镜像地址:", self.javdb_url_edit)

        # 超时时间
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        timeout_val = self.config.get('scraper_timeout', 30)
        self.timeout_spin.setValue(int(timeout_val) if not isinstance(timeout_val, list) else 30)
        self.timeout_spin.setSuffix(" 秒")
        layout.addRow("请求超时:", self.timeout_spin)

        # 重试次数
        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(0, 10)
        retries_val = self.config.get('scraper_retries', 3)
        self.retries_spin.setValue(int(retries_val) if not isinstance(retries_val, list) else 3)
        layout.addRow("重试次数:", self.retries_spin)

        # 请求延迟
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 10)
        delay_val = self.config.get('scraper_delay', 2)
        self.delay_spin.setValue(int(delay_val) if not isinstance(delay_val, list) else 2)
        self.delay_spin.setSuffix(" 秒")
        layout.addRow("请求延迟:", self.delay_spin)

        # 并发数
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        concurrent_val = self.config.get('scraper_concurrent', 3)
        self.concurrent_spin.setValue(int(concurrent_val) if not isinstance(concurrent_val, list) else 3)
        layout.addRow("并发请求数:", self.concurrent_spin)

        # 说明
        info_label = QLabel(
            "提示: 如果遇到反爬限制，可以增加请求延迟和减少并发数。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        layout.addRow("", info_label)

        self.setLayout(layout)

    def get_settings(self):
        """获取设置"""
        return {
            'javdb_url': self.javdb_url_edit.text(),
            'scraper_timeout': self.timeout_spin.value(),
            'scraper_retries': self.retries_spin.value(),
            'scraper_delay': self.delay_spin.value(),
            'scraper_concurrent': self.concurrent_spin.value(),
        }


class AppearanceSettingsTab(QWidget):
    """外观设置标签页"""

    def __init__(self, config, theme_manager):
        super().__init__()
        self.config = config
        self.theme_manager = theme_manager
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout()

        # 主题选择
        theme_group = QGroupBox("主题选择")
        theme_layout = QVBoxLayout()

        self.theme_group = QButtonGroup()
        self.theme_map = {}  # 索引 -> theme_id 映射

        # 创建主题按钮
        themes = [
            ('dark_amber', '深色琥珀', '#FFC107'),
            ('dark_blue', '深色蓝色', '#2196F3'),
            ('dark_cyan', '深色青色', '#00BCD4'),
            ('dark_lightgreen', '深色绿色', '#8BC34A'),
            ('dark_pink', '深色粉色', '#E91E63'),
            ('dark_purple', '深色紫色', '#9C27B0'),
            ('light_amber', '浅色琥珀', '#FFC107'),
            ('light_blue', '浅色蓝色', '#2196F3'),
            ('light_cyan', '浅色青色', '#00BCD4'),
        ]

        grid_layout = QGridLayout()
        row, col = 0, 0

        current_theme = self.config.get('theme', 'dark_amber')

        for idx, (theme_id, name, color) in enumerate(themes):
            radio = QRadioButton(name)
            if theme_id == current_theme:
                radio.setChecked(True)

            # 使用样式设置颜色指示
            radio.setStyleSheet(f"""
                QRadioButton {{
                    padding: 8px;
                    border: 2px solid #e0e0e0;
                    border-radius: 4px;
                    background-color: {color if theme_id.startswith('dark_') else '#ffffff'};
                    color: {'white' if theme_id.startswith('dark_') else 'black'};
                }}
                QRadioButton::indicator {{
                    width: 18px;
                    height: 18px;
                }}
            """)

            self.theme_group.addButton(radio)
            self.theme_group.setId(radio, idx)  # 使用整数索引
            self.theme_map[idx] = theme_id  # 保存映射

            grid_layout.addWidget(radio, row, col)

            col += 1
            if col >= 3:
                col = 0
                row += 1

        theme_layout.addLayout(grid_layout)
        theme_group.setLayout(theme_layout)
        layout.addRow(theme_group)

        # 缩略图大小
        self.thumb_size_spin = QSpinBox()
        self.thumb_size_spin.setRange(100, 400)
        thumb_val = self.config.get('thumb_size', 150)
        self.thumb_size_spin.setValue(int(thumb_val) if not isinstance(thumb_val, list) else 150)
        self.thumb_size_spin.setSuffix(" px")
        layout.addRow("缩略图大小:", self.thumb_size_spin)

        # 字体大小
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 16)
        font_val = self.config.get('font_size', 10)
        self.font_size_spin.setValue(int(font_val) if not isinstance(font_val, list) else 10)
        self.font_size_spin.setSuffix(" pt")
        layout.addRow("字体大小:", self.font_size_spin)

        self.setLayout(layout)

    def get_settings(self):
        """获取设置"""
        checked = self.theme_group.checkedButton()
        idx = self.theme_group.id(checked) if checked else 0
        theme_id = self.theme_map.get(idx, 'dark_amber')  # 通过映射获取主题ID

        return {
            'theme': theme_id,
            'thumb_size': self.thumb_size_spin.value(),
            'font_size': self.font_size_spin.value(),
        }


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, config, theme_manager, parent=None):
        super().__init__(parent)
        self.config = config
        self.theme_manager = theme_manager
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("设置")
        self.resize(600, 500)

        layout = QVBoxLayout()

        # 标签页
        self.tabs = QTabWidget()

        self.basic_tab = BasicSettingsTab(self.config)
        self.tabs.addTab(self.basic_tab, "基础设置")

        self.scraper_tab = ScraperSettingsTab(self.config)
        self.tabs.addTab(self.scraper_tab, "爬虫设置")

        self.appearance_tab = AppearanceSettingsTab(self.config, self.theme_manager)
        self.tabs.addTab(self.appearance_tab, "外观设置")

        layout.addWidget(self.tabs)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        try:
            cancel_btn.setIcon(qtawesome.icon('fa5s.times'))
        except:
            pass
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("保存")
        try:
            save_btn.setIcon(qtawesome.icon('fa5s.save'))
        except:
            pass
        save_btn.clicked.connect(self._save_settings)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _save_settings(self):
        """保存设置"""
        # 合并所有设置
        settings = {}
        settings.update(self.basic_tab.get_settings())
        settings.update(self.scraper_tab.get_settings())
        settings.update(self.appearance_tab.get_settings())

        # 保存到配置
        for key, value in settings.items():
            self.config.set(key, value)

        self.config.save()

        self.accept()
