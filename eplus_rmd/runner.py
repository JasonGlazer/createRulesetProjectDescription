from pathlib import Path
from sys import argv, exit
from eplus_rmd.translator import Translator


def run():
    if len(argv) < 2:
        print("Need to pass at least 1 args: epJSON file")
        exit(1)
    epjson_input_file_path = Path(argv[1])
    t = Translator(epjson_input_file_path)
    t.process()


if __name__ == "__main__":
    run()
