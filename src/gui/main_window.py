"""主窗口 - PyQt6 GUI实现"""

import os
import logging
import platform
import threading
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QComboBox, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFileDialog,
    QProgressBar, QProgressDialog, QDialog, QMessageBox, QSplitter,
    QTextEdit, QMenuBar, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QObject, QTimer
from PyQt6.QtGui import QPixmap, QImage, QIcon, QCloseEvent

import qtawesome

from core.database import Database
from core.scanner import VideoScanner, VideoFile
from core.scraper import get_scraper
from core.models import VideoMetadata
from gui.themes.theme_manager import ThemeManager
from gui.dialogs.settings_dialog import SettingsDialog
from gui.dialogs.actress_dialog import ActressDialog
from utils.config import get_config
from utils.logger import get_logger


class ScanThread(QThread):
    """扫描线程"""
    progress = pyqtSignal(str, int, int)  # 当前路径, 当前数量, 总数
    finished = pyqtSignal(list)  # 扫描结果
    stopped = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, directory: str, recursive: bool = True):
        super().__init__()
        self.directory = directory
        self.recursive = recursive
        self._stop_event = threading.Event()
        self._was_stopped = False

    def request_stop(self):
        self._stop_event.set()

    def is_stop_requested(self) -> bool:
        return self._stop_event.is_set()

    def was_stopped(self) -> bool:
        return self._was_stopped

    def run(self):
        try:
            scanner = VideoScanner()
            results = scanner.scan_directory(
                self.directory,
                progress_callback=lambda p, c, t: self.progress.emit(p, c, t),
                recursive=self.recursive,
                should_stop=self.is_stop_requested
            )
            self._was_stopped = self.is_stop_requested()
            if self._was_stopped:
                self.stopped.emit()
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class FetchMetadataThread(QThread):
    """元数据获取线程"""
    progress = pyqtSignal(str, str)  # 番号, 状态
    metadata_fetched = pyqtSignal(str, object)  # 番号, 元数据 - 实时保存
    finished = pyqtSignal(dict)  # {code: metadata}
    stopped = pyqtSignal()
    error = pyqtSignal(str, str)  # code, error

    def __init__(self, codes: list[str]):
        super().__init__()
        self.codes = codes
        self._stop_event = threading.Event()
        self._was_stopped = False

    def request_stop(self):
        self._stop_event.set()

    def is_stop_requested(self) -> bool:
        return self._stop_event.is_set()

    def was_stopped(self) -> bool:
        return self._was_stopped

    def run(self):
        scraper = get_scraper()
        results = {}
        for code in self.codes:
            if self.is_stop_requested():
                self._was_stopped = True
                self.stopped.emit()
                break
            try:
                self.progress.emit(code, "正在获取...")
                metadata = scraper.fetch(code)
                if metadata:
                    results[code] = metadata
                    self.metadata_fetched.emit(code, metadata)  # 实时发送
                    self.progress.emit(code, "完成")
                else:
                    self.progress.emit(code, "未找到")
            except Exception as e:
                self.error.emit(code, str(e))
        if self.is_stop_requested():
            self._was_stopped = True
        self.finished.emit(results)


class CoverViewerDialog(QDialog):
    """封面大图查看对话框"""

    def __init__(self, cover_path: str, video_id: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"封面 - {video_id}")
        self.setModal(False)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        pixmap = QPixmap(cover_path)
        label = QLabel()
        # 按屏幕大小缩放，最大 900x700
        screen = QApplication.primaryScreen().availableGeometry()
        max_w = min(900, screen.width() - 100)
        max_h = min(700, screen.height() - 100)
        scaled = pixmap.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(scaled)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.mousePressEvent = lambda e: self.close()
        layout.addWidget(label)

        self.setLayout(layout)
        self.adjustSize()


class ScanProgressDialog(QDialog):
    """扫描进度对话框"""
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("扫描视频文件")
        self.setFixedSize(500, 200)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # 状态标签
        self.status_label = QLabel("正在扫描...")
        layout.addWidget(self.status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # 统计标签
        self.stats_label = QLabel()
        layout.addWidget(self.stats_label)

        # 按钮
        btn_layout = QHBoxLayout()
        self.bg_button = QPushButton("后台运行")
        self.bg_button.clicked.connect(self.hide)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        btn_layout.addStretch()
        btn_layout.addWidget(self.bg_button)
        btn_layout.addWidget(self.cancel_button)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def update_progress(self, path: str, current: int, total: int):
        """更新进度"""
        self.status_label.setText(f"正在扫描: {os.path.basename(path)}")
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def update_stats(self, total: int, parsed: int):
        """更新统计"""
        self.stats_label.setText(f"已发现: {total} 个文件\n已识别番号: {parsed} 个")

    def _on_cancel_clicked(self):
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("正在停止...")
        self.stop_requested.emit()


class LogWindow(QDialog):
    """实时日志显示窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("运行日志")
        self.resize(900, 600)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("QTextEdit { font-family: Consolas, monospace; font-size: 10pt; }")
        layout.addWidget(self.log_text)

        # 清除按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        clear_button = QPushButton("清除日志")
        clear_button.clicked.connect(self.log_text.clear)
        btn_layout.addWidget(clear_button)
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.hide)
        btn_layout.addWidget(close_button)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def append(self, message: str):
        """添加日志消息"""
        self.log_text.append(message)
        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.config.ensure_directories()
        self.logger = get_logger()

        # 初始化主题管理器
        self.theme_manager = ThemeManager()

        # 初始化数据库
        self.db = Database(self.config.database_path)

        # 扫描结果
        self.scan_results: list[VideoFile] = []
        self.metadata_results: dict[str, VideoMetadata] = {}
        self.scan_thread: Optional[ScanThread] = None
        self.fetch_thread: Optional[FetchMetadataThread] = None
        self._active_qthreads: set[QThread] = set()
        self._current_fetch_mode: str = "scan"
        self._current_fetch_codes: list[str] = []

        # 创建日志窗口
        self.log_window = LogWindow(self)

        self._setup_ui()
        self._setup_menu_bar()
        self._setup_logger_handler()
        self._load_initial_data()

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("🎀 JAV Lib Manager")
        self.resize(
            self.config.get('window_width', 1600),
            self.config.get('window_height', 1000)
        )
        self.setMinimumSize(1200, 800)

        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 5, 10, 10)
        central.setLayout(main_layout)

        # 工具栏
        toolbar_widget = self._create_toolbar()
        main_layout.addWidget(toolbar_widget)

        # 搜索和过滤面板
        search_widget = self._create_search_panel()
        main_layout.addWidget(search_widget)

        # 分割器：视频列表 + 详情面板
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 视频列表（两列布局）
        self.video_list = QListWidget()
        self.video_list.setIconSize(QSize(160, 220))  # 图标大小（稍小以显示更多）
        self.video_list.setViewMode(QListWidget.ViewMode.IconMode)  # 图标模式
        self.video_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.video_list.setSpacing(15)
        self.video_list.setGridSize(QSize(480, 260))  # 固定两列（稍紧凑）
        self.video_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.video_list.itemClicked.connect(self._on_video_selected)
        splitter.addWidget(self.video_list)

        # 详情面板（改为支持按钮的容器）
        self.detail_container = QWidget()
        detail_layout = QVBoxLayout(self.detail_container)
        detail_layout.setContentsMargins(5, 5, 5, 5)

        # 封面图（可点击查看大图）
        self.cover_label = QLabel("选择视频后显示封面")
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setMinimumHeight(200)
        self.cover_label.mousePressEvent = self._on_cover_clicked
        detail_layout.addWidget(self.cover_label)

        self.detail_panel = QLabel()
        self.detail_panel.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.detail_panel.setWordWrap(True)
        self.detail_panel.linkActivated.connect(self._on_detail_link_clicked)
        detail_layout.addWidget(self.detail_panel)

        # 播放按钮（初始隐藏）
        self.play_button = QPushButton("🎬 播放视频")
        self.play_button.setVisible(False)
        self.play_button.clicked.connect(self._play_selected_video)
        detail_layout.addWidget(self.play_button)

        # 重新定位按钮（初始隐藏）
        self.relocate_button = QPushButton("📂 重新定位")
        self.relocate_button.setVisible(False)
        self.relocate_button.setToolTip("视频文件已移动？点此重新选择路径")
        self.relocate_button.clicked.connect(self._relocate_current_video)
        detail_layout.addWidget(self.relocate_button)

        detail_layout.addStretch()

        self.detail_container.setMinimumWidth(300)
        splitter.addWidget(self.detail_container)

        splitter.setStretchFactor(0, 5)  # 视频列表占更多空间
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter, 1)  # 添加拉伸因子，让视频列表区域占据剩余空间

        # 状态栏
        self.statusBar().showMessage("就绪")

    def _create_title_bar(self):
        """创建标题栏"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("JAV Lib Manager")
        title.setStyleSheet("""
            QLabel {
                font-size: 18pt;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px;
            }
        """)

        layout.addWidget(title)
        layout.addStretch()

        widget.setLayout(layout)
        return widget

    def _create_toolbar(self):
        """创建工具栏"""
        widget = QWidget()
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 4)
        outer_layout.setSpacing(4)

        # === 第一行：Logo + 核心操作 ===
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        # Logo标签 - 粉色艺术字体
        logo_label = QLabel("🎀 JAV Lib Manager")
        logo_label.setStyleSheet("""
            QLabel {
                font-family: "Segoe UI", "Microsoft YaHei UI", "Arial Black", sans-serif;
                font-size: 22px;
                font-weight: 900;
                font-style: italic;
                color: #FF1493;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #FFB6C1, stop:0.5 #FFC0CB, stop:1 #FFB6C1);
                padding: 8px 18px;
                border-radius: 10px;
                border: 2px solid #FF69B4;
            }
        """)
        logo_label.setToolTip("🎀 JAV Lib Manager - 您的个人视频收藏管理工具")
        row1.addWidget(logo_label)

        # 分隔线
        sep1 = QLabel("│")
        sep1.setStyleSheet("color: #FFB6C1; font-size: 16px; padding: 0 3px;")
        row1.addWidget(sep1)

        # 扫描按钮
        self.scan_button = QPushButton("扫描")
        try:
            self.scan_button.setIcon(qtawesome.icon('fa5s.folder'))
        except:
            pass
        self.scan_button.clicked.connect(self._scan_directory)

        # 刷新按钮
        self.refresh_button = QPushButton("刷新")
        try:
            self.refresh_button.setIcon(qtawesome.icon('fa5s.sync'))
        except:
            pass
        self.refresh_button.clicked.connect(self._load_initial_data)

        # 统计按钮
        self.stats_button = QPushButton("统计")
        try:
            self.stats_button.setIcon(qtawesome.icon('fa5s.chart-bar'))
        except:
            pass
        self.stats_button.clicked.connect(self._show_database_stats)

        # 日志按钮
        self.log_button = QPushButton("日志")
        try:
            self.log_button.setIcon(qtawesome.icon('fa5s.list'))
        except:
            pass
        self.log_button.clicked.connect(self.log_window.show)

        # 设置按钮
        self.settings_button = QPushButton("设置")
        try:
            self.settings_button.setIcon(qtawesome.icon('fa5s.cog'))
        except:
            pass
        self.settings_button.clicked.connect(self._show_settings)

        row1.addWidget(self.scan_button)
        row1.addWidget(self.refresh_button)
        row1.addWidget(self.stats_button)
        row1.addWidget(self.log_button)
        row1.addStretch()
        row1.addWidget(self.settings_button)

        outer_layout.addLayout(row1)

        # === 第二行：工具操作 ===
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        # 停止任务按钮
        self.stop_button = QPushButton("停止任务")
        self.stop_button.clicked.connect(self._stop_current_task)

        # 补全发行日期按钮
        self.backfill_release_date_button = QPushButton("补全发行日期")
        self.backfill_release_date_button.setToolTip("仅补全 release_date 为空的历史记录")
        self.backfill_release_date_button.clicked.connect(self._backfill_missing_release_dates)

        # 修复元数据按钮
        self.repair_metadata_button = QPushButton("修复元数据")
        self.repair_metadata_button.setToolTip("批量修复标题占位、封面缺失、演员缺失等异常记录")
        self.repair_metadata_button.clicked.connect(self._repair_incomplete_metadata)

        # 重新下载封面按钮
        self.retry_covers_button = QPushButton("重新下载封面")
        self.retry_covers_button.setToolTip("为没有封面的视频重新下载封面")
        self.retry_covers_button.clicked.connect(self._retry_download_covers)

        # 女优头像按钮
        self.actress_avatar_button = QPushButton("女优头像")
        try:
            self.actress_avatar_button.setIcon(qtawesome.icon('fa5s.user-circle'))
        except:
            pass
        self.actress_avatar_button.setToolTip("浏览女优头像和资料")
        self.actress_avatar_button.clicked.connect(self._show_actress_dialog)

        # 批量重定位按钮
        self.batch_relocate_button = QPushButton("批量重定位")
        self.batch_relocate_button.setToolTip("批量重定位路径失效的视频文件")
        self.batch_relocate_button.clicked.connect(self._batch_relocate_videos)

        # 删除按钮
        self.delete_button = QPushButton("删除选中")
        self.delete_button.setToolTip("删除选中的视频记录（不会删除本地文件）")
        self.delete_button.clicked.connect(self._delete_selected_videos)

        row2.addWidget(self.stop_button)
        row2.addWidget(self.backfill_release_date_button)
        row2.addWidget(self.repair_metadata_button)
        row2.addWidget(self.retry_covers_button)
        row2.addWidget(self.actress_avatar_button)
        row2.addWidget(self.batch_relocate_button)
        row2.addStretch()
        row2.addWidget(self.delete_button)

        outer_layout.addLayout(row2)

        widget.setLayout(outer_layout)
        return widget

    def _create_search_panel(self):
        """创建搜索面板"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)

        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        try:
            search_label.setIcon(qtawesome.icon('fa5s.search'))
        except:
            pass
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入番号、标题或演员名...")
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input, 1)

        layout.addLayout(search_layout)

        # 过滤器 - 单行布局
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        # 演员过滤
        filter_layout.addWidget(QLabel("演员:"))
        self.actress_combo = QComboBox()
        self.actress_combo.addItem("全部演员")
        self.actress_combo.setMinimumWidth(120)
        self.actress_combo.currentTextChanged.connect(self._on_search)
        filter_layout.addWidget(self.actress_combo)

        # 类型过滤
        filter_layout.addWidget(QLabel("类型:"))
        self.tag_combo = QComboBox()
        self.tag_combo.addItem("全部类型")
        self.tag_combo.setMinimumWidth(120)
        self.tag_combo.currentTextChanged.connect(self._on_search)
        filter_layout.addWidget(self.tag_combo)

        # 片商过滤
        filter_layout.addWidget(QLabel("片商:"))
        self.studio_combo = QComboBox()
        self.studio_combo.addItem("全部片商")
        self.studio_combo.setMinimumWidth(120)
        self.studio_combo.currentTextChanged.connect(self._on_search)
        filter_layout.addWidget(self.studio_combo)

        # 系列过滤
        filter_layout.addWidget(QLabel("系列:"))
        self.series_combo = QComboBox()
        self.series_combo.addItem("全部系列")
        self.series_combo.setMinimumWidth(120)
        self.series_combo.currentTextChanged.connect(self._on_search)
        filter_layout.addWidget(self.series_combo)

        # 排序下拉框
        filter_layout.addWidget(QLabel("排序:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["发行日期↓", "发行日期↑", "添加时间↓", "添加时间↑", "番号A-Z", "番号Z-A"])
        self.sort_combo.setMinimumWidth(120)
        self.sort_combo.currentTextChanged.connect(self._on_search)
        filter_layout.addWidget(self.sort_combo)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)
        widget.setLayout(layout)
        return widget

    def _setup_menu_bar(self):
        """设置菜单栏"""
        menubar = self.menuBar()

        # 查看菜单
        view_menu = menubar.addMenu("查看(&V)")
        view_menu.addAction("运行日志(&L)", self.log_window.show)
        view_menu.addSeparator()
        view_menu.addAction("刷新(&R)", self._load_initial_data)

        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")
        tools_menu.addAction("停止任务(&S)", self._stop_current_task)
        tools_menu.addAction("补全发行日期(&F)", self._backfill_missing_release_dates)
        tools_menu.addAction("修复不完整元数据(&M)", self._repair_incomplete_metadata)
        tools_menu.addSeparator()
        tools_menu.addAction("数据库统计(&D)", self._show_database_stats)
        tools_menu.addAction("清空数据库(&C)", self._clear_database)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction("关于(&A)", self._show_about)

    def _setup_logger_handler(self):
        """设置日志处理器，将日志输出到GUI窗口"""
        class LogEmitter(QObject):
            log_signal = pyqtSignal(str)

        emitter = LogEmitter()
        emitter.log_signal.connect(self.log_window.append)

        class GUILogHandler(logging.Handler):
            """自定义日志处理器，将日志发送到GUI"""
            def emit(self, record):
                try:
                    msg = self.format(record)
                    emitter.log_signal.emit(msg)
                except Exception:
                    pass

        # 创建处理器
        handler = GUILogHandler()
        handler.setFormatter(logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        ))

        # 添加到根日志记录器
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

        # 同时输出到控制台
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '[%(levelname)s] %(message)s'
        ))
        root_logger.addHandler(console_handler)

    def _register_thread(self, thread: QThread):
        """注册线程，确保线程结束后从活动列表移除。"""
        self._active_qthreads.add(thread)

        def _cleanup():
            self._active_qthreads.discard(thread)
            if thread is self.scan_thread:
                self.scan_thread = None
            if thread is self.fetch_thread:
                self.fetch_thread = None

        thread.finished.connect(_cleanup)

    def _stop_all_threads(self):
        """请求停止并等待所有活动线程结束。"""
        for thread in list(self._active_qthreads):
            if hasattr(thread, "request_stop"):
                try:
                    thread.request_stop()
                except Exception:
                    pass
        for thread in list(self._active_qthreads):
            try:
                thread.wait(5000)
            except Exception:
                pass

    def closeEvent(self, event: QCloseEvent):
        """窗口关闭时优雅停止后台线程，避免 QThread 销毁错误。"""
        self._stop_all_threads()
        try:
            scraper = get_scraper()
            if hasattr(scraper, "close"):
                scraper.close()
        except Exception as e:
            self.logger.warning(f"关闭爬虫管理器失败: {e}")
        super().closeEvent(event)

    def _stop_current_task(self):
        """停止当前扫描或抓取任务。"""
        stopped_any = False
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.request_stop()
            stopped_any = True
        if self.fetch_thread and self.fetch_thread.isRunning():
            self.fetch_thread.request_stop()
            stopped_any = True

        if stopped_any:
            self.statusBar().showMessage("正在停止任务...")
        else:
            self.statusBar().showMessage("当前没有正在运行的任务")

    def _backfill_missing_release_dates(self):
        """补全历史缺失发行日期（仅空值）。"""
        missing_codes = self.db.get_videos_missing_release_date(limit=10000)
        if not missing_codes:
            QMessageBox.information(self, "提示", "没有缺失发行日期的视频")
            return

        reply = QMessageBox.question(
            self,
            "补全发行日期",
            f"找到 {len(missing_codes)} 个缺失发行日期的视频。\n\n是否开始补全？（仅更新空值）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._fetch_metadata(missing_codes, mode="backfill_release_date")

    def _repair_incomplete_metadata(self):
        """批量修复不完整或疑似假命中的元数据。"""
        codes = self.db.get_videos_needing_metadata_refresh(limit=10000)
        if not codes:
            QMessageBox.information(self, "提示", "没有需要修复的元数据记录")
            return

        reply = QMessageBox.question(
            self,
            "修复元数据",
            f"找到 {len(codes)} 条疑似不完整的记录。\n\n是否开始批量修复？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._fetch_metadata(codes, mode="repair_metadata")

    def _on_backfill_release_date_single(self, code: str, metadata):
        """补全模式下单条处理：仅更新缺失发行日期。"""
        if not metadata or not metadata.release_date:
            return
        updated = self.db.update_release_date_if_missing(code, metadata.release_date)
        if updated:
            self.logger.info(f"已补全发行日期: {code} -> {metadata.release_date}")

    def _on_repair_metadata_single(self, code: str, metadata):
        """修复模式下单条处理：更新现有记录并补下封面。"""
        if not metadata:
            return

        updated = self.db.update_video_metadata(code, metadata)
        if updated:
            self.logger.info(f"已修复元数据: {code}")

        current_video = self.db.get_video(code)
        needs_cover = current_video and (not current_video.cover_path or not os.path.exists(current_video.cover_path))
        if needs_cover and metadata.cover_url:
            self._download_single_cover(code, metadata.cover_url)

    def _show_database_stats(self):
        """显示数据库统计"""
        try:
            stats = self.db.get_stats()
            issues = self.db.validate()
            issues_text = "\n".join(issues) if issues else "无问题"

            msg = f"""数据库统计:

• 视频总数: {stats.get('total_videos', 0)}
• 有封面: {stats.get('with_cover', 0)}
• 演员总数: {stats.get('total_actresses', 0)}
• 标签总数: {stats.get('total_tags', 0)}

数据完整性:
{issues_text}"""
            QMessageBox.information(self, "数据库状态", msg)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取数据库统计失败: {e}")

    def _clear_database(self):
        """清空数据库"""
        reply = QMessageBox.question(
            self,
            "确认清空",
            "确定要清空所有数据吗？此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.clear_all()
                self._load_initial_data()
                QMessageBox.information(self, "完成", "数据库已清空")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"清空失败: {e}")

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于",
            "JAV Lib Manager v1.0\n\n"
            "本地视频管理工具\n"
            "用于整理和检索个人视频收藏"
        )

    def _load_initial_data(self):
        """加载初始数据"""
        # 清空并加载演员列表
        self.actress_combo.clear()
        self.actress_combo.addItem("全部演员")
        actresses = self.db.get_all_actresses()
        self.actress_combo.addItems(actresses)

        # 清空并加载标签列表
        self.tag_combo.clear()
        self.tag_combo.addItem("全部类型")
        tags = self.db.get_all_tags()
        self.tag_combo.addItems(tags)

        # 清空并加载片商列表
        self.studio_combo.clear()
        self.studio_combo.addItem("全部片商")
        studios = self.db.get_all_studios()
        self.studio_combo.addItems(studios)

        # 清空并加载系列列表
        self.series_combo.clear()
        self.series_combo.addItem("全部系列")
        series = self.db.get_all_series()
        self.series_combo.addItems(series)

        # 显示所有视频
        self._refresh_video_list()

    def _refresh_video_list(self, keyword: str = None):
        """刷新视频列表"""
        # 获取过滤条件
        actress = None if self.actress_combo.currentText() == "全部演员" else self.actress_combo.currentText()
        tag = None if self.tag_combo.currentText() == "全部类型" else self.tag_combo.currentText()
        studio = None if self.studio_combo.currentText() == "全部片商" else self.studio_combo.currentText()
        series = None if self.series_combo.currentText() == "全部系列" else self.series_combo.currentText()

        # 解析排序选项
        sort_text = self.sort_combo.currentText()
        if "发行日期↓" in sort_text:
            sort_by, sort_order = "release_date", "DESC"
        elif "发行日期↑" in sort_text:
            sort_by, sort_order = "release_date", "ASC"
        elif "添加时间↓" in sort_text:
            sort_by, sort_order = "created_at", "DESC"
        elif "添加时间↑" in sort_text:
            sort_by, sort_order = "created_at", "ASC"
        elif "番号A-Z" in sort_text:
            sort_by, sort_order = "id", "ASC"
        elif "番号Z-A" in sort_text:
            sort_by, sort_order = "id", "DESC"
        else:
            sort_by, sort_order = "release_date", "DESC"

        # 搜索
        results = self.db.search(
            keyword=keyword,
            actress=actress,
            tag=tag,
            studio=studio,
            series=series,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=500
        )

        # 更新列表
        self.video_list.clear()

        for video in results:
            # 创建自定义Widget作为列表项
            item_widget = QWidget()
            layout = QHBoxLayout(item_widget)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(10)

            # 封面标签（完整显示）
            cover_label = QLabel()
            cover_label.setFixedSize(180, 240)  # 更大的尺寸，保持3:4比例
            cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cover_label.setScaledContents(False)  # 不拉伸，保持原始比例

            # 尝试加载封面
            if video.cover_path and os.path.exists(video.cover_path):
                try:
                    pixmap = QPixmap(video.cover_path)
                    if not pixmap.isNull():
                        # 保持完整比例缩放到容器大小
                        scaled_pixmap = pixmap.scaled(
                            180, 240,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        cover_label.setPixmap(scaled_pixmap)
                    else:
                        self.logger.warning(f"QPixmap isNull: {video.cover_path}")
                        cover_label.setText("加载失败")
                except Exception as e:
                    self.logger.error(f"加载封面失败 {video.id}: {e}")
                    cover_label.setText("加载失败")
            else:
                if not video.cover_path:
                    self.logger.debug(f"无封面路径: {video.id}")
                elif not os.path.exists(video.cover_path):
                    self.logger.warning(f"封面文件不存在: {video.cover_path}")
                cover_label.setText("无封面")
            cover_label.setStyleSheet("border: 1px solid #ccc; background-color: #222;")

            layout.addWidget(cover_label)

            # 信息标签（多行文本）
            actresses_str = ", ".join([a.name for a in video.actresses[:5]])
            info_text = f"""<b style='font-size: 14px;'>{video.id}</b>
<br><span style='font-size: 12px;'>{video.title}</span>
<br><span style='color: #666; font-size: 12px;'>{actresses_str}</span>"""

            info_label = QLabel(info_text)
            info_label.setWordWrap(True)
            info_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(info_label, 1)  # stretch=1 占据剩余空间

            # 创建列表项并设置Widget
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, video.id)
            item.setSizeHint(QSize(480, 270))  # 固定大小

            self.video_list.addItem(item)
            self.video_list.setItemWidget(item, item_widget)

        self.statusBar().showMessage(f"共 {len(results)} 个视频")

    def _scan_directory(self):
        """扫描目录"""
        if self.scan_thread and self.scan_thread.isRunning():
            QMessageBox.information(self, "提示", "扫描任务正在运行，请先停止当前任务")
            return

        # 选择目录
        last_dir = self.config.get('last_scan_dir', '')
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择视频目录",
            last_dir
        )

        if not directory:
            return

        # 保存目录
        self.config.set('last_scan_dir', directory)

        # 显示进度对话框
        progress_dialog = ScanProgressDialog(self)
        progress_dialog.stop_requested.connect(self._stop_current_task)
        progress_dialog.show()

        # 创建扫描线程
        self.scan_thread = ScanThread(directory, recursive=self.config.get('scan_recursive', True))
        self._register_thread(self.scan_thread)
        self.scan_thread.progress.connect(progress_dialog.update_progress)
        self.scan_thread.stopped.connect(lambda: self.statusBar().showMessage("扫描已停止"))
        self.scan_thread.finished.connect(lambda results, t=self.scan_thread: self._on_scan_finished(results, progress_dialog, t))
        self.scan_thread.error.connect(lambda error: QMessageBox.critical(self, "扫描失败", error))
        self.scan_thread.start()

    def _on_scan_finished(self, results: list[VideoFile], dialog: ScanProgressDialog, thread: Optional[ScanThread] = None):
        """扫描完成"""
        self.scan_results = results
        parsed = [r for r in results if r.code]

        dialog.update_stats(len(results), len(parsed))
        was_stopped = bool(thread and thread.was_stopped())
        dialog.status_label.setText("已停止" if was_stopped else "扫描完成！")

        if was_stopped:
            dialog.accept()
            self._refresh_video_list()
            self.statusBar().showMessage(f"扫描已停止，已处理 {len(results)} 个文件")
            return

        # 检查哪些已存在于数据库
        existing_codes = []
        new_codes = []
        for vf in parsed:
            if self.db.exists(vf.code):
                existing_codes.append(vf.code)
            else:
                new_codes.append(vf.code)

        total = len(parsed)
        existing = len(existing_codes)
        new = len(new_codes)

        # 根据情况显示不同对话框
        if existing == 0:
            # 全是新视频
            reply = QMessageBox.question(
                self,
                "扫描完成",
                f"发现 {total} 个视频文件\n识别到 {total} 个番号\n全部为新视频\n\n是否获取元数据？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                dialog.accept()
                self._fetch_metadata([r.code for r in parsed if r.code])
            else:
                dialog.accept()

        elif new == 0:
            # 全部已存在
            QMessageBox.information(
                self,
                "扫描完成",
                f"发现 {total} 个视频文件\n识别到 {total} 个番号\n全部已在数据库中\n\n无需重复获取元数据"
            )
            dialog.accept()

        else:
            # 部分已存在，部分是新视频
            msg = f"""扫描完成！
发现 {total} 个视频文件
识别到 {total} 个番号

已在数据库: {existing} 个
新视频: {new} 个

请选择:"""

            reply = QMessageBox.question(
                self,
                "扫描完成",
                f"{msg}\n\n点击「是」只扫描新视频\n点击「否」扫描全部",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 只扫描新视频
                dialog.accept()
                self._fetch_metadata(new_codes)
            else:
                # 扫描全部
                dialog.accept()
                self._fetch_metadata([r.code for r in parsed if r.code])

    def _fetch_metadata(self, codes: list[str], mode: str = "scan"):
        """获取元数据"""
        if not codes:
            QMessageBox.information(self, "提示", "没有需要获取元数据的番号")
            return
        if self.fetch_thread and self.fetch_thread.isRunning():
            QMessageBox.information(self, "提示", "元数据抓取任务正在运行，请先停止当前任务")
            return

        # 显示进度
        self.statusBar().showMessage(f"正在获取 {len(codes)} 个视频的元数据...")
        self._current_fetch_mode = mode
        self._current_fetch_codes = list(codes)

        # 创建获取线程
        self.fetch_thread = FetchMetadataThread(codes)
        self._register_thread(self.fetch_thread)
        self.fetch_thread.progress.connect(lambda code, status: self.statusBar().showMessage(f"{code}: {status}"))
        if mode == "backfill_release_date":
            self.fetch_thread.metadata_fetched.connect(self._on_backfill_release_date_single)
        elif mode == "repair_metadata":
            self.fetch_thread.metadata_fetched.connect(self._on_repair_metadata_single)
        else:
            self.fetch_thread.metadata_fetched.connect(self._on_single_metadata)  # 实时保存
        self.fetch_thread.stopped.connect(lambda: self.statusBar().showMessage("元数据抓取已停止"))
        self.fetch_thread.finished.connect(lambda results, t=self.fetch_thread: self._on_metadata_finished(results, t))
        self.fetch_thread.error.connect(lambda code, error: self.logger.error(f"获取 {code} 元数据失败: {error}"))
        self.fetch_thread.start()

    def _on_single_metadata(self, code: str, metadata):
        """单个视频元数据获取完成 - 实时保存并立刻下载封面"""
        vf = next((v for v in self.scan_results if v.code == code), None)
        if vf:
            self.db.add_video(metadata, vf.path, vf.size)
            self.logger.info(f"已保存: {code}")
            # 立刻在后台下载封面，下载完成后刷新列表
            if metadata.cover_url:
                self._download_single_cover(code, metadata.cover_url)

    def _on_metadata_finished(self, results: dict[str, VideoMetadata], thread: Optional[FetchMetadataThread] = None):
        """元数据获取完成 - 处理未找到的"""
        mode = self._current_fetch_mode
        was_stopped = bool(thread and thread.was_stopped())

        if mode == "backfill_release_date":
            self._refresh_video_list()
            status_msg = (
                f"发行日期补全已停止，已处理 {len(results)}/{len(self._current_fetch_codes)}"
                if was_stopped
                else f"发行日期补全完成，已处理 {len(results)} 条"
            )
            self.statusBar().showMessage(status_msg)
            return

        if mode == "repair_metadata":
            self._refresh_video_list()
            status_msg = (
                f"元数据修复已停止，已处理 {len(results)}/{len(self._current_fetch_codes)}"
                if was_stopped
                else f"元数据修复完成，已处理 {len(results)} 条"
            )
            self.statusBar().showMessage(status_msg)
            return

        if was_stopped:
            self._refresh_video_list()
            self.statusBar().showMessage(f"元数据抓取已停止，已处理 {len(results)}/{len(self._current_fetch_codes)}")
            return

        self.logger.info(f"=== _on_metadata_finished 被调用，results 大小: {len(results)} ===")
        not_found = []

        # 处理未找到元数据的视频
        for vf in self.scan_results:
            if not vf.code:
                continue
            code = vf.code

            # 未找到元数据，创建基本信息记录
            if code not in results and not self.db.exists(code):
                from core.models import VideoMetadata, SourceType
                basic_metadata = VideoMetadata(
                    id=code,
                    title=code,
                    cover_url=None,
                    actresses=[],
                    studio=None,
                    label=None,
                    series=None,
                    genres=[],
                    release_date=None,
                    duration=None,
                    source=SourceType.JAVDB
                )
                self.db.add_video(basic_metadata, vf.path, vf.size)
                not_found.append(code)

        if not_found:
            self.logger.info(f"以下番号未找到元数据，仅保存基本信息: {', '.join(not_found)}")

        # 批量下载封面（后台执行）
        self.logger.info(f"DEBUG: results 字典大小: {len(results)}")
        for k, v in list(results.items())[:3]:
            self.logger.info(f"DEBUG: {k} -> cover_url={v.cover_url}")
        covers_to_download = {k: v.cover_url for k, v in results.items() if v.cover_url}
        self.logger.info(f"DEBUG: covers_to_download 大小: {len(covers_to_download)}")
        if covers_to_download:
            self.logger.info(f"开始下载 {len(covers_to_download)} 个封面")
            self._download_covers(covers_to_download)
        else:
            self.logger.warning("没有需要下载的封面（所有视频的 cover_url 都为空）")

        # 立即刷新列表（不管有没有封面下载）
        # 封面下载完成后会再次刷新更新封面图
        self._refresh_video_list()
        self.statusBar().showMessage(f"元数据获取完成，共 {len(results)} 个视频")

    def _on_search(self):
        """搜索"""
        keyword = self.search_input.text().strip() or None
        self._refresh_video_list(keyword)

    def _on_video_selected(self, item: QListWidgetItem):
        """视频选中"""
        code = item.data(Qt.ItemDataRole.UserRole)
        video = self.db.get_video(code)

        if video:
            # 保存当前视频ID和路径供播放/重定位使用
            self.current_video_id = video.id
            self.current_video_path = video.file_path

            # 构建详情HTML
            tags_str = ", ".join(video.tags) if video.tags else "无"

            # 演员名带可点击链接 + 头像小图标
            from core.avatar_downloader import AvatarDownloader
            _av_dl = AvatarDownloader()
            actress_parts = []
            for a in video.actresses:
                avatar_path = self.db.get_actress_avatar(a.name)
                if avatar_path and os.path.exists(avatar_path):
                    # 用本地文件路径显示头像缩略图
                    actress_parts.append(
                        f'<img src="{avatar_path}" width="28" height="28" style="vertical-align:middle; border-radius:14px;"> '
                        f'<a href="actress:{a.name}" style="color:#FF69B4;text-decoration:none;">{a.name}</a>'
                    )
                else:
                    actress_parts.append(
                        f'<a href="actress:{a.name}" style="color:#FF69B4;text-decoration:none;">{a.name}</a>'
                    )
            _av_dl.close()
            actresses_html = "&nbsp;&nbsp;".join(actress_parts) if actress_parts else "未知"

            detail_html = f"""
            <h2>{video.id}</h2>
            <h3>{video.title}</h3>
            <p><b>演员:</b><br>{actresses_html}</p>
            <p><b>片商:</b> {video.studio or '未知'}</p>
            <p><b>发行:</b> {video.label or '未知'}</p>
            <p><b>系列:</b> {video.series or '无'}</p>
            <p><b>类型:</b> {tags_str}</p>
            <p><b>发行日期:</b> {video.release_date or '未知'}</p>
            <p><b>文件路径:</b> {video.file_path}</p>
            """

            self.detail_panel.setText(detail_html)

            # 显示播放按钮（如果文件存在）
            if video.file_path and os.path.exists(video.file_path):
                self.play_button.setVisible(True)
                self.relocate_button.setVisible(True)
            else:
                self.play_button.setVisible(False)
                self.relocate_button.setVisible(True)  # 文件不存在时也显示重定位

            # 显示封面 + 点击查看大图
            self.current_cover_path = video.cover_path if video.cover_path and os.path.exists(video.cover_path) else None
            if self.current_cover_path:
                pixmap = QPixmap(self.current_cover_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(260, 360, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.cover_label.setPixmap(scaled)
                    self.cover_label.setToolTip("点击查看大图")
                    self.cover_label.setCursor(Qt.CursorShape.PointingHandCursor)
                    self.current_video_id_for_cover = video.id
                else:
                    self.cover_label.clear()
                    self.cover_label.setText("无封面")
                    self.cover_label.setCursor(Qt.CursorShape.ArrowCursor)
            else:
                self.cover_label.clear()
                self.cover_label.setText("无封面")
                self.cover_label.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.detail_panel.setText("未找到视频信息")
            self.play_button.setVisible(False)

    def _on_cover_clicked(self, event):
        """点击封面查看大图"""
        if hasattr(self, 'current_cover_path') and self.current_cover_path:
            video_id = getattr(self, 'current_video_id_for_cover', '未知')
            dialog = CoverViewerDialog(self.current_cover_path, video_id, self)
            dialog.show()

    def _play_selected_video(self):
        """播放选中的视频"""
        if hasattr(self, 'current_video_path') and self.current_video_path:
            self._play_video(self.current_video_path)

    def _play_video(self, file_path: str):
        """用系统默认播放器打开视频"""
        if not file_path:
            QMessageBox.warning(self, "错误", "视频文件路径为空")
            return

        if not os.path.exists(file_path):
            reply = QMessageBox.question(
                self, "文件不存在",
                f"视频文件不存在:\n{file_path}\n\n是否重新定位该文件？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._relocate_current_video()
            return

        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(file_path)
            elif system == "Darwin":  # macOS
                os.system(f'open "{file_path}"')
            else:  # Linux
                os.system(f'xdg-open "{file_path}"')
            self.logger.info(f"已播放视频: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "播放失败", f"无法播放视频:\n{e}")
            self.logger.error(f"播放视频失败: {e}")

    def _relocate_current_video(self):
        """重新定位当前视频文件"""
        video_id = getattr(self, 'current_video_id', None)
        if not video_id:
            QMessageBox.warning(self, "提示", "请先选择一个视频")
            return

        new_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.mkv *.avi *.wmv *.mov *.flv *.ts *.m4v)"
        )
        if not new_path:
            return

        self.db.update_file_path(video_id, new_path)
        self.current_video_path = new_path
        self.logger.info(f"已更新路径: {video_id} -> {new_path}")

        # 更新播放按钮可见性
        self.play_button.setVisible(True)
        self._refresh_video_list()

    def _batch_relocate_videos(self):
        """批量重定位路径失效的视频"""
        broken = self.db.get_videos_with_missing_files()
        if not broken:
            QMessageBox.information(self, "提示", "所有视频路径正常，无需重定位")
            return

        reply = QMessageBox.question(
            self, "批量重定位",
            f"找到 {len(broken)} 个路径失效的视频\n\n请选择新的视频根目录，系统将按文件名自动匹配",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Ok:
            return

        new_dir = QFileDialog.getExistingDirectory(self, "选择新的视频根目录")
        if not new_dir:
            return

        # 递归扫描新目录中的所有视频文件
        video_exts = {'.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.ts', '.m4v'}
        found_files = {}  # {小写文件名: 完整路径}
        for root, dirs, files in os.walk(new_dir):
            for f in files:
                if os.path.splitext(f)[1].lower() in video_exts:
                    found_files[f.lower()] = os.path.join(root, f)

        # 按文件名匹配
        matched = {}
        unmatched = []
        for video in broken:
            filename = os.path.basename(video.file_path).lower()
            if filename in found_files:
                matched[video.id] = found_files[filename]
            else:
                unmatched.append(video.id)

        if not matched:
            QMessageBox.warning(
                self, "未找到匹配",
                f"在所选目录中未找到任何匹配文件\n\n未匹配: {len(unmatched)} 个"
            )
            return

        # 显示确认对话框
        unmatched_text = "\n".join(unmatched[:10])
        if len(unmatched) > 10:
            unmatched_text += f"\n... 共 {len(unmatched)} 个"

        msg = f"匹配结果:\n  已匹配: {len(matched)} 个\n  未匹配: {len(unmatched)} 个"
        if unmatched:
            msg += f"\n\n未匹配的番号:\n{unmatched_text}"
        msg += "\n\n是否更新已匹配视频的路径？"

        reply = QMessageBox.question(
            self, "确认批量更新",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # 批量更新数据库
        for vid_id, new_path in matched.items():
            self.db.update_file_path(vid_id, new_path)

        self.logger.info(f"批量重定位完成: 更新了 {len(matched)} 个视频路径")
        QMessageBox.information(self, "完成", f"已成功更新 {len(matched)} 个视频路径")
        self._refresh_video_list()

    def _delete_selected_videos(self):
        """删除选中的视频记录"""
        selected_items = self.video_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要删除的视频")
            return

        # 获取选中的视频ID
        selected_codes = []
        for item in selected_items:
            code = item.data(Qt.ItemDataRole.UserRole)
            if code:
                selected_codes.append(code)

        if not selected_codes:
            QMessageBox.information(self, "提示", "无法获取选中视频的信息")
            return

        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {len(selected_codes)} 个视频记录吗？\n\n"
            f"此操作将：\n"
            f"  • 从数据库中删除视频记录\n"
            f"  • 删除关联的封面图片文件\n"
            f"  • 保留本地视频文件不受影响",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 执行删除
        deleted_count = self.db.delete_videos(selected_codes)

        if deleted_count > 0:
            self.logger.info(f"删除了 {deleted_count} 个视频记录")
            QMessageBox.information(self, "完成", f"已成功删除 {deleted_count} 个视频记录")
            self._refresh_video_list()
        else:
            QMessageBox.warning(self, "失败", "删除失败，请查看日志")

    def _show_settings(self):
        """显示设置"""
        dialog = SettingsDialog(self.config, self.theme_manager, self)
        if dialog.exec():
            # 设置已保存，应用新主题
            app = QApplication.instance()
            theme = self.config.get('theme', 'dark_amber')
            self.theme_manager.apply_theme(app, theme)
            self.logger.info(f"应用主题: {theme}")

            # 应用新的缩略图大小
            thumb_size = self.config.get('thumb_size', 150)
            # 根据缩略图大小调整布局
            cover_width = int(thumb_size * 0.75)
            cover_height = thumb_size
            self.video_list.setIconSize(QSize(cover_width, cover_height))
            item_height = cover_height + 40
            self.video_list.setGridSize(QSize(500, item_height))

            # 刷新列表
            self._refresh_video_list()

    def _show_actress_dialog(self):
        """下载所有女优头像并更新数据库"""
        from core.avatar_downloader import AvatarDownloader

        db = self.db

        # 先确认
        reply = QMessageBox.question(
            self, "下载女优头像",
            "将从数据库下载 945 名女优的头像并更新数据库记录。\n已下载的会自动跳过。\n\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.actress_avatar_button.setEnabled(False)
        self.actress_avatar_button.setText("下载中...")

        def _do_download():
            dl = AvatarDownloader()
            data = dl.load_actress_data()
            downloaded = 0
            updated = 0
            skipped = 0

            for i, actress in enumerate(data):
                name = actress['name']
                url = actress.get('avatar_url', '')

                if not url or 'actor_unknow' in url:
                    skipped += 1
                    continue

                # 下载头像
                local_path = dl.download_avatar(name, url)

                if local_path:
                    downloaded += 1
                    # 更新数据库
                    if db.update_actress_avatar(name, local_path):
                        updated += 1
                else:
                    skipped += 1

                # 更新进度
                progress_text = f"女优头像下载: {i+1}/{len(data)} (已下载{downloaded})"
                QTimer.singleShot(0, lambda t=progress_text: self.statusBar().showMessage(t))

            dl.close()
            summary = f"头像下载完成: 共下载 {downloaded} 个, 更新数据库 {updated} 条, 跳过 {skipped} 个"
            QTimer.singleShot(0, lambda: self._on_avatar_download_finished(summary))

        import threading
        t = threading.Thread(target=_do_download, daemon=True)
        t.start()

    def _on_avatar_download_finished(self, summary: str):
        """头像下载完成回调"""
        self.actress_avatar_button.setEnabled(True)
        self.actress_avatar_button.setText("女优头像")
        self.statusBar().showMessage(summary)
        self._refresh_video_list()
        QMessageBox.information(self, "完成", summary)

    def _on_actress_selected_from_dialog(self, actress_name: str):
        """从女优对话框选中后，在主窗口过滤该女优的作品"""
        # 设置演员下拉框
        index = self.actress_combo.findText(actress_name)
        if index >= 0:
            self.actress_combo.setCurrentIndex(index)
        else:
            self.actress_combo.setCurrentText(actress_name)
        self._on_search()

    def _on_detail_link_clicked(self, link: str):
        """详情面板中的链接点击 - 查看女优头像大图"""
        if link.startswith("actress:"):
            actress_name = link[len("actress:"):]
            from core.avatar_downloader import AvatarDownloader
            dl = AvatarDownloader()
            avatar_path = dl.get_avatar_path(actress_name)
            info = dl.get_actress_info(actress_name)
            dl.close()

            # 弹窗显示头像大图 + 信息
            dialog = QDialog(self)
            dialog.setWindowTitle(actress_name)
            layout = QVBoxLayout(dialog)

            if avatar_path and os.path.exists(avatar_path):
                pixmap = QPixmap(avatar_path)
                if not pixmap.isNull():
                    screen = QApplication.primaryScreen().availableGeometry()
                    max_w = min(500, screen.width() - 100)
                    max_h = min(600, screen.height() - 100)
                    scaled = pixmap.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    img_label = QLabel()
                    img_label.setPixmap(scaled)
                    img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(img_label)

            # 信息
            if info:
                info_text = actress_name
                if info.get('cup'):
                    info_text += f"  |  罩杯: {info['cup']}"
                if info.get('height'):
                    info_text += f"  |  身高: {info['height']}cm"
                if info.get('birth_year'):
                    info_text += f"  |  出生: {info['birth_year']}年"
                info_label = QLabel(info_text)
                info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                info_label.setStyleSheet("font-size: 14px; padding: 8px;")
                layout.addWidget(info_label)

            if not avatar_path or not os.path.exists(avatar_path):
                no_img = QLabel("暂无头像\n可点击工具栏「女优头像」按钮下载")
                no_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_img.setStyleSheet("color: #888; font-size: 14px; padding: 30px;")
                layout.addWidget(no_img)

            dialog.exec()

    def _download_single_cover(self, code: str, cover_url: str):
        """下载单个封面并刷新列表（每爬完一个视频立刻调用）"""
        import threading
        db = self.db

        def _do_download():
            from core.cover_downloader import CoverDownloader
            downloader = CoverDownloader(self.config)
            try:
                local_path = downloader.download_one(code, cover_url)
                if local_path:
                    db.update_cover_path(code, local_path)
                    QTimer.singleShot(0, self._refresh_video_list)
            finally:
                downloader.close()

        thread = threading.Thread(target=_do_download, daemon=True)
        thread.start()

    def _download_covers(self, covers: dict[str, str]):
        """下载封面（在后台线程）"""
        import threading

        # 直接保存必要的引用，不使用弱引用
        db = self.db

        def download_thread():
            from core.cover_downloader import CoverDownloader

            downloader = CoverDownloader(self.config)

            def callback(video_id: str, local_path: str):
                # 只更新数据库，不访问 UI
                if local_path:
                    db.update_cover_path(video_id, local_path)

            try:
                downloaded = downloader.download_batch(covers, callback)
                # 下载完成后，在主线程中更新 UI
                QTimer.singleShot(0, lambda: self._on_download_complete(len(downloaded), len(covers)))
            finally:
                downloader.close()

        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

    def _on_download_complete(self, downloaded: int, total: int):
        """封面下载完成回调"""
        self.statusBar().showMessage(f"封面下载完成: {downloaded}/{total}")
        self._refresh_video_list()

    def _retry_download_covers(self):
        """重新下载没有封面的视频"""
        # 查询没有封面的视频
        missing = self.db.get_videos_without_covers()

        if not missing:
            QMessageBox.information(self, "提示", "所有视频都有封面")
            return

        # 询问用户
        reply = QMessageBox.question(
            self,
            "重新下载封面",
            f"找到 {len(missing)} 个没有封面的视频\n\n是否重新下载？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._download_missing_covers(missing)

    def _download_missing_covers(self, videos):
        """下载缺失的封面"""
        covers_to_download = {}
        missing_url_videos = []

        for video in videos:
            if video.cover_url:
                covers_to_download[video.id] = video.cover_url
            else:
                missing_url_videos.append(video.id)
                self.logger.warning(f"视频 {video.id} 没有封面URL，需要重新获取元数据")

        # 为没有封面URL的视频获取元数据
        if missing_url_videos:
            reply = QMessageBox.question(
                self,
                "获取封面URL",
                f"有 {len(missing_url_videos)} 个视频没有封面URL\n\n是否从 JavDB 重新获取元数据？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 传递 covers_to_download，获取完成后会自动下载
                self._fetch_missing_metadata(missing_url_videos, covers_to_download)
                return  # 等待元数据获取完成

        # 没有需要获取元数据的视频，直接下载
        if not covers_to_download:
            QMessageBox.warning(self, "警告", "没有可下载的封面（所有视频都没有封面URL）")
            return

        self.logger.info(f"开始下载 {len(covers_to_download)} 个缺失的封面")
        self._download_covers(covers_to_download)

    def _fetch_missing_metadata(self, video_ids: list[str], covers_dict: dict[str, str]):
        """为没有封面URL的视频获取元数据（在后台线程执行）"""
        if self.fetch_thread and self.fetch_thread.isRunning():
            QMessageBox.information(self, "提示", "已有元数据抓取任务正在运行，请稍后重试")
            return

        # 使用已有的 FetchMetadataThread
        self.fetch_thread = FetchMetadataThread(video_ids)
        self._register_thread(self.fetch_thread)
        self.fetch_thread.metadata_fetched.connect(lambda code, metadata: self._on_metadata_fetched_for_cover(code, metadata, covers_dict))
        self.fetch_thread.finished.connect(lambda results: self._on_fetch_metadata_finished_impl(video_ids, results, covers_dict))
        self.fetch_thread.stopped.connect(lambda: self.statusBar().showMessage("封面补全元数据任务已停止"))
        self.fetch_thread.error.connect(lambda code, error: self.logger.error(f"获取元数据出错 {code}: {error}"))
        self.fetch_thread.start()

    def _on_metadata_fetched_for_cover(self, code: str, metadata, covers_dict: dict[str, str]):
        """元数据获取成功回调"""
        if metadata and metadata.cover_url:
            self.db.update_video_metadata(code, metadata)
            covers_dict[code] = metadata.cover_url
            self.logger.info(f"获取到封面URL: {code}")

    def _on_fetch_metadata_finished_impl(self, video_ids: list[str], results: dict[str, VideoMetadata], covers_dict: dict[str, str]):
        """元数据获取完成回调"""
        # 处理结果，提取有 cover_url 的视频
        for code, metadata in results.items():
            if metadata.cover_url and code not in covers_dict:
                covers_dict[code] = metadata.cover_url

        fetched = len(covers_dict)
        total = len(video_ids)
        self.statusBar().showMessage(f"元数据获取完成: {fetched}/{total}")

        # 如果获取到了封面URL，自动下载
        if covers_dict:
            self.logger.info(f"开始下载 {len(covers_dict)} 个获取到的封面")
            self._download_covers(covers_dict)
        else:
            QMessageBox.information(self, "完成", f"成功获取 {fetched}/{total} 个视频的元数据")

    def _download_covers_sync(self, covers: dict[str, str]):
        """同步下载封面（在主线程中执行）"""
        from core.cover_downloader import CoverDownloader

        downloader = CoverDownloader(self.config)
        total = len(covers)

        try:
            for i, (video_id, url) in enumerate(covers.items(), 1):
                self.statusBar().showMessage(f"下载封面 {i}/{total}: {video_id}")

                local_path = downloader.download_one(video_id, url)
                if local_path:
                    self.db.update_cover_path(video_id, local_path)

            self.statusBar().showMessage(f"封面下载完成: {len(covers)} 个")
        finally:
            downloader.close()
