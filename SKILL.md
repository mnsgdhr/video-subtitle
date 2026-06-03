---
name: video-subtitle
description: 视频字幕自动生成与优化。流程：视频 → faster-whisper 转录 → 智能断句分割 → 领域术语纠错 → 输出 SRT。
---

# Video Subtitle Generator

从视频或音频文件自动生成高质量字幕，包含转录、智能断句、术语纠错全流程。

## 适用场景

- "给我这个视频做字幕"
- "这个字幕断句太长，帮我切短一点"
- "批量处理这些视频的字幕"
- "字幕里有术语错误，帮我修正"

---

## 工作流

```
Phase 1   确认输入
   1.1  确认视频/音频文件路径
   1.2  确认 faster-whisper 项目路径（含本地模型）
   1.3  确认领域类型（默认：德州扑克，可选：通用/自定义）

Phase 2   转录（可选）
   2.1  如果已有 SRT → 跳到 Phase 3
   2.2  用 faster-whisper large-v3 转录音频

Phase 3   智能断句
   3.1  按标点分割（。！？；，）
   3.2  按虚词分割（的了吗呢吧啊呀嘛着了过）
   3.3  按关联词分割（但是/所以/如果/因为/虽然/而且）
   3.4  控制每行 ≤16 字符
   3.5  时间戳按比例分配
   3.6  合并过短碎句

Phase 4   术语纠错
   4.1  根据领域应用纠错字典

Phase 5   输出
   5.1  SRT 文件输出到 corrected_subtitles/
```

---

## 使用方式

```bash
# 转录视频并生成字幕
python process.py --input video.mp4 --fw-dir /path/to/faster-whisper

# 处理已有 SRT 文件
python process.py --input /path/to/srt_folder

# 自定义每行字符数
python process.py --input video.mp4 --fw-dir /path/to/faster-whisper --max-chars 20

# 使用通用纠错（不应用特定领域规则）
python process.py --input video.mp4 --fw-dir /path/to/faster-whisper --domain generic
```

---

## 文件结构

```
video-subtitle/
├── SKILL.md              # 本文件
├── process.py            # 主处理脚本
├── requirements.txt      # 依赖
└── README.md             # 项目说明
```
