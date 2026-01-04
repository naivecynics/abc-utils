SYMPHONYNET_CLASSICAL_DIR = 'origin/SymphonyNet_Dataset/classical/'
KUNSTDERFUGE_DIR = 'origin/Kunst der Fuge - Classical Music/'
MERGED_DIR = 'origin/merged/'

import os, shutil

def collect_midis(directory):
    midis = {}
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith('.mid'):
                midis[f] = os.path.join(root, f)
    return midis

def main():
    sym = collect_midis(SYMPHONYNET_CLASSICAL_DIR)
    kunst = collect_midis(KUNSTDERFUGE_DIR)

    sym_names = set(sym.keys())
    kunst_names = set(kunst.keys())

    both = sym_names & kunst_names
    sym_only = sym_names - kunst_names
    kunst_only = kunst_names - sym_names

    os.makedirs(MERGED_DIR, exist_ok=True)
    copied = set()

    for name, src in {**sym, **kunst}.items():
        dst = os.path.join(MERGED_DIR, name)
        if name not in copied:
            shutil.copy2(src, dst)
            copied.add(name)

    print(f"✅ Merge complete: {len(copied)} files copied to '{MERGED_DIR}'")
    print(f"🎵 SymphonyNet only: {len(sym_only)}")
    print(f"🎵 Kunst der Fuge only: {len(kunst_only)}")
    print(f"🎵 Common files: {len(both)}")

if __name__ == "__main__":
    main()
