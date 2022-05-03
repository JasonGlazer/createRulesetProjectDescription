from json import dumps
from pathlib import Path
from typing import Dict


class OutputFile:
    def __init__(self, output_file_path: Path):
        self.output_file_path = output_file_path

    def write(self, json_data: Dict):
        self.output_file_path.write_text(dumps(json_data, indent=2))
