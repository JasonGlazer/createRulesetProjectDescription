from pathlib import Path
from tempfile import mkdtemp
from unittest import TestCase

from energyplus_rpd.compliance_parameter_handler import ComplianceParameterHandler


class TestComplianceParameterHandler(TestCase):

    def setUp(self) -> None:
        self.run_dir_path = Path(mkdtemp())
        input_file_path = self.run_dir_path / 'in.epJSON'
        self.cph = ComplianceParameterHandler(input_file_path)

    def test_init(self):
        input_file_path = self.run_dir_path / 'in.epJSON'
        cph = ComplianceParameterHandler(input_file_path)
        elements = cph.compliance_group_element
        self.assertEqual(elements['building'], {'building_open_schedule': ''})
        self.assertEqual(cph.cp_empty_file_path.name, 'in.comp-param-empty.json')
        self.assertEqual(cph.cp_file_path.name, 'in.comp-param.json')

    def test_add_compliance_parameters(self):
        return_dict = {}
        self.cph.add_compliance_parameters('', return_dict)
        self.assertEqual(return_dict, {})

        return_dict = {}
        self.cph.add_compliance_parameters('building', return_dict)
        self.assertEqual(return_dict,  {'building_open_schedule': ''})

        return_dict = {}
        self.cph.add_compliance_parameters('subsurfaces', return_dict)
        expected = ({'subclassification': 'OTHER',
                     'is_operable': False,
                     'has_open_sensor': False,
                     'framing_type': 'ALUMINUM_WITH_BREAK',
                     'has_manual_interior_shades': False,
                     'status_type': 'NEW'})
        self.assertEqual(return_dict,  expected)

    def test_mirror_nested(self):
        original_dict = {'id': 'Name1',
                         'a': 1,
                         'b': [
                             {'id': 'Name2', 'c': 8},
                             {'id': 'Name3', 'd': 9},
                             ],
                         'e': {'id': 'Name4', 'f': 3, 'g': 'h'}}
        result_dict = {}
        self.cph.mirror_nested(original_dict, result_dict)
        self.assertEqual(original_dict, result_dict)

    def test_merge_in_compliance_parameters(self):
        pass
