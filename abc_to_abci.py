import os
import re
import argparse
from pathlib import Path
from tqdm import tqdm

# 假设 abctoolkit 是一个可以安装或在本地路径的库
# 如果 abctoolkit 在本地，您可能需要调整 sys.path
# import sys
# sys.path.append(str(Path(__file__).parent))
from abc_cleaner_utils import clean_and_prepare_abc

def convert_to_abci(input_path: Path, output_path: Path):
    """
    将单个 ABC 文件转换为 ABCi (interleaved) 格式。
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        original_abc_lines = [line for line in f.readlines() if line.strip()]

    # 1. 清理和准备 ABC
    cleaned_abc_lines = clean_and_prepare_abc(original_abc_lines)
    
    # 2. 旋转 (interleave)
    interleaved_abc_lines = rotate_abc(cleaned_abc_lines)

    # 3. 写入输出文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(interleaved_abc_lines)

def main():
    """
    作为独立脚本运行时的主函数，用于批量处理目录。
    """
    parser = argparse.ArgumentParser(
        description="Convert standard ABC files to ABCi (interleaved) format in batch."
    )
    parser.add_argument('-i', '--input_dir', required=True, help='Input directory containing ABC files.')
    parser.add_argument('-o', '--output_dir', required=True, help='Output directory for ABCi files.')
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Searching for .abc files in {input_dir}...")
    abc_files = list(input_dir.rglob("*.abc"))
    print(f"Found {len(abc_files)} files.")

    if not abc_files:
        return

    for input_path in tqdm(abc_files, desc="Converting to ABCi"):
        try:
            # 保持原始目录结构
            relative_path = input_path.relative_to(input_dir)
            output_path = (output_dir / relative_path).with_suffix(".abci")
            
            # 如果文件已存在，则跳过
            if output_path.exists():
                continue

            convert_to_abci(input_path, output_path)
        except Exception as e:
            print(f"Failed to process {input_path.name}: {e}")
            # 也可以在这里写入日志文件
            continue

if __name__ == '__main__':
    main()
