"""数据模型定义"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import date


@dataclass
class Actress:
    """演员信息"""
    name: str
    name_ja: Optional[str] = None
    avatar_path: Optional[str] = None


@dataclass
class VideoMetadata:
    """视频元数据"""
    id: str                    # 番号
    title: str                 # 标题
    cover_url: Optional[str] = None  # 封面URL
    actresses: list[str] = field(default_factory=list)  # 演员列表
    studio: Optional[str] = None    # 制作商
    label: Optional[str] = None     # 发行商
    series: Optional[str] = None    # 系列
    genres: list[str] = field(default_factory=list)  # 类型标签
    release_date: Optional[date] = None  # 发行日期
    duration: Optional[int] = None  # 时长(秒)
    source: Optional[str] = None    # 数据来源


@dataclass
class VideoFile:
    """本地视频文件信息"""
    path: str                 # 文件路径
    size: int                 # 文件大小(字节)
    code: Optional[str] = None      # 解析出的番号
    mtime: Optional[float] = None   # 修改时间


@dataclass
class VideoRecord:
    """数据库中的视频记录"""
    id: str
    title: str
    cover_path: Optional[str] = None
    cover_url: Optional[str] = None
    release_date: Optional[date] = None
    studio: Optional[str] = None
    label: Optional[str] = None
    series: Optional[str] = None
    duration: Optional[int] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    actresses: list[Actress] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source: Optional[str] = None


class SourceType:
    """数据来源类型"""
    JAVDB = "javdb"
    JAVLIBRARY = "javlibrary"
    JAVBUS = "javbus"
    LOCAL = "local"
