# JAV Lib Manager 🎀

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-Latest-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

[English](README.md) | [简体中文](#简体中文) | [日本語](README_ja.md)

*现代化的个人视频收藏管理桌面应用*

</div>

---

## 简体中文

### 项目简介

🎀 **JAV Lib Manager** 是一款专为个人视频收藏管理设计的强大桌面应用。它能够智能地整理您的本地视频文件，自动从在线源获取元数据，并提供先进的搜索和过滤功能。

### 核心特性

- 🔍 **智能扫描** - 自动扫描目录，从文件名中提取视频番号
- 🌐 **元数据获取** - 从 JavDB 获取封面、女优信息和标签
- 🏷️ **多维度搜索** - 按番号、女优、标签或制作商搜索
- 📺 **现代化界面** - 基于 PyQt6 的精美界面，18种 Material Design 主题
- 💾 **本地数据库** - SQLite 存储，支持大规模收藏
- 📷 **封面缓存** - 自动下载和缓存封面图片
- ⚡ **高性能** - 多线程处理，体验流畅

### 界面预览

```
┌─────────────────────────────────────────────────────┐
│  🎀 JAV Lib Manager                                    │
├─────────────────────────────────────────────────────┤
│  [扫描] [刷新] [统计] [日志] [设置]                   │
│  搜索: [________________] [筛选]                       │
├──────────────────────┬──────────────────────────────┤
│  ┌────┐ ┌────┐      │ 封面大图                      │
│  │封面│ │封面│      │ ┌─────────────────────────┐  │
│  │    │ │    │      │ │                         │  │
│  └────┘ └────┘      │ │   [高清封面大图]        │  │
│  ┌────┐ ┌────┐      │ │                         │  │
│  │封面│ │封面│      │ └─────────────────────────┘  │
│  │    │ │    │      │ 标题: 视频标题             │
│  └────┘ └────┘      │ 女优: [女优1, 女优2]        │
│  ... 更多视频       │ 标签: [标签1, 标签2, 标签3]  │
│                     │ 制作商: 制作商名称           │
│                     │ 文件: /path/to/video.mp4     │
└──────────────────────┴──────────────────────────────┘
```

### 环境要求

- **Python**: 3.9 或更高版本 — [点击下载](https://www.python.org/downloads/)（安装时务必勾选 "Add Python to PATH"）
- **操作系统**: Windows 10/11
- **磁盘空间**: 500MB 以上用于依赖项
- **网络**: 获取元数据需要联网

### 安装指南

#### 方法一：使用 Git（推荐）

```bash
# 1. 确认 Python 版本（必须是 3.9+）
python --version

# 2. 克隆仓库
git clone https://github.com/ShadyDon-EdoTensei/jav-lib-manager.git
cd jav-lib-manager

# 3. 创建虚拟环境（可选）
python -m venv venv
venv\Scripts\activate

# 4. 安装 Python 依赖
pip install -r requirements.txt

# 5. 安装 Playwright 浏览器引擎（约300MB，首次安装）
playwright install chromium

# 6. 启动应用
python run_app.py
```

#### 方法二：下载 ZIP（无需 Git）

1. 前往 [发布页面](https://github.com/ShadyDon-EdoTensei/jav-lib-manager/releases) 下载最新 ZIP
2. 解压到任意文件夹（如 `C:\jav-lib-manager\`）
3. 在该文件夹打开 **命令提示符** 或 **PowerShell**
4. 依次执行：
```bash
python --version          # 确认 Python 3.9+
pip install -r requirements.txt
playwright install chromium
python run_app.py
```

> **提示：** 如果 `python` 命令无法识别，说明需要先安装 Python，并在安装时勾选 "Add Python to PATH"。

### 使用说明

#### 首次使用

1. **启动应用**
   ```bash
   python run_app.py
   ```

2. **扫描视频目录**
   - 点击工具栏中的 **"扫描"** 按钮
   - 选择包含视频文件的目录
   - 等待扫描完成
   - 确认检测到的视频数量

3. **获取元数据**
   - 选择 **"是"** 自动获取元数据
   - 等待处理完成
   - 视频将显示在主界面中

#### 搜索和筛选

- **关键词搜索**: 在搜索框输入番号、标题或女优名
- **女优筛选**: 从下拉菜单选择女优
- **标签筛选**: 从下拉菜单选择标签
- **制作商筛选**: 从下拉菜单选择制作商

#### 查看视频详情

点击任意视频卡片查看：
- 高清封面大图（点击可查看全尺寸）
- 完整女优列表
- 标签分类
- 文件信息（路径、大小、日期）

#### 更换主题

1. 点击 **"设置"** 按钮
2. 进入 **"外观设置"** 标签
3. 选择喜欢的主题（18种可选）
4. 点击 **"保存"**

### 配置说明

配置文件位置：`~/.javlibrary/config.json`

```json
{
  "database_path": "data/library.db",
  "covers_dir": "data/images/covers",
  "theme": "dark_amber",
  "window_width": 1600,
  "window_height": 900,
  "scraper_delay": 2,
  "scraper_timeout": 30
}
```

### 项目结构

```
jav-lib-manager/
├── README.md                 # 英文文档
├── README_zh.md              # 中文文档
├── README_ja.md              # 日文文档
├── LICENSE                   # MIT 许可证
├── .gitignore                # Git 忽略规则
├── CONTRIBUTING.md           # 贡献指南
├── CODE_OF_CONDUCT.md        # 社区准则
├── CHANGELOG.md              # 版本历史
├── requirements.txt          # Python 依赖
├── run_app.py                # 应用入口
├── src/                      # 源代码
│   ├── __init__.py
│   ├── main.py
│   ├── gui/                  # PyQt6 界面
│   │   ├── main_window.py
│   │   ├── themes/
│   │   └── dialogs/
│   ├── core/                 # 核心逻辑
│   │   ├── models.py
│   │   ├── parser.py
│   │   ├── scanner.py
│   │   ├── scraper.py
│   │   ├── javdb_scraper.py
│   │   ├── database.py
│   │   └── cover_downloader.py
│   └── utils/                # 工具模块
│       ├── config.py
│       └── logger.py
├── docs/                     # 额外文档
├── tests/                    # 测试文件
└── data/                     # 运行时数据（git忽略）
    ├── library.db
    └── images/
```

### 技术栈

| 组件 | 技术 |
|------|------|
| **GUI 框架** | PyQt6 |
| **主题引擎** | qt-material |
| **数据库** | SQLite |
| **网页爬虫** | Playwright + requests + lxml |
| **图片处理** | Pillow |
| **图标** | qtawesome (FontAwesome 5) |

### 支持的视频格式

MP4、MKV、AVI、WMV、MOV、FLV、M4V、TS、WebM

### 数据来源

- **JavDB**（默认，使用 Playwright 反爬虫）
- 更多数据源计划在未来版本中支持

### 常见问题

**Q: 我的数据会上传到服务器吗？**

A: 不会。所有数据都存储在您的本地电脑上。数据库位于 `~/.javlibrary/data/library.db`。

**Q: 可以在 Linux/Mac 上使用吗？**

A: 目前官方仅支持 Windows。Linux/Mac 支持计划在未来的版本中推出。

**Q: 如何备份我的数据？**

A: 备份整个 `~/.javlibrary/` 目录即可。

**Q: 元数据获取失败怎么办？**

A:
1. 检查网络连接
2. 尝试在设置中增加爬虫延迟
3. 查看日志文件 `~/.javlibrary/logs/javlibrary.log`

**Q: 可以添加自定义数据源吗？**

A: 此功能计划在 v2.0.0 版本中推出，敬请期待！

### 开发路线

- [ ] 视频播放器集成
- [ ] Linux 和 Mac 支持
- [ ] 自定义元数据源
- [ ] 批量文件重命名
- [ ] 导出为 CSV/JSON
- [ ] 高级统计和报告

### 贡献指南

欢迎贡献！详情请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

### 行为准则

请阅读 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) 了解我们的社区标准。

### 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE)。

### 致谢

- **PyQt6 团队** - 感谢出色的 GUI 框架
- **Playwright 团队** - 感谢可靠的浏览器自动化工具
- **qt-material** - 感谢精美的 Material Design 主题
- **所有贡献者** - 感谢让这个项目变得更好！

### 获取支持

- 📧 邮箱: ShadyDon-EdoTensein@users.noreply.github.com
- 🐛 问题反馈: [GitHub Issues](https://github.com/ShadyDon-EdoTensei/jav-lib-manager/issues)
- 💬 讨论: [GitHub Discussions](https://github.com/ShadyDon-EdoTensei/jav-lib-manager/discussions)

---

<div align="center">

**⭐ 如果这个项目对您有帮助，请考虑给它一个星标！⭐**

用 ❤️ 和 🎀 打造的 JAV Lib Manager

</div>
