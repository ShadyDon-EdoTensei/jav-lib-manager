# Contributing to JAV Lib Manager

感谢您考虑为 JAV Lib Manager 做出贡献！

## 开发环境设置

### 前置要求

- Python 3.9 或更高版本
- Windows 10/11（目前仅支持 Windows）
- Git

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/ShadyDon/jav-lib-manager.git
   cd jav-lib-manager
   ```

2. **创建虚拟环境（推荐）**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **安装 Playwright 浏览器**
   ```bash
   playwright install chromium
   ```

5. **运行应用**
   ```bash
   python run_app.py
   ```

## 项目结构

```
jav-lib-manager/
├── src/
│   ├── main.py              # 应用入口
│   ├── gui/                 # PyQt 界面
│   │   ├── main_window.py   # 主窗口
│   │   ├── themes/          # 主题管理
│   │   └── dialogs/         # 对话框
│   ├── core/                # 核心逻辑
│   │   ├── models.py        # 数据模型
│   │   ├── parser.py        # 番号解析器
│   │   ├── scanner.py       # 文件扫描器
│   │   ├── scraper.py       # 元数据抓取器
│   │   ├── javdb_scraper.py # JavDB 爬虫
│   │   ├── database.py      # 数据库操作
│   │   └── cover_downloader.py # 封面下载器
│   └── utils/               # 工具
│       ├── config.py        # 配置管理
│       └── logger.py        # 日志
├── data/                    # 数据目录（运行时生成）
├── requirements.txt         # Python 依赖
└── run_app.py               # 启动脚本
```

## 代码规范

### Python 风格

- 遵循 [PEP 8](https://pep8.org/) 编码规范
- 使用有意义的变量和函数名
- 添加类型注解（Type Hints）
- 编写文档字符串（Docstrings）

### 示例

```python
from typing import Optional
from datetime import date

def fetch_metadata(video_id: str, timeout: int = 30) -> Optional[dict]:
    """
    获取视频元数据

    Args:
        video_id: 视频番号
        timeout: 请求超时时间（秒）

    Returns:
        元数据字典，失败返回 None
    """
    # 实现代码...
    pass
```

### Git 提交规范

使用清晰的提交消息：

```
<type>: <description>

[optional body]
```

**类型（type）：**
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例：**
```
feat: 添加视频播放器功能
fix: 修复封面下载失败的问题
docs: 更新 README 安装说明
```

## 提交流程

### 1. Fork 仓库

点击 GitHub 页面右上角的 "Fork" 按钮

### 2. 创建特性分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

### 3. 进行更改

- 编写代码
- 添加测试（如果适用）
- 更新文档（如果需要）

### 4. 提交更改

```bash
git add .
git commit -m "feat: 添加你的新功能"
```

### 5. 推送到分支

```bash
git push origin feature/your-feature-name
```

### 6. 创建 Pull Request

1. 访问你 Fork 的仓库页面
2. 点击 "Compare & pull request"
3. 填写 PR 描述：
   - 简要说明你的更改
   - 关联相关的 Issue（如果有）
   - 确认所有检查通过

## 开发指南

### 添加新的数据源

1. 在 `src/core/` 创建新的爬虫模块
2. 继承或参考 `javdb_scraper.py` 的实现
3. 在 `src/core/scraper.py` 中注册新的数据源

### 添加新的主题

1. 在 `src/gui/themes/` 中定义新主题
2. 在 `src/gui/dialogs/settings_dialog.py` 中添加主题选项

### 调试技巧

- 查看日志文件：`~/.javlibrary/logs/javlibrary.log`
- 使用 VSCode 调试配置（`.vscode/launch.json`）
- 修改 `src/utils/logger.py` 调整日志级别

## 测试

### 手动测试

1. 扫描测试目录
2. 获取元数据
3. 验证搜索功能
4. 检查封面显示

### 测试数据

建议使用少量测试视频进行开发，避免频繁抓取。

## 问题反馈

如果你发现了 bug 或有功能建议：

1. 检查 [Issues](https://github.com/ShadyDon/jav-lib-manager/issues) 是否已存在
2. 如果没有，创建新的 Issue
3. 提供详细信息：
   - 复现步骤
   - 预期行为
   - 实际行为
   - 系统环境（Windows 版本、Python 版本等）
   - 日志片段（如果相关）

## 行为准则

- 尊重所有贡献者
- 接受建设性批评
- 关注对社区最有利的事情

## 许可证

通过贡献代码，你同意你的贡献将在 MIT 许可证下发布。

---

再次感谢你的贡献！🎉
