# Video Subtitle Generator

🎬 从视频或音频自动生成高质量字幕，支持智能断句、术语纠错、质量审查。

## 特性

- **自动转录**：基于 faster-whisper (large-v3) 的中文语音识别
- **智能断句**：按标点、虚词、关联词多维度分割，每行 ≤ 16 字符
- **术语纠错**：内置德州扑克领域纠错字典（可扩展自定义领域）
- **质量审查**：自动检测并修复单字行、纯标点行、极短行、行首标点
- **时间戳修复**：消除字幕时间重叠
- **英文单词修复**：修复被断开的英文单词（如 de/ny → deny）
- **批量处理**：支持单文件或整个目录

## 安装

```bash
pip install -r requirements.txt
```

需要 CUDA 环境和 faster-whisper 本地模型。推荐使用 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 官方项目下载模型。

## 完整处理流程

```bash
# 1. 转录 + 智能断句 + 术语纠错
python process.py --input video.mp4 --fw-dir /path/to/faster-whisper --domain poker

# 2. 质量审查（修复单字/标点行/行首标点等）
python review_and_fix.py --input ./corrected_subtitles

# 3. 修复时间戳重叠
python fix_timestamps.py --input ./final_subtitles

# 4. 修复英文单词断裂（如 de/ny → deny）
python fix_broken_words.py --input ./final_subtitles
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--input` | 视频/音频文件路径，或 SRT 目录 | 必需 |
| `--fw-dir` | faster-whisper 项目路径（含本地模型） | 无 |
| `--domain` | 纠错领域：`poker` / `generic` | `poker` |
| `--max-chars` | 每行最大字符数 | `16` |
| `--output` | 输出目录 | 输入同级 `corrected_subtitles/` |

## 纠错字典（德州扑克领域）

内置 80+ 条纠错规则，覆盖：

- **位置术语**：前卫→前位、贩卖前→翻牌前
- **动作术语**：根柱→跟注、泉下→全下、炸虎→诈唬
- **牌面表示**：K圈→KQ、狮狮→TT、口袋队→口袋对
- **听牌术语**：team牌→听牌、桶花→同花、定牌→听牌
- **策略术语**：sour→solver、棋牌率→弃牌率、套持→套池

可在 `process.py` 的 `CORRECTIONS_BY_DOMAIN` 中添加自定义领域规则。

## 英文单词断裂修复

修复策略：
1. **断裂词**：至少一个片段 <4 字母 → 直接拼接（de+ny=deny）
2. **短词对**：两个都是 4-6 字母的短词 → 加空格（deny+equity=deny equity）
3. **合并后超长**：把英文词移到下一行

## 许可证

MIT
