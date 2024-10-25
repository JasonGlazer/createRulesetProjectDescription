from json import loads
from pathlib import Path


class InputFile:

    def __init__(self, epjson_file_path: Path):
        self._load_epjson(epjson_file_path)
        self._load_output_json(epjson_file_path)
        self._load_hourly_output_json(epjson_file_path)

    def _load_epjson(self, epjson_file_path: Path):
        if not epjson_file_path.exists():
            raise Exception(f"Could not find input file at path: {epjson_file_path}")
        try:
            epjson_contents = epjson_file_path.read_text()
            self.epjson_object = loads(epjson_contents)
        except Exception as e:
            print(f"Could not process input file into JSON object; error: {e}")
            raise

    def _load_output_json(self, epjson_file_path: Path):
        self.json_results_input_path = epjson_file_path.with_suffix(".json")
        if not self.json_results_input_path.exists():
            # try with the out.json suffix
            self.json_results_input_path = epjson_file_path.with_name(epjson_file_path.stem + "out.json")
            if not self.json_results_input_path.exists():
                raise Exception(
                    f"Could not find EnergyPlus results json file at path: {self.json_results_input_path}")
        try:
            self.json_result_file_contents = self.json_results_input_path.read_text()
            self.json_results_object = loads(self.json_result_file_contents)
        except Exception as e:
            print(f"Could not process results file into JSON object; error: {e}")
            raise

    def _load_hourly_output_json(self, epjson_file_path):
        self.json_hourly_results_input_path = epjson_file_path.with_name(epjson_file_path.stem + "_hourly.json")
        if not self.json_hourly_results_input_path.exists():
            self.json_hourly_results_input_path = epjson_file_path.with_name(epjson_file_path.stem + "out_hourly.json")
            if not self.json_hourly_results_input_path.exists():
                raise Exception(
                    f"Could not find EnergyPlus hourly results json file at path: "
                    f"{self.json_hourly_results_input_path}")
        try:
            self.json_hourly_result_file_contents = self.json_hourly_results_input_path.read_text()
            self.json_hourly_results_object = loads(self.json_hourly_result_file_contents)
        except Exception as e:
            print(f"Could not process hourly results file into JSON object; error: {e}")
            raise
