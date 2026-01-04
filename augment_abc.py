import os
import re
import argparse
from pathlib import Path
from tqdm import tqdm

# 假设 abctoolkit 是一个可以安装或在本地路径的库
from abc_cleaner_utils import clean_and_prepare_abc

def augment_by_transposition(input_path: Path, output_root_dir: Path):
    """
    将单个 ABC 文件通过移调增强到所有12个大调。
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        original_abc_lines = [line for line in f.readlines() if line.strip()]

    # 1. 清理和准备 ABC
    cleaned_abc_lines = clean_and_prepare_abc(original_abc_lines)
    
    original_basename = input_path.stem

    # 2. 遍历所有目标调性进行移调
    for key in Key2index.keys():
        # 创建特定调性的输出目录
        key_output_dir = output_root_dir / key
        key_output_dir.mkdir(parents=True, exist_ok=True)
        
        output_filename = f"{original_basename}_{key}.abc"
        output_path = key_output_dir / output_filename
        
        # 如果文件已存在，则跳过
        if output_path.exists():
            continue

        # 执行移调
        transposed_abc_text = transpose_an_abc_text(cleaned_abc_lines, key)
        
        # 3. 写入输出文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(transposed_abc_text)

def main():
    """
    作为独立脚本运行时的主函数，用于批量处理目录。
    """
    parser = argparse.ArgumentParser(
        description="Augment ABC files by transposing them to all keys."
    )
    parser.add_argument('-i', '--input_dir', required=True, help='Input directory containing source ABC files.')
    parser.add_argument('-o', '--output_dir', required=True, help='Root output directory for augmented files.')
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Searching for .abc files in {input_dir}...")
    abc_files = list(input_dir.rglob("*.abc"))
    print(f"Found {len(abc_files)} files.")

    if not abc_files:
        return

    for input_path in tqdm(abc_files, desc="Augmenting ABC files"):
        try:
            augment_by_transposition(input_path, output_dir)
        except Exception as e:
            print(f"Failed to process {input_path.name}: {e}")
            # 也可以在这里写入日志文件
            continue

if __name__ == '__main__':
    main()
