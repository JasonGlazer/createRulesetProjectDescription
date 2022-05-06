from pathlib import Path
from typing import Dict

from eplus_rmd.input_file import InputFile
from eplus_rmd.output_file import OutputFile


class Translator:
    """This class reads in the input files and does the heavy lifting to write output files"""
    def __init__(self, epjson_file_path: Path):
        print(f"Reading epJSON input file at {str(epjson_file_path)}")
        self.epjson_file = InputFile(epjson_file_path)
        self.epjson_object = self.epjson_file.epjson_object
        self.json_results_object = self.epjson_file.json_results_object

        self.rmd_file_path = OutputFile(epjson_file_path)
        print(f"Will write output file to {str(self.rmd_file_path)}")

    @staticmethod
    def validate_input_contents(input_json: Dict):
        if 'Version' not in input_json:
            raise Exception("Did not find Version key in input file epJSON contents, aborting")
        if 'Version 1' not in input_json['Version']:
            raise Exception("Did not find \"Version 1\" key in input epJSON Version value, aborting")
        if "version_identifier" not in input_json['Version']['Version 1']:
            raise Exception("Did not find \"version_identifier\" key in input epJSON Version value, aborting")

    def process(self):
        epjson = self.epjson_object
        Translator.validate_input_contents(epjson)
        version_id = epjson['Version']['Version 1']['version_identifier']
        json_dictionary = {'message': f"Found input version as {version_id}"}
        self.rmd_file_path.write(json_dictionary)
