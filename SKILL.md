---
name: ai-learning-platform
description: 搭建本地 AI 视频学习平台。支持课程树、播放列表、学习进度追踪、AI 智能总结（DeepSeek）、Whisper 转录。适用于任何视频课程体系的自学管理。当用户说"搭建学习平台"、"课程网站"、"视频学习"、"AI 学习助手"、"learn.html"、"学习路线"、"课程管理"、"搭建学习系统"时触发。
---

# AI Learning Platform

零依赖的本地 AI 视频学习平台。一个 HTML 文件搞定前端，一个 Python 文件搞定后端，开箱即用。

**核心功能**：课程树导航、播放列表自动续播、学习进度与目标追踪、AI 智能总结、暗色/亮色主题、数据仪表盘。

## Getting Started（从零搭建）

### 第一步：准备文件

```bash
# 创建项目目录
mkdir my-learning-platform && cd my-learning-platform

# 从 Skill assets 复制核心文件
cp ~/.qoderwork/skills/ai-learning-platform/assets/learn.html .
cp ~/.qoderwork/skills/ai-learning-platform/assets/server.py .
cp ~/.qoderwork/skills/ai-learning-platform/assets/course-data.json .
```

### 第二步：配置视频路径

打开 `server.py`，找到 `VIDEO_ROOTS` 字典，填入你的视频目录：

```python
VIDEO_ROOTS = {
    "my-course": r"C:\Users\你的用户名\Videos\我的课程",
}
```

`course-data.json` 中 `video` 数组里的路径前缀（如 `/video/my-course/...`）必须与这里的 key 一致。

### 第三步：配置 AI 总结（可选）

如需 AI 总结功能，设置 DeepSeek API Key 环境变量：

```bash
# Windows
set DEEPSEEK_API_KEY=sk-your-api-key
python server.py

# macOS/Linux
DEEPSEEK_API_KEY=sk-your-api-key python server.py
```

不设置也不影响其他功能（视频播放、进度追踪等正常使用）。

### 第四步：启动

```bash
python server.py
```

浏览器自动打开 `http://localhost:8765`，即可开始使用。

### 第五步：自定义课程

编辑 `course-data.json` 添加你自己的课程。格式参考：

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
        "video": [
          "/video/my-course/01_环境搭建/01_介绍.mp4",
          "/video/my-course/01_环境搭建/02_安装.mp4"
        ],
        "notes": "本节课的环境搭建步骤..."
      }
    ]
  }
]
```

**字段说明**：
- `id` — 唯一标识（英文+数字+下划线）
- `name` — 显示名称
- `video` — 视频 URL 数组（自动组成播放列表）
- `notes` — 可选，Markdown 格式的笔记内容

## Architecture

```
learn.html            单文件 SPA（HTML + CSS + JS，约 3700 行）
server.py             Python HTTP 服务器（端口 8765）
course-data.json      课程树结构（阶段 → 课时 → 播放列表）
summaries_cache.json  AI 总结缓存（自动生成）
```

### 前端模块

| 模块 | 功能 |
|------|------|
| STATE | `state` 对象、`loadState()`、`saveState()` — localStorage 持久化 |
| RENDER | `renderTree()`、`renderDashboard()`、`selectLesson()` — 课程树与仪表盘渲染 |
| VIDEO | `playVideo()`、`playNextInPlaylist()`、`startWatchTracking()` — 播放与学习时长追踪 |
| TOAST | `showNotifyToast(msg, type, onClick)` — 通知提示 |
| HISTORY | `pushHistory()`、`renderContinueWatching()` — 观看历史 |

### 后端 API

| 端点 | 用途 |
|------|------|
| `GET /learn.html` | 加载前端页面 |
| `GET /video/<prefix>/...` | 流式传输本地视频 |
| `GET /course-data.json` | 课程结构数据 |
| `POST /api/ai-summary` | 启动 AI 总结（异步，DeepSeek） |
| `GET /api/ai-summary/<id>` | 查询总结任务状态 |
| `GET/POST /api/summaries` | 读写总结缓存 |

详见 [server-guide.md](server-guide.md)。

## Common Tasks

### 添加新功能

1. 在 `learn.html` 中找到对应区域（CSS / HTML / JS）
2. CSS 加在 `/* AI Summary Panel */` 标记之前（约第 1050 行）
3. HTML 加在对应容器内（`#player-col`、`#dashboard-panel`、`#sidebar` 等）
4. JS 加在 `<script>` 块中 — 状态变更放 STATE，渲染放 RENDER，事件处理放 UI ACTIONS
5. 新增状态字段需在 `loadState()` 和 `saveState()` 中同时处理
6. 刷新 `http://localhost:8765/learn.html` 测试

### 修复 Bug

1. 打开浏览器控制台查看 JS 错误
2. 通过 `localStorage.getItem('learn_state')` 检查状态数据
3. 注意：`state` 是 `let` 声明（不在 `window` 上），Playwright 需用 `localStorage` 读取
4. 注意：`state.playPositions` 按 **lesson ID** 存储，不是按单个视频
5. 注意：`state.currentPlaylist` 是运行时变量（不持久化）

### 自定义主题

CSS 变量控制整体配色，关键变量：
- `--bg`、`--surface`、`--border` — 背景色
- `--text-primary`、`--text-secondary` — 文字色
- `--accent`、`--accent-rgb` — 主题色（默认靛蓝 #6366f1）
- `--done` — 完成状态色（绿色）

## Known Pitfalls

| 问题 | 原因 | 解决 |
|------|------|------|
| `canplay` 只触发一次 | 使用了 `{ once: true }` | 去掉 options 或改为 `{ once: false }` |
| `removeAttribute('src')` + `load()` | 导致 `duration` 为 NaN | 用 `pause()` + `currentTime=0` + 设新 `src` |
| 播放列表进度继承 | `playPositions` 按 lesson 存储 | 仅在 `idx === 0` 时恢复 `savedPos` |
| 收藏按钮无反馈 | 空收藏时 `return` 静默退出 | 已改为弹出提示通知 |

## Additional Resources

- [architecture.md](architecture.md) — 前端 DOM 结构与 CSS 分区详解
- [server-guide.md](server-guide.md) — 服务器 API 参考与配置指南
- `assets/` — 完整源文件副本（learn.html / server.py / course-data.json / 设计文档）
