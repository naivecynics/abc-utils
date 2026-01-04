import os
import math
import subprocess
from tqdm import trange
from multiprocessing import Pool


def convert_abc(file_list, cmd, des_folder):
    for file_idx in trange(len(file_list)):
        file = file_list[file_idx]
        filename = os.path.splitext(file.split('\\')[-1])[0]

        try:
            p = subprocess.Popen(cmd + '"' + file + '"', stdout=subprocess.PIPE)
            result = p.communicate()
            output = result[0].decode('utf-8')

            if output=='':
                continue
            else:
                abc_path = os.path.join(des_folder, filename + '.abc')
                with open(abc_path, 'w', encoding='utf-8') as f:
                    f.write(output)
        except Exception as e:
            print(e)
            pass


def batch_convert_abc(ori_folder, des_folder, unified_L=8, no_line_breaks=True):
    '''
    ori_folder: str
    des_folder: str
    unified_L: set L to 1/unified_L
    no_line_breaks: if False, will output '$' as line breaks
    '''

    cmd = 'cd ' + os.getcwd()
    output = os.popen(cmd).read()
    cmd = 'cmd /u /c python xml2abc.py '
    if unified_L is not None:
        cmd += '-d ' + str(unified_L) + ' '
    cmd += '-c 6 '
    if no_line_breaks:
        cmd += '-x '

    file_list = []
    # traverse folder
    for root, dirs, files in os.walk(ori_folder):
        for file in files:
            if file.endswith('mxl') or file.endswith('musicxml') or file.endswith('.xml'):
                filename = os.path.join(root, file)
                file_list.append(filename)

    num_cpu = os.cpu_count()
    arg_lists = [[] for _ in range(num_cpu)]
    for i in range(num_cpu):
        start_idx = int(math.floor(i * len(file_list) / os.cpu_count()))
        end_idx = int(math.floor((i + 1) * len(file_list) / os.cpu_count()))
        for j in range(start_idx, end_idx):
            arg_lists[i].append((file_list[j], cmd, des_folder))

    pool = Pool(processes=os.cpu_count())
    pool.map(convert_abc, arg_lists)



