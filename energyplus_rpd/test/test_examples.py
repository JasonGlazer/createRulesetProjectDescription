from pathlib import Path
from unittest import TestCase

from energyplus_rpd.runner import run_with_path


class TestRunExampleFiles(TestCase):

    def setUp(self):
        current_file = Path(__file__).resolve()
        package_root = current_file.parent.parent
        self.example_dir = package_root / 'example'

    def test_examples(self):
        test_file = self.example_dir / 'ASHRAE901_OfficeSmall_STD2019_Denver.epJSON'
        # print('before run of example files')
        try:
            run_with_path(test_file)
        except Exception as e:
            self.fail(f"Could not process example file; error: {e}")
        # print('finished running example files')
