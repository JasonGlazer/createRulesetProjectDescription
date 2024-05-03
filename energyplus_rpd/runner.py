from pathlib import Path
from sys import argv, exit
from energyplus_rpd.translator import Translator

def run_with_path(p: Path) -> int:
    t = Translator(p)
    t.process()
    return 0

def run() -> int:
    if len(argv) < 2:
        print("Need to pass at least 1 args: epJSON file")
        return 1
    epjson_input_file_path = Path(argv[1])
    return run_with_path(epjson_input_file_path)


if __name__ == "__main__":
    exit(run())
