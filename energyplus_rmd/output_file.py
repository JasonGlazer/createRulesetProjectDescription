from json import dumps
from pathlib import Path
from typing import Dict


class OutputFile:
    def __init__(self, epjson_file_path: Path):
        self.rmd_file_path = epjson_file_path.with_suffix('.rmd')

    def write(self, json_data: Dict):
        self.rmd_file_path.write_text(dumps(json_data, indent=2))
