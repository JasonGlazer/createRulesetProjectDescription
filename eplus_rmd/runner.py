from pathlib import Path
from sys import argv, exit
from eplus_rmd.translator import Translator


def run():
    if len(argv) < 3:
        print("Need to pass at least 2 args: input file and output file")
        exit(1)
    input_file_path = Path(argv[1])
    output_file_path = Path(argv[2])
    t = Translator(input_file_path, output_file_path)
    t.process()


if __name__ == "__main__":
    run()
