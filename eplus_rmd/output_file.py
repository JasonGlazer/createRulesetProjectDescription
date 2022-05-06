import os

from json import dumps
from pathlib import Path
from typing import Dict


class OutputFile:
    def __init__(self, epjson_file_path: Path):

        epjson_file_path_no_ext, _ = os.path.splitext(epjson_file_path)
        self.rmd_file_path = Path(epjson_file_path_no_ext + ".rmd")

    def write(self, json_data: Dict):
        self.rmd_file_path.write_text(dumps(json_data, indent=2))
