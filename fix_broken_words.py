"""
修复英文单词被断开的问题
========================
问题：英文单词被分割在两行中间（如 de/ny, check/raise）
修复：检测行尾的半个英文词，合并到下一行，重新分割
"""
import pysubs2
import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

INPUT_DIR = r"F:\video\血战鱿鱼\精剪版\corrected_subtitles\final_subtitles\final_subtitles_v2\fixed_timestamps"
OUTPUT_DIR = os.path.join(INPUT_DIR, "no_broken_words")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MAX_CHARS = 20


def find_broken_word(subs, i):
    """检查第 i 行末尾是否有半个英文单词延伸到第 i+1 行"""
    if i >= len(subs) - 1:
        return None
    
    t1 = subs[i].text.strip()
    t2 = subs[i + 1].text.strip()
    
    # 提取行尾的英文字母
    match_end = re.search(r'([a-zA-Z]+)$', t1)
    if not match_end:
        return None
    
    end_fragment = match_end.group(1)
    
    # 提取下一行开头的英文字母
    match_start = re.match(r'^([a-zA-Z]+)', t2)
    if not match_start:
        return None
    
    start_fragment = match_start.group(1)
    
    # 合并后是否是一个合理的英文词（3-15字母）
    combined = end_fragment + start_fragment
    if 3 <= len(combined) <= 15:
        return (end_fragment, start_fragment, combined)
    
    return None


def fix_broken_words(subs):
    """修复被断开的英文单词"""
    fixes = 0
    max_rounds = 50
    
    for _ in range(max_rounds):
        changed = False
        i = 0
        while i < len(subs) - 1:
            result = find_broken_word(subs, i)
            if result:
                end_frag, start_frag, combined = result
                
                # 合并两行
                t1 = subs[i].text.strip()
                t2 = subs[i + 1].text.strip()
                
                # 去掉行尾的半词和行首的半词
                # 找到 end_frag 在 t1 末尾的位置
                end_pos = t1.rfind(end_frag)
                # 找到 start_frag 在 t2 开头的位置
                start_pos = t2.find(start_frag)
                
                # 保留 t1 的中文部分 + combined + t2 剩余部分
                before = t1[:end_pos].rstrip()
                after = t2[start_pos + len(start_frag):].lstrip()
                
                combined_text = before + ' ' + combined + ' ' + after if before and after else \
                                before + ' ' + combined if before else \
                                combined + ' ' + after if after else combined
                
                combined_text = combined_text.strip()
                
                # 如果合并后不超过 MAX_CHARS，直接合并为一行
                if len(combined_text) <= MAX_CHARS:
                    subs[i].text = combined_text
                    subs[i].end = subs[i + 1].end
                    subs.pop(i + 1)
                    fixes += 1
                    changed = True
                    # 不前进，继续检查当前位置
                    continue
                else:
                    # 合并后超长，需要重新分割
                    # 在 combined 之后找分割点
                    full_text = combined_text
                    split_pos = -1
                    
                    # 在 combined 之后的中文里找标点
                    after_combined = combined + after if after else combined
                    for p in '。！？；，,':
                        pos = after_combined.find(p)
                        if pos > 0 and len(combined + after_combined[:pos + 1]) <= MAX_CHARS:
                            part1 = before + ' ' + combined + after_combined[:pos + 1]
                            part2 = after_combined[pos + 1:].strip()
                            if len(part1) <= MAX_CHARS and len(part2) <= MAX_CHARS:
                                subs[i].text = part1.strip()
                                subs[i + 1].text = part2
                                # 按字符比例分时间
                                total_dur = subs[i + 1].end - subs[i].start
                                ratio = len(part1) / (len(part1) + len(part2))
                                split_time = subs[i].start + int(total_dur * ratio)
                                subs[i].end = split_time
                                subs[i + 1].start = split_time
                                fixes += 1
                                changed = True
                                i += 1
                                continue
                    
                    # 没找到好的分割点，尝试在 combined 前切
                    if before:
                        split_pos = -1
                        for p in '。！？；，,':
                            pos = before.rfind(p)
                            if pos > 0:
                                split_pos = pos + 1
                                break
                        
                        if split_pos > 0 and len(before[:split_pos]) <= MAX_CHARS:
                            part1 = before[:split_pos].strip()
                            part2 = before[split_pos:].strip() + ' ' + combined + ' ' + after if after else before[split_pos:].strip() + ' ' + combined
                            part2 = part2.strip()
                            
                            if len(part1) <= MAX_CHARS and len(part2) <= MAX_CHARS:
                                subs[i].text = part1
                                subs[i + 1].text = part2
                                total_dur = subs[i + 1].end - subs[i].start
                                ratio = len(part1) / (len(part1) + len(part2))
                                split_time = subs[i].start + int(total_dur * ratio)
                                subs[i].end = split_time
                                subs[i + 1].start = split_time
                                fixes += 1
                                changed = True
                                i += 1
                                continue
                    
                    # 实在没办法，合并为一行（可能超长）
                    subs[i].text = combined_text
                    subs[i].end = subs[i + 1].end
                    subs.pop(i + 1)
                    fixes += 1
                    changed = True
                    continue
            
            i += 1
        
        if not changed:
            break
    
    return subs, fixes


def process_file(input_path, output_path):
    subs = pysubs2.load(input_path, encoding='utf-8')
    original = len(subs)
    fixed, fixes = fix_broken_words(subs)
    fixed.save(output_path, encoding='utf-8')
    return original, len(fixed), fixes


# 处理
srt_files = sorted([f for f in os.listdir(INPUT_DIR) if f.endswith('.srt')])
print(f"找到 {len(srt_files)} 个字幕文件\n")

total_fixes = 0
for srt_file in srt_files:
    input_path = os.path.join(INPUT_DIR, srt_file)
    output_path = os.path.join(OUTPUT_DIR, srt_file)
    
    try:
        orig, final, fixes = process_file(input_path, output_path)
        total_fixes += fixes
        print(f"[OK] {srt_file}")
        print(f"     修复 {fixes} 处断裂\n")
    except Exception as e:
        import traceback
        print(f"[FAIL] {srt_file}: {e}")
        traceback.print_exc()

print(f"总计修复 {total_fixes} 处断裂\n完成！输出: {OUTPUT_DIR}")
