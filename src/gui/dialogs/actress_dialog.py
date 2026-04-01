"""女优头像浏览对话框"""

import os
import threading
import logging
from typing import Optional, List, Dict

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QLineEdit,
    QPushButton, QProgressBar, QMessageBox, QSplitter,
    QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QObject, QTimer
from PyQt6.QtGui import QPixmap, QImage

from core.avatar_downloader import AvatarDownloader

logger = logging.getLogger(__name__)


class DownloadAvatarThread(QThread):
    """头像批量下载线程"""
    progress = pyqtSignal(int, int, str, bool)  # current, total, name, success
    finished = pyqtSignal(int)  # downloaded count

    def __init__(self, downloader: AvatarDownloader):
        super().__init__()
        self.downloader = downloader

    error = pyqtSignal(str)  # 错误信息

    def run(self):
        try:
            def callback(current, total, name, success):
                self.progress.emit(current, total, name, success)

            results = self.downloader.download_missing_avatars(callback=callback)
            self.finished.emit(len(results))
        except Exception as e:
            self.error.emit(str(e))


class ActressDialog(QDialog):
    """女优头像浏览对话框 - 以卡片网格展示女优头像和信息"""

    actress_selected = pyqtSignal(str)  # 选中的女优名字

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("女优头像浏览")
        self.resize(1100, 750)
        self.setMinimumSize(900, 600)

        self.downloader = AvatarDownloader()
        self.download_thread: Optional[DownloadAvatarThread] = None
        self._all_actress_data: List[Dict] = []

        self._setup_ui()
        self._load_actresses()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 顶部操作栏
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索女优名字...")
        self.search_input.textChanged.connect(self._on_search)
        top_bar.addWidget(self.search_input, 1)

        # 只显示有头像
        self.filter_has_avatar = QPushButton("仅显示有头像")
        self.filter_has_avatar.setCheckable(True)
        self.filter_has_avatar.clicked.connect(self._apply_filter)
        top_bar.addWidget(self.filter_has_avatar)

        # 下载按钮
        self.download_btn = QPushButton("下载所有头像")
        self.download_btn.clicked.connect(self._download_all_avatars)
        top_bar.addWidget(self.download_btn)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)
        top_bar.addWidget(self.progress_bar)

        # 计数标签
        self.count_label = QLabel()
        top_bar.addWidget(self.count_label)

        layout.addLayout(top_bar)

        # 主内容：头像网格 + 右侧信息面板
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 女优列表
        self.actress_list = QListWidget()
        self.actress_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.actress_list.setIconSize(QSize(100, 100))
        self.actress_list.setGridSize(QSize(150, 170))
        self.actress_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.actress_list.setSpacing(8)
        self.actress_list.setItemAlignment(Qt.AlignmentFlag.AlignCenter)
        self.actress_list.setWordWrap(True)
        self.actress_list.itemClicked.connect(self._on_actress_clicked)
        self.actress_list.itemDoubleClicked.connect(self._on_actress_double_clicked)
        splitter.addWidget(self.actress_list)

        # 右侧详情面板
        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)
        detail_layout.setContentsMargins(10, 5, 10, 5)

        # 头像大图
        self.avatar_label = QLabel("选择女优查看头像")
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setMinimumSize(200, 200)
        self.avatar_label.setMaximumSize(300, 300)
        self.avatar_label.setStyleSheet("""
            QLabel {
                background-color: #222;
                border: 2px solid #444;
                border-radius: 8px;
            }
        """)
        detail_layout.addWidget(self.avatar_label)

        # 信息标签
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 13px; padding: 8px;")
        detail_layout.addWidget(self.info_label)

        # 查看作品按钮
        self.view_videos_btn = QPushButton("查看该女优作品")
        self.view_videos_btn.setVisible(False)
        self.view_videos_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF69B4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF1493;
            }
        """)
        self.view_videos_btn.clicked.connect(self._view_actress_videos)
        detail_layout.addWidget(self.view_videos_btn)

        detail_layout.addStretch()

        self.detail_widget.setMinimumWidth(250)
        self.detail_widget.setMaximumWidth(350)
        splitter.addWidget(self.detail_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        self.setLayout(layout)

    def _load_actresses(self):
        """加载女优列表"""
        self._all_actress_data = self.downloader.get_all_actress_info()
        self._populate_list(self._all_actress_data)

    def _populate_list(self, actresses: List[Dict]):
        """填充女优列表"""
        self.actress_list.clear()

        # 默认头像占位图
        default_pixmap = self._create_default_avatar()

        for actress in actresses:
            item = QListWidgetItem()
            name = actress['name']

            # 设置头像
            avatar_path = actress.get('avatar_path')
            if avatar_path and os.path.exists(avatar_path):
                pixmap = QPixmap(avatar_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    item.setIcon(QIcon(scaled))
                else:
                    item.setIcon(QIcon(default_pixmap))
            else:
                item.setIcon(QIcon(default_pixmap))

            # 显示文本：名字 + 罩杯
            cup = actress.get('cup')
            if cup:
                item.setText(f"{name}\n({cup} Cup)")
            else:
                item.setText(name)

            item.setData(Qt.ItemDataRole.UserRole, actress)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.actress_list.addItem(item)

        self.count_label.setText(f"共 {len(actresses)} 人")

    def _create_default_avatar(self) -> QPixmap:
        """创建默认头像占位图"""
        pixmap = QPixmap(100, 100)
        pixmap.fill(Qt.GlobalColor.darkGray)
        return pixmap

    def _on_search(self, text: str):
        self._apply_filter()

    def _apply_filter(self):
        """应用搜索和过滤"""
        keyword = self.search_input.text().strip().lower()
        only_with_avatar = self.filter_has_avatar.isChecked()

        filtered = []
        for actress in self._all_actress_data:
            if keyword and keyword not in actress['name'].lower():
                continue
            if only_with_avatar and not actress.get('avatar_path'):
                continue
            filtered.append(actress)

        self._populate_list(filtered)

    def _on_actress_clicked(self, item: QListWidgetItem):
        """单击显示详情"""
        actress = item.data(Qt.ItemDataRole.UserRole)
        if not actress:
            return

        name = actress['name']
        self.info_label.setText(f"")
        self.view_videos_btn.setVisible(False)

        # 显示头像大图
        avatar_path = actress.get('avatar_path')
        if avatar_path and os.path.exists(avatar_path):
            pixmap = QPixmap(avatar_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.avatar_label.setPixmap(scaled)
        else:
            self.avatar_label.clear()
            self.avatar_label.setText("无头像")

        # 显示信息
        info_parts = [f"<h3>{name}</h3>"]
        cup = actress.get('cup')
        if cup:
            info_parts.append(f"<p><b>罩杯:</b> {cup}</p>")
        height = actress.get('height')
        if height:
            info_parts.append(f"<p><b>身高:</b> {height} cm</p>")
        birth_year = actress.get('birth_year')
        if birth_year:
            info_parts.append(f"<p><b>出生年:</b> {birth_year}</p>")

        self.info_label.setText("".join(info_parts))
        self.view_videos_btn.setVisible(True)
        self._selected_actress = name

    def _on_actress_double_clicked(self, item: QListWidgetItem):
        """双击直接查看作品"""
        self._on_actress_clicked(item)
        self._view_actress_videos()

    def _view_actress_videos(self):
        """发送信号，在主窗口中查看该女优的作品"""
        if hasattr(self, '_selected_actress'):
            self.actress_selected.emit(self._selected_actress)
            self.accept()

    def _download_all_avatars(self):
        """批量下载所有缺失的头像"""
        self.download_btn.setEnabled(False)
        self.download_btn.setText("下载中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.download_thread = DownloadAvatarThread(self.downloader)
        self.download_thread.progress.connect(self._on_download_progress)
        self.download_thread.finished.connect(self._on_download_finished)
        self.download_thread.error.connect(self._on_download_error)
        self.download_thread.start()

    def _on_download_progress(self, current: int, total: int, name: str, success: bool):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        status = "OK" if success else "跳过"
        self.setWindowTitle(f"下载: {name} ({status}) {current}/{total}")

    def _on_download_error(self, error_msg: str):
        self.download_btn.setEnabled(True)
        self.download_btn.setText("下载所有头像")
        self.progress_bar.setVisible(False)
        self.setWindowTitle("女优头像浏览")
        QMessageBox.warning(self, "下载出错", f"下载过程中出错:\n{error_msg}")

    def _on_download_finished(self, count: int):
        self.download_btn.setEnabled(True)
        self.download_btn.setText("下载所有头像")
        self.progress_bar.setVisible(False)
        self.setWindowTitle("女优头像浏览")

        # 刷新列表
        self._load_actresses()
        self._apply_filter()

        QMessageBox.information(self, "完成", f"头像下载完成，共下载 {count} 个")

    def closeEvent(self, event):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.wait(3000)
        self.downloader.close()
        super().closeEvent(event)
