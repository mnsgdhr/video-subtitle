"""
修复英文单词被断开的问题 V2
========================
问题：英文单词被分割在两行中间（如 de/ny, check/raise）
策略：
1. 断裂词合并：至少一个片段<4字母 → 直接拼接（de+ny=deny）
2. 短词对合并：两个都是4-6字母的短词 → 加空格（deny+equity=deny equity）
3. 合并后超长时：把英文词移到下一行

用法:
  python fix_broken_words.py --input <SRT目录> [--output <输出目录>]
"""
import pysubs2
import os
import sys
import argparse
import re

sys.stdout.reconfigure(encoding='utf-8')

DEFAULT_MAX_CHARS = 20


def fix_broken_words(subs, max_chars=DEFAULT_MAX_CHARS):
    fixes = 0
    i = 0
    while i < len(subs) - 1:
        t1 = subs[i].text.strip()
        t2 = subs[i + 1].text.strip()

        match_end = re.search(r'([a-zA-Z]+)$', t1)
        match_start = re.match(r'^([a-zA-Z]+)', t2)

        if match_end and match_start:
            end_frag = match_end.group(1)
            start_frag = match_start.group(1)

            # 断裂词：至少一个片段<4字母
            is_broken = len(end_frag) < 4 or len(start_frag) < 4
            # 短词对：两个都是4-6字母
            is_short_words = 4 <= len(end_frag) <= 6 and 4 <= len(start_frag) <= 6

            if is_broken or is_short_words:
                # 断裂词直接拼接，短词对加空格
                if is_broken:
                    combined = end_frag + start_frag
                else:
                    combined = end_frag + ' ' + start_frag

                end_pos = t1.rfind(end_frag)
                start_pos = t2.find(start_frag)
                before = t1[:end_pos].rstrip()
                after = t2[start_pos + len(start_frag):].lstrip()

                parts = [p for p in [before, combined, after] if p]
                combined_text = ' '.join(parts)

                if len(combined_text) <= max_chars:
                    subs[i].text = combined_text
                    subs[i].end = subs[i + 1].end
                    subs.pop(i + 1)
                    fixes += 1
                    continue
                else:
                    # 超长：把英文词移到下一行
                    if before:
                        part1 = before
                        part2_parts = [p for p in [combined, after] if p]
                        part2 = ' '.join(part2_parts)

                        if len(part1) <= max_chars and len(part2) <= max_chars:
                            subs[i].text = part1
                            subs[i].end = subs[i + 1].start  # 确保不重叠
                            subs[i + 1].text = part2
                            fixes += 1
                            continue

        i += 1
    return subs, fixes


def process_file(input_path, output_path, max_chars=DEFAULT_MAX_CHARS):
    subs = pysubs2.load(input_path, encoding='utf-8')
    original = len(subs)
    fixed, fixes = fix_broken_words(subs, max_chars)
    fixed.save(output_path, encoding='utf-8')
    return original, len(fixed), fixes


def main():
    parser = argparse.ArgumentParser(description='修复英文单词断裂')
    parser.add_argument('--input', required=True, help='SRT 文件路径或目录')
    parser.add_argument('--output', default=None, help='输出目录')
    parser.add_argument('--max-chars', type=int, default=DEFAULT_MAX_CHARS, help='每行最大字符数')
    args = parser.parse_args()

    if args.output:
        output_dir = args.output
    else:
        input_parent = os.path.dirname(os.path.abspath(args.input))
        output_dir = os.path.join(input_parent, "no_broken_words")
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
                orig, final, changes = process_file(inp, out, args.max_chars)
                total_changes += changes

                # 验证
                out_subs = pysubs2.load(out, encoding='utf-8')
                remaining = 0
                for j in range(len(out_subs) - 1):
                    t1 = out_subs[j].text.strip()
                    t2 = out_subs[j + 1].text.strip()
                    m1 = re.search(r'([a-zA-Z]+)$', t1)
                    m2 = re.match(r'^([a-zA-Z]+)', t2)
                    if m1 and m2 and (len(m1.group(1)) < 4 or len(m2.group(1)) < 4):
                        remaining += 1

                status = "OK" if remaining == 0 else f"REMAINING {remaining}"
                print(f"[OK] {srt_file}")
                print(f"     修复 {changes} 处断裂  {status}")
            except Exception as e:
                import traceback
                print(f"[FAIL] {srt_file}: {e}")
                traceback.print_exc()
    elif os.path.isfile(input_path):
        out_file = os.path.join(output_dir, os.path.basename(input_path))
        orig, final, changes = process_file(input_path, out_file, args.max_chars)
        total_changes += changes
        print(f"[OK] {os.path.basename(input_path)}: {orig} -> {final} 条，修复 {changes} 处")

    print(f"\n总计修复 {total_changes} 处断裂\n完成！输出: {output_dir}")


if __name__ == '__main__':
    main()
