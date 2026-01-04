import os
import json
import re
from abctoolkit.utils import (find_all_abc, remove_information_field, remove_bar_no_annotations, Quote_re, Barlines,
                   strip_empty_bars)
from abctoolkit.convert import unidecode_abc_lines
from abctoolkit.rotate import rotate_abc
from abctoolkit.check import check_alignment_unrotated



def write_dataset_jsonline_tunesformer(dataset, dataset_folder, jsonl_path):
    '''
    {
        'dataset': '...',
        'filename': '...',
        'output': '...',
    }
    '''
    with open(jsonl_path, 'w', encoding='utf-8') as w:
        for abc_path in find_all_abc(dataset_folder):
            filename = os.path.splitext(os.path.split(abc_path)[-1])[0]
            entry_dict = {
                'dataset': dataset,
                'filename': filename,
                'output': ''
            }
            with open(abc_path, 'r', encoding='utf-8') as f:
                entry_dict['output'] = f.read()

            w.write(json.dumps(entry_dict) + '\n')


def split_jsonl_data(jsonl_path, eval_ratio=0.01):
    pass


def extract_files_from_jsonl(jsonl_path, des_folder):
    pass


def abc_processing_pipeline(ori_folder, des_folder):

    if not os.path.exists(des_folder):
        os.mkdir(des_folder)

    for abc_path in find_all_abc(ori_folder):
        with open(abc_path, 'r', encoding='utf-8') as f:
            abc_lines = f.readlines()

        # 去掉纯换行符
        abc_lines = [line for line in abc_lines if line.strip() != '']

        # unidecode
        abc_lines = unidecode_abc_lines(abc_lines)

        # information field
        abc_lines = remove_information_field(abc_lines=abc_lines, info_fields=['X:', 'T:', 'C:', 'W:', 'w:', 'Z:', '%%MIDI'])

        # 去掉行尾小节号
        abc_lines = remove_bar_no_annotations(abc_lines)

        # 删掉 \"
        for i, line in enumerate(abc_lines):
            if re.search(r'^[A-Za-z]:', line) or line.startswith('%'):
                continue
            else:
                if r'\"' in line:
                    abc_lines[i] = abc_lines[i].replace(r'\"', '')

        # 删掉含小节线的引号文本
        for i, line in enumerate(abc_lines):
            quote_contents = re.findall(Quote_re, line)
            for quote_content in quote_contents:
                for barline in Barlines:
                    if barline in quote_content:
                        line = line.replace(quote_content, '')
                        abc_lines[i] = line

        # 去头尾空白小节
        try:
            stripped_abc_lines, bar_counts = strip_empty_bars(abc_lines)
        except Exception as e:
            print(abc_path, 'Error in stripping empty bars:', e)
            continue
        if stripped_abc_lines is None:
            print(abc_path, 'Failed to strip')
            continue

        # 检查小节数，小于8舍弃
        if bar_counts < 8:
            print(abc_path, 'Few bars:', bar_counts)
            continue

        # 省略：text_annotation 处理

        # 检查小节数、小节线、小节时值是否对齐
        _, bar_no_equal_flag, bar_dur_equal_flag = check_alignment_unrotated(abc_lines)
        if not bar_no_equal_flag:
            print(abc_path, 'Unequal bar number')
            continue
        if not bar_dur_equal_flag:
            print(abc_path, 'Unequal bar duration (unaligned)')
            continue

        # 转置
        try:
            rotated_abc_lines = rotate_abc(stripped_abc_lines)
        except Exception as e:
            print(abc_path, 'Error in rotating:', e)
            continue
        if rotated_abc_lines is None:
            print(abc_path, 'Failed to rotate')
            continue

        des_path = os.path.join(des_folder, os.path.split(abc_path)[-1])
        with open(des_path, 'w', encoding='utf-8') as w:
            w.writelines(rotated_abc_lines)