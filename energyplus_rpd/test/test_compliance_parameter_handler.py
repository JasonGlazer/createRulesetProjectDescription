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
        original_dict = {'id': 'CORE_ZN ZN PSZ-AC-1',
                         'heating_system': {'id': 'CORE_ZN ZN PSZ-AC-1-heating', 'design_capacity': 9209.104,
                                            'type': 'HEAT_PUMP', 'energy_source_type': 'ELECTRICITY',
                                            'rated_capacity': 9221.21, 'oversizing_factor': 1.000000434352977,
                                            'is_sized_based_on_design_day': True, 'heating_coil_setpoint': 46.8,
                                            'efficiency_metric_values': [7.53, 6.84],
                                            'efficiency_metric_types': ['HEATING_SEASONAL_PERFORMANCE_FACTOR',
                                                                        'HEATING_SEASONAL_PERFORMANCE_FACTOR_2'],
                                            'heatpump_low_shutoff_temperature': -12.2},
                         'fan_system': {'id': 'CORE_ZN ZN PSZ-AC-1 FAN-fansystem',
                                        'minimum_airflow': 370.90000000000003,
                                        'minimum_outdoor_airflow': 64.60000000000001, 'fan_control': 'CONSTANT',
                                        'supply_fans': [{'id': 'CORE_ZN ZN PSZ-AC-1 FAN', 'design_airflow': 0.37,
                                                         'is_airflow_sized_based_on_design_day': True,
                                                         'design_electric_power': 415.54,
                                                         'design_pressure_rise': 622.72, 'total_efficiency': 0.56,
                                                         'motor_efficiency': 0.85,
                                                         'motor_heat_to_airflow_fraction': 1.0,
                                                         'motor_heat_to_zone_fraction': 0.0,
                                                         'motor_location_zone': 'N/A',
                                                         'specification_method': 'SIMPLE'}]}}
        result_dict = {}
        self.cph.mirror_nested(original_dict, result_dict)

        expected = {'fan_system': {'id': 'CORE_ZN ZN PSZ-AC-1 FAN-fansystem',
                                   'supply_fans': [{'id': 'CORE_ZN ZN PSZ-AC-1 FAN'}]},
                    'heating_system': {'id': 'CORE_ZN ZN PSZ-AC-1-heating'}, 'id': 'CORE_ZN ZN PSZ-AC-1'}

        self.assertEqual(result_dict, expected)

    def test_merge_in_compliance_parameters(self):
        pass
