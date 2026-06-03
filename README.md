# Video Subtitle Generator

🎬 从视频或音频自动生成高质量字幕，支持智能断句和领域术语纠错。

## 特性

- **自动转录**：基于 faster-whisper (large-v3) 的中文语音识别
- **智能断句**：按标点、虚词、关联词多维度分割，每行 ≤ 16 字符
- **术语纠错**：内置德州扑克领域纠错字典（可扩展自定义领域）
- **质量审查**：自动检测并修复单字行、纯标点行、极短行、行首标点、截断英文、短逗号行
- **批量处理**：支持单文件或整个目录
- **时间同步**：分割后时间戳按比例精确分配

## 安装

```bash
pip install -r requirements.txt
```

需要 CUDA 环境和 faster-whisper 本地模型。推荐使用 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 官方项目下载模型。

## 快速开始

### 从视频生成字幕

```bash
python process.py --input video.mp4 --fw-dir /path/to/faster-whisper
```

### 优化已有 SRT 字幕

```bash
python process.py --input ./subtitles_folder
```

### 质量审查（修复单字/极短行）

```bash
python review_and_fix.py --input ./corrected_subtitles
```

### 自定义参数

```bash
python process.py --input video.mp4 \
                  --fw-dir /path/to/faster-whisper \
                  --domain poker \
                  --max-chars 16 \
                  --output ./output
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--input` | 视频/音频文件路径，或 SRT 目录 | 必需 |
| `--fw-dir` | faster-whisper 项目路径（含本地模型） | 无 |
| `--domain` | 纠错领域：`poker` / `generic` | `poker` |
| `--max-chars` | 每行最大字符数 | `16` |
| `--output` | 输出目录 | 输入同级 `corrected_subtitles/` |

## 断句算法

字幕分割按优先级进行：

1. **强标点**：`。 ！ ？ \n` — 必须分割
2. **中标点**：`； ;` — 优先分割
3. **弱标点**：`， ,` — 次优先
4. **虚词后**：`的 了 吗 呢 吧 啊 呀 嘛 着 了 过`
5. **关联词前**：`但是 所以 如果 因为 虽然 而且`
6. **空格**：备选
7. **强制切**：前 5 步未找到时在 max_chars 处切

合并规则：相邻片段间隔 <0.2s 且内容 <6 字则自动合并。

## 纠错字典（德州扑克领域）

内置 80+ 条纠错规则，覆盖：

- **位置术语**：前卫→前位、贩卖前→翻牌前
- **动作术语**：根柱→跟注、泉下→全下、炸虎→诈唬
- **牌面表示**：K圈→KQ、狮狮→TT、口袋队→口袋对
- **听牌术语**：team牌→听牌、桶花→同花、定牌→听牌
- **策略术语**：sour→solver、棋牌率→弃牌率、套持→套池

可在 `process.py` 的 `CORRECTIONS_BY_DOMAIN` 中添加自定义领域规则。

## 质量审查规则

自动检测并修复以下问题：
1. **极短行**：≤2 字符
2. **纯标点行**：仅包含标点
3. **行首标点**：以 ，。！？; 开头
4. **截断英文**：1-4 字母（如 on, er, se）
5. **短逗号行**：≤5 字且以逗号结尾，无完整主谓

修复策略：行首标点强制与前一行合并；其他情况合并到前/后行或三行重分；最多 50 轮迭代。

## 输出示例

输入视频字幕（Whisper 原始输出）：
```
接下来我们来看短码这种情况其实是非常常见的在很多的
```

处理后输出：
```
接下来我们来看短码这种情况
其实是非常常见的
在很多的游戏刚开始的阶段
```

## 许可证

MIT
