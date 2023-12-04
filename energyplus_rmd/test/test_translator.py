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
