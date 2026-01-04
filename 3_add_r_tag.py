import os
import argparse

def process_abc_file(in_path, out_path):
    with open(in_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    body_lines = [i for i, line in enumerate(lines) if line.strip().startswith("[")]
    total = len(body_lines)
    if total == 0:
        return

    new_lines = []
    count = 1
    for i, line in enumerate(lines):
        if i in body_lines:
            new_lines.append(f"[r:{count}/{total-count}]{line}")
            count += 1
        else:
            new_lines.append(line)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def main():
    parser = argparse.ArgumentParser(description="Recursively add [r:x/rest] tags to body lines in ABC files.")
    parser.add_argument("-i", "--input_dir", required=True, help="Input directory containing .abc files")
    parser.add_argument("-o", "--output_dir", required=True, help="Output directory for processed files")
    args = parser.parse_args()

    in_dir = os.path.abspath(args.input_dir)
    out_dir = os.path.abspath(args.output_dir)

    for root, _, files in os.walk(in_dir):
        for name in files:
            if name.lower().endswith(".abc"):
                in_path = os.path.join(root, name)
                rel_path = os.path.relpath(in_path, in_dir)
                out_path = os.path.join(out_dir, rel_path)
                process_abc_file(in_path, out_path)

if __name__ == "__main__":
    main()
