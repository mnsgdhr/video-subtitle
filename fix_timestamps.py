"""
修复字幕时间戳重叠
===================
问题：有些字幕还没显示完，下一行就出现了
策略：将当前行结束时间设为下一行开始时间，确保每行至少显示 300ms
"""
import pysubs2
import os
import sys
import argparse

sys.stdout.reconfigure(encoding='utf-8')

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
            
            # 将当前行结束时间设为下一行开始时间
            min_end = subs[i].start + MIN_DISPLAY_MS
            
            if next_start >= min_end:
                subs[i].end = next_start
            else:
                # 如果重叠太大，把下一行开始时间往前挪
                subs[i + 1].start = curr_end
    
    return subs, fixes


def process_file(input_path, output_path):
    subs = pysubs2.load(input_path, encoding='utf-8')
    original = len(subs)
    fixed, fixes = fix_overlaps(subs)
    
    # 验证
    remaining = 0
    for i in range(len(fixed) - 1):
        if fixed[i].end > fixed[i + 1].start:
            remaining += 1
    
    fixed.save(output_path, encoding='utf-8')
    return original, fixes, remaining


def main():
    parser = argparse.ArgumentParser(description='修复字幕时间戳重叠')
    parser.add_argument('--input', required=True, help='SRT 文件路径或目录')
    parser.add_argument('--output', default=None, help='输出目录（默认 fixed_timestamps/）')
    args = parser.parse_args()

    if args.output:
        output_dir = args.output
    else:
        input_parent = os.path.dirname(os.path.abspath(args.input))
        output_dir = os.path.join(input_parent, "fixed_timestamps")
    os.makedirs(output_dir, exist_ok=True)

    input_path = os.path.abspath(args.input)
    total_fixes = 0

    if os.path.isdir(input_path):
        srt_files = sorted([f for f in os.listdir(input_path) if f.endswith('.srt')])
        print(f"找到 {len(srt_files)} 个 SRT 文件\n")
        for srt_file in srt_files:
            inp = os.path.join(input_path, srt_file)
            out = os.path.join(output_dir, srt_file)
            try:
                orig, fixes, remaining = process_file(inp, out)
                total_fixes += fixes
                status = "OK" if remaining == 0 else f"剩余 {remaining} 处重叠"
                print(f"[OK] {srt_file}")
                print(f"     修复 {fixes} 处重叠  {status}")
            except Exception as e:
                import traceback
                print(f"[FAIL] {srt_file}: {e}")
                traceback.print_exc()
    elif os.path.isfile(input_path):
        out_file = os.path.join(output_dir, os.path.basename(input_path))
        orig, fixes, remaining = process_file(input_path, out_file)
        total_fixes += fixes
        status = "OK" if remaining == 0 else f"剩余 {remaining} 处重叠"
        print(f"[OK] {os.path.basename(input_path)}")
        print(f"     修复 {fixes} 处重叠  {status}")

    print(f"\n总计修复 {total_fixes} 处重叠\n完成！输出: {output_dir}")


if __name__ == '__main__':
    main()
