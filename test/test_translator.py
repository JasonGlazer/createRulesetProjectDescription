from json import dumps, loads
from pathlib import Path
from tempfile import mkdtemp
from unittest import TestCase

from eplus_rmd.translator import Translator


class TestTranslator(TestCase):
    def setUp(self) -> None:
        self.run_dir_path = Path(mkdtemp())

    def test_operation(self):
        input_file_path = self.run_dir_path / 'in.epJSON'
        output_file_path = self.run_dir_path / 'out.json'
        input_file_path.write_text(dumps(
            {
                "Version": {
                    "Version 1": {
                        "version_identifier": "22.1"
                    }
                }
            }
        ))
        t = Translator(input_file_path, output_file_path)
        t.process()
        written_json = loads(output_file_path.read_text())
        self.assertIn('message', written_json)

    def test_input_file_is_invalid_for_translation(self):
        input_file_path = self.run_dir_path / 'in.epJSON'
        output_file_path = self.run_dir_path / 'out.json'
        input_file_path.write_text(dumps(
            {
                "MISSINGVERSION": "Hi"
            }
        ))
        t = Translator(input_file_path, output_file_path)
        with self.assertRaises(Exception):
            t.process()

        input_file_path = self.run_dir_path / 'in.epJSON'
        output_file_path = self.run_dir_path / 'out.json'
        input_file_path.write_text(dumps(
            {
                "Version": {
                    "MISSING VERSION 1": "Hey"
                }
            }
        ))
        t = Translator(input_file_path, output_file_path)
        with self.assertRaises(Exception):
            t.process()

        input_file_path = self.run_dir_path / 'in.epJSON'
        output_file_path = self.run_dir_path / 'out.json'
        input_file_path.write_text(dumps(
            {
                "Version": {
                    "Version 1": {
                        "MISSING_version_identifier": "hai"
                    }
                }
            }
        ))
        t = Translator(input_file_path, output_file_path)
        with self.assertRaises(Exception):
            t.process()

    def test_from_resource_input_file(self):
        this_dir = Path(__file__).parent.absolute()
        resource_dir = this_dir / 'resources'
        resource_input_file = resource_dir / 'test_input.epJSON'
        output_file_path = self.run_dir_path / 'out.json'
        t = Translator(resource_input_file, output_file_path)
        t.process()
        written_json = loads(output_file_path.read_text())
        self.assertIn('message', written_json)
