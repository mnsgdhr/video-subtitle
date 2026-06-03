"""
Subtitle Quality Review & Fix
=============================
检测并修复字幕中的问题行：
1. 极短行（≤2字符）
2. 纯标点行
3. 行首标点（，。！？;等）
4. 截断英文（如 on, er, se, ker 等）
5. 逗号结尾的短行（≤5字且无完整主谓结构）

修复策略：
1. 行首标点：强制与前一行合并并重分
2. 合并到前一行（如合并后≤MAX_CHARS）
3. 合并到后一行（如合并后≤MAX_CHARS）
4. 三行合并后按标点重新分割
5. 多轮迭代直到无问题

用法:
  python review_and_fix.py --input <SRT目录> [--output <输出目录>]
  python review_and_fix.py --input <单个SRT文件> [--output <输出目录>]
"""
import pysubs2
import os
import sys
import argparse
import re

sys.stdout.reconfigure(encoding='utf-8')

DEFAULT_MAX_CHARS = 16
PUNCT_SET = set('，。！？；、,.!?;…—～（）\n ')
BAD_START_CHARS = set('，。！？；,.!?;')


def is_problematic(text, max_chars=DEFAULT_MAX_CHARS):
    """检查一行字幕是否有问题"""
    t = text.strip()
    tlen = len(t)

    if not t:
        return 'empty'
    if tlen <= 1:
        return 'single'
    if all(c in PUNCT_SET for c in t):
        return 'punct'
    if tlen <= 2:
        return 'short'
    if t[0] in BAD_START_CHARS:
        return 'start_punct'
    # 逗号结尾的短行（≤5字）
    if tlen <= 5 and t[-1] in '，,;；':
        has_subject = any(s in t for s in '你我他她它我们他们这那谁')
        has_verb = any(v in t for v in '是的有的会在可能应该可以会就去让能打')
        if not (has_subject and has_verb):
            return f'short_comma({tlen})'
    # 截断英文（1-4字母+可选逗号）
    if re.match(r'^[a-zA-Z]{1,4},?$', t):
        return f'broken_en({tlen})'
    return None


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


def reassign_times(subs, start_idx, parts, orig_start, orig_end):
    """给分割后的部分重新分配时间戳"""
    total_chars = sum(len(p) for p in parts)
    total_dur = orig_end - orig_start
    current_start = orig_start

    subs[start_idx].text = parts[0]
    char_ratio = len(parts[0]) / total_chars
    subs[start_idx].end = orig_start + int(total_dur * char_ratio)
    current_start = subs[start_idx].end

    for i in range(1, len(parts)):
        char_ratio = len(parts[i]) / total_chars
        dur = int(total_dur * char_ratio)
        end_time = current_start + dur

        if start_idx + i < len(subs):
            subs[start_idx + i].text = parts[i]
            subs[start_idx + i].start = current_start
            subs[start_idx + i].end = end_time
        else:
            ev = pysubs2.SSAEvent(start=current_start, end=end_time)
            ev.text = parts[i]
            subs.append(ev)

        current_start = end_time


def fix_subtitles(subs, max_chars=DEFAULT_MAX_CHARS):
    max_rounds = 50
    total_changes = 0

    for _ in range(max_rounds):
        changes_this_round = 0
        i = 0
        while i < len(subs):
            reason = is_problematic(subs[i].text, max_chars)

            if reason:
                fixed = False

                # 策略A: 行首标点 → 强制与前一行合并并重分
                if reason in ('start_punct', 'empty') and i > 0:
                    if i + 1 < len(subs):
                        combined = subs[i-1].text.strip() + subs[i].text.strip() + subs[i+1].text.strip()
                    else:
                        combined = subs[i-1].text.strip() + subs[i].text.strip()

                    orig_start = subs[i-1].start
                    orig_end = subs[i+1].end if i+1 < len(subs) else subs[i].end

                    parts = smart_split(combined, max_chars)
                    if len(parts) >= 2:
                        # 移除中间行
                        subs.pop(i)
                        # 移除多余行
                        while len(parts) > 1 and i < len(subs):
                            subs.pop(i)
                        # 添加新行
                        for j, p in enumerate(parts):
                            if start_idx + j < len(subs):
                                subs[start_idx + j].text = p
                            else:
                                ev = pysubs2.SSAEvent(start=orig_start, end=orig_end)
                                ev.text = p
                                subs.append(ev)
                        changes_this_round += 1
                        fixed = True

                # 策略B: 合并前+当前+后三行，重新分割
                if not fixed and i > 0 and i + 1 < len(subs):
                    combined = subs[i-1].text.strip() + subs[i].text.strip() + subs[i+1].text.strip()
                    parts = smart_split(combined, max_chars)
                    if len(parts) == 2 and all(len(p) <= max_chars for p in parts):
                        orig_start = subs[i-1].start
                        orig_end = subs[i+1].end
                        subs[i-1].text = parts[0]
                        subs[i-1].end = orig_start + int((orig_end - orig_start) * len(parts[0]) / len(combined))
                        subs[i+1].text = parts[1]
                        subs[i+1].start = subs[i-1].end
                        subs.pop(i)
                        changes_this_round += 1
                        fixed = True

                # 策略C: 合并到前一行
                if not fixed and i > 0:
                    combined = subs[i-1].text.strip() + subs[i].text.strip()
                    if len(combined) <= max_chars:
                        subs[i-1].text = combined
                        subs[i-1].end = subs[i].end
                        subs.pop(i)
                        changes_this_round += 1
                        fixed = True

                # 策略D: 合并到后一行
                if not fixed and i + 1 < len(subs):
                    combined = subs[i].text.strip() + subs[i+1].text.strip()
                    if len(combined) <= max_chars:
                        subs[i+1].text = combined
                        subs[i+1].start = subs[i].start
                        subs.pop(i)
                        changes_this_round += 1
                        fixed = True

                if not fixed:
                    i += 1
            else:
                i += 1

        total_changes += changes_this_round
        if changes_this_round == 0:
            break

    return subs, total_changes


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
                remaining = 0
                examples = []
                for i, line in enumerate(out_subs):
                    r = is_problematic(line.text, max_chars)
                    if r:
                        remaining += 1
                        if len(examples) < 10:
                            examples.append((i + 1, r, line.text.strip()))

                status = "OK" if remaining == 0 else f"REMAINING {remaining}"
                print(f"[OK] {srt_file}")
                print(f"     {orig} -> {final} 条，修复 {changes} 处  {status}")
                if examples:
                    for num, cat, t in examples:
                        print(f"     行{num} [{cat}]: |{t}|")
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
