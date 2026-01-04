import os
import shutil
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="Flatten and copy all files with a given extension into a single output directory."
    )
    parser.add_argument(
        "-i", "--input_dir",
        default="scores",
        help="Root directory to search (default: 'scores')"
    )
    parser.add_argument(
        "-o", "--output_dir",
        default="mxl",
        help="Destination directory (default: 'mxl')"
    )
    parser.add_argument(
        "-e", "--ext",
        default="mxl",
        help="File extension to include (default: 'mxl')"
    )
    parser.add_argument(
        "-s", "--sep",
        default="-",
        help="Separator for replacing '/' in flattened filenames (default: '-')"
    )

    args = parser.parse_args()
    input_dir = args.input_dir
    output_dir = args.output_dir
    ext = args.ext.lower().lstrip(".")
    sep = args.sep

    os.makedirs(output_dir, exist_ok=True)
    count = 0

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith(f".{ext}"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, input_dir)
                flat_name = rel_path.replace(os.sep, sep)
                dest_path = os.path.join(output_dir, flat_name)

                shutil.copy2(full_path, dest_path)
                count += 1

    print(f"Copied {count} '.{ext}' files from '{input_dir}' to '{output_dir}' (separator='{sep}').")

if __name__ == "__main__":
    main()
