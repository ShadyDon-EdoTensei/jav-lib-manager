"""文件扫描器 - 扫描本地目录，识别视频文件"""

import os
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass

from .parser import get_parser
from .models import VideoFile


@dataclass
class ScanResult:
    """扫描结果"""
    total_files: int           # 发现的视频文件总数
    parsed_files: int          # 成功解析番号的文件数
    new_files: int             # 新增文件数
    updated_files: int         # 更新文件数
    failed_files: int          # 失败文件数


class VideoScanner:
    """视频文件扫描器"""

    SUPPORTED_FORMATS = {'.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.m4v',
                         '.MP4', '.MKV', '.AVI', '.WMV', '.MOV', '.FLV', '.M4V'}
    SUPPORTED_FORMATS_LOWER = {fmt.lower() for fmt in SUPPORTED_FORMATS}

    def __init__(self):
        """初始化扫描器"""
        self.parser = get_parser()

    def scan_directory(
        self,
        directory: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        recursive: bool = True
    ) -> List[VideoFile]:
        """
        扫描目录，返回视频文件列表

        Args:
            directory: 要扫描的目录路径
            progress_callback: 进度回调函数 (current_path, current_count, total_count)
            recursive: 是否递归扫描子目录

        Returns:
            VideoFile 对象列表
        """
        video_files = []

        if not os.path.isdir(directory):
            raise ValueError(f"目录不存在: {directory}")

        # 收集所有文件
        all_files = []
        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    all_files.append(os.path.join(root, file))
        else:
            for item in os.listdir(directory):
                full_path = os.path.join(directory, item)
                if os.path.isfile(full_path):
                    all_files.append(full_path)

        total_count = len(all_files)

        for i, file_path in enumerate(all_files):
            # 进度回调
            if progress_callback:
                progress_callback(file_path, i + 1, total_count)

            # 检查文件扩展名
            ext = os.path.splitext(file_path)[1]
            if ext.lower() not in self.SUPPORTED_FORMATS_LOWER:
                continue

            try:
                # 获取文件信息
                stat = os.stat(file_path)
                size = stat.st_size
                mtime = stat.st_mtime

                # 解析番号
                filename = os.path.basename(file_path)
                code = self.parser.parse(filename)

                video_files.append(VideoFile(
                    path=file_path,
                    size=size,
                    code=code,
                    mtime=mtime
                ))

            except Exception as e:
                print(f"处理文件失败: {file_path}, 错误: {e}")
                continue

        return video_files

    def scan(
        self,
        directory: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        recursive: bool = True
    ) -> List[VideoFile]:
        """兼容旧接口：调用 scan_directory。"""
        return self.scan_directory(
            directory=directory,
            progress_callback=progress_callback,
            recursive=recursive
        )

    def scan_single_file(self, file_path: str) -> Optional[VideoFile]:
        """
        扫描单个文件

        Args:
            file_path: 文件路径

        Returns:
            VideoFile 或 None
        """
        if not os.path.isfile(file_path):
            return None

        # 检查文件扩展名
        ext = os.path.splitext(file_path)[1]
        if ext.lower() not in self.SUPPORTED_FORMATS_LOWER:
            return None

        try:
            stat = os.stat(file_path)
            size = stat.st_size
            mtime = stat.st_mtime

            filename = os.path.basename(file_path)
            code = self.parser.parse(filename)

            return VideoFile(
                path=file_path,
                size=size,
                code=code,
                mtime=mtime
            )
        except Exception as e:
            print(f"处理文件失败: {file_path}, 错误: {e}")
            return None

    def filter_by_code(self, video_files: List[VideoFile]) -> List[VideoFile]:
        """
        过滤出成功解析番号的文件

        Args:
            video_files: 视频文件列表

        Returns:
            有番号的文件列表
        """
        return [vf for vf in video_files if vf.code is not None]

    def group_by_code(self, video_files: List[VideoFile]) -> dict[str, List[VideoFile]]:
        """
        按番号分组

        Args:
            video_files: 视频文件列表

        Returns:
            {番号: [文件列表]} 的字典
        """
        groups = {}
        for vf in video_files:
            if vf.code:
                if vf.code not in groups:
                    groups[vf.code] = []
                groups[vf.code].append(vf)
        return groups


# 全局实例
_scanner_instance = None


def get_scanner() -> VideoScanner:
    """获取扫描器单例"""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = VideoScanner()
    return _scanner_instance
