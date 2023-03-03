from json import loads
from pathlib import Path
from tempfile import mkdtemp
from unittest import TestCase

from energyplus_rmd.output_file import OutputFile


class TestOutputFile(TestCase):
    def setUp(self) -> None:
        self.run_dir_path = Path(mkdtemp())

    def test_valid_path_has_json(self):
        out_file = self.run_dir_path / 'output.rmd'
        output_dict = {'message': 'We are all good here'}
        o = OutputFile(out_file)
        o.write(output_dict)
        written_json = loads(out_file.read_text())
        self.assertIn('message', written_json)
