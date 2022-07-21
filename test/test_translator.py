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
        input_file_path.write_text(dumps(
            {
                "Version": {
                    "Version 1": {
                        "version_identifier": "22.1"
                    }
                },
                "Building": {
                    "OfficeSmall": {
                        "loads_convergence_tolerance_value": 0.04
                    }
                }
            }
        ))
        output_file_path = self.run_dir_path / 'inout.json'
        output_file_path.write_text(dumps(
            {
                "TabularReports": ""
            }
        ))
        hourly_result_file = self.run_dir_path / 'inout_hourly.json'
        hourly_result_file.write_text(dumps(
            {
                "Cols": []
            }
        ))
        t = Translator(input_file_path)
        t.process()
        written_json = loads(output_file_path.read_text())
        self.assertIn('TabularReports', written_json)

    def test_input_file_is_invalid_for_translation(self):
        input_file_path = self.run_dir_path / 'in.epJSON'
        input_file_path.write_text(dumps(
            {
                "MISSINGVERSION": "Hi"
            }
        ))

        output_file_path = self.run_dir_path / 'inout.json'
        output_file_path.write_text(dumps(
            {
                "TabularReports": ""
            }
        ))

        hourly_result_file = self.run_dir_path / 'inout_hourly.json'
        hourly_result_file.write_text(dumps(
            {
                "Cols": []
            }
        ))

        t = Translator(input_file_path)
        with self.assertRaises(Exception):
            t.process()

        input_file_path = self.run_dir_path / 'in.epJSON'
        input_file_path.write_text(dumps(
            {
                "Version": {
                    "MISSING VERSION 1": "Hey"
                }
            }
        ))
        t = Translator(input_file_path)
        with self.assertRaises(Exception):
            t.process()

        input_file_path = self.run_dir_path / 'in.epJSON'
        input_file_path.write_text(dumps(
            {
                "Version": {
                    "Version 1": {
                        "MISSING_version_identifier": "hai"
                    }
                }
            }
        ))
        t = Translator(input_file_path)
        with self.assertRaises(Exception):
            t.process()

    def test_from_resource_input_file(self):
        this_dir = Path(__file__).parent.absolute()
        resource_dir = this_dir / 'resources'
        resource_input_file = resource_dir / 'test_input.epJSON'
        output_file_path = resource_dir / 'test_inputout.json'
        t = Translator(resource_input_file)
        t.process()
        written_json = loads(output_file_path.read_text())
        self.assertIn('TabularReports', written_json)

    def set_minimal_files(self):
        input_file_path = self.run_dir_path / 'in.epJSON'
        input_file_path.write_text(dumps(
            {
                "Version": {
                    "Version 1": {
                        "version_identifier": "22.1"
                    }
                },
                "Building": {
                    "OfficeSmall": {
                        "loads_convergence_tolerance_value": 0.04
                    }
                }
            }
        ))
        output_file_path = self.run_dir_path / 'inout.json'
        output_file_path.write_text(dumps(
            {
                "TabularReports": ""
            }
        ))
        hourly_result_file = self.run_dir_path / 'inout_hourly.json'
        hourly_result_file.write_text(dumps(
            {
                "Cols": []
            }
        ))
        t = Translator(input_file_path)
        return t

    def test_add_schedules(self):
        t = self.set_minimal_files()
        t.schedules_used_names = ['ONLY-SCHEDULE',]
        t.json_hourly_results_object = (
            {
                'Cols': [
                    {"Variable": "ONLY-SCHEDULE:Schedule Value"},
                ],
                'Rows': [
                    {
                        "01/01 01:00:00": [ 1, ]
                    }
                ]
            }
        )
        instance = [
            {
                'id': 'ONLY-SCHEDULE',
                'schedule_sequence_type': 'HOURLY',
                'hourly_values': [1]
             }
        ]
        t.add_schedules()
        self.assertEqual(t.instance['schedules'], instance)


