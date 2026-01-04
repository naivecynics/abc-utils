import argparse
import subprocess
from pathlib import Path
from multiprocessing import Pool
from tqdm import tqdm
import os
import sys
import tempfile

script_dir = Path(__file__).parent
sys.path.append(str(script_dir))
sys.path.append(str(script_dir / "EasyABC"))
sys.path.append(str(script_dir / "abctoolkit"))

# --- 1. Core Single-Step Processing Functions ---

def musescore_convert(input_path: Path, output_path: Path, mode: str):
    musescore_app = "/Applications/MuseScore 4.app/Contents/MacOS/mscore"
    if not Path(musescore_app).exists():
        raise FileNotFoundError(f"MuseScore not found at: {musescore_app}")
    
    command = f'"{musescore_app}" -o "{str(output_path.absolute())}" "{str(input_path.absolute())}"'
    process = subprocess.run(command, capture_output=True, text=True, shell=True)
    
    if process.returncode != 0 or not output_path.exists():
        error_message = process.stderr or process.stdout
        raise RuntimeError(f"MuseScore conversion failed: {error_message}")

def midi2xml(input_path: Path, output_path: Path):
    musescore_convert(input_path, output_path, "midi2xml")

def xml2midi(input_path: Path, output_path: Path):
    musescore_convert(input_path, output_path, "xml2midi")

def xml2abc(input_path: Path, output_path: Path):
    script_path = script_dir / "EasyABC" / "xml2abc.py"
    command = f'python "{script_path}" -d 8 -c 6 -x "{str(input_path.absolute())}"'
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"xml2abc.py failed: {result.stderr}")
    
    if not result.stdout:
        raise RuntimeError("xml2abc.py produced no output.")
        
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result.stdout)

def abc2xml(input_path: Path, output_path: Path):
    script_path = script_dir / "EasyABC" / "abc2xml.py"
    command = f'python "{script_path}" "{str(input_path.absolute())}" -o "{str(output_path.absolute())}"'
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        raise RuntimeError(f"abc2xml.py failed: {result.stderr}")

def abc2abci(input_path: Path, output_path: Path):
    from abctoolkit.rotate import rotate_abc
    with open(input_path, 'r', encoding='utf-8') as f:
        abc_lines = [line for line in f.readlines() if line.strip()]
    interleaved_lines = rotate_abc(abc_lines)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(interleaved_lines)

def abci2abc(input_path: Path, output_path: Path):
    from abctoolkit.rotate import unrotate_abc
    with open(input_path, 'r', encoding='utf-8') as f:
        abci_lines = [line for line in f.readlines() if line.strip()]
    abc_lines = unrotate_abc(abci_lines)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(abc_lines)

# --- 2. Batch Processor Framework ---

def _process_wrapper(args):
    input_path, output_path, process_function, log_file = args
    try:
        if output_path.exists():
            return
        process_function(input_path, output_path)
    except Exception as e:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"Error processing {input_path}: {e}\n")

class BatchProcessor:
    def __init__(self, input_dir, output_dir, in_globs, out_suffix, process_function):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.in_globs = in_globs if isinstance(in_globs, list) else [in_globs]
        self.out_suffix = out_suffix
        self.process_function = process_function
        self.log_file = self.output_dir / "logs" / f"{self.output_dir.name}_error.log"

    def _setup_directories(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        self._setup_directories()
        
        files_to_process = []
        for glob_pattern in self.in_gloglobs:
            files_to_process.extend(self.input_dir.rglob(glob_pattern))
        
        files_to_process = sorted(list(set(files_to_process)))

        if not files_to_process:
            print(f"No files found matching {self.in_globs} in {self.input_dir}. Exiting step.")
            return False

        print(f"Found {len(files_to_process)} files. Processing...")

        tasks = []
        for input_path in files_to_process:
            relative_path = input_path.relative_to(self.input_dir)
            output_path = (self.output_dir / relative_path).with_suffix(self.out_suffix)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            tasks.append((input_path, output_path, self.process_function, self.log_file))

        with Pool(os.cpu_count()) as pool:
            list(tqdm(pool.imap_unordered(_process_wrapper, tasks), total=len(tasks)))
        
        print(f"Step complete. Output in: {self.output_dir}")
        if self.log_file.exists():
            print(f"Errors (if any) logged in: {self.log_file}")
        return True


# --- 3. Main Entry Point & Chain Execution ---

def main():
    parser = argparse.ArgumentParser(description="A chained batch converter for music files.")
    parser.add_argument("mode", help="Conversion mode, e.g., 'midi2abc'.")
    parser.add_argument("-i", "--input_dir", required=True, help="Input directory.")
    parser.add_argument("-o", "--output_dir", required=True, help="Final output directory.")
    parser.add_argument("-t", "--temp_dir", help="Optional: Specify a directory for temporary files.")
    parser.add_argument("--keep_temp", action="store_true", help="Keep the temporary directory for debugging.")
    args = parser.parse_args()

    xml_exts = ["*.xml", "*.mxl", "*.musicxml"]

    step_definitions = {
        "midi2xml": {"func": midi2xml, "in_globs": "*.mid",  "out_suffix": ".mxl"},
        "xml2midi": {"func": xml2midi, "in_globs": xml_exts, "out_suffix": ".mid"},
        "xml2abc":  {"func": xml2abc,  "in_globs": xml_exts, "out_suffix": ".abc"},
        "abc2xml":  {"func": abc2xml,  "in_globs": "*.abc",  "out_suffix": ".mxl"},
        "abc2abci": {"func": abc2abci, "in_globs": "*.abc",  "out_suffix": ".abci"},
        "abci2abc": {"func": abci2abc, "in_globs": "*.abci", "out_suffix": ".abc"},
        "abci2xml": {"func": abc2xml,  "in_globs": "*.abci", "out_suffix": ".mxl"},
    }

    conversion_chains = {
        "midi2xml": ["midi2xml"],
        "xml2midi": ["xml2midi"],
        "xml2abc":  ["xml2abc"],
        "abc2xml":  ["abc2xml"],
        "abc2abci": ["abc2abci"],
        "abci2abc": ["abci2abc"],
        "midi2abc": ["midi2xml", "xml2abc"],
        "abc2midi": ["abc2xml", "xml2midi"],
        "midi2abci": ["midi2xml", "xml2abc", "abc2abci"],
        "abci2midi": ["abci2abc", "abc2xml", "xml2midi"],
        "xml2abci": ["xml2abc", "abc2abci"],
        "abci2xml": ["abci2xml"],
    }

    mode = args.mode.lower()
    if mode not in conversion_chains:
        print(f"Error: Invalid mode '{mode}'.")
        print("Available modes are:", ", ".join(conversion_chains.keys()))
        sys.exit(1)

    chain = conversion_chains[mode]
    
    if args.keep_temp:
        temp_dir_base = args.temp_dir if args.temp_dir else None
        # Manually create a persistent temporary directory
        temp_dir = tempfile.mkdtemp(prefix="converter_", dir=temp_dir_base)
        print(f"Temporary directory will be kept at: {temp_dir}")
        try:
            run_chain(chain, args.input_dir, args.output_dir, step_definitions, temp_dir)
        finally:
            # Don't clean up when keep_temp is True
            pass
    else:
        temp_dir_base = args.temp_dir if args.temp_dir else None
        if temp_dir_base:
            Path(temp_dir_base).mkdir(parents=True, exist_ok=True)
        # Use context manager for automatic cleanup
        with tempfile.TemporaryDirectory(prefix="converter_", dir=temp_dir_base) as temp_dir:
            run_chain(chain, args.input_dir, args.output_dir, step_definitions, temp_dir)
            
    print("\nAll steps completed.")

def run_chain(chain, input_dir, output_dir, step_definitions, temp_dir):
    current_input_dir = input_dir
    
    for i, step_name in enumerate(chain):
        step_config = step_definitions[step_name]
        is_last_step = (i == len(chain) - 1)
        
        print(f"\n--- Running Step {i+1}/{len(chain)}: {step_name} ---")
        
        if is_last_step:
            current_output_dir = output_dir
        else:
            temp_step_dir = Path(temp_dir) / f"step_{i+1}"
            current_output_dir = str(temp_step_dir)
        
        processor = BatchProcessor(
            input_dir=current_input_dir,
            output_dir=current_output_dir,
            in_globs=step_config["in_globs"],
            out_suffix=step_config["out_suffix"],
            process_function=step_config["func"]
        )
        
        success = processor.run()
        if not success:
            print(f"Step '{step_name}' failed because no input files were found. Halting chain.")
            break

        current_input_dir = current_output_dir

if __name__ == "__main__":
    main()
