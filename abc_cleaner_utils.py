import re
from abctoolkit.utils import (
    remove_information_field,
    remove_bar_no_annotations,
    check_alignment_unrotated,
)
from abctoolkit.convert import unidecode_abc_lines

def clean_and_prepare_abc(abc_lines: list) -> list:
    """
    对 ABC 文本进行初步的清理和标准化。
    移除信息字段、不必要的注释，并检查对齐。
    """
    abc_lines = unidecode_abc_lines(abc_lines)
    abc_lines = remove_information_field(
        abc_lines=abc_lines,
        info_fields=['X:', 'T:', 'C:', 'W:', 'w:', 'Z:', '%%MIDI']
    )
    abc_lines = remove_bar_no_annotations(abc_lines)

    cleaned_lines = []
    for line in abc_lines:
        # 移除行内可能的反斜杠转义双引号
        if not re.search(r'^[A-Za-z]:', line) and not line.startswith('%'):
            line = line.replace(r'\"', '"')
        cleaned_lines.append(line)
        
    try:
        _, ok, _ = check_alignment_unrotated(cleaned_lines)
        if not ok:
            raise ValueError("Unequal bar number, alignment check failed.")
    except Exception as e:
        raise ValueError(f"Alignment error during cleaning: {e}")
        
    return cleaned_lines
