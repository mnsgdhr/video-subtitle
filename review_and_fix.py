"""
字幕质量修复 V6 - 激进版
处理策略：
1. 合并极短行到前/后行
2. 前后都超长时：合并前+当前+后，重新分割
"""
import pysubs2
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

INPUT_DIR = r"F:\video\血战鱿鱼\精剪版\corrected_subtitles"
OUTPUT_DIR = os.path.join(INPUT_DIR, "final_subtitles")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MAX_CHARS = 16
PUNCT_SET = set('，。！？；、,.!?;…—～（）\n ')


def is_too_short(text):
    t = text.strip()
    if len(t) <= 1:
        return True
    if len(t) <= 2:
        return True
    if all(c in PUNCT_SET for c in t):
        return True
    return False


def smart_split(text):
    """把文本分割成≤MAX_CHARS的行"""
    if len(text) <= MAX_CHARS:
        return [text]
    result = []
    remaining = text
    while len(remaining) > MAX_CHARS:
        search = remaining[:MAX_CHARS]
        pos = -1
        for p in '。！？\n；;，,':
            p2 = search.rfind(p)
            if p2 >= 3:
                pos = p2 + 1
                break
        if pos <= 0:
            for sc in '的了吗呢吧啊呀嘛着了过':
                p2 = search.rfind(sc)
                if p2 >= 3:
                    pos = p2 + 1
                    break
        if pos <= 0:
            pos = MAX_CHARS
        part = remaining[:pos].strip()
        if part:
            result.append(part)
        remaining = remaining[pos:].strip()
    if remaining.strip():
        result.append(remaining.strip())
    return result


def fix_subtitles(subs):
    changes = 0
    i = 0
    while i < len(subs):
        if not is_too_short(subs[i].text):
            i += 1
            continue

        # 尝试合并前+当前+后，重新分割
        if i > 0 and i + 1 < len(subs):
            combined = subs[i - 1].text.strip() + subs[i].text.strip() + subs[i + 1].text.strip()
            parts = smart_split(combined)
            if len(parts) == 2:
                subs[i - 1].text = parts[0]
                subs[i - 1].end = subs[i + 1].end
                subs[i + 1].text = parts[1]
                subs.pop(i)
                changes += 1
                continue

        # 合并前+当前
        if i > 0:
            combined = subs[i - 1].text.strip() + subs[i].text.strip()
            if len(combined) <= MAX_CHARS:
                subs[i - 1].text = combined
                subs[i - 1].end = subs[i].end
                subs.pop(i)
                changes += 1
                continue

        # 合并当前+后
        if i + 1 < len(subs):
            combined = subs[i].text.strip() + subs[i + 1].text.strip()
            if len(combined) <= MAX_CHARS:
                subs[i + 1].text = combined
                subs[i + 1].start = subs[i].start
                subs.pop(i)
                changes += 1
                continue

        i += 1
    return subs, changes


def process_file(input_path, output_path):
    subs = pysubs2.load(input_path, encoding='utf-8')
    original = len(subs)
    fixed, changes = fix_subtitles(subs)
    fixed.save(output_path, encoding='utf-8')
    return original, len(fixed), changes


# 处理
srt_files = sorted([f for f in os.listdir(INPUT_DIR) if f.endswith('.srt')])
print(f"找到 {len(srt_files)} 个字幕文件\n")

total_changes = 0
for srt_file in srt_files:
    input_path = os.path.join(INPUT_DIR, srt_file)
    output_path = os.path.join(OUTPUT_DIR, srt_file)
    try:
        orig, final, changes = process_file(input_path, output_path)
        total_changes += changes

        out_subs = pysubs2.load(output_path, encoding='utf-8')
        short_count = 0
        examples = []
        for i, line in enumerate(out_subs):
            if is_too_short(line.text):
                short_count += 1
                if len(examples) < 10:
                    examples.append((i + 1, len(line.text.strip()), line.text.strip()))

        status = "✓" if short_count == 0 else f"⚠ 极短行 {short_count}"
        print(f"[OK] {srt_file}")
        print(f"     {orig} -> {final} 条，修复 {changes} 处  {status}")
        if examples:
            for num, ln, t in examples:
                print(f"     行{num} ({ln}字): |{t}|")
        print()
    except Exception as e:
        import traceback
        print(f"[FAIL] {srt_file}: {e}")
        traceback.print_exc()

print(f"总计修复 {total_changes} 处\n完成！输出: {OUTPUT_DIR}")
