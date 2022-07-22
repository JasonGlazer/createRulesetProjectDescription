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

    def test_add_schedules_5(self):
        t = self.set_minimal_files()
        t.schedules_used_names = ['ONLY-SCHEDULE', ]
        t.json_hourly_results_object = (
            {
                'Cols': [
                    {"Variable": "ONLY-SCHEDULE:Schedule Value"},
                ],
                'Rows': [
                    {"01/01 01:00:00": [1, ]},
                    {"01/01 02:00:00": [2, ]},
                    {"01/01 03:00:00": [3, ]},
                    {"01/01 04:00:00": [4, ]},
                    {"01/01 05:00:00": [5, ]}
                ]
            }
        )
        instance = [
            {
                'id': 'ONLY-SCHEDULE',
                'schedule_sequence_type': 'HOURLY',
                'hourly_values': [1, 2, 3, 4, 5]
            }
        ]
        t.add_schedules()
        self.assertEqual(t.instance['schedules'], instance)

    def test_add_schedules_3_5(self):
        t = self.set_minimal_files()
        t.schedules_used_names = ['ONE-SCHEDULE', 'TWO-SCHEDULE', 'THREE-SCHEDULE']
        t.json_hourly_results_object = (
            {
                'Cols': [
                    {"Variable": "ONE-SCHEDULE:Schedule Value"},
                    {"Variable": "TWO-SCHEDULE:Schedule Value"},
                    {"Variable": "THREE-SCHEDULE:Schedule Value"},
                ],
                'Rows': [
                    {"01/01 01:00:00": [1, 11, 21 ]},
                    {"01/01 02:00:00": [2, 12, 22]},
                    {"01/01 03:00:00": [3, 13, 23]},
                    {"01/01 04:00:00": [4, 14, 24]},
                    {"01/01 05:00:00": [5, 15, 25]}
                ]
            }
        )
        instance = [
            {
                'id': 'ONE-SCHEDULE',
                'schedule_sequence_type': 'HOURLY',
                'hourly_values': [1, 2, 3, 4, 5]
            },
            {
                'id': 'TWO-SCHEDULE',
                'schedule_sequence_type': 'HOURLY',
                'hourly_values': [11, 12, 13, 14, 15]
            },
            {
                'id': 'THREE-SCHEDULE',
                'schedule_sequence_type': 'HOURLY',
                'hourly_values': [21, 22, 23, 24, 25]
            }
        ]
        t.add_schedules()
        self.assertEqual(t.instance['schedules'], instance)

    def test_gather_infiltration(self):
        t = self.set_minimal_files()
        t.json_results_object['TabularReports'] = \
            [
                {'For': 'Entire Facility', 'ReportName': 'InitializationSummary',
                 'Tables': [
                     {'Cols':
                          ['Name',
                           'Schedule Name',
                           'Zone Name',
                           'Zone Floor Area {m2}',
                           '# Zone Occupants',
                           'Design Volume Flow Rate {m3/s}'],
                      'Rows':
                          {'1':
                               ['ATTIC_INFILTRATION',
                                'ALWAYS_ON',
                                'ATTIC',
                                '567.98',
                                '0.0',
                                '0.200'
                                ],
                           '3':
                               ['PERIMETER_ZN_1_INFILTRATION',
                                'INFIL_QUARTER_ON_SCH',
                                'PERIMETER_ZN_1',
                                '113.45',
                                '6.8',
                                '4.805E-002'
                                ],
                           '4':
                               ['PERIMETER_ZN_2_INFILTRATION',
                                'INFIL_QUARTER_ON_SCH',
                                'PERIMETER_ZN_2',
                                '67.30',
                                '4.1',
                                '3.203E-002'
                                ],
                           '5':
                               ['PERIMETER_ZN_3_INFILTRATION',
                                'INFIL_QUARTER_ON_SCH',
                                'PERIMETER_ZN_3',
                                '113.45',
                                '6.8',
                                '4.805E-002'
                                ],
                           '6':
                               ['PERIMETER_ZN_4_INFILTRATION',
                                'INFIL_QUARTER_ON_SCH',
                                'PERIMETER_ZN_4',
                                '67.30',
                                '4.1',
                                '3.203E-002'
                                ]
                           },
                      'TableName': 'ZoneInfiltration Airflow Stats Nominal'},
                 ],
                 }
            ]
        gathered_infiltration = t.gather_infiltration()
        expected = {'ATTIC':
                        {'id': 'ATTIC_INFILTRATION',
                         'modeling_method': 'WEATHER_DRIVEN',
                         'algorithm_name': 'ZoneInfiltration',
                         'infiltration_flow_rate': 0.2,
                         'multiplier_schedule': 'ALWAYS_ON'},
                    'PERIMETER_ZN_1':
                        {'id': 'PERIMETER_ZN_1_INFILTRATION',
                         'modeling_method': 'WEATHER_DRIVEN',
                         'algorithm_name': 'ZoneInfiltration',
                         'infiltration_flow_rate': 0.04805,
                         'multiplier_schedule': 'INFIL_QUARTER_ON_SCH'},
                    'PERIMETER_ZN_2':
                        {'id': 'PERIMETER_ZN_2_INFILTRATION',
                         'modeling_method': 'WEATHER_DRIVEN',
                         'algorithm_name': 'ZoneInfiltration',
                         'infiltration_flow_rate': 0.03203,
                         'multiplier_schedule': 'INFIL_QUARTER_ON_SCH'},
                    'PERIMETER_ZN_3':
                        {'id': 'PERIMETER_ZN_3_INFILTRATION',
                         'modeling_method': 'WEATHER_DRIVEN',
                         'algorithm_name': 'ZoneInfiltration',
                         'infiltration_flow_rate': 0.04805,
                         'multiplier_schedule': 'INFIL_QUARTER_ON_SCH'},
                    'PERIMETER_ZN_4':
                        {'id': 'PERIMETER_ZN_4_INFILTRATION',
                         'modeling_method': 'WEATHER_DRIVEN',
                         'algorithm_name': 'ZoneInfiltration',
                         'infiltration_flow_rate': 0.03203,
                         'multiplier_schedule': 'INFIL_QUARTER_ON_SCH'}
                    }

        self.assertEqual(gathered_infiltration, expected)

    def test_get_construction_and_materials(self):
        t = self.set_minimal_files()
        t.epjson_object['Construction'] = {
            'nonres_ext_wall':
                {'layer_2': 'G01 16mm gypsum board',
                 'layer_3': 'Nonres_Exterior_Wall_Insulation',
                 'layer_4': 'G01 16mm gypsum board',
                 'outside_layer': 'F07 25mm stucco'},
        }
        t.epjson_object['Material'] = {
            'F07 25mm stucco': {'conductivity': 0.72,
                                'density': 1856,
                                'roughness': 'Smooth',
                                'solar_absorptance': 0.7,
                                'specific_heat': 840,
                                'thermal_absorptance': 0.9,
                                'thickness': 0.0254,
                                'visible_absorptance': 0.7
                                },
            'G01 16mm gypsum board': {'conductivity': 0.16,
                                      'density': 800,
                                      'roughness': 'MediumSmooth',
                                      'specific_heat': 1090,
                                      'thickness': 0.0159
                                      }
        }
        t.epjson_object['Material:NoMass'] = {
            'Nonres_Exterior_Wall_Insulation': {'roughness': 'MediumSmooth',
                                                'solar_absorptance': 0.7,
                                                'thermal_absorptance': 0.9,
                                                'thermal_resistance': 3.06941962105791,
                                                'visible_absorptance': 0.7
                                                }

        }
        expected = {
            'NONRES_EXT_WALL':
                {'id': 'nonres_ext_wall',
                 'surface_construction_input_option':
                     'LAYERS', 'primary_layers':
                     [
                         {'id': 'G01 16mm gypsum board',
                          'thickness': 0.0159,
                          'thermal_conductivity': 0.16,
                          'density': 800,
                          'specific_heat': 1090},
                         {'id': 'Nonres_Exterior_Wall_Insulation',
                          'r_value': 3.06941962105791},
                         {'id': 'G01 16mm gypsum board',
                          'thickness': 0.0159,
                          'thermal_conductivity': 0.16,
                          'density': 800,
                          'specific_heat': 1090},
                         {'id': 'F07 25mm stucco',
                          'thickness': 0.0254,
                          'thermal_conductivity': 0.72,
                          'density': 1856,
                          'specific_heat': 840}
                     ]
                 }
        }
        gotten_construction = t.get_constructions_and_materials()
        self.assertEqual(gotten_construction, expected)

    def test_gather_subsurface(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {'For': 'Entire Facility',
             'ReportName': 'EnvelopeSummary',
             'Tables':
                 [
                     {'Cols': ['Construction',
                               'Frame and Divider',
                               'Glass Area [m2]',
                               'Frame Area [m2]',
                               'Divider Area [m2]',
                               'Area of One Opening [m2]',
                               'Area of Multiplied Openings [m2]',
                               'Glass U-Factor [W/m2-K]',
                               'Glass SHGC',
                               'Glass Visible Transmittance',
                               'Frame Conductance [W/m2-K]',
                               'Divider Conductance [W/m2-K]',
                               'NFRC Product Type',
                               'Assembly U-Factor [W/m2-K]',
                               'Assembly SHGC',
                               'Assembly Visible Transmittance',
                               'Shade Control',
                               'Parent Surface',
                               'Azimuth [deg]',
                               'Tilt [deg]',
                               'Cardinal Direction'],
                      'Rows': {
                          'PERIMETER_ZN_2_WALL_EAST_WINDOW_1': [
                              'WINDOW_U_0.36_SHGC_0.38',
                              '',
                              '2.79',
                              '0.00',
                              '0.00',
                              '2.79',
                              '2.79',
                              '2.045',
                              '0.381',
                              '0.420',
                              '',
                              '',
                              '',
                              '',
                              '',
                              '',
                              'No',
                              'PERIMETER_ZN_2_WALL_EAST',
                              '90.00',
                              '90.00',
                              'E'],
                          'PERIMETER_ZN_2_WALL_EAST_WINDOW_2': [
                              'WINDOW_U_0.36_SHGC_0.38',
                              '',
                              '2.79',
                              '0.00',
                              '0.00',
                              '2.79',
                              '2.79',
                              '2.045',
                              '0.381',
                              '0.420',
                              '',
                              '',
                              '',
                              '',
                              '',
                              '',
                              'No',
                              'PERIMETER_ZN_2_WALL_EAST',
                              '90.00',
                              '90.00',
                              'E'],
                          'PERIMETER_ZN_2_WALL_EAST_WINDOW_3': [
                              'WINDOW_U_0.36_SHGC_0.38',
                              '',
                              '2.79',
                              '0.00',
                              '0.00',
                              '2.79',
                              '2.79',
                              '2.045',
                              '0.381',
                              '0.420',
                              '',
                              '',
                              '',
                              '',
                              '',
                              '',
                              'No',
                              'PERIMETER_ZN_2_WALL_EAST',
                              '90.00',
                              '90.00',
                              'E'],
                          'PERIMETER_ZN_2_WALL_EAST_WINDOW_4': [
                              'WINDOW_U_0.36_SHGC_0.38',
                              '',
                              '2.79',
                              '0.00',
                              '0.00',
                              '2.79',
                              '2.79',
                              '2.045',
                              '0.381',
                              '0.420',
                              '',
                              '',
                              '',
                              '',
                              '',
                              '',
                              'No',
                              'PERIMETER_ZN_2_WALL_EAST',
                              '90.00',
                              '90.00',
                              'E']},
                      'TableName': 'Exterior Fenestration'},
                     ]}
        ]


        gathered_subsurface_by_surface = t.gather_subsurface()

        expected = \
            {'PERIMETER_ZN_2_WALL_EAST':
                [
                    {'id': 'PERIMETER_ZN_2_WALL_EAST_WINDOW_1',
                     'classification': 'WINDOW',
                     'glazed_area': 2.79,
                     'opaque_area': 0.0,
                     'u_factor': 2.045,
                     'solar_heat_gain_coefficient': 0.381,
                     'visible_transmittance': 0.42,
                     'has_automatic_shades': False},
                    {'id': 'PERIMETER_ZN_2_WALL_EAST_WINDOW_2',
                     'classification': 'WINDOW',
                     'glazed_area': 2.79,
                     'opaque_area': 0.0,
                     'u_factor': 2.045,
                     'solar_heat_gain_coefficient': 0.381,
                     'visible_transmittance': 0.42,
                     'has_automatic_shades': False},
                    {'id': 'PERIMETER_ZN_2_WALL_EAST_WINDOW_3',
                     'classification': 'WINDOW',
                     'glazed_area': 2.79,
                     'opaque_area': 0.0,
                     'u_factor': 2.045,
                     'solar_heat_gain_coefficient': 0.381,
                     'visible_transmittance': 0.42,
                     'has_automatic_shades': False},
                    {'id': 'PERIMETER_ZN_2_WALL_EAST_WINDOW_4',
                     'classification': 'WINDOW',
                     'glazed_area': 2.79,
                     'opaque_area': 0.0,
                     'u_factor': 2.045,
                     'solar_heat_gain_coefficient': 0.381,
                     'visible_transmittance': 0.42,
                     'has_automatic_shades': False}
                ]
            }

        self.assertEqual(gathered_subsurface_by_surface, expected)

        print('gathered_subsurface_by_surface', gathered_subsurface_by_surface)
