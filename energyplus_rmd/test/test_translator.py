from json import dumps, loads
from pathlib import Path
from tempfile import mkdtemp
from unittest import TestCase

from energyplus_rmd.translator import Translator


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
        t.schedules_used_names = ['ONLY-SCHEDULE', ]
        t.json_hourly_results_object = (
            {
                'Cols': [
                    {"Variable": "ONLY-SCHEDULE:Schedule Value"},
                ],
                'Rows': [
                    {
                        "01/01 01:00:00": [1, ]
                    }
                ]
            }
        )
        model_description = [
            {
                'id': 'ONLY-SCHEDULE',
                'sequence_type': 'HOURLY',
                'hourly_values': [1]
            }
        ]
        t.add_schedules()
        self.assertEqual(t.model_description['schedules'], model_description)

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
        model_description = [
            {
                'id': 'ONLY-SCHEDULE',
                'sequence_type': 'HOURLY',
                'hourly_values': [1, 2, 3, 4, 5]
            }
        ]
        t.add_schedules()
        self.assertEqual(t.model_description['schedules'], model_description)

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
                    {"01/01 01:00:00": [1, 11, 21]},
                    {"01/01 02:00:00": [2, 12, 22]},
                    {"01/01 03:00:00": [3, 13, 23]},
                    {"01/01 04:00:00": [4, 14, 24]},
                    {"01/01 05:00:00": [5, 15, 25]}
                ]
            }
        )
        model_description = [
            {
                'id': 'ONE-SCHEDULE',
                'sequence_type': 'HOURLY',
                'hourly_values': [1, 2, 3, 4, 5]
            },
            {
                'id': 'TWO-SCHEDULE',
                'sequence_type': 'HOURLY',
                'hourly_values': [11, 12, 13, 14, 15]
            },
            {
                'id': 'THREE-SCHEDULE',
                'sequence_type': 'HOURLY',
                'hourly_values': [21, 22, 23, 24, 25]
            }
        ]
        t.add_schedules()
        self.assertEqual(t.model_description['schedules'], model_description)

    def test_gather_infiltration(self):
        t = self.set_minimal_files()
        t.json_results_object['TabularReports'] = [
            {
                'For': 'Entire Facility', 'ReportName': 'InitializationSummary',
                'Tables': [
                    {
                        'Cols':
                            [
                                'Name',
                                'Schedule Name',
                                'Zone Name',
                                'Zone Floor Area {m2}',
                                '# Zone Occupants',
                                'Design Volume Flow Rate {m3/s}'
                            ],
                        'Rows':
                            {
                                '1':
                                    [
                                        'ATTIC_INFILTRATION',
                                        'ALWAYS_ON',
                                        'ATTIC',
                                        '567.98',
                                        '0.0',
                                        '0.200'
                                    ],
                                '3':
                                    [
                                        'PERIMETER_ZN_1_INFILTRATION',
                                        'INFIL_QUARTER_ON_SCH',
                                        'PERIMETER_ZN_1',
                                        '113.45',
                                        '6.8',
                                        '4.805E-002'
                                    ],
                                '4':
                                    [
                                        'PERIMETER_ZN_2_INFILTRATION',
                                        'INFIL_QUARTER_ON_SCH',
                                        'PERIMETER_ZN_2',
                                        '67.30',
                                        '4.1',
                                        '3.203E-002'
                                    ],
                                '5':
                                    [
                                        'PERIMETER_ZN_3_INFILTRATION',
                                        'INFIL_QUARTER_ON_SCH',
                                        'PERIMETER_ZN_3',
                                        '113.45',
                                        '6.8',
                                        '4.805E-002'
                                    ],
                                '6':
                                    [
                                        'PERIMETER_ZN_4_INFILTRATION',
                                        'INFIL_QUARTER_ON_SCH',
                                        'PERIMETER_ZN_4',
                                        '67.30',
                                        '4.1',
                                        '3.203E-002'
                                    ]
                            },
                        'TableName': 'ZoneInfiltration Airflow Stats Nominal'
                    },
                ],
            }
        ]
        gathered_infiltration = t.gather_infiltration()
        expected = {
            'ATTIC': {
                'id': 'ATTIC_INFILTRATION',
                'modeling_method': 'WEATHER_DRIVEN',
                'algorithm_name': 'ZoneInfiltration',
                'flow_rate': 0.2,
                'multiplier_schedule': 'ALWAYS_ON'
            },
            'PERIMETER_ZN_1':
                {
                    'id': 'PERIMETER_ZN_1_INFILTRATION',
                    'modeling_method': 'WEATHER_DRIVEN',
                    'algorithm_name': 'ZoneInfiltration',
                    'flow_rate': 0.04805,
                    'multiplier_schedule': 'INFIL_QUARTER_ON_SCH'
                },
            'PERIMETER_ZN_2':
                {
                    'id': 'PERIMETER_ZN_2_INFILTRATION',
                    'modeling_method': 'WEATHER_DRIVEN',
                    'algorithm_name': 'ZoneInfiltration',
                    'flow_rate': 0.03203,
                    'multiplier_schedule': 'INFIL_QUARTER_ON_SCH'
                },
            'PERIMETER_ZN_3':
                {
                    'id': 'PERIMETER_ZN_3_INFILTRATION',
                    'modeling_method': 'WEATHER_DRIVEN',
                    'algorithm_name': 'ZoneInfiltration',
                    'flow_rate': 0.04805,
                    'multiplier_schedule': 'INFIL_QUARTER_ON_SCH'
                },
            'PERIMETER_ZN_4':
                {
                    'id': 'PERIMETER_ZN_4_INFILTRATION',
                    'modeling_method': 'WEATHER_DRIVEN',
                    'algorithm_name': 'ZoneInfiltration',
                    'flow_rate': 0.03203,
                    'multiplier_schedule': 'INFIL_QUARTER_ON_SCH'
                }
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

        expected = {
            'PERIMETER_ZN_2_WALL_EAST':
                [
                    {
                        'id': 'PERIMETER_ZN_2_WALL_EAST_WINDOW_1',
                        'classification': 'WINDOW',
                        'glazed_area': 2.79,
                        'opaque_area': 0.0,
                        'u_factor': 2.045,
                        'solar_heat_gain_coefficient': 0.381,
                        'visible_transmittance': 0.42,
                        'has_automatic_shades': False
                    },
                    {
                        'id': 'PERIMETER_ZN_2_WALL_EAST_WINDOW_2',
                        'classification': 'WINDOW',
                        'glazed_area': 2.79,
                        'opaque_area': 0.0,
                        'u_factor': 2.045,
                        'solar_heat_gain_coefficient': 0.381,
                        'visible_transmittance': 0.42,
                        'has_automatic_shades': False
                    },
                    {
                        'id': 'PERIMETER_ZN_2_WALL_EAST_WINDOW_3',
                        'classification': 'WINDOW',
                        'glazed_area': 2.79,
                        'opaque_area': 0.0,
                        'u_factor': 2.045,
                        'solar_heat_gain_coefficient': 0.381,
                        'visible_transmittance': 0.42,
                        'has_automatic_shades': False
                    },
                    {
                        'id': 'PERIMETER_ZN_2_WALL_EAST_WINDOW_4',
                        'classification': 'WINDOW',
                        'glazed_area': 2.79,
                        'opaque_area': 0.0,
                        'u_factor': 2.045,
                        'solar_heat_gain_coefficient': 0.381,
                        'visible_transmittance': 0.42,
                        'has_automatic_shades': False
                    }
                ]
        }

        self.assertEqual(gathered_subsurface_by_surface, expected)

    def test_gather_surfaces(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [{
            'For': 'Entire Facility',
            'ReportName': 'EnvelopeSummary',
            'Tables': [{
                'Cols': [
                    'Construction',
                    'Reflectance',
                    'U-Factor with Film [W/m2-K]',
                    'U-Factor no Film [W/m2-K]',
                    'Gross Area [m2]',
                    'Net Area [m2]',
                    'Azimuth [deg]',
                    'Tilt [deg]',
                    'Cardinal Direction'
                ],
                'Rows': {
                    'PERIMETER_ZN_4_WALL_WEST': [
                        'NONRES_EXT_WALL',
                        '0.30',
                        '0.290',
                        '0.303',
                        '56.30',
                        '45.15',
                        '270.00',
                        '90.00',
                        'W'
                    ]
                },
                'TableName': 'Opaque Exterior'
            }]
        }]

        gathered_surfaces = t.gather_surfaces()

        expected = {
            'PERIMETER_ZN_4_WALL_WEST': {
                'id': 'PERIMETER_ZN_4_WALL_WEST',
                'classification': 'WALL',
                'area': 56.3,
                'tilt': 90.0,
                'azimuth': 270.0,
                'adjacent_to': 'EXTERIOR',
                'does_cast_shade': True,
            }
        }

        self.assertEqual(gathered_surfaces, expected)

    def test_gather_interior_lighting(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {
                'For': 'Entire Facility',
                'ReportName': 'LightingSummary',
                'Tables': [
                    {
                        'Cols': [
                            'Zone Name',
                            'Space Name',
                            'Space Type',
                            'Lighting Power Density [W/m2]',
                            'Space Area [m2]',
                            'Total Power [W]',
                            'End Use Subcategory',
                            'Schedule Name',
                            'Scheduled Hours/Week [hr]',
                            'Hours/Week > 1% [hr]',
                            'Full Load Hours/Week [hr]',
                            'Return Air Fraction',
                            'Conditioned (Y/N)',
                            'Consumption [GJ]'
                        ],
                        'Rows': {
                            'PERIMETER_ZN_1_LIGHTS': [
                                'PERIMETER_ZN_1',
                                'PERIMETER_ZN_1',
                                'GENERAL',
                                '6.8889',
                                '113.45',
                                '781.55',
                                'LightsWired',
                                'BLDG_LIGHT_SCH',
                                '57.72',
                                '168.00',
                                '35.49',
                                '0.0000',
                                'Y',
                                '5.21'
                            ]
                        },
                        'TableName': 'Interior Lighting'
                    },
                    {
                        'Cols': [
                            'Zone',
                            'Control Name',
                            'Daylighting Method',
                            'Control Type',
                            'Fraction Controlled',
                            'Lighting Installed in Zone [W]',
                            'Lighting Controlled [W]'
                        ],
                        'Rows': {
                            'PERIMETER_ZN_1_DAYLREFPT1': [
                                'PERIMETER_ZN_1',
                                'PERIMETER_ZN_1_DAYLCTRL',
                                'SplitFlux',
                                'Continuous/Off',
                                '0.24',
                                '781.55',
                                '187.49'
                            ],
                            'PERIMETER_ZN_1_DAYLREFPT2': [
                                'PERIMETER_ZN_1',
                                'PERIMETER_ZN_1_DAYLCTRL',
                                'SplitFlux',
                                'Continuous/Off',
                                '0.03',
                                '781.55',
                                '23.60'
                            ]
                        },
                        'TableName': 'Daylighting'
                    }
                ]
            }
        ]

        gathered_lights = t.gather_interior_lighting()

        expected = {
            'PERIMETER_ZN_1': [{
                'id': 'PERIMETER_ZN_1_LIGHTS',
                'power_per_area': 6.8889,
                'lighting_multiplier_schedule': 'BLDG_LIGHT_SCH',
                'daylighting_control_type': 'CONTINUOUS_DIMMING',
                'are_schedules_used_for_modeling_occupancy_control': True,
                'are_schedules_used_for_modeling_daylighting_control': False
            }]
        }

        self.assertEqual(gathered_lights, expected)

    def test_add_spaces(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [{
            'For': 'Entire Facility',
            'ReportName': 'InputVerificationandResultsSummary',
            'Tables': [{
                'Cols': [
                    'Area [m2]',
                    'Conditioned (Y/N)',
                    'Part of Total Floor Area (Y/N)',
                    'Multipliers',
                    'Zone Name',
                    'Space Type',
                    'Radiant/Solar Enclosure Name',
                    'Lighting [W/m2]',
                    'People [m2 per person]',
                    'Plug and Process [W/m2]',
                    'Tags'
                ],
                'Rows': {
                    'PERIMETER_ZN_1': [
                        '113.45',
                        'Yes',
                        'Yes',
                        '1.00',
                        'PERIMETER_ZN_1',
                        'COPY_PRINT_ROOM',
                        'PERIMETER_ZN_1',
                        '6.8889',
                        '16.59',
                        '6.7800',
                        ''
                    ]
                },
                'TableName': 'Space Summary'
            }]
        }]

        t.building_segment['zones'] = [{'id': 'PERIMETER_ZN_1'}]

        added_spaces = t.add_spaces()

        expected = {
            'PERIMETER_ZN_1': {
                'id': 'PERIMETER_ZN_1',
                'floor_area': 113.45,
                'number_of_occupants': 6.84,
                'lighting_space_type': 'COPY_PRINT_ROOM'
            }
        }

        self.assertEqual(added_spaces, expected)

    def test_get_zone_for_each_surface(self):
        t = self.set_minimal_files()

        t.epjson_object['BuildingSurface:Detailed'] = {
            'Core_ZN_wall_east': {'zone_name': 'Core_ZN'},
            'Core_ZN_wall_north': {'zone_name': 'Core_ZN'},
            'Perimeter_ZN_1_floor': {'zone_name': 'Perimeter_ZN_1'},
            'Perimeter_ZN_1_wall_east': {'zone_name': 'Perimeter_ZN_1'}
        }

        gotten_surfaces_to_zone = t.get_zone_for_each_surface()

        expected = \
            {
                'CORE_ZN_WALL_EAST': 'CORE_ZN',
                'CORE_ZN_WALL_NORTH': 'CORE_ZN',
                'PERIMETER_ZN_1_FLOOR': 'PERIMETER_ZN_1',
                'PERIMETER_ZN_1_WALL_EAST': 'PERIMETER_ZN_1'
            }

        self.assertEqual(gotten_surfaces_to_zone, expected)

    def test_get_adjacent_surface_for_each_surface(self):
        t = self.set_minimal_files()

        t.epjson_object['BuildingSurface:Detailed'] = {
            'Core_ZN_wall_east': {'outside_boundary_condition_object': 'Perimeter_ZN_2_wall_west'},
            'Core_ZN_wall_north': {'outside_boundary_condition_object': 'Perimeter_ZN_3_wall_south'},
            'Perimeter_ZN_1_wall_east': {'outside_boundary_condition_object': 'Perimeter_ZN_2_wall_south'}
        }

        gotten_adjacent_by_surface = t.get_adjacent_surface_for_each_surface()

        expected = \
            {
                'CORE_ZN_WALL_EAST': 'PERIMETER_ZN_2_WALL_WEST',
                'CORE_ZN_WALL_NORTH': 'PERIMETER_ZN_3_WALL_SOUTH',
                'PERIMETER_ZN_1_WALL_EAST': 'PERIMETER_ZN_2_WALL_SOUTH'
            }

        self.assertEqual(gotten_adjacent_by_surface, expected)

    def test_gather_thermostat_setpoint_schedules(self):
        t = self.set_minimal_files()

        t.epjson_object['ZoneControl:Thermostat'] = \
            {
                'Core_ZN Thermostat': {'control_1_name': 'Core_ZN DualSPSched',
                                       'control_1_object_type': 'ThermostatSetpoint:DualSetpoint',
                                       'control_type_schedule_name': 'Dual Zone Control Type Sched',
                                       'zone_or_zonelist_name': 'Core_ZN'},
                'Perimeter_ZN_1 Thermostat': {'control_1_name': 'Perimeter_ZN_1 DualSPSched',
                                              'control_1_object_type': 'ThermostatSetpoint:DualSetpoint',
                                              'control_type_schedule_name': 'Dual Zone Control Type Sched',
                                              'zone_or_zonelist_name': 'Perimeter_ZN_1'},
                'Perimeter_ZN_2 Thermostat': {'control_1_name': 'Perimeter_ZN_2 DualSPSched',
                                              'control_1_object_type': 'ThermostatSetpoint:DualSetpoint',
                                              'control_type_schedule_name': 'Dual Zone Control Type Sched',
                                              'zone_or_zonelist_name': 'Perimeter_ZN_2'},
                'Perimeter_ZN_3 Thermostat': {'control_1_name': 'Perimeter_ZN_3 DualSPSched',
                                              'control_1_object_type': 'ThermostatSetpoint:DualSetpoint',
                                              'control_type_schedule_name': 'Dual Zone Control Type Sched',
                                              'zone_or_zonelist_name': 'Perimeter_ZN_3'},
                'Perimeter_ZN_4 Thermostat': {'control_1_name': 'Perimeter_ZN_4 DualSPSched',
                                              'control_1_object_type': 'ThermostatSetpoint:DualSetpoint',
                                              'control_type_schedule_name': 'Dual Zone Control Type Sched',
                                              'zone_or_zonelist_name': 'Perimeter_ZN_4'}
            }

        t.epjson_object['ThermostatSetpoint:DualSetpoint'] = \
            {
                'Core_ZN DualSPSched': {'cooling_setpoint_temperature_schedule_name': 'CLGSETP_SCH_NO_OPTIMUM',
                                        'heating_setpoint_temperature_schedule_name': 'HTGSETP_SCH_NO_OPTIMUM'},
                'Perimeter_ZN_1 DualSPSched': {'cooling_setpoint_temperature_schedule_name': 'CLGSETP_SCH_NO_OPTIMUM',
                                               'heating_setpoint_temperature_schedule_name': 'HTGSETP_SCH_NO_OPTIMUM'},
                'Perimeter_ZN_2 DualSPSched': {
                    'cooling_setpoint_temperature_schedule_name': 'CLGSETP_SCH_NO_OPTIMUM_w_SB',
                    'heating_setpoint_temperature_schedule_name': 'HTGSETP_SCH_NO_OPTIMUM_w_SB'},
                'Perimeter_ZN_3 DualSPSched': {'cooling_setpoint_temperature_schedule_name': 'CLGSETP_SCH_NO_OPTIMUM',
                                               'heating_setpoint_temperature_schedule_name': 'HTGSETP_SCH_NO_OPTIMUM'},
                'Perimeter_ZN_4 DualSPSched': {'cooling_setpoint_temperature_schedule_name': 'CLGSETP_SCH_NO_OPTIMUM',
                                               'heating_setpoint_temperature_schedule_name': 'HTGSETP_SCH_NO_OPTIMUM'}
            }

        gathered_thermostat_setpoint_schedules = t.gather_thermostat_setpoint_schedules()

        expected = \
            {
                'CORE_ZN': {'cool': 'CLGSETP_SCH_NO_OPTIMUM', 'heat': 'HTGSETP_SCH_NO_OPTIMUM'},
                'PERIMETER_ZN_1': {'cool': 'CLGSETP_SCH_NO_OPTIMUM', 'heat': 'HTGSETP_SCH_NO_OPTIMUM'},
                'PERIMETER_ZN_2': {'cool': 'CLGSETP_SCH_NO_OPTIMUM_w_SB', 'heat': 'HTGSETP_SCH_NO_OPTIMUM_w_SB'},
                'PERIMETER_ZN_3': {'cool': 'CLGSETP_SCH_NO_OPTIMUM', 'heat': 'HTGSETP_SCH_NO_OPTIMUM'},
                'PERIMETER_ZN_4': {'cool': 'CLGSETP_SCH_NO_OPTIMUM', 'heat': 'HTGSETP_SCH_NO_OPTIMUM'}
            }

        self.assertEqual(gathered_thermostat_setpoint_schedules, expected)

    def test_gather_people_schedule_by_zone(self):
        t = self.set_minimal_files()
        t.json_results_object['TabularReports'] = [{
            'For': 'Entire Facility',
            'ReportName': 'InitializationSummary',
            'Tables': [{
                'Cols': [
                    'Name',
                    'Schedule Name',
                    'Zone Name',
                ],
                'Rows': {
                    '1': ['CORE_ZN', 'BLDG_OCC_SCH_WO_SB', 'CORE_ZN'],
                    '2': ['PERIMETER_ZN_1', 'BLDG_OCC_SCH_WO_SB', 'PERIMETER_ZN_1'],
                    '3': ['PERIMETER_ZN_2', 'BLDG_OCC_SCH_W_SB', 'PERIMETER_ZN_2'],
                    '4': ['PERIMETER_ZN_3', 'BLDG_OCC_SCH_WO_SB', 'PERIMETER_ZN_3'],
                    '5': ['PERIMETER_ZN_4', 'BLDG_OCC_SCH_WO_SB', 'PERIMETER_ZN_4']
                },
                'TableName': 'People Internal Gains Nominal'
            }]
        }]
        gathered_people_schedule_by_zone = t.gather_people_schedule_by_zone()
        expected = {
            'CORE_ZN': 'BLDG_OCC_SCH_WO_SB', 'PERIMETER_ZN_1': 'BLDG_OCC_SCH_WO_SB',
            'PERIMETER_ZN_2': 'BLDG_OCC_SCH_W_SB', 'PERIMETER_ZN_3': 'BLDG_OCC_SCH_WO_SB',
            'PERIMETER_ZN_4': 'BLDG_OCC_SCH_WO_SB'
        }

        self.assertEqual(gathered_people_schedule_by_zone, expected)

    def test_add_weather(self):
        t = self.set_minimal_files()
        t.json_results_object['TabularReports'] = \
            [
                {'For': 'Entire Facility', 'ReportName': 'InputVerificationandResultsSummary',
                 'Tables':
                     [
                         {'Cols': ['Value'],
                          'Rows': {
                              'Weather File': ['Denver-Aurora-Buckley AFB CO USA TMY3 WMO#=724695']
                          },
                          'TableName': 'General'},
                     ]
                 },
                {'For': 'Entire Facility', 'ReportName': 'ClimaticDataSummary',
                 'Tables': [
                     {'Cols': [
                         'Maximum Dry Bulb [C]',
                         'Daily Temperature Range [deltaC]',
                         'Humidity Value',
                         'Humidity Type',
                         'Wind Speed [m/s]',
                         'Wind Direction'],
                         'Rows': {
                             'DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB':
                                 [],
                             'DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB':
                                 []},
                         'TableName': 'SizingPeriod:DesignDay'},
                     {'Cols': ['Value'], 'Rows': {
                         'ASHRAE Climate Zone': ['5B'],
                     },
                      'TableName': 'Weather Statistics File'}]}
            ]
        added_weather = t.add_weather()
        expected = {
            'file_name': 'Denver-Aurora-Buckley AFB CO USA TMY3 WMO#=724695', 'data_source_type': 'OTHER',
            'climate_zone': 'CZ5B', 'cooling_design_day_type': 'COOLING_0_4',
            'heating_design_day_type': 'HEATING_99_6'}

        self.assertEqual(added_weather, expected)

    def test_add_exterior_lighting(self):
        t = self.set_minimal_files()
        t.json_results_object['TabularReports'] = [{
            'For': 'Entire Facility',
            'ReportName': 'LightingSummary',
            'Tables': [{
                'Cols':
                    [
                        'Total Watts',
                        'Astronomical Clock/Schedule',
                        'Schedule Name',
                        'Scheduled Hours/Week [hr]',
                        'Hours/Week > 1% [hr]',
                        'Full Load Hours/Week [hr]',
                        'Consumption [GJ]'
                    ],
                'Rows': {
                    'EXTERIOR_LIGHTS_A': ['50.70', 'AstronomicalClock', '-', '', '42.26', '42.26', '0.40'],
                    'EXTERIOR_LIGHTS_B': ['115.10', 'AstronomicalClock', '-', '', '83.67', '62.97', '1.36'],
                    'EXTERIOR_LIGHTS_C': ['445.50', 'AstronomicalClock', '-', '', '83.67', '46.88', '3.92'],
                    'Exterior Lighting Total': ['611.30', '', '', '', '', '', '5.68'
                                                ]},
                'TableName': 'Exterior Lighting'
            }]
        }]
        added_exterior_lighting = t.add_exterior_lighting()

        expected = [
            {'id': 'EXTERIOR_LIGHTS_A',
             'power': 50.7,
             'multiplier_schedule': 'uses_astronomical_clock_not_schedule'},
            {'id': 'EXTERIOR_LIGHTS_B',
             'power': 115.1,
             'multiplier_schedule': 'uses_astronomical_clock_not_schedule'},
            {'id': 'EXTERIOR_LIGHTS_C',
             'power': 445.5,
             'multiplier_schedule': 'uses_astronomical_clock_not_schedule'}]

        self.assertEqual(added_exterior_lighting, expected)

    def test_add_zones(self):
        t = self.set_minimal_files()
        t.json_results_object['TabularReports'] = \
            [
                {'For': 'Entire Facility', 'ReportName': 'InputVerificationandResultsSummary',
                 'Tables':
                     [
                         {'Cols': ['Area [m2]',
                                   'Conditioned (Y/N)',
                                   'Part of Total Floor Area (Y/N)',
                                   'Volume [m3]',
                                   'Multipliers',
                                   'Above Ground Gross Wall Area [m2]',
                                   'Underground Gross Wall Area [m2]',
                                   'Window Glass Area [m2]',
                                   'Opening Area [m2]',
                                   'Lighting [W/m2]',
                                   'People [m2 per person]',
                                   'Plug and Process [W/m2]'],
                          'Rows': {
                              'ATTIC': ['567.98', 'No', 'No', '720.19', '1.00', '0.00', '0.00', '0.00', '0.00',
                                        '0.0000',
                                        '', '0.0000'],
                              'CORE_ZN': ['149.66', 'Yes', 'Yes', '456.46', '1.00', '0.00', '0.00', '0.00', '0.00',
                                          '6.8889', '16.59', '6.7800'],
                              'Conditioned Total': ['511.16', '', '', '1559.03', '', '281.51', '0.00', '59.68', '59.68',
                                                    '6.8889', '16.59', '6.7800'],
                              'Not Part of Total': ['567.98', '', '', '720.19', '', '0.00', '0.00', '0.00', '0.00',
                                                    '0.0000', '', '0.0000'],
                              'PERIMETER_ZN_1': ['113.45', 'Yes', 'Yes', '346.02', '1.00', '84.45', '0.00', '20.64',
                                                 '20.64', '6.8889', '16.59', '6.7800'],
                              'PERIMETER_ZN_2': ['67.30', 'Yes', 'Yes', '205.26', '1.00', '56.30', '0.00', '11.16',
                                                 '11.16', '6.8889', '16.59', '6.7800'],
                              'PERIMETER_ZN_3': ['113.45', 'Yes', 'Yes', '346.02', '1.00', '84.45', '0.00', '16.73',
                                                 '16.73', '6.8889', '16.59', '6.7800'],
                              'PERIMETER_ZN_4': ['67.30', 'Yes', 'Yes', '205.26', '1.00', '56.30', '0.00', '11.16',
                                                 '11.16', '6.8889', '16.59', '6.7800'],
                              'Total': ['511.16', '', '', '1559.03', '', '281.51', '0.00', '59.68', '59.68', '6.8889',
                                        '16.59', '6.7800'],
                              'Unconditioned Total': ['0.00', '', '', '0.00', '', '0.00', '0.00', '0.00', '0.00', '',
                                                      '',
                                                      '']},
                          'TableName': 'Zone Summary'}

                     ]
                 }
            ]
        added_zones = t.add_zones()
        expected = [
            {'id': 'ATTIC', 'volume': 720.19, 'surfaces': []},
            {'id': 'CORE_ZN', 'volume': 456.46, 'surfaces': []},
            {'id': 'PERIMETER_ZN_1', 'volume': 346.02, 'surfaces': []},
            {'id': 'PERIMETER_ZN_2', 'volume': 205.26, 'surfaces': []},
            {'id': 'PERIMETER_ZN_3', 'volume': 346.02, 'surfaces': []},
            {'id': 'PERIMETER_ZN_4', 'volume': 205.26, 'surfaces': []}
        ]

        self.assertEqual(added_zones, expected)

    def test_add_calendar(self):
        t = self.set_minimal_files()
        t.json_results_object['TabularReports'] = \
            [
                {'For': 'Entire Facility', 'ReportName': 'InitializationSummary',
                 'Tables':
                     [
                         {
                             "Cols": [
                                 "Environment Name",
                                 "Environment Type",
                                 "Start Date",
                                 "End Date",
                                 "Start DayOfWeek",
                                 "Duration {#days}",
                                 "Source:Start DayOfWeek",
                                 "Use Daylight Saving",
                                 "Use Holidays",
                                 "Apply Weekend Holiday Rule",
                                 "Use Rain Values",
                                 "Use Snow Values",
                                 "Sky Temperature Model"
                             ],
                             "Rows": {
                                 "1": [
                                     "RUNPERIOD 1",
                                     "WeatherFileRunPeriod",
                                     "01/01/2017",
                                     "12/31/2017",
                                     "Sunday",
                                     "365",
                                     "Use RunPeriod Specified Day",
                                     "No",
                                     "No",
                                     "No",
                                     "Yes",
                                     "Yes",
                                     "Clark and Allen"
                                 ]
                             },
                             "TableName": "Environment"
                         },
                         {
                             "Cols": [
                                 "Daylight Saving Indicator",
                                 "Source",
                                 "Start Date",
                                 "End Date"
                             ],
                             "Rows": {
                                 "1": [
                                     "Yes",
                                     "InputFile",
                                     "03/12",
                                     "11/05"
                                 ]
                             },
                             "TableName": "Environment:Daylight Saving"
                         },
                     ]
                 }
            ]

        added_calendar = t.add_calendar()

        expected = {'notes': 'name environment: RUNPERIOD 1', 'day_of_week_for_january_1': 'SUNDAY',
                    'is_leap_year': False, 'has_daylight_saving_time': True}

        self.assertEqual(added_calendar, expected)

    def test_gather_miscellaneous_equipment(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {'For': 'Entire Facility', 'ReportName': 'InitializationSummary',
             'Tables':
                 [
                     {
                         "Cols": [
                             "Name",
                             "Schedule Name",
                             "Zone Name",
                             "Zone Floor Area {m2}",
                             "# Zone Occupants",
                             "Equipment Level {W}",
                             "Equipment/Floor Area {W/m2}",
                             "Equipment per person {W/person}",
                             "Fraction Latent",
                             "Fraction Radiant",
                             "Fraction Lost",
                             "Fraction Convected",
                             "End-Use SubCategory",
                             "Nominal Minimum Equipment Level {W}",
                             "Nominal Maximum Equipment Level {W}"
                         ],
                         "Rows": {
                             "1": [
                                 "PERIMETER_ZN_2_MISCPLUG_EQUIP",
                                 "BLDG_EQUIP_SCH",
                                 "PERIMETER_ZN_2",
                                 "67.30",
                                 "4.1",
                                 "456.294",
                                 "6.780",
                                 "112.467",
                                 "0.000",
                                 "0.000",
                                 "0.000",
                                 "1.000",
                                 "MiscPlug",
                                 "0.000",
                                 "456.294"
                             ],
                         },
                         "TableName": "ElectricEquipment Internal Gains Nominal"
                     },
                 ]
             }
        ]

        gathered_equipment = t.gather_miscellaneous_equipment()

        expected = {
            'PERIMETER_ZN_2': [
                {'id': 'PERIMETER_ZN_2_MISCPLUG_EQUIP',
                 'energy_type': 'ELECTRICITY',
                 'multiplier_schedule': 'BLDG_EQUIP_SCH',
                 'sensible_fraction': 1.0,
                 'latent_fraction': 0.0,
                 'POWER DENSITY': 6.78}
            ]
        }

        self.assertEqual(gathered_equipment, expected)

    def test_is_site_shaded(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {'For': 'Entire Facility', 'ReportName': 'ObjectCountSummary',
             'Tables':
                 [
                     {
                         "Cols": [
                             "Total",
                             "Outdoors"
                         ],
                         "Rows": {
                             "Building Detached Shading": [
                                 "0",
                                 "0"
                             ],
                             "Fixed Detached Shading": [
                                 "0",
                                 "0"
                             ],
                         },
                         "TableName": "Surfaces by Class"
                     },
                 ]
             }
        ]

        self.assertFalse(t.is_site_shaded())

        t.json_results_object['TabularReports'] = [
            {'For': 'Entire Facility', 'ReportName': 'ObjectCountSummary',
             'Tables':
                 [
                     {
                         "Cols": [
                             "Total",
                             "Outdoors"
                         ],
                         "Rows": {
                             "Building Detached Shading": [
                                 "1",
                                 "0"
                             ],
                             "Fixed Detached Shading": [
                                 "0",
                                 "0"
                             ],
                         },
                         "TableName": "Surfaces by Class"
                     },
                 ]
             }
        ]

        self.assertTrue(t.is_site_shaded())

        t.json_results_object['TabularReports'] = [
            {'For': 'Entire Facility', 'ReportName': 'ObjectCountSummary',
             'Tables':
                 [
                     {
                         "Cols": [
                             "Total",
                             "Outdoors"
                         ],
                         "Rows": {
                             "Building Detached Shading": [
                                 "0",
                                 "0"
                             ],
                             "Fixed Detached Shading": [
                                 "1",
                                 "0"
                             ],
                         },
                         "TableName": "Surfaces by Class"
                     },
                 ]
             }
        ]

        self.assertTrue(t.is_site_shaded())

    def test_are_shadows_cast_from_surfaces(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {'For': 'Entire Facility', 'ReportName': 'InitializationSummary',
             'Tables':
                 [
                     {
                         "Cols": [
                             "Solar Distribution"
                         ],
                         "Rows": {
                             "1": [
                                 "FullInteriorAndExterior"
                             ]
                         },
                         "TableName": "Building Information"
                     },
                 ]
             }
        ]

        self.assertTrue(t.are_shadows_cast_from_surfaces())

        t.json_results_object['TabularReports'] = [
            {'For': 'Entire Facility', 'ReportName': 'InitializationSummary',
             'Tables':
                 [
                     {
                         "Cols": [
                             "Solar Distribution"
                         ],
                         "Rows": {
                             "1": [
                                 "MinimalShadowing"
                             ]
                         },
                         "TableName": "Building Information"
                     },
                 ]
             }
        ]

        self.assertFalse(t.are_shadows_cast_from_surfaces())

    def test_add_heating_ventilation_system(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {'For': 'Entire Facility', 'ReportName': 'CoilSizingDetails',
             'Tables':
                 [
                     {
                         "Cols": [
                             "Coil Type",
                             "Coil Location",
                             "HVAC Type",
                             "HVAC Name",
                             "Zone Name(s)",
                             "System Sizing Method Concurrence",
                             "System Sizing Method Capacity",
                             "System Sizing Method Air Flow",
                             "Autosized Coil Capacity?",
                             "Autosized Coil Airflow?",
                             "Autosized Coil Water Flow?",
                             "OA Pretreated prior to coil inlet?",
                             "Coil Final Gross Total Capacity [W]",
                             "Coil Final Gross Sensible Capacity [W]",

                             "Coil Total Capacity at Rating Conditions [W]",
                             "Coil Sensible Capacity at Rating Conditions [W]",
                             "Coil Total Capacity at Ideal Loads Peak [W]",
                             "Autosized Coil Capacity?",
                             "Coil Leaving Air Drybulb at Rating Conditions [C]",
                             "Supply Fan Name for Coil",
                         ],
                         "Rows": {
                             "5 ZONE PVAV 1 2SPD DX CLG COIL 320KBTU/HR 9.8EER": [
                                 "Coil:Cooling:DX:TwoSpeed",
                                 "AirLoop",
                                 "AirLoopHVAC",
                                 "5 ZONE PVAV 1",
                                 "PERIMETER_MID_ZN_1 ZN; PERIMETER_MID_ZN_2 ZN;",
                                 "Coincident",
                                 "CoolingDesignCapacity",
                                 "N/A",
                                 "Yes",
                                 "Yes",
                                 "unknown",
                                 "No",
                                 "98149.824",
                                 "78534.220",
                                 "12345.67",
                                 "12345.67",
                                 "12345.67",
                                 "Yes",
                                 "25.0",
                                 "Fan1"
                             ],
                             "PERIMETER_MID_ZN_1 ZN ELECTRIC REHEAT COIL": [
                                 "Coil:Heating:Electric",
                                 "Zone Equipment",
                                 "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                 "ADU PERIMETER_MID_ZN_1 ZN VAV TERMINAL",
                                 "PERIMETER_MID_ZN_1 ZN",
                                 "N/A",
                                 "N/A",
                                 "N/A",
                                 "Yes",
                                 "No",
                                 "unknown",
                                 "No",
                                 "11828.176",
                                 "11828.176",
                                 "12345.67",
                                 "12345.67",
                                 "12345.67",
                                 "Yes",
                                 "25.0",
                                 "Fan1",
                             ]
                         },
                         "TableName": "Coils"
                     }
                 ]
             }
        ]

        added_hvac_systems, added_terminals_by_zone = t.add_heating_ventilation_system()

        expected_hvac = [{
            'id': '5 ZONE PVAV 1',
            'cooling_system': {
                'id': '5 ZONE PVAV 1-cooling',
                'is_autosized': True,
                'oversizing_factor': 7.950141547603329,
                'design_total_cool_capacity': 98149.824,
                'design_sensible_cool_capacity': 78534.22,
                'rated_sensible_cool_capacity': 12345.67,
                'rated_total_cool_capacity': 12345.67,
                'type': 'DIRECT_EXPANSION',
            }
        }]

        expected_terminals = {
            'PERIMETER_MID_ZN_1 ZN': [{
                'id': 'PERIMETER_MID_ZN_1 ZN-terminal',
                'served_by_heating_ventilating_air_conditioning_system': '5 ZONE PVAV 1',
                'heating_capacity': 11828.176
            }],
            'PERIMETER_MID_ZN_2 ZN': [{
                'id': 'PERIMETER_MID_ZN_2 ZN-terminal',
                'served_by_heating_ventilating_air_conditioning_system': '5 ZONE PVAV 1'
            }],
        }

        self.assertEqual(added_hvac_systems, expected_hvac)

        self.assertEqual(added_terminals_by_zone, expected_terminals)

    def test_replace_serial_number(self):
        t = self.set_minimal_files()

        # first time should cause no change
        _id = 'unique-id'
        self.assertEqual(_id, t.replace_serial_number(_id))

        # second time should add a serial number
        self.assertEqual(_id + '~~~00000001', t.replace_serial_number(_id))

        # third time should increment the serial number
        self.assertEqual(_id + '~~~00000002', t.replace_serial_number(_id))

        _id = 'another_id'
        self.assertEqual(_id, t.replace_serial_number(_id))
        self.assertEqual(_id + '~~~00000003', t.replace_serial_number(_id))
        self.assertEqual(_id + '~~~00000004', t.replace_serial_number(_id))

        self.assertEqual(_id + '~~~00000005', t.replace_serial_number(_id + '~~~00000004'))

    def test_add_serial_number_nested(self):
        t = self.set_minimal_files()

        in_dict = {0: {'id': 'a'},
                   1: {'id': 'a'}}

        out_dict = {0: {'id': 'a'},
                    1: {'id': 'a~~~00000001'}}

        t.add_serial_number_nested(in_dict, 'id')
        self.assertEqual(in_dict, out_dict)

        in_dict = {0: [{'id': 'b'},
                       {'id': 'b'}]}

        out_dict = {0: [{'id': 'b'},
                        {'id': 'b~~~00000002'}]}

        t.add_serial_number_nested(in_dict, 'id')
        self.assertEqual(in_dict, out_dict)

    def test_ensure_all_id_unique(self):
        t = self.set_minimal_files()

        t.model_description = {0: {'id': 'a'},
                               1: {'id': 'a'}}

        out_dict = {0: {'id': 'a'},
                    1: {'id': 'a~~~00000001'}}

        t.ensure_all_id_unique()
        self.assertEqual(t.model_description, out_dict)

    def test_add_pumps(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {
                "For": "Entire Facility",
                "ReportName": "EquipmentSummary",
                "Tables": [
                    {
                        "Cols": [
                            "Type",
                            "Control",
                            "Head [pa]",
                            "Water Flow [m3/s]",
                            "Electricity Rate [W]",
                            "Power Per Water Flow Rate [W-s/m3]",
                            "Motor Efficiency [W/W]",
                            "End Use Subcategory",
                            "Is Autosized",
                            "Plantloop Name",
                            "Plantloop Branch Name"
                        ],
                        "Rows": {
                            "90.1-PRM-2019 WATERCOOLED  ROTARY SCREW CHILLER 0 1 PRIMARY PUMP": [
                                "Pump:ConstantSpeed",
                                "Intermittent",
                                "21635.69",
                                "0.066094",
                                "2095.21",
                                "31700.65",
                                "0.88",
                                "General",
                                "Yes",
                                "CHILLED WATER LOOP_PRIMARY",
                                "CHILLED WATER LOOP_PRIMARY SUPPLY BRANCH 3"
                            ],
                            "90.1-PRM-2019 WATERCOOLED  ROTARY SCREW CHILLER 0 PRIMARY PUMP": [
                                "Pump:ConstantSpeed",
                                "Intermittent",
                                "44260.44",
                                "0.066094",
                                "4190.42",
                                "63401.29",
                                "0.90",
                                "General",
                                "Yes",
                                "CHILLED WATER LOOP_PRIMARY",
                                "CHILLED WATER LOOP_PRIMARY SUPPLY BRANCH 1"
                            ],
                            "CHILLED WATER LOOP PUMP": [
                                "Pump:VariableSpeed",
                                "Intermittent",
                                "134508.01",
                                "0.018160",
                                "3479.58",
                                "191606.85",
                                "0.90",
                                "General",
                                "Yes",
                                "CHILLED WATER LOOP",
                                "CHILLED WATER LOOP DEMAND INLET BRANCH"
                            ],
                            "CONDENSER WATER LOOP CONSTANT PUMP BANK OF 2": [
                                "HeaderedPumps:VariableSpeed",
                                "Intermittent",
                                "219868.07",
                                "0.210916",
                                "63518.60",
                                "301156.14",
                                "0.94",
                                "General",
                                "Yes",
                                "CONDENSER WATER LOOP",
                                "CONDENSER WATER LOOP SUPPLY INLET BRANCH"
                            ],
                            "MAIN SERVICE WATER LOOP CIRCULATOR PUMP": [
                                "Pump:ConstantSpeed",
                                "Intermittent",
                                "29891.00",
                                "0.000439",
                                "20.40",
                                "46450.66",
                                "0.82",
                                "General",
                                "Yes",
                                "SERVICE WATER HEATING LOOP",
                                "SERVICE WATER HEATING LOOP SUPPLY INLET BRANCH"
                            ]
                        },
                        "TableName": "Pumps"
                    },
                ]
            },
        ]

        added_pumps = t.add_pumps()

        expected = [{'id': '90.1-PRM-2019 WATERCOOLED  ROTARY SCREW CHILLER 0 1 PRIMARY PUMP',
                     'loop_or_piping': 'CHILLED WATER LOOP_PRIMARY', 'specification_method': 'SIMPLE',
                     'design_electric_power': 2095.21, 'design_head': 21635.69, 'motor_efficiency': 0.88,
                     'speed_control': 'FIXED_SPEED', 'design_flow': 66.094, 'is_flow_autosized': True},
                    {'id': '90.1-PRM-2019 WATERCOOLED  ROTARY SCREW CHILLER 0 PRIMARY PUMP',
                     'loop_or_piping': 'CHILLED WATER LOOP_PRIMARY', 'specification_method': 'SIMPLE',
                     'design_electric_power': 4190.42, 'design_head': 44260.44, 'motor_efficiency': 0.9,
                     'speed_control': 'FIXED_SPEED', 'design_flow': 66.094, 'is_flow_autosized': True},
                    {'id': 'CHILLED WATER LOOP PUMP', 'loop_or_piping': 'CHILLED WATER LOOP',
                     'specification_method': 'SIMPLE', 'design_electric_power': 3479.58, 'design_head': 134508.01,
                     'motor_efficiency': 0.9, 'speed_control': 'VARIABLE_SPEED', 'design_flow': 18.16,
                     'is_flow_autosized': True},
                    {'id': 'CONDENSER WATER LOOP CONSTANT PUMP BANK OF 2', 'loop_or_piping': 'CONDENSER WATER LOOP',
                     'specification_method': 'SIMPLE', 'design_electric_power': 63518.6, 'design_head': 219868.07,
                     'motor_efficiency': 0.94, 'speed_control': 'VARIABLE_SPEED', 'design_flow': 210.916,
                     'is_flow_autosized': True},
                    {'id': 'MAIN SERVICE WATER LOOP CIRCULATOR PUMP', 'loop_or_piping': 'SERVICE WATER HEATING LOOP',
                     'specification_method': 'SIMPLE', 'design_electric_power': 20.4, 'design_head': 29891.0,
                     'motor_efficiency': 0.82, 'speed_control': 'FIXED_SPEED', 'design_flow': 0.439,
                     'is_flow_autosized': True}]

        self.assertEqual(added_pumps, expected)

    def test_add_heat_rejection(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {
                "For": "Entire Facility",
                "ReportName": "EquipmentSummary",
                "Tables": [
                    {
                        "Cols": [
                            "Type",
                            "Fluid Type",
                            "Range [C]",
                            "Approach [C]",
                            "Design Fan Power [W]",
                            "Design Inlet Air Wet-Bulb Temperature [C]",
                            "Design Water Flow Rate [m3/s]",
                            "Leaving Water Setpoint Temperature [C]",
                            "Condenser Loop Name",
                            "Condenser Loop Branch Name"
                        ],
                        "Rows": {
                            "HEAT PUMP LOOP FLUIDCOOLERTWOSPEED 4.0 GPM/HP": [
                                "FluidCooler:TwoSpeed",
                                "ETHYLENEGLYCOL_40",
                                "26.07",
                                "12.0",
                                "53675.71",
                                "25.60",
                                "0.02",
                                "0.00",
                                "HEAT PUMP LOOP",
                                "HEAT PUMP LOOP SUPPLY BRANCH 1"
                            ]
                        },
                        "TableName": "Cooling Towers and Fluid Coolers"
                    },
                ]
            },
        ]

        added_heat_rejection = t.add_heat_rejection()

        expected = [{'id': 'HEAT PUMP LOOP FLUIDCOOLERTWOSPEED 4.0 GPM/HP', 'loop': 'HEAT PUMP LOOP', 'range': 26.07,
                     'fan_motor_nameplate_power': 53675.71, 'design_wetbulb_temperature': 25.6,
                     'design_water_flowrate': 20.0, 'leaving_water_setpoint_temperature': 0.0, 'approach': 12.0}]

        self.assertEqual(added_heat_rejection, expected)

    def test_add_boilers(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {
                "For": "Entire Facility",
                "ReportName": "EquipmentSummary",
                "Tables": [
                    {
                        "Cols": [
                            "Type",
                            "Reference Capacity [W]",
                            "Reference Efficiency[W/W]",
                            "Rated Capacity [W]",
                            "Rated Efficiency [W/W]",
                            "Minimum Part Load Ratio",
                            "Fuel Type",
                            "Parasitic Electric Load [W]",
                            "Plantloop Name",
                            "Plantloop Branch Name"
                        ],
                        "Rows": {
                            "BOILER 5939KBTU/HR 0.75 THERMAL EFF": [
                                "Boiler:HotWater",
                                "1891644.33",
                                "0.75",
                                "1891644.33",
                                "0.75",
                                "0.00",
                                "NaturalGas",
                                "0.00",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP SUPPLY BRANCH 1"
                            ],
                            "HEAT PUMP LOOP SUPPLEMENTAL BOILER 2669KBTU/HR 0.75 THERMAL EFF": [
                                "Boiler:HotWater",
                                "715840.29",
                                "0.75",
                                "715840.29",
                                "0.75",
                                "0.00",
                                "NaturalGas",
                                "0.00",
                                "HEAT PUMP LOOP",
                                "HEAT PUMP LOOP SUPPLY BRANCH 2"
                            ]
                        },
                        "TableName": "Boilers"
                    }
                ]
            },
        ]

        added_boilers = t.add_boilers()

        expected = [
            {'id': 'BOILER 5939KBTU/HR 0.75 THERMAL EFF', 'loop': 'HOT WATER LOOP', 'design_capacity': 1891644.33,
             'rated_capacity': 1891644.33, 'minimum_load_ratio': 0.0, 'energy_source_type': 'NATURAL_GAS',
             'efficiency_metric': 'THERMAL', 'efficiency': 0.75, 'auxiliary_power': 0.0},
            {'id': 'HEAT PUMP LOOP SUPPLEMENTAL BOILER 2669KBTU/HR 0.75 THERMAL EFF', 'loop': 'HEAT PUMP LOOP',
             'design_capacity': 715840.29, 'rated_capacity': 715840.29, 'minimum_load_ratio': 0.0,
             'energy_source_type': 'NATURAL_GAS', 'efficiency_metric': 'THERMAL', 'efficiency': 0.75,
             'auxiliary_power': 0.0}]

        self.assertEqual(added_boilers, expected)

    def test_add_chillers(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {
                "For": "Entire Facility",
                "ReportName": "EquipmentSummary",
                "Tables": [
                    {
                        "Cols": [
                            "Type",
                            "Reference Capacity[W]",
                            "TypeReference Efficiency [W/W]",
                            "Rated Capacity [W]",
                            "Rated Efficiency [W/W]",
                            "IPLV in SI Units [W/W]",
                            "IPLV in IP Units [Btu/W-h]",
                            "Minimum Part Load Ratio",
                            "Fuel Type",
                            "Rated Entering Condenser Temperature [C]",
                            "Rated Leaving Evaporator Temperature [C]",
                            "Reference Entering Condenser Temperature [C]",
                            "Reference Leaving Evaporator Temperature [C]",
                            "Design Size Reference Chilled Water Flow Rate [kg/s]",
                            "Design Size Reference Condenser Fluid Flow Rate [kg/s]",
                            "Plantloop Name",
                            "Plantloop Branch Name",
                            "Condenser Loop Name",
                            "Condenser Loop Branch Name",
                            "Heat Recovery Plantloop Name",
                            "Heat Recovery Plantloop Branch Name",
                            "Recovery Relative Capacity Fraction"
                        ],
                        "Rows": {
                            "90.1-2004 WATERCOOLED  CENTRIFUGAL CHILLER 0 416TONS 0.6KW/TON": [
                                "Chiller:Electric:EIR",
                                "1762283.32",
                                "6.10",
                                "1762283.32",
                                "6.10",
                                "6.88",
                                "6.92",
                                "0.00",
                                "Electricity",
                                "35.00",
                                "6.67",
                                "35.00",
                                "6.67",
                                "74.82",
                                "87.82",
                                "CHILLED WATER LOOP",
                                "CHILLED WATER LOOP SUPPLY BRANCH 1",
                                "CONDENSER WATER LOOP",
                                "CONDENSER WATER LOOP DEMAND BRANCH 2",
                                "N/A",
                                "N/A",
                                "0.00"
                            ],
                            "90.1-2004 WATERCOOLED  CENTRIFUGAL CHILLER 1 416TONS 0.6KW/TON": [
                                "Chiller:Electric:EIR",
                                "1762283.32",
                                "6.10",
                                "1762283.32",
                                "6.10",
                                "6.88",
                                "6.92",
                                "0.00",
                                "Electricity",
                                "35.00",
                                "6.67",
                                "35.00",
                                "6.67",
                                "74.82",
                                "87.82",
                                "CHILLED WATER LOOP",
                                "CHILLED WATER LOOP SUPPLY BRANCH 2",
                                "CONDENSER WATER LOOP",
                                "CONDENSER WATER LOOP DEMAND BRANCH 3",
                                "HeatRecoveryLoop1",
                                "SomeBranch",
                                "0.67"
                            ]
                        },
                        "TableName": "Chillers"
                    },
                ]
            },
        ]

        added_chillers = t.add_chillers()

        expected = [{'id': '90.1-2004 WATERCOOLED  CENTRIFUGAL CHILLER 0 416TONS 0.6KW/TON',
                     'cooling_loop': 'CHILLED WATER LOOP', 'condensing_loop': 'CONDENSER WATER LOOP',
                     'energy_source_type': 'ELECTRICITY', 'design_capacity': 1762283.32, 'rated_capacity': 1762283.32,
                     'rated_entering_condenser_temperature': 35.0, 'rated_leaving_evaporator_temperature': 6.67,
                     'minimum_load_ratio': 0.0, 'design_flow_evaporator': 74.82, 'design_flow_condenser': 87.82,
                     'design_entering_condenser_temperature': 35.0, 'design_leaving_evaporator_temperature': 6.67,
                     'full_load_efficiency': 6.1, 'part_load_efficiency': 6.88,
                     'part_load_efficiency_metric': 'INTEGRATED_PART_LOAD_VALUE'},
                    {'id': '90.1-2004 WATERCOOLED  CENTRIFUGAL CHILLER 1 416TONS 0.6KW/TON',
                     'cooling_loop': 'CHILLED WATER LOOP', 'condensing_loop': 'CONDENSER WATER LOOP',
                     'energy_source_type': 'ELECTRICITY', 'design_capacity': 1762283.32, 'rated_capacity': 1762283.32,
                     'rated_entering_condenser_temperature': 35.0, 'rated_leaving_evaporator_temperature': 6.67,
                     'minimum_load_ratio': 0.0, 'design_flow_evaporator': 74.82, 'design_flow_condenser': 87.82,
                     'design_entering_condenser_temperature': 35.0, 'design_leaving_evaporator_temperature': 6.67,
                     'full_load_efficiency': 6.1, 'part_load_efficiency': 6.88,
                     'part_load_efficiency_metric': 'INTEGRATED_PART_LOAD_VALUE',
                     'heat_recovery_loop': 'HeatRecoveryLoop1', 'heat_recovery_fraction': 0.67}]

        self.assertEqual(added_chillers, expected)

    def test_gather_equipment_fans(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {
                "For": "Entire Facility",
                "ReportName": "EquipmentSummary",
                "Tables": [
                    {
                        "Cols": [
                            "Type",
                            "Total Efficiency [W/W]",
                            "Delta Pressure [pa]",
                            "Max Air Flow Rate [m3/s]",
                            "Rated Electricity Rate [W]",
                            "Rated Power Per Max Air Flow Rate [W-s/m3]",
                            "Motor Heat In Air Fraction",
                            "Fan Energy Index",
                            "End Use Subcategory",
                            "Design Day Name for Fan Sizing Peak",
                            "Date/Time for Fan Sizing Peak",
                            "Purpose",
                            "Is Autosized",
                            "Motor Efficiency",
                            "Motor Heat to Zone Fraction",
                            "Airloop Name"
                        ],
                        "Rows": {
                            "BASEMENT STORY 0 VAV_PFP_BOXES (SYS8) FAN": [
                                "Fan:VariableVolume",
                                "0.64",
                                "1363.04",
                                "7.69",
                                "16476.83",
                                "2141.35",
                                "1.00",
                                "1.18",
                                "VAV System Fans",
                                "TAMPA-MACDILL.AFB_FL_USA ANN CLG .4% CONDNS DB=>MWB",
                                "8/21 08:20:00",
                                "N/A",
                                "Yes",
                                "0.92",
                                "1.00",
                                "N/A"
                            ],
                            "BASEMENT ZN PFP TERM FAN": [
                                "Fan:ConstantVolume",
                                "0.49",
                                "365.09",
                                "7.67",
                                "5688.72",
                                "741.68",
                                "1.00",
                                "1.11",
                                "General",
                                "TAMPA-MACDILL.AFB_FL_USA ANN CLG .4% CONDNS DB=>MWB",
                                "8/21 08:00:00",
                                "N/A",
                                "Yes",
                                "0.90",
                                "1.00",
                                "N/A"
                            ],
                            "CORE_BOTTOM ZN PFP TERM FAN": [
                                "Fan:ConstantVolume",
                                "0.49",
                                "365.09",
                                "7.94",
                                "5888.97",
                                "741.68",
                                "1.00",
                                "1.11",
                                "General",
                                "TAMPA-MACDILL.AFB_FL_USA ANN CLG .4% CONDNS DB=>MWB",
                                "8/21 08:00:00",
                                "N/A",
                                "Yes",
                                "0.90",
                                "1.00",
                                "N/A"
                            ],
                            "DATACENTER_BASEMENT_ZN_6 ZN PSZ-VAV FAN": [
                                "Fan:VariableVolume",
                                "0.57",
                                "0.00",
                                "30.36",
                                "0.00",
                                "0.00",
                                "1.00",
                                "0.00",
                                "VAV System Fans",
                                "TAMPA-MACDILL.AFB_FL_USA ANN CLG .4% CONDNS DB=>MWB",
                                "8/21 06:00:00",
                                "N/A",
                                "Yes",
                                "0.94",
                                "1.00",
                                "N/A"
                            ],
                            "PERIMETER_BOT_ZN_2 ZN PFP TERM FAN": [
                                "Fan:ConstantVolume",
                                "0.46",
                                "342.66",
                                "1.53",
                                "1137.67",
                                "741.68",
                                "1.00",
                                "1.23",
                                "General",
                                "TAMPA-MACDILL.AFB_FL_USA ANN CLG .4% CONDNS DB=>MWB",
                                "8/21 09:40:00",
                                "N/A",
                                "Yes",
                                "0.84",
                                "1.00",
                                "N/A"
                            ],
                        },
                        "TableName": "Fans"
                    },
                ]
            },
        ]

        gathered_equipment_fans = t.gather_equipment_fans()

        expected = {'BASEMENT STORY 0 VAV_PFP_BOXES (SYS8) FAN': (
            {'design_airflow': 7.69, 'is_airflow_autosized': True, 'design_electric_power': 16476.83,
             'design_pressure_rise': 1363.04, 'total_efficiency': 0.64, 'motor_efficiency': 0.92,
             'motor_heat_to_airflow_fraction': 1.0, 'motor_heat_to_zone_fraction': 1.0},
            {'type': 'Fan:VariableVolume', 'fan_energy_index': 1.18, 'purpose': 'N/A', 'airloop_name': 'N/A'}),
            'BASEMENT ZN PFP TERM FAN': (
                {'design_airflow': 7.67, 'is_airflow_autosized': True, 'design_electric_power': 5688.72,
                 'design_pressure_rise': 365.09, 'total_efficiency': 0.49, 'motor_efficiency': 0.9,
                 'motor_heat_to_airflow_fraction': 1.0, 'motor_heat_to_zone_fraction': 1.0},
                {'type': 'Fan:ConstantVolume', 'fan_energy_index': 1.11, 'purpose': 'N/A', 'airloop_name': 'N/A'}),
            'CORE_BOTTOM ZN PFP TERM FAN': (
                {'design_airflow': 7.94, 'is_airflow_autosized': True, 'design_electric_power': 5888.97,
                 'design_pressure_rise': 365.09, 'total_efficiency': 0.49, 'motor_efficiency': 0.9,
                 'motor_heat_to_airflow_fraction': 1.0, 'motor_heat_to_zone_fraction': 1.0},
                {'type': 'Fan:ConstantVolume', 'fan_energy_index': 1.11, 'purpose': 'N/A', 'airloop_name': 'N/A'}),
            'DATACENTER_BASEMENT_ZN_6 ZN PSZ-VAV FAN': (
                {'design_airflow': 30.36, 'is_airflow_autosized': True, 'design_electric_power': 0.0,
                 'design_pressure_rise': 0.0, 'total_efficiency': 0.57, 'motor_efficiency': 0.94,
                 'motor_heat_to_airflow_fraction': 1.0, 'motor_heat_to_zone_fraction': 1.0},
                {'type': 'Fan:VariableVolume', 'fan_energy_index': 0.0, 'purpose': 'N/A', 'airloop_name': 'N/A'}),
            'PERIMETER_BOT_ZN_2 ZN PFP TERM FAN': (
                {'design_airflow': 1.53, 'is_airflow_autosized': True, 'design_electric_power': 1137.67,
                 'design_pressure_rise': 342.66, 'total_efficiency': 0.46, 'motor_efficiency': 0.84,
                 'motor_heat_to_airflow_fraction': 1.0, 'motor_heat_to_zone_fraction': 1.0},
                {'type': 'Fan:ConstantVolume', 'fan_energy_index': 1.23, 'purpose': 'N/A', 'airloop_name': 'N/A'})}

        self.assertEqual(gathered_equipment_fans, expected)

    def test_process_heating_metrics(self):
        t = self.set_minimal_files()
        coil_name = 'PSZ-AC:1 HEAT PUMP DX HEATING COIL'
        coil_efficiencies = {
            'PSZ-AC:1 HEAT PUMP DX HEATING COIL': {'type': 'Coil:Heating:DX:SingleSpeed', 'used_as_sup_heat': False,
                                                   'nominal_eff': 3.36, 'HSPF': 7.33, 'HSPF_region': '4',
                                                   'minimum_temperature_compressor': -12.2, 'HSPF2': 6.63,
                                                   'HSPF2_region': '4'},
            'PSZ-AC:1 HEAT PUMP DX SUPP HEATING COIL': {'type': 'Coil:Heating:Fuel', 'used_as_sup_heat': True,
                                                        'nominal_eff': 0.81}, }

        processed_metric_types, processed_metric_values = t.process_heating_metrics(coil_name, coil_efficiencies)

        expected_metric_types = ['HEATING_SEASONAL_PERFORMANCE_FACTOR', 'HEATING_SEASONAL_PERFORMANCE_FACTOR_2']
        expected_metric_values = [7.33, 6.63]

        self.assertEqual(processed_metric_types, expected_metric_types)
        self.assertEqual(processed_metric_values, expected_metric_values)

        coil_name = 'PSZ-AC:1 HEAT PUMP DX SUPP HEATING COIL'

        processed_metric_types, processed_metric_values = t.process_heating_metrics(coil_name, coil_efficiencies)

        expected_metric_types = ['THERMAL_EFFICIENCY']
        expected_metric_values = [0.81]

        self.assertEqual(processed_metric_types, expected_metric_types)
        self.assertEqual(processed_metric_values, expected_metric_values)

    def test_gather_heating_coil_efficiencies(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {
                "For": "Entire Facility",
                "ReportName": "EquipmentSummary",
                "Tables": [
                    {
                        "Cols": [
                            "DX Heating Coil Type",
                            "High Temperature Heating (net) Rating Capacity [W]",
                            "Low Temperature Heating (net) Rating Capacity [W]",
                            "HSPF [Btu/W-h]",
                            "Region Number",
                            "Minimum Outdoor Dry-Bulb Temperature for Compressor Operation",
                            "Airloop Name"
                        ],
                        "Rows": {
                            "CORE_ZN ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "9507.1",
                                "5231.3",
                                "7.53",
                                "4",
                                "-12.20",
                                "N/A"
                            ],
                            "PERIMETER_ZN_1 ZN HP HTG COIL 30 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8797.2",
                                "4840.7",
                                "7.51",
                                "4",
                                "-12.20",
                                "N/A"
                            ],
                            "PERIMETER_ZN_2 ZN HP HTG COIL 25 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "7386.5",
                                "4064.5",
                                "7.51",
                                "4",
                                "-12.20",
                                "N/A"
                            ],
                            "PERIMETER_ZN_3 ZN HP HTG COIL 28 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8200.4",
                                "4512.3",
                                "7.50",
                                "4",
                                "-12.20",
                                "N/A"
                            ],
                            "PERIMETER_ZN_4 ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8944.9",
                                "4922.0",
                                "7.52",
                                "4",
                                "-12.20",
                                "N/A"
                            ]
                        },
                        "TableName": "DX Heating Coils"
                    },
                    {
                        "Cols": [
                            "DX Heating Coil Type",
                            "High Temperature Heating (net) Rating Capacity [W]",
                            "Low Temperature Heating (net) Rating Capacity [W]",
                            "HSPF2 [Btu/W-h]",
                            "Region Number"
                        ],
                        "Rows": {
                            "CORE_ZN ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "9507.1",
                                "5231.3",
                                "6.84",
                                "4"
                            ],
                            "PERIMETER_ZN_1 ZN HP HTG COIL 30 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8797.2",
                                "4840.7",
                                "6.84",
                                "4"
                            ],
                            "PERIMETER_ZN_2 ZN HP HTG COIL 25 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "7386.5",
                                "4064.5",
                                "6.84",
                                "4"
                            ],
                            "PERIMETER_ZN_3 ZN HP HTG COIL 28 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8200.4",
                                "4512.3",
                                "6.84",
                                "4"
                            ],
                            "PERIMETER_ZN_4 ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8944.9",
                                "4922.0",
                                "6.84",
                                "4"
                            ]
                        },
                        "TableName": "DX Heating Coils [ HSPF2 ]"
                    },
                    {
                        "Cols": [
                            "Type",
                            "Design Coil Load [W]",
                            "Nominal Total Capacity [W]",
                            "Nominal Efficiency [W/W]",
                            "Used as Supplementary Heat",
                            "Airloop Name",
                            "Plantloop Name"
                        ],
                        "Rows": {
                            "CORE_ZN ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "",
                                "9209.12",
                                "3.36",
                                "No",
                                "CORE_ZN ZN PSZ-AC-1",
                                "N/A"
                            ],
                            "CORE_ZN ZN PSZ-AC-1 GAS BACKUP HTG COIL 31KBTU/HR 0.8 THERMAL EFF": [
                                "Coil:Heating:Fuel",
                                "",
                                "9209.12",
                                "0.80",
                                "Yes",
                                "CORE_ZN ZN PSZ-AC-1",
                                "N/A"
                            ],
                            "PERIMETER_ZN_1 ZN HP HTG COIL 30 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "",
                                "8521.48",
                                "3.36",
                                "No",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2",
                                "N/A"
                            ],
                            "PERIMETER_ZN_1 ZN PSZ-AC-2 GAS BACKUP HTG COIL 30KBTU/HR 0.8 THERMAL EFF": [
                                "Coil:Heating:Fuel",
                                "",
                                "8521.48",
                                "0.80",
                                "Yes",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2",
                                "N/A"
                            ],
                            "PERIMETER_ZN_2 ZN HP HTG COIL 25 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "",
                                "7154.98",
                                "3.36",
                                "No",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "N/A"
                            ],
                            "PERIMETER_ZN_2 ZN PSZ-AC-3 GAS BACKUP HTG COIL 25KBTU/HR 0.8 THERMAL EFF": [
                                "Coil:Heating:Fuel",
                                "",
                                "7154.98",
                                "0.80",
                                "Yes",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "N/A"
                            ],
                            "PERIMETER_ZN_3 ZN HP HTG COIL 28 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "",
                                "7943.45",
                                "3.36",
                                "No",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4",
                                "N/A"
                            ],
                            "PERIMETER_ZN_3 ZN PSZ-AC-4 GAS BACKUP HTG COIL 28KBTU/HR 0.8 THERMAL EFF": [
                                "Coil:Heating:Fuel",
                                "",
                                "7943.45",
                                "0.80",
                                "Yes",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4",
                                "N/A"
                            ],
                            "PERIMETER_ZN_4 ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "",
                                "8664.58",
                                "3.36",
                                "No",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5",
                                "N/A"
                            ],
                            "PERIMETER_ZN_4 ZN PSZ-AC-5 GAS BACKUP HTG COIL 31KBTU/HR 0.8 THERMAL EFF": [
                                "Coil:Heating:Fuel",
                                "",
                                "8664.58",
                                "0.80",
                                "Yes",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5",
                                "N/A"
                            ]
                        },
                        "TableName": "Heating Coils"
                    },
                ]
            },
        ]

        gathered_heating_coil_efficiencies = t.gather_heating_coil_efficiencies()

        expected = {'CORE_ZN ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF': {'type': 'Coil:Heating:DX:SingleSpeed',
                                                                      'used_as_sup_heat': False, 'nominal_eff': 3.36,
                                                                      'HSPF': 7.53, 'HSPF_region': '4',
                                                                      'minimum_temperature_compressor': -12.2,
                                                                      'HSPF2': 6.84, 'HSPF2_region': '4'},
                    'CORE_ZN ZN PSZ-AC-1 GAS BACKUP HTG COIL 31KBTU/HR 0.8 THERMAL EFF': {'type': 'Coil:Heating:Fuel',
                                                                                          'used_as_sup_heat': True,
                                                                                          'nominal_eff': 0.8},
                    'PERIMETER_ZN_1 ZN HP HTG COIL 30 CLG KBTU/HR 8.0HSPF': {'type': 'Coil:Heating:DX:SingleSpeed',
                                                                             'used_as_sup_heat': False,
                                                                             'nominal_eff': 3.36, 'HSPF': 7.51,
                                                                             'HSPF_region': '4',
                                                                             'minimum_temperature_compressor': -12.2,
                                                                             'HSPF2': 6.84, 'HSPF2_region': '4'},
                    'PERIMETER_ZN_1 ZN PSZ-AC-2 GAS BACKUP HTG COIL 30KBTU/HR 0.8 THERMAL EFF': {
                        'type': 'Coil:Heating:Fuel', 'used_as_sup_heat': True, 'nominal_eff': 0.8},
                    'PERIMETER_ZN_2 ZN HP HTG COIL 25 CLG KBTU/HR 8.0HSPF': {'type': 'Coil:Heating:DX:SingleSpeed',
                                                                             'used_as_sup_heat': False,
                                                                             'nominal_eff': 3.36, 'HSPF': 7.51,
                                                                             'HSPF_region': '4',
                                                                             'minimum_temperature_compressor': -12.2,
                                                                             'HSPF2': 6.84, 'HSPF2_region': '4'},
                    'PERIMETER_ZN_2 ZN PSZ-AC-3 GAS BACKUP HTG COIL 25KBTU/HR 0.8 THERMAL EFF': {
                        'type': 'Coil:Heating:Fuel', 'used_as_sup_heat': True, 'nominal_eff': 0.8},
                    'PERIMETER_ZN_3 ZN HP HTG COIL 28 CLG KBTU/HR 8.0HSPF': {'type': 'Coil:Heating:DX:SingleSpeed',
                                                                             'used_as_sup_heat': False,
                                                                             'nominal_eff': 3.36, 'HSPF': 7.5,
                                                                             'HSPF_region': '4',
                                                                             'minimum_temperature_compressor': -12.2,
                                                                             'HSPF2': 6.84, 'HSPF2_region': '4'},
                    'PERIMETER_ZN_3 ZN PSZ-AC-4 GAS BACKUP HTG COIL 28KBTU/HR 0.8 THERMAL EFF': {
                        'type': 'Coil:Heating:Fuel', 'used_as_sup_heat': True, 'nominal_eff': 0.8},
                    'PERIMETER_ZN_4 ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF': {'type': 'Coil:Heating:DX:SingleSpeed',
                                                                             'used_as_sup_heat': False,
                                                                             'nominal_eff': 3.36, 'HSPF': 7.52,
                                                                             'HSPF_region': '4',
                                                                             'minimum_temperature_compressor': -12.2,
                                                                             'HSPF2': 6.84, 'HSPF2_region': '4'},
                    'PERIMETER_ZN_4 ZN PSZ-AC-5 GAS BACKUP HTG COIL 31KBTU/HR 0.8 THERMAL EFF': {
                        'type': 'Coil:Heating:Fuel', 'used_as_sup_heat': True, 'nominal_eff': 0.8}}

        self.assertEqual(gathered_heating_coil_efficiencies, expected)

    def test_process_cooling_metrics(self):
        t = self.set_minimal_files()
        coil_name = 'CORE_ZN ZN PSZ-AC-1 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER'
        coil_efficiencies = {
            'CORE_ZN ZN PSZ-AC-1 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER': {'type': 'Coil:Cooling:DX:SingleSpeed',
                                                                           'nominal_eff': 4.12,
                                                                           'StandardRatedNetCOP2017': 3.53,
                                                                           'EER2017': 12.05, 'SEER2017': 11.97,
                                                                           'IEER2017': 12.22,
                                                                           'StandardRatedNetCOP2023': 3.43,
                                                                           'EER2023': 11.7, 'SEER2023': 11.93,
                                                                           'IEER2023': 11.7}}

        processed_metric_types, processed_metric_values = t.process_cooling_metrics(coil_name, coil_efficiencies)

        expected_metric_types = ['FULL_LOAD_COEFFICIENT_OF_PERFORMANCE', 'ENERGY_EFFICIENCY_RATIO',
                                 'SEASONAL_ENERGY_EFFICIENCY_RATIO', 'INTEGRATED_ENERGY_EFFICIENCY_RATIO']
        expected_metric_values = [3.53, 12.05, 11.97, 11.7]

        self.assertEqual(processed_metric_types, expected_metric_types)
        self.assertEqual(processed_metric_values, expected_metric_values)

    def test_gather_cooling_coil_efficiencies(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {
                "For": "Entire Facility",
                "ReportName": "EquipmentSummary",
                "Tables": [
                    {
                        "Cols": [
                            "Type",
                            "Design Coil Load [W]",
                            "Nominal Total Capacity [W]",
                            "Nominal Sensible Capacity [W]",
                            "Nominal Latent Capacity [W]",
                            "Nominal Sensible Heat Ratio",
                            "Nominal Efficiency [W/W]",
                            "Nominal Coil UA Value [W/C]",
                            "Nominal Coil Surface Area [m2]"
                        ],
                        "Rows": {
                            "CORE_ZN ZN PSZ-AC-1 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "",
                                "9209.12",
                                "6456.36",
                                "2752.76",
                                "0.70",
                                "4.12",
                                "",
                                ""
                            ],
                            "PERIMETER_ZN_1 ZN PSZ-AC-2 1SPD DX HP CLG COIL 30KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "",
                                "8521.48",
                                "5974.26",
                                "2547.21",
                                "0.70",
                                "4.12",
                                "",
                                ""
                            ],
                            "PERIMETER_ZN_2 ZN PSZ-AC-3 1SPD DX HP CLG COIL 25KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "",
                                "7154.98",
                                "5016.24",
                                "2138.74",
                                "0.70",
                                "4.12",
                                "",
                                ""
                            ],
                            "PERIMETER_ZN_3 ZN PSZ-AC-4 1SPD DX HP CLG COIL 28KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "",
                                "7943.45",
                                "5569.02",
                                "2374.43",
                                "0.70",
                                "4.12",
                                "",
                                ""
                            ],
                            "PERIMETER_ZN_4 ZN PSZ-AC-5 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "",
                                "8664.58",
                                "6074.59",
                                "2589.99",
                                "0.70",
                                "4.12",
                                "",
                                ""
                            ]
                        },
                        "TableName": "Cooling Coils"
                    },
                    {
                        "Cols": [
                            "Cooling Coil Type #1",
                            "Standard Rated Net Cooling Capacity [W] #2",
                            "Standard Rated Net COP [W/W] #2",
                            "EER [Btu/W-h] #2",
                            "SEER User [Btu/W-h] #2,3",
                            "SEER Standard [Btu/W-h] #2,3",
                            "IEER [Btu/W-h] #2"
                        ],
                        "Rows": {
                            "CORE_ZN ZN PSZ-AC-1 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER": [
                                "",
                                "8916.6",
                                "3.53",
                                "12.05",
                                "11.97",
                                "11.97",
                                "12.22"
                            ],
                            "PERIMETER_ZN_1 ZN PSZ-AC-2 1SPD DX HP CLG COIL 30KBTU/HR 14.0SEER": [
                                "",
                                "8250.8",
                                "3.53",
                                "12.05",
                                "11.97",
                                "11.97",
                                "12.22"
                            ],
                            "PERIMETER_ZN_2 ZN PSZ-AC-3 1SPD DX HP CLG COIL 25KBTU/HR 14.0SEER": [
                                "",
                                "6927.7",
                                "3.53",
                                "12.05",
                                "11.97",
                                "11.97",
                                "12.22"
                            ],
                            "PERIMETER_ZN_3 ZN PSZ-AC-4 1SPD DX HP CLG COIL 28KBTU/HR 14.0SEER": [
                                "",
                                "7691.1",
                                "3.53",
                                "12.05",
                                "11.97",
                                "11.97",
                                "12.22"
                            ],
                            "PERIMETER_ZN_4 ZN PSZ-AC-5 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER": [
                                "",
                                "8389.3",
                                "3.53",
                                "12.05",
                                "11.97",
                                "11.97",
                                "12.22"
                            ]
                        },
                        "TableName": "DX Cooling Coil Standard Ratings 2017"
                    },
                    {
                        "Cols": [
                            "Cooling Coil Type #1",
                            "Standard Rated Net Cooling Capacity [W] #2",
                            "Standard Rated Net COP [W/W] #2,4",
                            "EER [Btu/W-h] #2,4",
                            "SEER User [Btu/W-h] #2,3",
                            "SEER Standard [Btu/W-h] #2,3",
                            "IEER [Btu/W-h] #2"
                        ],
                        "Rows": {
                            "CORE_ZN ZN PSZ-AC-1 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "8856.8",
                                "3.43",
                                "11.70",
                                "11.59",
                                "11.93",
                                "11.7"
                            ],
                            "PERIMETER_ZN_1 ZN PSZ-AC-2 1SPD DX HP CLG COIL 30KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "8195.5",
                                "3.43",
                                "11.70",
                                "11.59",
                                "11.93",
                                "11.7"
                            ],
                            "PERIMETER_ZN_2 ZN PSZ-AC-3 1SPD DX HP CLG COIL 25KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "6881.3",
                                "3.43",
                                "11.70",
                                "11.59",
                                "11.93",
                                "11.7"
                            ],
                            "PERIMETER_ZN_3 ZN PSZ-AC-4 1SPD DX HP CLG COIL 28KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "7639.6",
                                "3.43",
                                "11.70",
                                "11.59",
                                "11.93",
                                "11.7"
                            ],
                            "PERIMETER_ZN_4 ZN PSZ-AC-5 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "8333.1",
                                "3.43",
                                "11.70",
                                "11.59",
                                "11.93",
                                "11.7"
                            ]
                        },
                        "TableName": "DX Cooling Coil Standard Ratings 2023"
                    },
                ]
            },
        ]

        gathered_cooling_coil_efficiencies = t.gather_cooling_coil_efficiencies()

        expected = {
            'CORE_ZN ZN PSZ-AC-1 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER': {'type': 'Coil:Cooling:DX:SingleSpeed',
                                                                           'nominal_eff': 4.12,
                                                                           'StandardRatedNetCOP2017': 3.53,
                                                                           'EER2017': 12.05, 'SEER2017': 11.97,
                                                                           'IEER2017': 12.22,
                                                                           'StandardRatedNetCOP2023': 3.43,
                                                                           'EER2023': 11.7, 'SEER2023': 11.93,
                                                                           'IEER2023': 11.7},
            'PERIMETER_ZN_1 ZN PSZ-AC-2 1SPD DX HP CLG COIL 30KBTU/HR 14.0SEER': {'type': 'Coil:Cooling:DX:SingleSpeed',
                                                                                  'nominal_eff': 4.12,
                                                                                  'StandardRatedNetCOP2017': 3.53,
                                                                                  'EER2017': 12.05, 'SEER2017': 11.97,
                                                                                  'IEER2017': 12.22,
                                                                                  'StandardRatedNetCOP2023': 3.43,
                                                                                  'EER2023': 11.7, 'SEER2023': 11.93,
                                                                                  'IEER2023': 11.7},
            'PERIMETER_ZN_2 ZN PSZ-AC-3 1SPD DX HP CLG COIL 25KBTU/HR 14.0SEER': {'type': 'Coil:Cooling:DX:SingleSpeed',
                                                                                  'nominal_eff': 4.12,
                                                                                  'StandardRatedNetCOP2017': 3.53,
                                                                                  'EER2017': 12.05, 'SEER2017': 11.97,
                                                                                  'IEER2017': 12.22,
                                                                                  'StandardRatedNetCOP2023': 3.43,
                                                                                  'EER2023': 11.7, 'SEER2023': 11.93,
                                                                                  'IEER2023': 11.7},
            'PERIMETER_ZN_3 ZN PSZ-AC-4 1SPD DX HP CLG COIL 28KBTU/HR 14.0SEER': {'type': 'Coil:Cooling:DX:SingleSpeed',
                                                                                  'nominal_eff': 4.12,
                                                                                  'StandardRatedNetCOP2017': 3.53,
                                                                                  'EER2017': 12.05, 'SEER2017': 11.97,
                                                                                  'IEER2017': 12.22,
                                                                                  'StandardRatedNetCOP2023': 3.43,
                                                                                  'EER2023': 11.7, 'SEER2023': 11.93,
                                                                                  'IEER2023': 11.7},
            'PERIMETER_ZN_4 ZN PSZ-AC-5 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER': {'type': 'Coil:Cooling:DX:SingleSpeed',
                                                                                  'nominal_eff': 4.12,
                                                                                  'StandardRatedNetCOP2017': 3.53,
                                                                                  'EER2017': 12.05, 'SEER2017': 11.97,
                                                                                  'IEER2017': 12.22,
                                                                                  'StandardRatedNetCOP2023': 3.43,
                                                                                  'EER2023': 11.7, 'SEER2023': 11.93,
                                                                                  'IEER2023': 11.7}}
        self.assertEqual(gathered_cooling_coil_efficiencies, expected)
