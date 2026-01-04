# -*- coding: utf-8 -*-
"""
MuseScore command line conversion script.

Intended for the lieder corpus, but applicable more widely.

By Alex Pacha (apacha) 2023
and Mark Gotham 2025
Modified by Langchu 2025
"""

import argparse
import subprocess
from pathlib import Path
from tqdm import tqdm


def convert(
    in_path: Path,
    out_path: Path,
    musescore_command: str = "/Applications/MuseScore 4.app/Contents/MacOS/mscore"
):
    """Convert one file with MuseScore command line conversion script."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    convert_command = f'"{musescore_command}" -o "{str(out_path.absolute())}" "{str(in_path.absolute())}"'
    process = subprocess.run(convert_command, stderr=subprocess.PIPE, text=True, shell=True)
    if not out_path.exists():
        print("Failed to convert: " + str(in_path) + "\n" + process.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Converts a directory of score files using MuseScore CLI.'
    )
    parser.add_argument('-i', '--input_directory', default="scores", help='The input directory')
    parser.add_argument('-o', '--output_directory', default=None, help='The output directory (if omitted, same as input)')
    parser.add_argument('--in_format', default="mscx", help='Input file format (e.g. mscx, mscz, mid)')
    parser.add_argument('--out_format', default="mxl", help='Output file format (e.g. mxl, midi, pdf)')

    args = parser.parse_args()

    input_directory = Path(args.input_directory)
    output_directory = Path(args.output_directory) if args.output_directory else None
    in_format = args.in_format
    out_format = args.out_format

    all_input_files = list(input_directory.rglob(f"*.{in_format}"))
    for in_path in tqdm(all_input_files, desc=f"Converting {in_format} to {out_format}"):
        if output_directory:
            # flat mode: put all outputs into the given directory
            flat_name = in_path.relative_to(input_directory).as_posix().replace("/", "_")
            out_path = (output_directory / flat_name).with_suffix(f".{out_format}")
        else:
            # original mode: preserve folder structure
            out_path = (in_path.parent / in_path.stem).with_suffix(f".{out_format}")

        if out_path.exists():
            continue
        convert(in_path, out_path)
