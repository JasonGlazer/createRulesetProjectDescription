from json import loads
from pathlib import Path


class InputFile:
    def __init__(self, input_file_path: Path):
        if not input_file_path.exists():
            raise Exception(f"Could not find input file at path: {str(input_file_path)}")
        try:
            input_file_contents = input_file_path.read_text()
            self.input_file_json = loads(input_file_contents)
        except Exception as e:
            print(f"Could not process input file into JSON object; error: {str(e)}")
            raise
