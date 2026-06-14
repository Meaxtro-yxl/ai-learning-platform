"""Local HTTP server for the AI learning navigator.
Serves the single-page app, video/notes files, quiz API, and AI summary endpoints.
"""
import http.server
import os
import sys
import urllib.parse
import webbrowser
import json
import subprocess
import threading
import uuid
import tempfile
import time
from pathlib import Path

PORT = 8765
ROOT = Path(__file__).parent.resolve()

# Map URL mount points to real directories.
# IMPORTANT: Configure these paths to match YOUR local video directories.
# Key = URL prefix used in course-data.json video paths
# Value = absolute path to the root directory on your machine
#
# Example:
#   VIDEO_ROOTS = {
#       "course-a": r"D:\courses\Python基础教程",
#       "course-b":   r"E:\courses\进阶实战项目",
#   }
#
# A URL like /video/course-a/01_basics/day01/lesson.mp4
# will resolve to: D:\courses\Python基础教程\01_basics\day01\lesson.mp4
VIDEO_ROOTS = {
    # "example": r"C:\path\to\your\course\videos",
}

# Fallback: scan common drives for course directories
def auto_detect_video_roots():
    """Auto-detect course directories if VIDEO_ROOTS is empty.
    
    Scans common drive letters for directories containing course keywords.
    Customize the 'candidates' list below to match your course providers.
    """
    import glob as _g
    results = {}
    # Customize these keywords to match your course folder naming conventions
    candidates = [
        ("example", "课程"),
        ("example", "course"),
        ("example", "学习"),
    ]
    for mount, keyword in candidates:
        if mount in results:
            continue
        for drive in ["D:\\", "E:\\", "F:\\", "C:\\"]:
            for item in _g.glob(f"{drive}*{keyword}*"):
                if os.path.isdir(item):
                    results[mount] = item
                    print(f"  Auto-detected {mount}: {item}")
                    break
            if mount in results:
                break
    return results


FALLBACK = True
# DeepSeek API key — MUST be set via environment variable DEEPSEEK_API_KEY
# Usage: DEEPSEEK_API_KEY=sk-your-key python server.py
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
QUIZ_FILE = ROOT / "quiz_data.json"
SUMMARIES_FILE = ROOT / "summaries_cache.json"

# AI Summary async task store
_ai_tasks = {}
_ai_tasks_lock = threading.Lock()

WHISPER_MODEL = "tiny"  # tiny/base/small/medium/large (tiny=72MB最快, small~500MB平衡)


def _resolve_video_path(video_url):
    """Resolve /video/<mount>/... URL to absolute filesystem path."""
    parts = video_url[7:].split("/", 1)
    if len(parts) != 2:
        return None
    mount, rel = parts
    root_dir = VIDEO_ROOTS.get(mount)
    if not root_dir or not os.path.isdir(root_dir):
        return None
    rel = urllib.parse.unquote(rel)
    resolved = os.path.normpath(os.path.join(root_dir, rel))
    if os.path.commonpath([resolved, root_dir]) == root_dir:
        return resolved
    return None


def _run_ai_summary(task_id, video_path, lesson_title, stage_title):
    """Async: extract audio → transcribe → summarize + quiz."""
    try:
        with _ai_tasks_lock:
            _ai_tasks[task_id] = {"status": "extracting", "progress": 0, "message": "正在提取音频..."}

        # Step 1: Extract audio with ffmpeg
        wav_fd, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(wav_fd)
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            wav_path
        ]
        subprocess.run(cmd, capture_output=True, timeout=300, check=True)

        with _ai_tasks_lock:
            _ai_tasks[task_id] = {"status": "transcribing", "progress": 20, "message": "正在语音识别..."}

        # Step 2: Transcribe with openai-whisper
        import whisper
        model = whisper.load_model(WHISPER_MODEL)
        result = model.transcribe(wav_path, language="zh", beam_size=1, fp16=False, condition_on_previous_text=False)
        transcript_parts = []
        for seg in result["segments"]:
            transcript_parts.append(f"[{_fmt_time(seg['start'])}] {seg['text'].strip()}")
        transcript = "\n".join(transcript_parts)
        duration = result.get("duration", 0)
        os.unlink(wav_path)

        with _ai_tasks_lock:
            _ai_tasks[task_id] = {"status": "summarizing", "progress": 60, "message": "正在AI总结..."}

        # Step 3: DeepSeek summary + quiz
        summary, questions = _deepseek_summarize(transcript, lesson_title, stage_title)

        with _ai_tasks_lock:
            _ai_tasks[task_id] = {
                "status": "done", "progress": 100,
                "summary": summary, "questions": questions,
                "transcript": transcript,
                "duration_seconds": duration,
            }

    except subprocess.CalledProcessError as e:
        with _ai_tasks_lock:
            _ai_tasks[task_id] = {"status": "error", "message": f"音频提取失败: {e.stderr.decode() if e.stderr else str(e)}"}
    except Exception as e:
        with _ai_tasks_lock:
            _ai_tasks[task_id] = {"status": "error", "message": str(e)}


def _fmt_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _deepseek_summarize(transcript, lesson_title, stage_title, quiz_count=5):
    """Send transcript to DeepSeek, get summary + quiz questions."""
    import urllib.request as urlreq

    context = f"课程: {stage_title} - {lesson_title}" if stage_title else f"课时: {lesson_title}"

    prompt = f"""你是一个AI教育专家。以下是课程视频的语音转录文本，请完成两项任务：

{context}

【语音转录文本】
{transcript[:12000]}

任务一：总结
用中文写出课程内容的结构化总结，包括：
1. 本节核心知识点（要点列表）
2. 重点难点（要点列表）
3. 一句话总结

任务二：出题
基于内容生成 {quiz_count} 道题目（选择题与简答题各约一半，覆盖不同知识点）。

请严格按以下JSON格式输出，不要包含其他内容：
{{
  "summary": {{
    "core_points": ["知识点1", "知识点2", ...],
    "key_difficulties": ["难点1", "难点2", ...],
    "one_liner": "一句话总结"
  }},
  "questions": [
    {{
      "type": "choice",
      "question": "题目内容",
      "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
      "answer": 0,
      "source_time": "时间戳，如 12:30"
    }},
    {{
      "type": "short",
      "question": "题目内容",
      "answer": "参考答案",
      "source_time": "时间戳"
    }}
  ]
}}"""

    api_body = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个严谨的AI教育专家，只输出JSON，不输出任何其他内容。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 4096
    }, ensure_ascii=False).encode("utf-8")

    api_req = urlreq.Request(DEEPSEEK_API_URL, data=api_body)
    api_req.add_header("Content-Type", "application/json")
    api_req.add_header("Authorization", f"Bearer {DEEPSEEK_API_KEY}")

    with urlreq.urlopen(api_req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    raw = result["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    data = json.loads(raw)
    for q in data.get("questions", []):
        q["lesson_title"] = lesson_title
        q["stage_title"] = stage_title
    return data.get("summary", {}), data.get("questions", [])


def _deepseek_quiz_only(transcript, lesson_title, stage_title, count=5):
    """Generate quiz questions only from a cached transcript."""
    import urllib.request as urlreq

    context = f"课程: {stage_title} - {lesson_title}" if stage_title else f"课时: {lesson_title}"
    prompt = f"""你是一个AI教育专家。以下是课程视频的语音转录文本，请基于内容出题。

{context}

【语音转录文本】
{transcript[:12000]}

请生成 {count} 道题目（选择题与简答题各约一半，覆盖不同知识点），题目与上次生成的务必不同。

请严格按以下JSON格式输出，不要包含其他内容：
{{
  "questions": [
    {{
      "type": "choice",
      "question": "题目内容",
      "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
      "answer": 0,
      "source_time": "时间戳，如 12:30"
    }},
    {{
      "type": "short",
      "question": "题目内容",
      "answer": "参考答案",
      "source_time": "时间戳"
    }}
  ]
}}"""

    api_body = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个严谨的AI教育专家，只输出JSON，不输出任何其他内容。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4096
    }, ensure_ascii=False).encode("utf-8")

    api_req = urlreq.Request(DEEPSEEK_API_URL, data=api_body)
    api_req.add_header("Content-Type", "application/json")
    api_req.add_header("Authorization", f"Bearer {DEEPSEEK_API_KEY}")

    with urlreq.urlopen(api_req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    raw = result["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    data = json.loads(raw)
    for q in data.get("questions", []):
        q["lesson_title"] = lesson_title
        q["stage_title"] = stage_title
    return data.get("questions", [])


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def translate_path(self, path):
        """Override to support /video/<mount>/... URLs."""
        if path.startswith("/video/"):
            parts = path[7:].split("/", 1)
            if len(parts) == 2:
                mount, rel = parts
                root_dir = VIDEO_ROOTS.get(mount)
                if root_dir and os.path.isdir(root_dir):
                    rel = urllib.parse.unquote(rel)
                    resolved = os.path.normpath(os.path.join(root_dir, rel))
                    # Security: ensure resolved path stays within root_dir
                    if os.path.commonpath([resolved, root_dir]) == root_dir:
                        return resolved
        return super().translate_path(path)

    def log_message(self, format, *args):
        if any(str(a) in ("206", "304", "416") for a in args):
            return
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), format % args))

    def do_POST(self):
        if self.path == "/api/generate-quiz":
            self._handle_generate_quiz()
        elif self.path == "/api/quiz-data":
            self._handle_quiz_data_save()
        elif self.path == "/api/ai-summary":
            self._handle_ai_summary_start()
        elif self.path == "/api/ai-quiz":
            self._handle_ai_quiz()
        elif self.path == "/api/summaries":
            self._handle_summaries_save()
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path == "/api/quiz-data":
            self._handle_quiz_data_load()
        elif self.path.startswith("/api/ai-summary"):
            self._handle_ai_summary_poll()
        elif self.path == "/api/summaries":
            self._handle_summaries_load()
        else:
            super().do_GET()

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_quiz_data_save(self):
        try:
            data = self._read_body()
            with open(QUIZ_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._send_json({"ok": True})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_quiz_data_load(self):
        try:
            if QUIZ_FILE.exists():
                with open(QUIZ_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._send_json(data)
            else:
                self._send_json({})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_summaries_save(self):
        try:
            data = self._read_body()
            with open(SUMMARIES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._send_json({"ok": True})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_summaries_load(self):
        try:
            if SUMMARIES_FILE.exists():
                with open(SUMMARIES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._send_json(data)
            else:
                self._send_json({})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_ai_summary_start(self):
        """POST /api/ai-summary  → start async processing, return task_id."""
        try:
            req = self._read_body()
            video_url = req.get("video", "")
            lesson_title = req.get("lesson_title", "")
            stage_title = req.get("stage_title", "")

            if not video_url:
                self._send_json({"error": "缺少 video 参数"}, 400)
                return

            video_path = _resolve_video_path(video_url)
            if not video_path or not os.path.isfile(video_path):
                self._send_json({"error": f"视频文件不存在: {video_url}"}, 400)
                return

            task_id = str(uuid.uuid4())[:8]
            with _ai_tasks_lock:
                _ai_tasks[task_id] = {"status": "pending", "progress": 0, "message": "排队中..."}

            t = threading.Thread(target=_run_ai_summary,
                                 args=(task_id, video_path, lesson_title, stage_title),
                                 daemon=True)
            t.start()

            self._send_json({"ok": True, "task_id": task_id})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_ai_summary_poll(self):
        """GET /api/ai-summary?task_id=xxx  → poll task status/results."""
        try:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            task_id = params.get("task_id", [None])[0]

            if not task_id:
                self._send_json({"error": "缺少 task_id 参数"}, 400)
                return

            with _ai_tasks_lock:
                task = _ai_tasks.get(task_id)
            if not task:
                self._send_json({"error": "任务不存在或已过期"}, 404)
                return

            self._send_json(task)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_ai_quiz(self):
        """POST /api/ai-quiz  → generate quiz questions from cached transcript."""
        try:
            body = self._read_body()
            transcript = body.get("transcript", "")
            lesson_title = body.get("lesson_title", "")
            stage_title = body.get("stage_title", "")
            count = int(body.get("count", 5))

            if not transcript:
                self._send_json({"error": "缺少语音转录文本 (transcript)"}, 400)
                return
            if count < 1 or count > 20:
                self._send_json({"error": "题目数量需在 1-20 之间"}, 400)
                return

            questions = _deepseek_quiz_only(transcript, lesson_title, stage_title, count)
            self._send_json({"ok": True, "questions": questions})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_generate_quiz(self):
        if not DEEPSEEK_API_KEY:
            self._send_json({"error": "API Key 未配置，请在环境变量 DEEPSEEK_API_KEY 中设置"}, 500)
            return

        try:
            req = self._read_body()
            annotations = req.get("annotations", [])
            lesson_title = req.get("lesson_title", "")
            stage_title = req.get("stage_title", "")
            count = req.get("count", 3)

            if not annotations:
                self._send_json({"error": "缺少知识点数据"}, 400)
                return

            # Build prompt
            knowledge_items = []
            for a in annotations:
                tag = a.get("tag", "")
                text = a.get("text", "").strip()
                time = a.get("time", "")
                if text:
                    item = f"- [{tag}] {text}"
                    if time:
                        item += f" (时间戳: {time})"
                    knowledge_items.append(item)

            if not knowledge_items:
                self._send_json({"error": "知识点文本为空"}, 400)
                return

            context = f"课程: {stage_title} - {lesson_title}" if stage_title else f"课时: {lesson_title}"

            prompt = f"""你是一个AI教育出题专家。根据以下课程知识点的标注内容，生成{count}道题目。

{context}

知识点列表：
{chr(10).join(knowledge_items)}

要求：
1. 生成 {count} 道题目，其中至少包含1道简答题（type: "short"），其余为选择题（type: "choice"）
2. 选择题为单选题，4个选项，格式如 "A. 选项内容"
3. 简答题要求用1-3句话回答
4. 题目难度适中，覆盖不同知识点
5. 严格输出纯JSON数组，不要包含其他文字：

[
  {{
    "type": "choice",
    "question": "题目内容",
    "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
    "answer": 0,
    "source_time": "原始标注的时间戳，如 12:30"
  }},
  {{
    "type": "short",
    "question": "题目内容",
    "answer": "参考答案",
    "source_time": "原始标注的时间戳"
  }}
]"""

            # Call DeepSeek API
            import urllib.request as urlreq
            api_body = json.dumps({
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个严谨的AI教育出题专家，只输出JSON数组，不输出任何其他内容。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 4096
            }, ensure_ascii=False).encode("utf-8")

            api_req = urlreq.Request(DEEPSEEK_API_URL, data=api_body)
            api_req.add_header("Content-Type", "application/json")
            api_req.add_header("Authorization", f"Bearer {DEEPSEEK_API_KEY}")

            with urlreq.urlopen(api_req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            content = result["choices"][0]["message"]["content"].strip()
            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            questions = json.loads(content)

            # Attach lesson info to each question
            for q in questions:
                q["lesson_title"] = lesson_title
                q["stage_title"] = stage_title

            self._send_json({"ok": True, "questions": questions})

        except json.JSONDecodeError as e:
            self._send_json({"error": f"AI返回内容解析失败: {e}\n原始内容: {content[:500] if 'content' in dir() else 'N/A'}"}, 500)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)


def main():
    global VIDEO_ROOTS

    # Auto-detect if no paths configured
    missing = [k for k, v in VIDEO_ROOTS.items() if not v or not os.path.isdir(v)]
    if missing:
        detected = auto_detect_video_roots()
        VIDEO_ROOTS.update({k: v for k, v in detected.items() if v and os.path.isdir(v)})

    os.chdir(str(ROOT))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}/learn.html"
    print(f"\n  Local server: {url}")
    print(f"  Video mounts: {json_dumps(VIDEO_ROOTS, indent=2)}")
    print(f"  Press Ctrl+C to stop.\n")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.shutdown()


def json_dumps(obj, **kw):
    import json
    return json.dumps(obj, ensure_ascii=False, **kw)


if __name__ == "__main__":
    main()
