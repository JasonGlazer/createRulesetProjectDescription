from pathlib import Path

from eplus_rmd.input_file import InputFile
from eplus_rmd.output_file import OutputFile


class Translator:
    """This class reads in the input files and does the heavy lifting to write output files"""
    def __init__(self, input_file_path: Path, output_file_path: Path):
        self.input_file_object = InputFile(input_file_path)
        self.output_file_path = output_file_path

    def process(self):
        input_json = self.input_file_object.input_file_json
        if 'Version' not in input_json:
            raise Exception("Did not find Version key in input file epJSON contents, aborting")
        if 'Version 1' not in input_json['Version']:
            raise Exception("Did not find \"Version 1\" key in input epJSON Version value, aborting")
        version_id = input_json['Version']['Version 1']
        json_dictionary = {'message': f"Found input version as {version_id}"}
        o = OutputFile(self.output_file_path)
        o.write(json_dictionary)
