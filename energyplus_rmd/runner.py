from pathlib import Path
from sys import argv, exit
from energyplus_rmd.translator import Translator


def run() -> int:
    if len(argv) < 2:
        print("Need to pass at least 1 args: epJSON file")
        return 1
    epjson_input_file_path = Path(argv[1])
    t = Translator(epjson_input_file_path)
    t.process()
    return 0


if __name__ == "__main__":
    exit(run())
