"""
Video Subtitle Generator
========================
视频字幕自动生成与优化工具

流程:
1. faster-whisper 转录（或加载已有 SRT）
2. 智能断句分割
3. 领域术语纠错
4. 输出 SRT

用法:
  python process.py --input <视频/音频/目录> --fw-dir <faster-whisper路径>
  python process.py --input <SRT目录> --fw-dir <faster-whisper路径> --transcribe-only
"""
import os
import sys
import argparse
import pysubs2

sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 配置
# ============================================================

DEFAULT_MAX_CHARS = 16
DEFAULT_MIN_CHARS = 4
DEFAULT_MERGE_GAP = 0.2
DEFAULT_MERGE_MAX = 6
DEFAULT_DOMAIN = "poker"

# 分割优先级
PUNCT_HIGH = set('。！？\n')
PUNCT_MID = set('；;')
PUNCT_LOW = set('，,')
AFTER_PARTICLE = list('的了吗呢吧啊呀嘛着了过')
BEFORE_CONJ = ['但是', '可是', '不过', '然而', '所以', '因此',
               '如果', '假如', '因为', '由于', '虽然', '尽管',
               '而且', '并且', '或者', '否则', '那么']


# ============================================================
# 纠错字典
# ============================================================

CORRECTIONS_BY_DOMAIN = {
    "poker": [
        # 游戏名
        ("雪战游戏", "血战鱿鱼"), ("雪战犹豫", "血战鱿鱼"),
        ("学战由于", "血战鱿鱼"), ("雪山里面", "血战里面"),
        ("雪战里面", "血战里面"), ("雪战", "血战"), ("学战", "血战"),
        # 位置
        ("前卫", "前位"), ("后卫", "后位"),
        ("贩卖前", "翻牌前"), ("贩卖后", "翻牌后"),
        ("中节位", "中间位"), ("卡到五", "卡到UTG"), ("卡到5", "卡到UTG"),
        # 动作
        ("根柱", "跟注"), ("泉下", "全下"), ("盲柱", "盲注"),
        ("下大柱", "下大注"), ("下小柱", "下小注"), ("下柱", "下注"),
        ("套持", "套池"), ("起牌", "弃牌"),
        ("跟住", "跟注"), ("跟住范围", "跟注范围"), ("的跟住", "的跟注"),
        ("夹注", "加注"), ("夹住", "夹击"),
        ("棋牌率", "弃牌率"), ("气排率", "弃牌率"),
        # 诈唬
        ("炸虎", "诈唬"), ("炸火", "诈唬"), ("炸户", "诈唬"),
        ("账户", "诈唬"), ("的账户", "的诈唬"), ("去账户", "去诈唬"),
        ("抓炸牌", "抓诈牌"),
        # 牌面
        ("口袋队", "口袋对"), ("顶队", "顶对"), ("超队", "超对"),
        ("中对", "中对"), ("底队", "底对"), ("中队", "中对"),
        ("代码数量", "筹码数量"), ("代码", "筹码"),
        ("狮狮", "TT"), ("十十", "TT"),
        # 牌面 Q/J
        ("K圈", "KQ"), ("A圈", "AQ"), ("Q圈", "QQ"),
        ("K钩", "KJ"), ("A钩", "AJ"),
        ("圈A", "QA"), ("圈K", "QK"),
        ("同花圈", "同花Q"), ("同花钩", "同花J"),
        ("不同花圈", "不同花Q"), ("不同花钩", "不同花J"),
        ("的圈", "的Q"), ("的钩", "的J"),
        # 听牌
        ("team牌", "听牌"), ("ting牌", "听牌"), ("定牌", "听牌"),
        ("的定牌", "的听牌"), ("定牌的", "听牌的"),
        ("性牌", "听牌"),
        ("铜花", "同花"), ("桶花", "同花"),
        ("童话连张", "同花连张"), ("童话", "同花"),
        ("小桶花", "小同花"), ("大桶花", "大同花"),
        # 策略
        ("sour", "solver"),
        ("imp只是", "limp只是"), ("imp进去", "limp进去"),
        ("SP2", "SPR"), ("logic", "Lojack"),
        ("奥斯", "outs"), ("凹子", "outs"),
        ("板板过牌", "百分百过牌"), ("百百过牌", "百分百过牌"),
        # raise
        ("会race", "会raise"), ("去race", "去raise"),
        ("会去race", "会去raise"), ("rate他", "raise他"),
        ("race过多", "raise过多"), ("race太宽", "raise太宽"),
        # 其他
        ("枪牌", "强牌"), ("强盘", "强牌"), ("挤牙", "挤压"),
        ("多条件慢玩", "多人底池慢玩"), ("多条件漫玩", "多人底池慢玩"),
        ("多人体试", "多人底池"), ("多人体这边", "多人底池这边"),
        ("提交小的", "弃掉小的"), ("抢鱼", "抓鱼"),
        ("发D牌", "发公牌"), ("D牌", "公牌"),
        ("多加负", "多加注"), ("敌人", "对手"),
        ("下卡顺", "卡顺"), ("上卡顺", "卡顺"),
        ("同化定牌", "同花听牌"), ("后门化定牌", "后门花听牌"),
        ("有利被止", "有利位置"), ("靠的范围", "call的范围"),
        ("去靠", "去call"), ("能靠", "能call"), ("靠住", "call住"),
        ("靠下来", "call下来"),
    ],
    "generic": [],
}


# ============================================================
# 核心函数
# ============================================================

def find_split_point(text, max_chars, min_chars=DEFAULT_MIN_CHARS):
    """在 text[:max_chars] 范围内找最佳分割点"""
    if len(text) <= max_chars:
        return len(text)
    search = text[:max_chars]

    for p in PUNCT_HIGH:
        pos = search.rfind(p)
        if pos >= min_chars and len(text) - pos - 1 >= min_chars:
            return pos + 1

    for p in PUNCT_MID:
        pos = search.rfind(p)
        if pos >= min_chars and len(text) - pos - 1 >= min_chars:
            return pos + 1

    for p in PUNCT_LOW:
        pos = search.rfind(p)
        if pos >= min_chars and len(text) - pos - 1 >= min_chars:
            return pos + 1

    for sc in AFTER_PARTICLE:
        pos = search.rfind(sc)
        if pos >= min_chars and len(text) - pos - len(sc) >= min_chars:
            return pos + len(sc)

    for conj in BEFORE_CONJ:
        pos = search.find(conj)
        if pos >= min_chars and len(text) - pos > min_chars:
            return pos

    pos = search.rfind(' ')
    if pos >= min_chars:
        return pos + 1

    return max_chars


def split_segment(text, start, end, max_chars=DEFAULT_MAX_CHARS):
    """将一段文本按语义分割，时间按比例分配"""
    if len(text) <= max_chars:
        return [(text, start, end)]
    results = []
    remaining = text
    current_start = start
    duration = end - start

    while len(remaining) > max_chars:
        split_at = find_split_point(remaining, max_chars)
        part = remaining[:split_at].strip()
        if part:
            ratio = len(part) / len(remaining)
            seg_dur = duration * ratio
            seg_end = current_start + seg_dur
            results.append((part, current_start, seg_end))
            current_start = seg_end
            duration -= seg_dur
        remaining = remaining[split_at:].strip()

    if remaining.strip():
        results.append((remaining.strip(), current_start, end))
    return results


def merge_short_cues(cues, gap=DEFAULT_MERGE_GAP, max_chars=DEFAULT_MAX_CHARS):
    """合并过短的相邻片段"""
    merged = []
    for text, start, end in cues:
        if merged and (start - merged[-1][1]) < gap and len(text) < DEFAULT_MERGE_MAX:
            prev_text, prev_start, prev_end = merged[-1]
            if len(prev_text) + len(text) <= max_chars:
                merged[-1] = (prev_text + text, prev_start, end)
                continue
        merged.append((text, start, end))
    return merged


def correct_text(text, corrections):
    """应用纠错规则"""
    for wrong, right in corrections:
        text = text.replace(wrong, right)
    return text


def process_srt_file(input_path, output_path, corrections, max_chars=DEFAULT_MAX_CHARS):
    """处理已有 SRT：分割 + 纠错"""
    subs = pysubs2.load(input_path, encoding='utf-8')
    new_subs = pysubs2.SSAFile()
    new_subs.styles = subs.styles

    total_split = 0
    for line in subs:
        text = line.text.replace('\n', '').replace('\\N', '').strip()
        if not text:
            continue

        # 纠错
        text = correct_text(text, corrections)

        # 分割
        parts = split_segment(text, line.start / 1000, line.end / 1000, max_chars)
        total_split += len(parts)

        for part_text, part_start, part_end in parts:
            event = pysubs2.SSAEvent(
                start=int(part_start * 1000),
                end=int(part_end * 1000)
            )
            event.text = part_text
            new_subs.append(event)

    # 合并
    cues = [(e.text, e.start / 1000, e.end / 1000) for e in new_subs]
    merged = merge_short_cues(cues)

    # 保存
    final_subs = pysubs2.SSAFile()
    final_subs.styles = new_subs.styles
    for text, start, end in merged:
        event = pysubs2.SSAEvent(start=int(start * 1000), end=int(end * 1000))
        event.text = text
        final_subs.append(event)
    final_subs.save(output_path, encoding='utf-8')

    return len(subs), len(final_subs)


def transcribe_and_process(video_path, output_path, fw_dir, corrections,
                           max_chars=DEFAULT_MAX_CHARS):
    """转录 + 分割 + 纠错"""
    from faster_whisper import WhisperModel

    hf_cache = os.path.join(fw_dir, "huggingface")
    model = WhisperModel(
        "Systran/faster-whisper-large-v3",
        device="cuda",
        compute_type="float16",
        download_root=hf_cache,
        local_files_only=True
    )

    segments, info = model.transcribe(
        video_path,
        language='zh',
        word_timestamps=True,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)
    )

    # 分割 + 纠错
    all_cues = []
    original_count = 0
    for seg in segments:
        original_count += 1
        text = correct_text(seg.text.strip(), corrections)
        parts = split_segment(text, seg.start, seg.end, max_chars)
        all_cues.extend(parts)

    # 合并
    merged = merge_short_cues(all_cues)

    # 保存
    subs = pysubs2.SSAFile()
    for text, start, end in merged:
        event = pysubs2.SSAEvent(start=int(start * 1000), end=int(end * 1000))
        event.text = text
        subs.append(event)
    subs.save(output_path, encoding='utf-8')

    return original_count, len(subs)


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='视频字幕生成与优化')
    parser.add_argument('--input', required=True, help='视频/音频文件路径，或 SRT 目录')
    parser.add_argument('--fw-dir', default=None, help='faster-whisper 项目路径')
    parser.add_argument('--domain', default='poker', choices=['poker', 'generic'], help='纠错领域')
    parser.add_argument('--max-chars', type=int, default=DEFAULT_MAX_CHARS, help='每行最大字符数')
    parser.add_argument('--output', default=None, help='输出目录（默认 corrected_subtitles/）')

    args = parser.parse_args()

    # 准备输出目录
    if args.output:
        output_dir = args.output
    else:
        input_parent = os.path.dirname(os.path.abspath(args.input))
        output_dir = os.path.join(input_parent, "corrected_subtitles")
    os.makedirs(output_dir, exist_ok=True)

    corrections = CORRECTIONS_BY_DOMAIN.get(args.domain, [])

    input_path = os.path.abspath(args.input)

    # 判断输入类型
    if os.path.isdir(input_path):
        # 目录：处理所有 SRT
        srt_files = [f for f in os.listdir(input_path) if f.endswith('.srt')]
        print(f"找到 {len(srt_files)} 个 SRT 文件\n")
        for srt_file in sorted(srt_files):
            inp = os.path.join(input_path, srt_file)
            out = os.path.join(output_dir, srt_file)
            try:
                orig, final = process_srt_file(inp, out, corrections, args.max_chars)
                print(f"[OK] {srt_file}: {orig} -> {final} 条")
            except Exception as e:
                print(f"[FAIL] {srt_file}: {e}")
    elif os.path.isfile(input_path):
        ext = os.path.splitext(input_path)[1].lower()
        basename = os.path.basename(input_path)

        if ext == '.srt':
            out_file = os.path.join(output_dir, basename)
            orig, final = process_srt_file(input_path, out_file, corrections, args.max_chars)
            print(f"[OK] {basename}: {orig} -> {final} 条")
        elif ext in ('.mp4', '.mkv', '.avi', '.mov', '.mp3', '.wav', '.m4a'):
            out_file = os.path.join(output_dir, basename.rsplit('.', 1)[0] + '.srt')
            if not args.fw_dir:
                print("错误: 转录需要 --fw-dir 参数指定 faster-whisper 项目路径")
                sys.exit(1)
            orig, final = transcribe_and_process(
                input_path, out_file, args.fw_dir, corrections, args.max_chars
            )
            print(f"[OK] {basename}: {orig} -> {final} 条")
        else:
            print(f"不支持的文件格式: {ext}")
            sys.exit(1)
    else:
        print(f"路径不存在: {input_path}")
        sys.exit(1)

    print(f"\n完成！输出目录: {output_dir}")


if __name__ == '__main__':
    main()
