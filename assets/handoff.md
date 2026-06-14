# AI 学习平台 — 交接文档

## 访问方式

- **URL**: `http://localhost:8765/learn.html`
- **服务器**: `server.py`（端口 8765，127.0.0.1）
- **禁止**用 `file://` 直接打开 — `course-data.json` 会因 CORS 加载失败

## 关键文件

| 文件 | 说明 |
|------|------|
| learn.html | 前端单文件 SPA（HTML + CSS + JS） |
| server.py | Python HTTP 服务器 |
| course-data.json | 课程树结构数据 |
| summaries_cache.json | AI 总结缓存（自动生成） |

## 核心开发约定

- 所有前端逻辑在 `learn.html` 的单 `<script>` 块内
- 状态变更需在 `loadState()` 和 `saveState()` 中同时处理
- 新 CSS 加在 `/* AI Summary Panel */` 标记之前
- 服务器文件 `server.py` 和 `course-data.json` 与 `learn.html` 放在同一目录
- 验证方式：`http://localhost:8765/learn.html`

## 视频路径配置

视频 URL 格式：`/video/{prefix}/{relative-path}`

在 `server.py` 中配置 `VIDEO_ROOTS` 映射前缀到本地目录：

```python
VIDEO_ROOTS = {
    "course-a": r"C:\Users\you\Videos\CourseA",
}
```

`/video/course-a/01_intro/lesson.mp4` → `C:\Users\you\Videos\CourseA\01_intro\lesson.mp4`

## AI 功能配置（可选）

设置环境变量启用 AI 总结：

```bash
DEEPSEEK_API_KEY=sk-your-key python server.py
```

不设置不影响核心功能（视频播放、进度追踪等）。

## 已知 Pitfalls

| 问题 | 原因 | 解决 |
|------|------|------|
| `canplay` 只触发一次 | `{ once: true }` 选项 | 去掉或改为 `{ once: false }` |
| 视频切换续播位置继承 | 浏览器缓存旧播放位置 | `pause()` + `currentTime=0` + `loadedmetadata` 二次确认 |
| `state` 不可从 Playwright 访问 | `let` 声明不在 `window` | 用 `localStorage` 验证状态 |
| 空收藏时按钮无反馈 | `return` 静默退出 | 已改为弹出通知 |
