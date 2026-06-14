# AI Learning Platform

零依赖的本地 AI 视频学习平台。一个 HTML 文件搞定前端，一个 Python 文件搞定后端，开箱即用。

**核心功能**：课程树导航、播放列表自动续播、学习进度与目标追踪、AI 智能总结（DeepSeek）、暗色/亮色主题、数据仪表盘。

## Quick Start

### 1. 准备文件

```bash
# 克隆仓库
git clone https://github.com/27258/ai-learning-platform.git
cd ai-learning-platform/assets
```

### 2. 配置视频路径

打开 `server.py`，找到 `VIDEO_ROOTS` 字典，填入你的视频目录：

```python
VIDEO_ROOTS = {
    "my-course": r"C:\Users\你的用户名\Videos\我的课程",
}
```

### 3. 启动服务器

```bash
# 基础启动（无需 API Key）
python server.py

# 启用 AI 总结（需要 DeepSeek API Key）
# Windows:
set DEEPSEEK_API_KEY=sk-your-api-key
python server.py

# macOS/Linux:
DEEPSEEK_API_KEY=sk-your-api-key python server.py
```

浏览器自动打开 `http://localhost:8765`，即可开始使用。

### 4. 自定义课程

编辑 `course-data.json` 添加你自己的课程：

```json
[
  {
    "id": "stage_01",
    "name": "阶段一 基础入门",
    "lessons": [
      {
        "id": "lesson_01",
        "name": "第一课 环境搭建",
        "source": "基础教程",
        "video": ["/video/my-course/01_介绍.mp4"],
        "notes": "本节课的环境搭建步骤..."
      }
    ]
  }
]
```

## 项目结构

```
ai-learning-platform/
├── assets/
│   ├── learn.html          # 前端单文件 SPA
│   ├── server.py           # Python HTTP 服务器
│   ├── course-data.json    # 课程数据模板
│   ├── handoff.md          # 开发约定
│   ── 设计蓝图.md         # 架构设计文档
├── SKILL.md                # QoderWork Skill 主文件
├── architecture.md         # 前端架构详解
├── server-guide.md         # 后端 API 指南
└── README.md               # 本文档
```

## 技术栈

- **前端**：原生 HTML + CSS + JavaScript（零框架依赖）
- **后端**：Python `http.server`（端口 8765）
- **数据存储**：localStorage（浏览器本地存储）
- **AI 功能**：DeepSeek API（可选，不设置不影响核心功能）

## 特性

| 特性 | 说明 |
|------|------|
| 零依赖部署 | 一个 HTML + 一个 Python 文件，双击启动即用 |
| 课程树导航 | 阶段 → 课时 → 播放列表，层级清晰 |
| 自动续播 | 一个课时的多个视频自动串联播放 |
| 进度追踪 | 完成状态、观看历史、每日学习时长统计 |
| AI 智能总结 | DeepSeek API 自动生成内容摘要和练习题（可选） |
| 暗色/亮色主题 | 一键切换，保护视力 |
| 数据仪表盘 | 今日目标、阶段进度、收藏管理一目了然 |
| 完全离线可用 | 除 AI 功能外，所有核心功能无需网络 |

## 常见问题

**Q: 提示 "python 不是内部或外部命令"？**  
A: 需要先安装 Python 3。从 [python.org](https://www.python.org/downloads/) 下载并勾选"Add Python to PATH"后重新安装。

**Q: 如何停止服务器？**  
A: 在运行 `python server.py` 的命令行窗口中按 `Ctrl+C`，或直接关闭窗口。

**Q: 可以修改端口吗？**  
A: 可以。打开 `server.py`，找到 `PORT = 8765`，改成你想要的端口号。

## License

MIT License — 自由使用、修改和分发。

## 贡献

欢迎提交 Issue 和 Pull Request！
