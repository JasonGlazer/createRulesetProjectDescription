import os

from json import loads
from pathlib import Path


class InputFile:

    def __init__(self, epjson_file_path: Path):
        if not epjson_file_path.exists():
            raise Exception(f"Could not find input file at path: {str(epjson_file_path)}")
        try:
            epjson_contents = epjson_file_path.read_text()
            self.epjson_object = loads(epjson_contents)
        except Exception as e:
            print(f"Could not process input file into JSON object; error: {str(e)}")
            raise

        input_file_path_noext, _ = os.path.splitext(epjson_file_path)
        json_results_input_path = Path(input_file_path_noext + ".json")
        if not json_results_input_path.exists():
            json_results_input_path = Path(input_file_path_noext + "out.json")
            if not json_results_input_path.exists():
                raise Exception(f"Could not find EnergyPlus results json file at path: {str(input_file_path_noext)} .json or out.json")
            try:
                json_result_file_contents = json_results_input_path.read_text()
                self.json_results_object = loads(json_result_file_contents)
            except Exception as e:
                print(f"Could not process results file into JSON object; error: {str(e)}")
                raise
