"""
Subtitle Quality Review & Fix
=============================
检测并修复字幕中的问题行：
- 单字行（≤1字符）
- 纯标点行
- 极短行（≤2字符）

修复策略：
1. 合并到前一行（如合并后≤MAX_CHARS）
2. 合并到后一行（如合并后≤MAX_CHARS）
3. 三行合并后按标点重新分割

用法:
  python review_and_fix.py --input <SRT目录> [--output <输出目录>]
  python review_and_fix.py --input <单个SRT文件> [--output <输出目录>]
"""
import pysubs2
import os
import sys
import argparse

sys.stdout.reconfigure(encoding='utf-8')

DEFAULT_MAX_CHARS = 16
PUNCT_SET = set('，。！？；、,.!?;…—～（）\n ')


def is_too_short(text, max_chars=DEFAULT_MAX_CHARS):
    t = text.strip()
    if len(t) <= 1:
        return True
    if len(t) <= 2:
        return True
    if all(c in PUNCT_SET for c in t):
        return True
    return False


def smart_split(text, max_chars=DEFAULT_MAX_CHARS):
    """把文本分割成≤max_chars的行"""
    if len(text) <= max_chars:
        return [text]
    result = []
    remaining = text
    while len(remaining) > max_chars:
        search = remaining[:max_chars]
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
            pos = max_chars
        part = remaining[:pos].strip()
        if part:
            result.append(part)
        remaining = remaining[pos:].strip()
    if remaining.strip():
        result.append(remaining.strip())
    return result


def fix_subtitles(subs, max_chars=DEFAULT_MAX_CHARS):
    changes = 0
    i = 0
    while i < len(subs):
        if not is_too_short(subs[i].text, max_chars):
            i += 1
            continue

        # 尝试合并前+当前+后，重新分割
        if i > 0 and i + 1 < len(subs):
            combined = subs[i - 1].text.strip() + subs[i].text.strip() + subs[i + 1].text.strip()
            parts = smart_split(combined, max_chars)
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
            if len(combined) <= max_chars:
                subs[i - 1].text = combined
                subs[i - 1].end = subs[i].end
                subs.pop(i)
                changes += 1
                continue

        # 合并当前+后
        if i + 1 < len(subs):
            combined = subs[i].text.strip() + subs[i + 1].text.strip()
            if len(combined) <= max_chars:
                subs[i + 1].text = combined
                subs[i + 1].start = subs[i].start
                subs.pop(i)
                changes += 1
                continue

        i += 1
    return subs, changes


def process_file(input_path, output_path, max_chars=DEFAULT_MAX_CHARS):
    subs = pysubs2.load(input_path, encoding='utf-8')
    original = len(subs)
    fixed, changes = fix_subtitles(subs, max_chars)
    fixed.save(output_path, encoding='utf-8')
    return original, len(fixed), changes


def main():
    parser = argparse.ArgumentParser(description='字幕质量审查与修复')
    parser.add_argument('--input', required=True, help='SRT 文件路径或目录')
    parser.add_argument('--output', default=None, help='输出目录（默认 final_subtitles/）')
    parser.add_argument('--max-chars', type=int, default=DEFAULT_MAX_CHARS, help='每行最大字符数')
    args = parser.parse_args()

    max_chars = args.max_chars

    if args.output:
        output_dir = args.output
    else:
        input_parent = os.path.dirname(os.path.abspath(args.input))
        output_dir = os.path.join(input_parent, "final_subtitles")
    os.makedirs(output_dir, exist_ok=True)

    input_path = os.path.abspath(args.input)
    total_changes = 0

    if os.path.isdir(input_path):
        srt_files = sorted([f for f in os.listdir(input_path) if f.endswith('.srt')])
        print(f"找到 {len(srt_files)} 个 SRT 文件\n")
        for srt_file in srt_files:
            inp = os.path.join(input_path, srt_file)
            out = os.path.join(output_dir, srt_file)
            try:
                orig, final, changes = process_file(inp, out, max_chars)
                total_changes += changes

                out_subs = pysubs2.load(out, encoding='utf-8')
                short_count = 0
                examples = []
                for i, line in enumerate(out_subs):
                    if is_too_short(line.text, max_chars):
                        short_count += 1
                        if len(examples) < 10:
                            examples.append((i + 1, len(line.text.strip()), line.text.strip()))

                status = "OK" if short_count == 0 else f"REMAINING {short_count}"
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
    elif os.path.isfile(input_path):
        out_file = os.path.join(output_dir, os.path.basename(input_path))
        orig, final, changes = process_file(input_path, out_file, max_chars)
        total_changes += changes
        print(f"[OK] {os.path.basename(input_path)}: {orig} -> {final} 条，修复 {changes} 处")

    print(f"总计修复 {total_changes} 处\n完成！输出: {output_dir}")


if __name__ == '__main__':
    main()
