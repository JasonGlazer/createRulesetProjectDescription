from pathlib import Path
from sys import exit
from energyplus_rpd.translator import Translator
import argparse


def run_with_path(p: Path, add_cp=False, empty_cp=False) -> int:
    t = Translator(p, add_cp=add_cp, empty_cp=empty_cp)
    t.process()
    return 0


def build_argument_parser():
    parser = argparse.ArgumentParser(
        prog='createRulesetProjectDescription',
        description='An EnergyPlus utility that creates a Ruleset Project Description (RPD) file based on output (and '
                    'some input) from a simulation that is consistent with Standard 229P.'
    )
    parser.add_argument(
        'filename',
        help='the name of the epJSON file name with path'
    )
    parser.add_argument(
        '--add_cp',
        '-a',
        action="store_true",
        help='Add the compliance parameters located in the <filename>.comp-param.json file'
    )
    parser.add_argument(
        '--create_empty_cp',
        '-c',
        action="store_true",
        help='Create an empty compliance parameter file using the name <filename>.comp-param-empty.json'
    )
    return parser


def run() -> int:
    cli = build_argument_parser()
    args = cli.parse_args()
    if args.filename:
        epjson_input_file_path = Path(args.filename)
        return run_with_path(epjson_input_file_path, args.add_cp, args.create_empty_cp)
    else:
        print('An epJSON file name must be specified.')
        return 1


if __name__ == "__main__":
    exit(run())
