import os
import random
import argparse
import subprocess
from tqdm import tqdm
from multiprocessing import Pool

def convert_xml2abc(file_list, des_folder):
    cmd = 'python utils/xml2abc.py -d 8 -c 6 -x '
    for file in tqdm(file_list):
        filename = os.path.basename(file)
        os.makedirs(des_folder, exist_ok=True)

        try:
            p = subprocess.Popen(cmd + '"' + file + '"', stdout=subprocess.PIPE, shell=True)
            result = p.communicate()
            output = result[0].decode('utf-8')

            if output == '':
                with open("logs/xml2abc_error_log.txt", "a", encoding="utf-8") as f:
                    f.write(file + '\n')
                continue
            else:
                with open(os.path.join(des_folder, filename.rsplit('.', 1)[0] + '.abc'), 'w', encoding='utf-8') as f:
                    f.write(output)
        except Exception as e:
            with open("logs/xml2abc_error_log.txt", "a", encoding="utf-8") as f:
                f.write(file + ' ' + str(e) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Batch convert MusicXML/MXL files to ABC notation.")
    parser.add_argument('-i', '--input_dir', required=True, help='Input directory containing XML/MXL files')
    parser.add_argument('-o', '--output_dir', required=True, help='Output directory for ABC files')
    args = parser.parse_args()

    ori_folder = args.input_dir
    des_folder = args.output_dir

    file_list = []
    os.makedirs("logs", exist_ok=True)

    for root, dirs, files in os.walk(os.path.abspath(ori_folder)):
        for file in files:
            if file.endswith((".mxl", ".xml", ".musicxml")):
                filename = os.path.join(root, file).replace("\\", "/")
                file_list.append(filename)

    random.shuffle(file_list)
    num_files = len(file_list)
    num_processes = os.cpu_count()
    file_lists = [file_list[i::num_processes] for i in range(num_processes)]

    with Pool(processes=num_processes) as pool:
        pool.starmap(convert_xml2abc, [(chunk, des_folder) for chunk in file_lists])
