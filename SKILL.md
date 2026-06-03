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

Phase 5   质量审查与修复
   5.1  检测问题行：单字行、纯标点行、极短行（≤2字）
   5.2  检测行首标点（，。！？;等）
   5.3  检测截断英文（如 on, er, se, ker 等）
   5.4  检测逗号结尾的短行（≤5字且无完整主谓结构）
   5.5  行首标点：强制与前一行合并并重分
   5.6  合并到前/后一行（如合并后≤16字）
   5.7  三行合并重分：前后超长时合并前+当前+后，按标点重分
   5.8  多轮迭代直到无问题行

Phase 6   时间戳修复
   6.1  检测时间戳重叠（当前行结束 > 下一行开始）
   6.2  将当前行结束时间设为下一行开始时间
   6.3  确保每行至少显示 300ms

Phase 7   输出
   7.1  SRT 文件输出到 fixed_timestamps/
   7.2  报告处理统计
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

### 质量审查（修复问题行）

```bash
python review_and_fix.py --input ./corrected_subtitles
```

### 修复时间戳重叠

```bash
python fix_timestamps.py --input ./final_subtitles
```

---

## 文件结构

```
video-subtitle/
├── SKILL.md              # 本文件
├── process.py            # 主处理脚本（转录+断句+纠错）
├── review_and_fix.py     # 质量审查与修复工具
├── fix_timestamps.py     # 时间戳重叠修复工具
├── requirements.txt      # 依赖
└── README.md             # 项目说明
```

## 质量审查规则

### 问题行定义
1. **极短行**：≤2 字符
2. **纯标点行**：仅包含标点符号
3. **行首标点**：以 ，。！？; 等开头
4. **截断英文**：1-4 字母（如 on, er, se, ker）
5. **短逗号行**：≤5 字且以逗号结尾，且无完整主谓结构

### 修复策略（按优先级）
1. **行首标点**：强制与前一行合并，三行重分
2. **合并到前一行**：合并后 ≤16 字则合并
3. **合并到后一行**：合并后 ≤16 字则合并
4. **三行合并重分**：合并前+当前+后，按标点分割成 ≤16 字
5. **多轮迭代**：最多 50 轮，直到无问题行
