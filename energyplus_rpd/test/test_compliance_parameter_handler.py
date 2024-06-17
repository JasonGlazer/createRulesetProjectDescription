from pathlib import Path
from tempfile import mkdtemp
from unittest import TestCase

from energyplus_rpd.compliance_parameter_handler import ComplianceParameterHandler


class TestComplianceParameterHandler(TestCase):

    def setUp(self) -> None:
        self.run_dir_path = Path(mkdtemp())

    def test_init(self):
        input_file_path = self.run_dir_path / 'in.epJSON'
        cph = ComplianceParameterHandler(input_file_path)
        elements = cph.compliance_group_element
        self.assertEqual(elements['building'], {'building_open_schedule': ''})
        self.assertEqual(cph.cp_empty_file_path.name, 'in.comp-param-empty.json')
        self.assertEqual(cph.cp_file_path.name, 'in.comp-param.json')
