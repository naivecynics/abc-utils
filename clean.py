ORI_DIRS = ["/nas/hlc/abc/interleaved/classical", "/nas/hlc/abc/interleaved/contemporary", "/nas/hlc/abc/interleaved/pdmx", "/nas/hlc/abc/interleaved/kunstderfuge/"]
TAR_DIRS = ["/nas/hlc/abc/clean/classical", "/nas/hlc/abc/clean/contemporary", "/nas/hlc/abc/clean/pdmx", "/nas/hlc/abc/clean/kunstderfuge"]

# clean.py
from pathlib import Path
from tqdm import tqdm
from cleaner import ABCCleaner


cleaner = ABCCleaner()

def clean_abc(text: str) -> str:
    enc = cleaner.encode(text)
    return enc.text

def process_file(src: Path, dst_root: Path):
    raw = src.read_text(errors="ignore")
    cleaned = clean_abc(raw)
    rel = src.relative_to(src.parents[0])
    dst = dst_root.joinpath(rel)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(cleaned, newline="\n")

def main():
    if len(ORI_DIRS) != len(TAR_DIRS):
        raise ValueError("ORI_DIRS and TAR_DIRS must have the same length")

    for ori, tar in zip(ORI_DIRS, TAR_DIRS):
        ori_path = Path(ori)
        tar_root = Path(tar).resolve()
        tar_root.mkdir(parents=True, exist_ok=True)

        if not ori_path.exists():
            print(f"[WARN] path not found: {ori}")
            continue

        files = list(ori_path.rglob("*.abc"))
        for abc in tqdm(files, desc=f"Cleaning {ori}"):
            try:
                process_file(abc, tar_root)
            except Exception as e:
                print(f"[ERROR] {abc}: {e}")

if __name__ == "__main__":
    main()
