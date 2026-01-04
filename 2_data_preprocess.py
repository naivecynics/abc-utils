import os
import re
import json
import random
import argparse
from tqdm import tqdm
from abctoolkit.utils import (
    remove_information_field, 
    remove_bar_no_annotations, 
    Quote_re, 
    Barlines,
    extract_metadata_and_parts, 
    extract_global_and_local_metadata,
    extract_barline_and_bartext_dict)
from abctoolkit.convert import unidecode_abc_lines
from abctoolkit.rotate import rotate_abc
from abctoolkit.check import check_alignment_unrotated
from abctoolkit.transpose import Key2index, transpose_an_abc_text


def abc_preprocess_pipeline(abc_path, interleaved_folder, augmented_folder=None):
    with open(abc_path, 'r', encoding='utf-8') as f:
        abc_lines = [line for line in f.readlines() if line.strip()]

    abc_lines = unidecode_abc_lines(abc_lines)
    abc_lines = remove_information_field(
        abc_lines=abc_lines,
        info_fields=['X:', 'T:', 'C:', 'W:', 'w:', 'Z:', '%%MIDI']
    )
    abc_lines = remove_bar_no_annotations(abc_lines)

    for i, line in enumerate(abc_lines):
        if not re.search(r'^[A-Za-z]:', line) and not line.startswith('%'):
            abc_lines[i] = line.replace(r'\"', '')

    for i, line in enumerate(abc_lines):
        for quote_content in re.findall(Quote_re, line):
            if any(barline in quote_content for barline in Barlines):
                abc_lines[i] = line.replace(quote_content, '')

    try:
        _, ok, _ = check_alignment_unrotated(abc_lines)
        if not ok:
            raise Exception("Unequal bar number")
    except Exception:
        raise Exception(f"Alignment error in {abc_path}")

    for i, line in enumerate(abc_lines):
        for match in re.findall(r'"[^"]*"', line):
            if match == '""':
                line = line.replace(match, '')
            if match[1] in ['^', '_']:
                sub_string = re.sub(r'([^a-zA-Z0-9])\1+', r'\1', match)
                if len(sub_string) <= 40:
                    line = line.replace(match, sub_string)
                else:
                    line = line.replace(match, '')
        abc_lines[i] = line

    abc_name = os.path.splitext(os.path.basename(abc_path))[0]
    metadata_lines, part_text_dict = extract_metadata_and_parts(abc_lines)
    global_metadata_dict, _ = extract_global_and_local_metadata(metadata_lines)
    ori_key = global_metadata_dict.get('K', ['C'])[0] or 'C'

    interleaved_abc = rotate_abc(abc_lines)
    interleaved_path = os.path.join(interleaved_folder, abc_name + '.abc')
    with open(interleaved_path, 'w', encoding='utf-8') as w:
        w.writelines(interleaved_abc)

    if augmented_folder:
        for key in Key2index.keys():
            transposed_abc_text = transpose_an_abc_text(abc_lines, key)
            transposed_abc_lines = [line + '\n' for line in transposed_abc_text.split('\n') if line.strip()]
            metadata_lines, prefix_dict, left_barline_dict, bar_text_dict, right_barline_dict = \
                extract_barline_and_bartext_dict(transposed_abc_lines)

            reduced_abc_lines = metadata_lines
            for i in range(len(bar_text_dict['V:1'])):
                line = ''
                for symbol in prefix_dict.keys():
                    if any(ch.isalpha() and ch not in 'ZzXx' for ch in bar_text_dict[symbol][i]):
                        if i == 0:
                            part_patch = f'[{symbol}]{prefix_dict[symbol]}{left_barline_dict[symbol][0]}{bar_text_dict[symbol][0]}{right_barline_dict[symbol][0]}'
                        else:
                            part_patch = f'[{symbol}]{bar_text_dict[symbol][i]}{right_barline_dict[symbol][i]}'
                        line += part_patch
                line += '\n'
                reduced_abc_lines.append(line)

            reduced_path = os.path.join(augmented_folder, key, f"{abc_name}_{key}.abc")
            os.makedirs(os.path.dirname(reduced_path), exist_ok=True)
            with open(reduced_path, 'w', encoding='utf-8') as w:
                w.writelines(reduced_abc_lines)

    return abc_name, ori_key


def main():
    parser = argparse.ArgumentParser(description="Preprocess ABC files with interleaving, augmentation, and key extraction.")
    parser.add_argument('-i', '--input_dir', required=True, help='Input directory containing ABC files')
    parser.add_argument('-o', '--interleaved_dir', required=True, help='Output directory for interleaved ABC files')
    parser.add_argument('-a', '--augmented_dir', default='', help='Output directory for augmented ABC files (optional)')
    args = parser.parse_args()

    ori_folder = args.input_dir
    interleaved_folder = args.interleaved_dir
    augmented_folder = args.augmented_dir or None

    os.makedirs(interleaved_folder, exist_ok=True)
    if augmented_folder:
        for key in Key2index.keys():
            os.makedirs(os.path.join(augmented_folder, key), exist_ok=True)

    for file in tqdm(os.listdir(ori_folder)):
        abc_path = os.path.join(ori_folder, file)
        try:
            abc_preprocess_pipeline(abc_path, interleaved_folder, augmented_folder)
        except Exception as e:
            print(abc_path, 'failed:', e)
            continue



if __name__ == '__main__':
    main()


    

