import os
import math
import subprocess
from tqdm import trange
from multiprocessing import Pool
from unidecode import unidecode


cmd = 'cd ' + os.getcwd()
output = os.popen(cmd).read()

def convert_xml2abc(args):
    file_list, cmd_local, des_folder = args

    for file_idx in trange(len(file_list)):
        file = file_list[file_idx]
        filename = os.path.splitext(os.path.split(file)[-1])[0]
        try:
            p = subprocess.Popen(cmd_local + '"' + file + '"', stdout=subprocess.PIPE)
            result = p.communicate()
            output = result[0].decode('utf-8')

            if output == '':
                continue
            else:
                abc_path = os.path.join(des_folder, filename + '.abc')
                with open(abc_path, 'w', encoding='utf-8') as f:
                    f.write(output)
        except Exception as e:
            print(e)
            pass


def convert_abc2xml(args):
    file_list, cmd_local, des_folder = args

    for file_idx in trange(len(file_list)):
        file = file_list[file_idx]
        filename = os.path.splitext(os.path.split(file)[-1])[0]
        try:
            p = subprocess.Popen(cmd_local + file, stdout=subprocess.PIPE)
            result = p.communicate()
            output = result[0].decode('utf-8')

            if output == '':
                continue
            else:
                xml_path = os.path.join(des_folder, filename + '.xml')
                with open(xml_path, 'w', encoding='utf-8') as f:
                    f.write(output)
        except Exception as e:
            print(e)
            pass


def unidecode_abc(args):
    file_list, des_folder = args

    for file_idx in trange(len(file_list)):
        file = file_list[file_idx]
        filename = os.path.splitext(os.path.split(file)[-1])[0]
        unidecoded_abc_path = os.path.join(des_folder, filename + '.abc')

        with open(file, 'r', encoding='utf-8') as f:
            abc_text = f.read()

        abc_text = unidecode(abc_text)

        with open(unidecoded_abc_path, 'w', encoding='utf-8') as w:
            w.write(abc_text)


def unidecode_abc_lines(abc_lines: list):
    # 只返回unidecode结果，不写入文件
    unideccoded_abc_lines = []

    for line in abc_lines:
        unideccoded_abc_lines.append(unidecode(line))

    return unideccoded_abc_lines


def batch_convert_xml2abc(ori_folder, des_folder, unified_L=8, no_line_breaks=True):
    '''
    ori_folder: str
    des_folder: str
    unified_L: set L to 1/unified_L
    no_line_breaks: if False, will output '$' as line breaks
    '''
    if not os.path.exists(des_folder):
        os.mkdir(des_folder)

    cmd_local = 'cmd /u /c python xml2abc.py '
    if unified_L is not None:
        cmd_local += '-d ' + str(unified_L) + ' '
    cmd_local += '-c 6 '
    if no_line_breaks:
        cmd_local += '-x '

    file_list = []
    # traverse folder
    for root, dirs, files in os.walk(ori_folder):
        for file in files:
            if file.endswith('.mxl') or file.endswith('.musicxml') or file.endswith('.xml'):
                filename = os.path.join(root, file)
                file_list.append(filename)

    num_cpu = os.cpu_count()
    arg_lists = []
    for i in range(num_cpu):
        start_idx = int(math.floor(i * len(file_list) / os.cpu_count()))
        end_idx = int(math.floor((i + 1) * len(file_list) / os.cpu_count()))
        arg_lists.append((file_list[start_idx:end_idx], cmd_local, des_folder))

    pool = Pool(processes=os.cpu_count())
    pool.map(convert_xml2abc, arg_lists)


def batch_convert_abc2xml(ori_folder, des_folder):
    '''
    ori_folder: str
    des_folder: str
    '''
    if not os.path.exists(des_folder):
        os.mkdir(des_folder)

    cmd_local = 'cmd /u /c python abc2xml.py '

    file_list = []
    # traverse folder
    for root, dirs, files in os.walk(ori_folder):
        for file in files:
            if file.endswith('.abc') or file.endswith('.txt'):
                filename = os.path.join(root, file)
                file_list.append(filename)

    num_cpu = os.cpu_count()
    arg_lists = []
    for i in range(num_cpu):
        start_idx = int(math.floor(i * len(file_list) / os.cpu_count()))
        end_idx = int(math.floor((i + 1) * len(file_list) / os.cpu_count()))
        arg_lists.append((file_list[start_idx:end_idx], cmd_local, des_folder))

    pool = Pool(processes=os.cpu_count())
    pool.map(convert_abc2xml, arg_lists)


def batch_unidecode_abc(ori_folder, des_folder):
    '''
    ori_folder: str
    des_folder: str
    '''
    if not os.path.exists(des_folder):
        os.mkdir(des_folder)

    file_list = []
    # traverse folder
    for root, dirs, files in os.walk(ori_folder):
        for file in files:
            if file.endswith('.abc') or file.endswith('.txt'):
                filename = os.path.join(root, file)
                if not os.path.exists(os.path.join(des_folder, os.path.splitext(file)[0] + '.abc')):
                    file_list.append(filename)

    num_cpu = os.cpu_count()
    arg_lists = []
    for i in range(num_cpu):
        start_idx = int(math.floor(i * len(file_list) / os.cpu_count()))
        end_idx = int(math.floor((i + 1) * len(file_list) / os.cpu_count()))
        arg_lists.append((file_list[start_idx:end_idx], des_folder))

    pool = Pool(processes=os.cpu_count())
    pool.map(unidecode_abc, arg_lists)



if __name__ == '__main__':
    # batch_unidecode_abc(ori_folder=r'D:\Research\Projects\MultitrackComposer\dataset\03_abc\piano',
    #                     des_folder=r'D:\Research\Projects\MultitrackComposer\dataset\04_abc_unidecoded\piano')

    # batch_convert_xml(ori_folder=r'D:\Research\Projects\MultitrackComposer\dataset\00_raw\midi_abc\meta',
    #                   des_folder=r'D:\Research\Projects\MultitrackComposer\dataset\01_xml\meta')

    batch_convert_xml2abc(ori_folder=r'D:\Research\Projects\MultitrackComposer\dataset\01_xml\meta',
                        des_folder=r'D:\Research\Projects\MultitrackComposer\dataset\03_abc\meta')