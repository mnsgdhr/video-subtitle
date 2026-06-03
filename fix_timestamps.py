"""
修复字幕时间戳重叠
===================
问题：有些字幕还没显示完，下一行就出现了
策略：确保每行结束时间 <= 下一行开始时间
"""
import pysubs2
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

INPUT_DIR = r"F:\video\血战鱿鱼\精剪版\corrected_subtitles\final_subtitles\final_subtitles_v2"
OUTPUT_DIR = os.path.join(INPUT_DIR, "fixed_timestamps")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 最小显示时间（毫秒），避免一行只显示一瞬间
MIN_DISPLAY_MS = 300


def fix_overlaps(subs):
    """修复时间戳重叠"""
    fixes = 0
    
    for i in range(len(subs) - 1):
        curr_end = subs[i].end
        next_start = subs[i + 1].start
        
        if curr_end > next_start:
            overlap = curr_end - next_start
            fixes += 1
            
            # 策略：将当前行结束时间设为下一行开始时间
            # 但要确保当前行至少显示 MIN_DISPLAY_MS
            min_end = subs[i].start + MIN_DISPLAY_MS
            
            if next_start >= min_end:
                subs[i].end = next_start
            else:
                # 如果重叠太大，把下一行开始时间往前挪
                subs[i + 1].start = curr_end
    
    return subs, fixes


def process_file(input_path, output_path):
    subs = pysubs2.load(input_path, encoding='utf-8')
    original_count = len(subs)
    
    fixed, fixes = fix_overlaps(subs)
    
    # 再次检查确保无重叠
    remaining = 0
    for i in range(len(fixed) - 1):
        if fixed[i].end > fixed[i + 1].start:
            remaining += 1
    
    fixed.save(output_path, encoding='utf-8')
    return original_count, fixes, remaining


# 处理
srt_files = sorted([f for f in os.listdir(INPUT_DIR) if f.endswith('.srt')])
print(f"找到 {len(srt_files)} 个字幕文件\n")

total_fixes = 0
for srt_file in srt_files:
    input_path = os.path.join(INPUT_DIR, srt_file)
    output_path = os.path.join(OUTPUT_DIR, srt_file)
    
    try:
        orig, fixes, remaining = process_file(input_path, output_path)
        total_fixes += fixes
        status = "OK" if remaining == 0 else f"剩余 {remaining} 处重叠"
        print(f"[OK] {srt_file}")
        print(f"     修复 {fixes} 处重叠  {status}\n")
    except Exception as e:
        import traceback
        print(f"[FAIL] {srt_file}: {e}")
        traceback.print_exc()

print(f"总计修复 {total_fixes} 处重叠\n完成！输出: {OUTPUT_DIR}")
