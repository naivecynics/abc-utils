import os
import random
import argparse
import subprocess
from tqdm import tqdm
from multiprocessing import Pool


def convert_abc2xml(file_list, des_folder):
    cmd = "python utils/abc2xml.py "
    os.makedirs(des_folder, exist_ok=True)

    for file in tqdm(file_list):
        filename = os.path.basename(file)
        output_path = os.path.join(
            des_folder,
            ".".join(filename.split(".")[:-1]) + ".xml"
        )

        try:
            p = subprocess.Popen(
                cmd + '"' + file + '"',
                stdout=subprocess.PIPE,
                shell=True
            )
            result = p.communicate()
            output = result[0].decode("utf-8")

            if output.strip() == "":
                with open("logs/abc2xml_error_log.txt", "a", encoding="utf-8") as f:
                    f.write(file + "\n")
                continue

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)

        except Exception as e:
            with open("logs/abc2xml_error_log.txt", "a", encoding="utf-8") as f:
                f.write(file + " " + str(e) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch convert ABC files to MusicXML."
    )
    parser.add_argument( "-i", "--input_dir", required=True, help="Input directory containing ABC files",)
    parser.add_argument( "-o", "--output_dir", required=True, help="Output directory for XML files",)
    args = parser.parse_args()

    ori_folder = os.path.abspath(args.input_dir)
    des_folder = os.path.abspath(args.output_dir)

    os.makedirs("logs", exist_ok=True)

    file_list = []

    # Collect ABC files
    for root, _, files in os.walk(ori_folder):
        for file in files:
            if not file.lower().endswith(".abc"):
                continue
            filename = os.path.join(root, file).replace("\\", "/")
            file_list.append(filename)

    random.shuffle(file_list)

    num_proc = os.cpu_count() or 1
    # split file_list into num_proc chunks
    chunks = [file_list[i::num_proc] for i in range(num_proc)]

    with Pool(processes=num_proc) as pool:
        pool.starmap(convert_abc2xml, [(chunk, des_folder) for chunk in chunks])
