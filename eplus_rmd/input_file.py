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

        json_results_input_path = epjson_file_path.with_suffix(".json")
        if not json_results_input_path.exists():
            # try with the out.json suffix
            json_results_input_path = epjson_file_path.parent.joinpath(epjson_file_path.stem + "out.json")
            if not json_results_input_path.exists():
                raise Exception(f"Could not find EnergyPlus results json file at path: {str(json_results_input_path)}")
            try:
                json_result_file_contents = json_results_input_path.read_text()
                self.json_results_object = loads(json_result_file_contents)
            except Exception as e:
                print(f"Could not process results file into JSON object; error: {str(e)}")
                raise
