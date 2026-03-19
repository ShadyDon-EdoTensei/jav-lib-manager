# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed
- 男演员筛选功能（不再需要）
- `GenderType` 类和相关代码
- `male_actor_blacklist.py` 模块
- `remove_male_actors.py` 迁移脚本
- 数据库 `actresses` 表的 `gender` 字段支持

### Fixed
- 修复并发插入时的 UNIQUE 约束错误（使用 INSERT OR IGNORE）
- 修复 Playwright 事件循环冲突问题
- 修复 `.H265`、`.HEVC` 等编码后缀文件无法解析的问题
- 修复设置对话框中 `cover_dir`/`covers_dir` 不一致的问题

### Changed
- 统一使用 `covers_dir` 配置键
- 清理配置文件中的废弃键（`display_language`、`cover_dir`）

## [1.0.0] - 2024-03-19

### Added
- 智能扫描本地目录，从文件名提取番号
- 从 JavDB 等站点获取视频元数据（封面、演员、标签等）
- 多维度搜索功能（番号、演员、标签、片商）
- PyQt6 桌面应用界面
- 18 种 Material Design 主题（深色/浅色）
- 封面自动下载和缓存
- SQLite 本地数据库存储
- 支持多种视频格式（MP4, MKV, AVI, WMV, MOV, FLV, M4V）
- 视频卡片和列表双视图
- 封面大图查看器
- 多线程处理，避免界面卡顿
- 灵活的配置系统

### Technical Details
- GUI: PyQt6 + qt-material
- Database: SQLite
- Web Scraping: Playwright + requests + lxml
- Image Processing: Pillow
- Python: 3.9+
- Platform: Windows 10/11

[Unreleased]: https://github.com/ShadyDon/jav-lib-manager/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/ShadyDon/jav-lib-manager/releases/tag/v1.0.0
