from json import dumps
from pathlib import Path
from tempfile import mkdtemp
from unittest import TestCase

from eplus_rmd.input_file import InputFile


class TestInputFile(TestCase):
    def setUp(self) -> None:
        self.run_dir_path = Path(mkdtemp())

    def test_invalid_path(self):
        fake_file = self.run_dir_path / 'dummy.epJSON'
        with self.assertRaises(Exception):
            InputFile(fake_file)

    def test_valid_path_has_json(self):
        real_file = self.run_dir_path / 'real.epJSON'
        real_file.write_text(dumps(
            {
                "Version": {
                    "Version 1": {
                        "version_identifier": "22.1"
                    }
                }
            }
        ))
        result_file = self.run_dir_path / 'realout.JSON'
        result_file.write_text(dumps(
            {
                "out": 7
            }
        ))
        i = InputFile(real_file)
        self.assertIn('Version', i.epjson_object)

    def test_valid_path_but_bad_contents(self):
        real_file = self.run_dir_path / 'real.epJSON'
        real_file.write_text("Hello!")
        with self.assertRaises(Exception):
            InputFile(real_file)
