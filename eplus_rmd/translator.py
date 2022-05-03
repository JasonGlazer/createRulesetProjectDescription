from pathlib import Path
from typing import Dict

from eplus_rmd.input_file import InputFile
from eplus_rmd.output_file import OutputFile


class Translator:
    """This class reads in the input files and does the heavy lifting to write output files"""
    def __init__(self, input_file_path: Path, output_file_path: Path):
        print(f"Reading input file at {str(input_file_path)}")
        self.input_file_object = InputFile(input_file_path)
        print(f"Will write output file to {str(output_file_path)}")
        self.output_file_path = output_file_path

    @staticmethod
    def validate_input_contents(input_json: Dict):
        if 'Version' not in input_json:
            raise Exception("Did not find Version key in input file epJSON contents, aborting")
        if 'Version 1' not in input_json['Version']:
            raise Exception("Did not find \"Version 1\" key in input epJSON Version value, aborting")
        if "version_identifier" not in input_json['Version']['Version 1']:
            raise Exception("Did not find \"version_identifier\" key in input epJSON Version value, aborting")

    def process(self):
        input_json = self.input_file_object.input_file_json
        Translator.validate_input_contents(input_json)
        version_id = input_json['Version']['Version 1']['version_identifier']
        json_dictionary = {'message': f"Found input version as {version_id}"}
        o = OutputFile(self.output_file_path)
        o.write(json_dictionary)
