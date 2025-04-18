from json import dumps, loads
from pathlib import Path
from tempfile import mkdtemp
from unittest import TestCase

from energyplus_rpd.translator import Translator
from energyplus_rpd.translator import is_float
from energyplus_rpd.translator import energy_source_convert
from energyplus_rpd.translator import heating_type_convert
from energyplus_rpd.translator import cooling_type_convert
from energyplus_rpd.translator import source_from_coil
from energyplus_rpd.translator import terminal_option_convert
from energyplus_rpd.translator import terminal_heating_source_convert
from energyplus_rpd.translator import terminal_cooling_source_convert
from energyplus_rpd.translator import terminal_config_convert
from energyplus_rpd.translator import heat_rejection_type_convert
from energyplus_rpd.translator import heat_rejection_fan_speed_convert
from energyplus_rpd.translator import do_share_branch
from energyplus_rpd.translator import do_chiller_and_pump_share_branch


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
                'hourly_values': [1],
                'hourly_cooling_design_day': [],
                'hourly_heating_design_day': []
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
                'hourly_values': [1, 2, 3, 4, 5],
                'hourly_cooling_design_day': [],
                'hourly_heating_design_day': []
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
                'hourly_values': [1, 2, 3, 4, 5],
                'hourly_cooling_design_day': [],
                'hourly_heating_design_day': []
            },
            {
                'id': 'TWO-SCHEDULE',
                'sequence_type': 'HOURLY',
                'hourly_values': [11, 12, 13, 14, 15],
                'hourly_cooling_design_day': [],
                'hourly_heating_design_day': []
            },
            {
                'id': 'THREE-SCHEDULE',
                'sequence_type': 'HOURLY',
                'hourly_values': [21, 22, 23, 24, 25],
                'hourly_cooling_design_day': [],
                'hourly_heating_design_day': []
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
                 'primary_layers':
                     [
                         {'id': 'F07 25mm stucco',
                          'thickness': 0.0254,
                          'thermal_conductivity': 0.72,
                          'density': 1856,
                          'specific_heat': 840},
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
                          'specific_heat': 1090}
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

        expected = {'file_name': 'Denver-Aurora-Buckley AFB CO USA TMY3 WMO#=724695',
                    'data_source_type': 'OTHER',
                    'climate_zone': 'CZ5B',
                    'cooling_dry_bulb_design_day_type': 'COOLING_0_4',
                    'heating_dry_bulb_design_day_type': 'HEATING_99_6'}

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
            {'id': 'ATTIC', 'infiltration':
                {'algorithm_name': 'ZoneInfiltration', 'flow_rate': 0.0, 'id': 'infiltration-ATTIC',
                 'modeling_method': 'WEATHER_DRIVEN', 'multiplier_schedule': 'always_1'},
             'surfaces': [], 'volume': 720.19},
            {'id': 'CORE_ZN', 'infiltration':
                {'algorithm_name': 'ZoneInfiltration', 'flow_rate': 0.0, 'id': 'infiltration-CORE_ZN',
                 'modeling_method': 'WEATHER_DRIVEN', 'multiplier_schedule': 'always_1'},
             'surfaces': [], 'volume': 456.46},
            {'id': 'PERIMETER_ZN_1', 'infiltration':
                {'algorithm_name': 'ZoneInfiltration', 'flow_rate': 0.0, 'id': 'infiltration-PERIMETER_ZN_1',
                 'modeling_method': 'WEATHER_DRIVEN', 'multiplier_schedule': 'always_1'},
             'surfaces': [], 'volume': 346.02},
            {'id': 'PERIMETER_ZN_2', 'infiltration':
                {'algorithm_name': 'ZoneInfiltration', 'flow_rate': 0.0, 'id': 'infiltration-PERIMETER_ZN_2',
                 'modeling_method': 'WEATHER_DRIVEN', 'multiplier_schedule': 'always_1'},
             'surfaces': [], 'volume': 205.26},
            {'id': 'PERIMETER_ZN_3', 'infiltration':
                {'algorithm_name': 'ZoneInfiltration', 'flow_rate': 0.0, 'id': 'infiltration-PERIMETER_ZN_3',
                 'modeling_method': 'WEATHER_DRIVEN', 'multiplier_schedule': 'always_1'},
             'surfaces': [], 'volume': 346.02},
            {'id': 'PERIMETER_ZN_4', 'infiltration':
                {'algorithm_name': 'ZoneInfiltration', 'flow_rate': 0.0, 'id': 'infiltration-PERIMETER_ZN_4',
                 'modeling_method': 'WEATHER_DRIVEN', 'multiplier_schedule': 'always_1'},
             'surfaces': [], 'volume': 205.26}
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
                     },
                 ]
             },
            {'For': 'Entire Facility', 'ReportName': 'EquipmentSummary',
             'Tables':
                 [
                     {
                         "Cols": [
                             "Zone Name",
                             "Minimum Flow [m3/s]",
                             "Minimum Outdoor Flow [m3/s]",
                             "Supply Cooling Setpoint [C]",
                             "Supply Heating Setpoint [C]",
                             "Heating Capacity [W]",
                             "Cooling Capacity [W]",
                             "Type of Input Object",
                             "Heat/Reheat Coil Object Type",
                             "Chilled Water Coil Object Type",
                             "Fan Object Type",
                             "Fan Name",
                             "Primary Air Flow Rate [m3/s]",
                             "Secondary Air Flow Rate [m3/s]",
                             "Minimum Flow Schedule Name",
                             "Maximum Flow During Reheat [m3/s]",
                             "Minimum Outdoor Flow Schedule Name"
                         ],
                         "Rows": {
                             "ADU PERIMETER_MID_ZN_1 ZN VAV TERMINAL": [
                                 "PERIMETER_MID_ZN_1 ZN",
                                 "0.16",
                                 "0.09",
                                 "12.78",
                                 "50.00",
                                 "9253.34",
                                 "11993.20",
                                 "AirTerminal:SingleDuct:VAV:Reheat",
                                 "COIL:HEATING:ELECTRIC",
                                 "n/a",
                                 "n/a",
                                 "",
                                 "1.09",
                                 "n/a",
                                 "n/a",
                                 "0.00",
                                 "n/a"
                             ]
                         },
                         "TableName": "Air Terminals"
                     }
                 ]
             }
        ]

        added_hvac_systems, added_terminals_by_zone = t.add_heating_ventilation_system()

        expected_hvac = [{
            'id': '5 ZONE PVAV 1',
            'cooling_system':
                {'id': '5 ZONE PVAV 1-cooling',
                 'design_total_cool_capacity': 98149.824,
                 'design_sensible_cool_capacity': 78534.22,
                 'type': 'DIRECT_EXPANSION',
                 'rated_total_cool_capacity': 12345.67,
                 'rated_sensible_cool_capacity': 12345.67,
                 'oversizing_factor': 7.950141547603329,
                 'is_calculated_size': True}
        }]

        expected_terminals = {'PERIMETER_MID_ZN_1 ZN': [
            {'id': 'ADU PERIMETER_MID_ZN_1 ZN VAV TERMINAL', 'type': 'VARIABLE_AIR_VOLUME',
             'heating_source': 'ELECTRIC', 'cooling_source': 'NONE',
             'served_by_heating_ventilating_air_conditioning_system': '5 ZONE PVAV 1', 'primary_airflow': 1090.0,
             'supply_design_heating_setpoint_temperature': 50.0, 'supply_design_cooling_setpoint_temperature': 12.78,
             'minimum_airflow': 160.0, 'minimum_outdoor_airflow': 90.0, 'heating_capacity': 11828.176,
             'cooling_capacity': 11993.2}]}

        self.assertEqual(added_hvac_systems, expected_hvac)

        self.assertEqual(added_terminals_by_zone, expected_terminals)

    def test_add_heating_ventilation_system_hp(self):
        #  uses the small office proposed model
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
                                "9209.10",
                                "6456.35",
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
                                "7154.99",
                                "5016.25",
                                "2138.75",
                                "0.70",
                                "4.12",
                                "",
                                ""
                            ],
                            "PERIMETER_ZN_3 ZN PSZ-AC-4 1SPD DX HP CLG COIL 28KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "",
                                "7943.43",
                                "5569.01",
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
                            "Cooling Coil Type [1]",
                            "Standard Rating Net Cooling Capacity [W][2]",
                            "Standard Rating Net COP [W/W][2]",
                            "EER [Btu/W-h][2]",
                            "SEER User [Btu/W-h][2,3]",
                            "SEER Standard [Btu/W-h][2,3]",
                            "IEER [Btu/W-h][2]"
                        ],
                        "Rows": {
                            "CORE_ZN ZN PSZ-AC-1 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "8916.5",
                                "3.53",
                                "12.05",
                                "11.97",
                                "11.97",
                                "12.2"
                            ],
                            "PERIMETER_ZN_1 ZN PSZ-AC-2 1SPD DX HP CLG COIL 30KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "8250.8",
                                "3.53",
                                "12.05",
                                "11.97",
                                "11.97",
                                "12.2"
                            ],
                            "PERIMETER_ZN_2 ZN PSZ-AC-3 1SPD DX HP CLG COIL 25KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "6927.7",
                                "3.53",
                                "12.05",
                                "11.97",
                                "11.97",
                                "12.2"
                            ],
                            "PERIMETER_ZN_3 ZN PSZ-AC-4 1SPD DX HP CLG COIL 28KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "7691.1",
                                "3.53",
                                "12.05",
                                "11.97",
                                "11.97",
                                "12.2"
                            ],
                            "PERIMETER_ZN_4 ZN PSZ-AC-5 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "8389.3",
                                "3.53",
                                "12.05",
                                "11.97",
                                "11.97",
                                "12.2"
                            ]
                        },
                        "TableName": "DX Cooling Coil Standard Ratings 2017"
                    },
                    {
                        "Cols": [
                            "Cooling Coil Type [1]",
                            "Standard Rating Net Cooling Capacity [W][2]",
                            "Standard Rating Net COP2 [W/W][2,4]",
                            "EER2 [Btu/W-h][2,4]",
                            "SEER2 User [Btu/W-h][2,3]",
                            "SEER2 Standard [Btu/W-h][2,3]",
                            "IEER [Btu/W-h][2]"
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
                                "7639.5",
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
                    {
                        "Cols": [
                            "DX Heating Coil Type",
                            "High Temperature Heating (net) Rating Capacity [W]",
                            "Low Temperature Heating (net) Rating Capacity [W]",
                            "HSPF [Btu/W-h]",
                            "Region Number",
                            "Minimum Outdoor Dry-Bulb Temperature for Compressor Operation [C]",
                            "Supplemental Heat High Shutoff Temperature [C]",
                            "Airloop Name"
                        ],
                        "Rows": {
                            "CORE_ZN ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "9507.0",
                                "5231.3",
                                "7.53",
                                "4",
                                "-12.20",
                                "4.44",
                                "N/A"
                            ],
                            "PERIMETER_ZN_1 ZN HP HTG COIL 30 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8797.2",
                                "4840.7",
                                "7.51",
                                "4",
                                "-12.20",
                                "4.44",
                                "N/A"
                            ],
                            "PERIMETER_ZN_2 ZN HP HTG COIL 25 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "7386.5",
                                "4064.5",
                                "7.51",
                                "4",
                                "-12.20",
                                "4.44",
                                "N/A"
                            ],
                            "PERIMETER_ZN_3 ZN HP HTG COIL 28 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8200.4",
                                "4512.3",
                                "7.50",
                                "4",
                                "-12.20",
                                "4.44",
                                "N/A"
                            ],
                            "PERIMETER_ZN_4 ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8944.9",
                                "4922.0",
                                "7.52",
                                "4",
                                "-12.20",
                                "4.44",
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
                            "Region Number",
                            "Minimum Outdoor Dry-Bulb Temperature for Compressor Operation [C]",
                            "Airloop Name"
                        ],
                        "Rows": {
                            "CORE_ZN ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "9507.0",
                                "5231.3",
                                "6.84",
                                "4",
                                "-12.20",
                                "N/A"
                            ],
                            "PERIMETER_ZN_1 ZN HP HTG COIL 30 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8797.2",
                                "4840.7",
                                "6.84",
                                "4",
                                "-12.20",
                                "N/A"
                            ],
                            "PERIMETER_ZN_2 ZN HP HTG COIL 25 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "7386.5",
                                "4064.5",
                                "6.84",
                                "4",
                                "-12.20",
                                "N/A"
                            ],
                            "PERIMETER_ZN_3 ZN HP HTG COIL 28 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8200.4",
                                "4512.3",
                                "6.84",
                                "4",
                                "-12.20",
                                "N/A"
                            ],
                            "PERIMETER_ZN_4 ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8944.9",
                                "4922.0",
                                "6.84",
                                "4",
                                "-12.20",
                                "N/A"
                            ]
                        },
                        "TableName": "DX Heating Coils AHRI 2023"
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
                                "9209.10",
                                "3.36",
                                "No",
                                "CORE_ZN ZN PSZ-AC-1",
                                "N/A"
                            ],
                            "CORE_ZN ZN PSZ-AC-1 GAS BACKUP HTG COIL 31KBTU/HR 0.8 THERMAL EFF": [
                                "Coil:Heating:Fuel",
                                "",
                                "9209.10",
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
                                "7154.99",
                                "3.36",
                                "No",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "N/A"
                            ],
                            "PERIMETER_ZN_2 ZN PSZ-AC-3 GAS BACKUP HTG COIL 25KBTU/HR 0.8 THERMAL EFF": [
                                "Coil:Heating:Fuel",
                                "",
                                "7154.99",
                                "0.80",
                                "Yes",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "N/A"
                            ],
                            "PERIMETER_ZN_3 ZN HP HTG COIL 28 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "",
                                "7943.43",
                                "3.36",
                                "No",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4",
                                "N/A"
                            ],
                            "PERIMETER_ZN_3 ZN PSZ-AC-4 GAS BACKUP HTG COIL 28KBTU/HR 0.8 THERMAL EFF": [
                                "Coil:Heating:Fuel",
                                "",
                                "7943.43",
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
                            "Motor Loss Zone Name",
                            "Airloop Name"
                        ],
                        "Rows": {
                            "CORE_ZN ZN PSZ-AC-1 FAN": [
                                "Fan:OnOff",
                                "0.56",
                                "622.72",
                                "0.37",
                                "415.54",
                                "1120.51",
                                "1.00",
                                "1.71",
                                "General",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 18:40:00",
                                "N/A",
                                "Yes",
                                "0.85",
                                "0.00",
                                "N/A",
                                "CORE_ZN ZN PSZ-AC-1"
                            ],
                            "PERIMETER_ZN_1 ZN PSZ-AC-2 FAN": [
                                "Fan:OnOff",
                                "0.56",
                                "622.72",
                                "0.34",
                                "384.51",
                                "1120.51",
                                "1.00",
                                "1.76",
                                "General",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 14:00:00",
                                "N/A",
                                "Yes",
                                "0.85",
                                "0.00",
                                "N/A",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2"
                            ],
                            "PERIMETER_ZN_2 ZN PSZ-AC-3 FAN": [
                                "Fan:OnOff",
                                "0.56",
                                "622.72",
                                "0.29",
                                "322.85",
                                "1120.51",
                                "1.00",
                                "1.88",
                                "General",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 09:30:00",
                                "N/A",
                                "Yes",
                                "0.85",
                                "0.00",
                                "N/A",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3"
                            ],
                            "PERIMETER_ZN_3 ZN PSZ-AC-4 FAN": [
                                "Fan:OnOff",
                                "0.56",
                                "622.72",
                                "0.32",
                                "358.43",
                                "1120.51",
                                "1.00",
                                "1.80",
                                "General",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 18:30:00",
                                "N/A",
                                "Yes",
                                "0.85",
                                "0.00",
                                "N/A",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4"
                            ],
                            "PERIMETER_ZN_4 ZN PSZ-AC-5 FAN": [
                                "Fan:OnOff",
                                "0.56",
                                "622.72",
                                "0.35",
                                "390.97",
                                "1120.51",
                                "1.00",
                                "1.75",
                                "General",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 17:40:00",
                                "N/A",
                                "Yes",
                                "0.85",
                                "0.00",
                                "N/A",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5"
                            ]
                        },
                        "TableName": "Fans"
                    },
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
                            "MAIN SERVICE WATER LOOP WATER MAINS PRESSURE DRIVEN": [
                                "Pump:VariableSpeed",
                                "Intermittent",
                                "0.00",
                                "0.000004",
                                "0.00",
                                "0.00",
                                "0.70",
                                "General",
                                "Yes",
                                "MAIN SERVICE WATER LOOP",
                                "MAIN SERVICE WATER LOOP SUPPLY INLET BRANCH"
                            ]
                        },
                        "TableName": "Pumps"
                    },
                    {
                        "Cols": [
                            "Type",
                            "Provides Heating",
                            "Provides Cooling",
                            "Maximum Loop Flow Rate [m3/s]",
                            "Minimum Loop Flow Rate [m3/s]"
                        ],
                        "Rows": {
                            "MAIN SERVICE WATER LOOP": [
                                "PlantLoop",
                                "Yes",
                                "Yes",
                                "0.00",
                                "0.00"
                            ]
                        },
                        "TableName": "PlantLoop or CondenserLoop"
                    },
                    {
                        "Cols": [
                            "Zone Name",
                            "Minimum Flow [m3/s]",
                            "Minimum Outdoor Flow [m3/s]",
                            "Supply Cooling Setpoint [C]",
                            "Supply Heating Setpoint [C]",
                            "Heating Capacity [W]",
                            "Cooling Capacity [W]",
                            "Type of Input Object",
                            "Heat/Reheat Coil Object Type",
                            "Chilled Water Coil Object Type",
                            "Fan Object Type",
                            "Fan Name",
                            "Primary Air Flow Rate [m3/s]",
                            "Secondary Air Flow Rate [m3/s]",
                            "Minimum Flow Schedule Name",
                            "Maximum Flow During Reheat [m3/s]",
                            "Minimum Outdoor Flow Schedule Name"
                        ],
                        "Rows": {
                            "ADU CORE_ZN ZN PSZ-AC-1 DIFFUSER": [
                                "CORE_ZN ZN",
                                "0.11",
                                "0.06",
                                "12.78",
                                "50.00",
                                "1270.47",
                                "4058.82",
                                "AirTerminal:SingleDuct:ConstantVolume:NoReheat",
                                "",
                                "n/a",
                                "n/a",
                                "",
                                "0.37",
                                "n/a",
                                "n/a",
                                "0.00",
                                "n/a"
                            ],
                            "ADU PERIMETER_ZN_1 ZN PSZ-AC-2 DIFFUSER": [
                                "PERIMETER_ZN_1 ZN",
                                "0.09",
                                "0.05",
                                "12.78",
                                "50.00",
                                "3729.13",
                                "3755.63",
                                "AirTerminal:SingleDuct:ConstantVolume:NoReheat",
                                "",
                                "n/a",
                                "n/a",
                                "",
                                "0.34",
                                "n/a",
                                "n/a",
                                "0.00",
                                "n/a"
                            ],
                            "ADU PERIMETER_ZN_2 ZN PSZ-AC-3 DIFFUSER": [
                                "PERIMETER_ZN_2 ZN",
                                "0.05",
                                "0.03",
                                "12.78",
                                "50.00",
                                "2272.61",
                                "3153.59",
                                "AirTerminal:SingleDuct:ConstantVolume:NoReheat",
                                "",
                                "n/a",
                                "n/a",
                                "",
                                "0.29",
                                "n/a",
                                "n/a",
                                "0.00",
                                "n/a"
                            ],
                            "ADU PERIMETER_ZN_3 ZN PSZ-AC-4 DIFFUSER": [
                                "PERIMETER_ZN_3 ZN",
                                "0.09",
                                "0.05",
                                "12.78",
                                "50.00",
                                "3761.15",
                                "3501.01",
                                "AirTerminal:SingleDuct:ConstantVolume:NoReheat",
                                "",
                                "n/a",
                                "n/a",
                                "",
                                "0.32",
                                "n/a",
                                "n/a",
                                "0.00",
                                "n/a"
                            ],
                            "ADU PERIMETER_ZN_4 ZN PSZ-AC-5 DIFFUSER": [
                                "PERIMETER_ZN_4 ZN",
                                "0.05",
                                "0.03",
                                "12.78",
                                "50.00",
                                "2272.61",
                                "3818.87",
                                "AirTerminal:SingleDuct:ConstantVolume:NoReheat",
                                "",
                                "n/a",
                                "n/a",
                                "",
                                "0.35",
                                "n/a",
                                "n/a",
                                "0.00",
                                "n/a"
                            ]
                        },
                        "TableName": "Air Terminals"
                    },
                ]
            },
            {
                "For": "Entire Facility",
                "ReportName": "CoilSizingDetails",
                "Tables": [
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
                            "Coil Final Reference Air Volume Flow Rate [m3/s]",
                            "Coil Final Reference Plant Fluid Volume Flow Rate [m3/s]",
                            "Coil U-value Times Area Value [W/K]",
                            "Terminal Unit Reheat Coil Multiplier",
                            "DX Coil Capacity Increase Ratio from Too Low Flow/Capacity Ratio",
                            "DX Coil Capacity Decrease Ratio from Too High Flow/Capacity Ratio",
                            "Moist Air Heat Capacity [J/kg-K]",
                            "Dry Air Heat Capacity [J/kg-K]",
                            "Standard Air Density Adjusted for Elevation [kg/m3]",
                            "Supply Fan Name for Coil",
                            "Supply Fan Type for Coil",
                            "Supply Fan Maximum Air Volume Flow Rate [m3/s]",
                            "Supply Fan Maximum Air Mass Flow Rate [kg/s]",
                            "Plant Name for Coil",
                            "Plant Fluid Specific Heat Capacity [J/kg-K]",
                            "Plant Fluid Density [kg/m3]",
                            "Plant Maximum Fluid Mass Flow Rate [kg/s]",
                            "Plant Design Fluid Return Temperature [C]",
                            "Plant Design Fluid Supply Temperature [C]",
                            "Plant Design Fluid Temperature Difference [deltaC]",
                            "Plant Design Capacity [W]",
                            "Coil Capacity Percentage of Plant Design Capacity [%]",
                            "Coil Fluid Flow Rate Percentage of Plant Design Flow Rate [%]",
                            "Design Day Name at Sensible Ideal Loads Peak",
                            "Date/Time at Sensible Ideal Loads Peak",
                            "Design Day Name at Total Ideal Loads Peak",
                            "Date/Time at Total Ideal Loads Peak",
                            "Design Day Name at Air Flow Ideal Loads Peak",
                            "Date/Time at Air Flow Ideal Loads Peak",
                            "Peak Load Type to Size On",
                            "Coil Total Capacity at Ideal Loads Peak [W]",
                            "Coil Sensible Capacity at Ideal Loads Peak [W]",
                            "Coil Off-Rating Capacity Modifier at Ideal Loads Peak [ ]",
                            "Coil Air Mass Flow Rate at Ideal Loads Peak [kg/s]",
                            "Coil Air Volume Flow Rate at Ideal Loads Peak [m3/s]",
                            "Coil Entering Air Drybulb at Ideal Loads Peak [C]",
                            "Coil Entering Air Wetbulb at Ideal Loads Peak [C]",
                            "Coil Entering Air Humidity Ratio at Ideal Loads Peak [kgWater/kgDryAir]",
                            "Coil Entering Air Enthalpy at Ideal Loads Peak [J/KG-K]",
                            "Coil Leaving Air Drybulb at Ideal Loads Peak [C]",
                            "Coil Leaving Air Wetbulb at Ideal Loads Peak [C]",
                            "Coil Leaving Air Humidity Ratio at Ideal Loads Peak [kgWater/kgDryAir]",
                            "Coil Leaving Air Enthalpy at Ideal Loads Peak [J/KG-K]",
                            "Coil Plant Fluid Mass Flow Rate at Ideal Loads Peak [kg/s]",
                            "Coil Entering Plant Fluid Temperature at Ideal Loads Peak [C]",
                            "Coil Leaving Plant Fluid Temperature at Ideal Loads Peak [C]",
                            "Coil Plant Fluid Temperature Difference at Ideal Loads Peak [deltaC]",
                            "Supply Fan Air Heat Gain at Ideal Loads Peak [W]",
                            "Coil and Fan Net Total Capacity at Ideal Loads Peak [W]",
                            "Outdoor Air Drybulb at Ideal Loads Peak [C]",
                            "Outdoor Air Humidity Ratio at Ideal Loads Peak [kgWater/kgDryAir]",
                            "Outdoor Air Wetbulb at Ideal Loads Peak [C]",
                            "Outdoor Air Volume Flow Rate at Ideal Loads Peak [m3/s]",
                            "Outdoor Air Flow Percentage at Ideal Loads Peak [%]",
                            "System Return Air Drybulb at Ideal Loads Peak [C]",
                            "System Return Air Humidity Ratio at Ideal Loads Peak [kgWater/kgDryAir]",
                            "Zone Air Drybulb at Ideal Loads Peak [C]",
                            "Zone Air Humidity Ratio at Ideal Loads Peak [kgWater/kgDryAir]",
                            "Zone Air Relative Humidity at Ideal Loads Peak [%]",
                            "Zone Sensible Heat Gain at Ideal Loads Peak [W]",
                            "Zone Latent Heat Gain at Ideal Loads Peak [W]",
                            "Coil Total Capacity at Rating Conditions [W]",
                            "Coil Sensible Capacity at Rating Conditions [W]",
                            "Coil Air Mass Flow Rate at Rating Conditions [kg/s]",
                            "Coil Entering Air Drybulb at Rating Conditions [C]",
                            "Coil Entering Air Wetbulb at Rating Conditions [C]",
                            "Coil Entering Air Humidity Ratio at Rating Conditions [kgWater/kgDryAir]",
                            "Coil Entering Air Enthalpy at Rating Conditions [J/KG-K]",
                            "Coil Leaving Air Drybulb at Rating Conditions [C]",
                            "Coil Leaving Air Wetbulb at Rating Conditions [C]",
                            "Coil Leaving Air Humidity Ratio at Rating Conditions [kgWater/kgDryAir]",
                            "Coil Leaving Air Enthalpy at Rating Conditions [J/KG-K]"
                        ],
                        "Rows": {
                            "CORE_ZN ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "COIL:HEATING:DX:SINGLESPEED",
                                "AirLoop",
                                "AirLoopHVAC",
                                "CORE_ZN ZN PSZ-AC-1",
                                "CORE_ZN ZN",
                                "Coincident",
                                "HeatingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "9209.104",
                                "9209.104",
                                "0.370851",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1019.7116",
                                "1004.8586",
                                "0.9651",
                                "CORE_ZN ZN PSZ-AC-1 FAN",
                                "Fan:OnOff",
                                "0.370851",
                                "0.35790110",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 00:10:00",
                                "unknown",
                                "unknown",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 00:10:00",
                                "Sensible",
                                "9209.10",
                                "9209.10",
                                "1.0000",
                                "0.35790110",
                                "0.370851",
                                "14.31",
                                "9.03",
                                "0.00677242",
                                "31499.3",
                                "50.00",
                                "21.25",
                                "0.00800000",
                                "70993.1",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "0.000",
                                "9209.10",
                                "-17.90",
                                "0.00095524",
                                "-17.93",
                                "0.06462207",
                                "17.4254",
                                "21.11",
                                "0.00800000",
                                "21.11",
                                "0.00800000",
                                "41.1698",
                                "1057.91",
                                "0.00",
                                "9221.21",
                                "9221.21",
                                "0.35157687",
                                "21.11",
                                "15.56",
                                "0.00875166",
                                "43444.1",
                                "46.80",
                                "23.62",
                                "0.00875166",
                                "69672.2"
                            ],
                            "CORE_ZN ZN PSZ-AC-1 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "AirLoop",
                                "AirLoopHVAC",
                                "CORE_ZN ZN PSZ-AC-1",
                                "CORE_ZN ZN",
                                "Coincident",
                                "CoolingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "9209.104",
                                "6456.349",
                                "0.370851",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1020.5687",
                                "1004.8586",
                                "0.9651",
                                "CORE_ZN ZN PSZ-AC-1 FAN",
                                "Fan:OnOff",
                                "0.370851",
                                "0.35790110",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 15:00:00",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 15:00:00",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 18:40:00",
                                "Sensible",
                                "8266.83",
                                "8266.83",
                                "0.8977",
                                "0.35790110",
                                "0.370851",
                                "26.80",
                                "15.01",
                                "0.00846108",
                                "48516.1",
                                "12.78",
                                "10.05",
                                "0.00846108",
                                "34201.2",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "415.541",
                                "7851.29",
                                "33.90",
                                "0.00547527",
                                "14.94",
                                "0.06462207",
                                "17.4254",
                                "23.89",
                                "0.00910585",
                                "23.89",
                                "0.00910585",
                                "39.5114",
                                "3318.53",
                                "0.00",
                                "9207.52",
                                "5940.65",
                                "0.34376671",
                                "26.67",
                                "19.44",
                                "0.01118466",
                                "55322.4",
                                "9.70",
                                "9.68",
                                "0.00745868",
                                "28538.2"
                            ],
                            "CORE_ZN ZN PSZ-AC-1 GAS BACKUP HTG COIL 31KBTU/HR 0.8 THERMAL EFF": [
                                "COIL:HEATING:FUEL",
                                "AirLoop",
                                "AirLoopHVAC",
                                "CORE_ZN ZN PSZ-AC-1",
                                "CORE_ZN ZN",
                                "Coincident",
                                "HeatingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "9209.104",
                                "9209.104",
                                "-999.0",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1019.7116",
                                "1004.8586",
                                "0.9651",
                                "CORE_ZN ZN PSZ-AC-1 FAN",
                                "Fan:OnOff",
                                "0.370851",
                                "0.35790110",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 00:10:00",
                                "unknown",
                                "unknown",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 00:10:00",
                                "Sensible",
                                "9209.10",
                                "9209.10",
                                "1.0000",
                                "0.35790110",
                                "0.370851",
                                "14.31",
                                "9.03",
                                "0.00677242",
                                "31499.3",
                                "50.00",
                                "21.25",
                                "0.00800000",
                                "70993.1",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "0.000",
                                "9209.10",
                                "-17.90",
                                "0.00095524",
                                "-17.93",
                                "0.06462207",
                                "17.4254",
                                "21.11",
                                "0.00800000",
                                "21.11",
                                "0.00800000",
                                "41.1698",
                                "1057.91",
                                "0.00",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.0"
                            ],
                            "PERIMETER_ZN_1 ZN HP HTG COIL 30 CLG KBTU/HR 8.0HSPF": [
                                "COIL:HEATING:DX:SINGLESPEED",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2",
                                "PERIMETER_ZN_1 ZN",
                                "Coincident",
                                "HeatingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "8521.475",
                                "8521.475",
                                "0.343160",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1019.7116",
                                "1004.8586",
                                "0.9651",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2 FAN",
                                "Fan:OnOff",
                                "0.343160",
                                "0.33117718",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "unknown",
                                "unknown",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "Sensible",
                                "8521.48",
                                "8521.48",
                                "1.0000",
                                "0.33117718",
                                "0.343160",
                                "15.54",
                                "9.36",
                                "0.00660474",
                                "32324.1",
                                "50.00",
                                "21.25",
                                "0.00800000",
                                "70993.1",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "0.000",
                                "8521.48",
                                "-17.90",
                                "0.00095524",
                                "-17.93",
                                "0.04898771",
                                "14.2755",
                                "21.11",
                                "0.00754554",
                                "21.11",
                                "0.00754554",
                                "38.8620",
                                "3107.61",
                                "0.00",
                                "8532.67",
                                "8532.67",
                                "0.32532518",
                                "21.11",
                                "15.56",
                                "0.00875166",
                                "43444.1",
                                "46.80",
                                "23.62",
                                "0.00875166",
                                "69672.2"
                            ],
                            "PERIMETER_ZN_1 ZN PSZ-AC-2 1SPD DX HP CLG COIL 30KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2",
                                "PERIMETER_ZN_1 ZN",
                                "Coincident",
                                "CoolingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "8521.475",
                                "5974.263",
                                "0.343160",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1020.5703",
                                "1004.8586",
                                "0.9651",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2 FAN",
                                "Fan:OnOff",
                                "0.343160",
                                "0.33117718",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 14:00:00",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 14:00:00",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 14:00:00",
                                "Sensible",
                                "7625.72",
                                "7625.71",
                                "0.8949",
                                "0.33117718",
                                "0.343160",
                                "26.46",
                                "14.89",
                                "0.00846195",
                                "48162.5",
                                "12.78",
                                "10.05",
                                "0.00846195",
                                "34203.4",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "384.513",
                                "7241.20",
                                "33.90",
                                "0.00547527",
                                "14.94",
                                "0.04898771",
                                "14.2755",
                                "23.89",
                                "0.00895931",
                                "23.89",
                                "0.00895931",
                                "38.8841",
                                "3129.69",
                                "0.00",
                                "8520.01",
                                "5497.07",
                                "0.31809818",
                                "26.67",
                                "19.44",
                                "0.01118466",
                                "55322.4",
                                "9.70",
                                "9.68",
                                "0.00745868",
                                "28538.2"
                            ],
                            "PERIMETER_ZN_1 ZN PSZ-AC-2 GAS BACKUP HTG COIL 30KBTU/HR 0.8 THERMAL EFF": [
                                "COIL:HEATING:FUEL",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2",
                                "PERIMETER_ZN_1 ZN",
                                "Coincident",
                                "HeatingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "8521.475",
                                "8521.475",
                                "-999.0",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1019.7116",
                                "1004.8586",
                                "0.9651",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2 FAN",
                                "Fan:OnOff",
                                "0.343160",
                                "0.33117718",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "unknown",
                                "unknown",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "Sensible",
                                "8521.48",
                                "8521.48",
                                "1.0000",
                                "0.33117718",
                                "0.343160",
                                "15.54",
                                "9.36",
                                "0.00660474",
                                "32324.1",
                                "50.00",
                                "21.25",
                                "0.00800000",
                                "70993.1",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "0.000",
                                "8521.48",
                                "-17.90",
                                "0.00095524",
                                "-17.93",
                                "0.04898771",
                                "14.2755",
                                "21.11",
                                "0.00754554",
                                "21.11",
                                "0.00754554",
                                "38.8620",
                                "3107.61",
                                "0.00",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.0"
                            ],
                            "PERIMETER_ZN_2 ZN HP HTG COIL 25 CLG KBTU/HR 8.0HSPF": [
                                "COIL:HEATING:DX:SINGLESPEED",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "PERIMETER_ZN_2 ZN",
                                "Coincident",
                                "HeatingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "7154.994",
                                "7154.994",
                                "0.288132",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1019.7116",
                                "1004.8586",
                                "0.9651",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3 FAN",
                                "Fan:OnOff",
                                "0.288132",
                                "0.27807050",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "unknown",
                                "unknown",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "Sensible",
                                "7154.99",
                                "7154.99",
                                "1.0000",
                                "0.27807050",
                                "0.288132",
                                "17.17",
                                "10.23",
                                "0.00684510",
                                "34595.2",
                                "50.00",
                                "21.25",
                                "0.00800000",
                                "70993.1",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "0.000",
                                "7154.99",
                                "-17.90",
                                "0.00095524",
                                "-17.93",
                                "0.02906014",
                                "10.0857",
                                "21.11",
                                "0.00750577",
                                "21.11",
                                "0.00750577",
                                "38.6599",
                                "1893.84",
                                "0.00",
                                "7164.40",
                                "7164.40",
                                "0.27315691",
                                "21.11",
                                "15.56",
                                "0.00875166",
                                "43444.1",
                                "46.80",
                                "23.62",
                                "0.00875166",
                                "69672.2"
                            ],
                            "PERIMETER_ZN_2 ZN PSZ-AC-3 1SPD DX HP CLG COIL 25KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "PERIMETER_ZN_2 ZN",
                                "Coincident",
                                "CoolingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "7154.994",
                                "5016.246",
                                "0.288132",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1020.6121",
                                "1004.8586",
                                "0.9651",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3 FAN",
                                "Fan:OnOff",
                                "0.288132",
                                "0.27807050",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 09:40:00",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 09:40:00",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 09:30:00",
                                "Sensible",
                                "6713.86",
                                "6713.86",
                                "0.9383",
                                "0.27807050",
                                "0.288132",
                                "25.39",
                                "14.56",
                                "0.00848442",
                                "47128.2",
                                "12.78",
                                "10.07",
                                "0.00848442",
                                "34260.2",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "322.854",
                                "6391.01",
                                "27.44",
                                "0.00546540",
                                "12.76",
                                "0.02906014",
                                "10.0857",
                                "23.89",
                                "0.00882422",
                                "23.89",
                                "0.00882422",
                                "38.3044",
                                "2619.93",
                                "0.00",
                                "7153.77",
                                "4615.58",
                                "0.26708882",
                                "26.67",
                                "19.44",
                                "0.01118466",
                                "55322.4",
                                "9.70",
                                "9.68",
                                "0.00745868",
                                "28538.2"
                            ],
                            "PERIMETER_ZN_2 ZN PSZ-AC-3 GAS BACKUP HTG COIL 25KBTU/HR 0.8 THERMAL EFF": [
                                "COIL:HEATING:FUEL",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "PERIMETER_ZN_2 ZN",
                                "Coincident",
                                "HeatingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "7154.994",
                                "7154.994",
                                "-999.0",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1019.7116",
                                "1004.8586",
                                "0.9651",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3 FAN",
                                "Fan:OnOff",
                                "0.288132",
                                "0.27807050",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "unknown",
                                "unknown",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "Sensible",
                                "7154.99",
                                "7154.99",
                                "1.0000",
                                "0.27807050",
                                "0.288132",
                                "17.17",
                                "10.23",
                                "0.00684510",
                                "34595.2",
                                "50.00",
                                "21.25",
                                "0.00800000",
                                "70993.1",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "0.000",
                                "7154.99",
                                "-17.90",
                                "0.00095524",
                                "-17.93",
                                "0.02906014",
                                "10.0857",
                                "21.11",
                                "0.00750577",
                                "21.11",
                                "0.00750577",
                                "38.6599",
                                "1893.84",
                                "0.00",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.0"
                            ],
                            "PERIMETER_ZN_3 ZN HP HTG COIL 28 CLG KBTU/HR 8.0HSPF": [
                                "COIL:HEATING:DX:SINGLESPEED",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4",
                                "PERIMETER_ZN_3 ZN",
                                "Coincident",
                                "HeatingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "7943.433",
                                "7943.433",
                                "0.319882",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1019.7116",
                                "1004.8586",
                                "0.9651",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4 FAN",
                                "Fan:OnOff",
                                "0.319882",
                                "0.30871225",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "unknown",
                                "unknown",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "Sensible",
                                "7943.43",
                                "7943.43",
                                "1.0000",
                                "0.30871225",
                                "0.319882",
                                "15.13",
                                "9.12",
                                "0.00652286",
                                "31704.9",
                                "50.00",
                                "21.25",
                                "0.00800000",
                                "70993.1",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "0.000",
                                "7943.43",
                                "-17.90",
                                "0.00095524",
                                "-17.93",
                                "0.04898771",
                                "15.3143",
                                "21.11",
                                "0.00752969",
                                "21.11",
                                "0.00752969",
                                "38.7815",
                                "3134.29",
                                "0.00",
                                "7953.87",
                                "7953.87",
                                "0.30325721",
                                "21.11",
                                "15.56",
                                "0.00875166",
                                "43444.1",
                                "46.80",
                                "23.62",
                                "0.00875166",
                                "69672.2"
                            ],
                            "PERIMETER_ZN_3 ZN PSZ-AC-4 1SPD DX HP CLG COIL 28KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4",
                                "PERIMETER_ZN_3 ZN",
                                "Coincident",
                                "CoolingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "7943.433",
                                "5569.008",
                                "0.319882",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1020.5529",
                                "1004.8586",
                                "0.9651",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4 FAN",
                                "Fan:OnOff",
                                "0.319882",
                                "0.30871225",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 15:10:00",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 15:10:00",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 18:30:00",
                                "Sensible",
                                "7123.67",
                                "7123.67",
                                "0.8968",
                                "0.30871225",
                                "0.319882",
                                "26.54",
                                "14.91",
                                "0.00845256",
                                "48226.5",
                                "12.78",
                                "10.04",
                                "0.00845256",
                                "34179.8",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "358.430",
                                "6765.24",
                                "33.75",
                                "0.00547504",
                                "14.89",
                                "0.04898771",
                                "15.3143",
                                "23.89",
                                "0.00899305",
                                "23.89",
                                "0.00899305",
                                "39.0285",
                                "2908.06",
                                "0.00",
                                "7942.07",
                                "5124.19",
                                "0.29652045",
                                "26.67",
                                "19.44",
                                "0.01118466",
                                "55322.4",
                                "9.70",
                                "9.68",
                                "0.00745868",
                                "28538.2"
                            ],
                            "PERIMETER_ZN_3 ZN PSZ-AC-4 GAS BACKUP HTG COIL 28KBTU/HR 0.8 THERMAL EFF": [
                                "COIL:HEATING:FUEL",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4",
                                "PERIMETER_ZN_3 ZN",
                                "Coincident",
                                "HeatingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "7943.433",
                                "7943.433",
                                "-999.0",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1019.7116",
                                "1004.8586",
                                "0.9651",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4 FAN",
                                "Fan:OnOff",
                                "0.319882",
                                "0.30871225",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "unknown",
                                "unknown",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "Sensible",
                                "7943.43",
                                "7943.43",
                                "1.0000",
                                "0.30871225",
                                "0.319882",
                                "15.13",
                                "9.12",
                                "0.00652286",
                                "31704.9",
                                "50.00",
                                "21.25",
                                "0.00800000",
                                "70993.1",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "0.000",
                                "7943.43",
                                "-17.90",
                                "0.00095524",
                                "-17.93",
                                "0.04898771",
                                "15.3143",
                                "21.11",
                                "0.00752969",
                                "21.11",
                                "0.00752969",
                                "38.7815",
                                "3134.29",
                                "0.00",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.0"
                            ],
                            "PERIMETER_ZN_4 ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "COIL:HEATING:DX:SINGLESPEED",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5",
                                "PERIMETER_ZN_4 ZN",
                                "Coincident",
                                "HeatingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "8664.576",
                                "8664.576",
                                "0.348922",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1019.7116",
                                "1004.8586",
                                "0.9651",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5 FAN",
                                "Fan:OnOff",
                                "0.348922",
                                "0.33673862",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "unknown",
                                "unknown",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "Sensible",
                                "8664.58",
                                "8664.58",
                                "1.0000",
                                "0.33673862",
                                "0.348922",
                                "17.86",
                                "10.60",
                                "0.00696021",
                                "35584.4",
                                "50.00",
                                "21.25",
                                "0.00800000",
                                "70993.1",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "0.000",
                                "8664.58",
                                "-17.90",
                                "0.00095524",
                                "-17.93",
                                "0.02906014",
                                "8.3285",
                                "21.11",
                                "0.00750577",
                                "21.11",
                                "0.00750577",
                                "38.6599",
                                "1893.84",
                                "0.00",
                                "8675.96",
                                "8675.96",
                                "0.33078835",
                                "21.11",
                                "15.56",
                                "0.00875166",
                                "43444.1",
                                "46.80",
                                "23.62",
                                "0.00875166",
                                "69672.2"
                            ],
                            "PERIMETER_ZN_4 ZN PSZ-AC-5 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5",
                                "PERIMETER_ZN_4 ZN",
                                "Coincident",
                                "CoolingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "8664.576",
                                "6074.589",
                                "0.348922",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1020.6249",
                                "1004.8586",
                                "0.9651",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5 FAN",
                                "Fan:OnOff",
                                "0.348922",
                                "0.33673862",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 17:40:00",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 17:40:00",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN CLG .4% CONDNS DB=>MWB",
                                "7/21 17:40:00",
                                "Sensible",
                                "7933.68",
                                "7933.68",
                                "0.9156",
                                "0.33673862",
                                "0.348922",
                                "25.61",
                                "14.64",
                                "0.00849130",
                                "47370.2",
                                "12.78",
                                "10.08",
                                "0.00849130",
                                "34277.6",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "390.970",
                                "7542.71",
                                "30.84",
                                "0.00547057",
                                "13.93",
                                "0.02906014",
                                "8.3285",
                                "23.89",
                                "0.00876574",
                                "23.89",
                                "0.00876574",
                                "38.0545",
                                "3182.40",
                                "0.00",
                                "8663.09",
                                "5589.38",
                                "0.32343999",
                                "26.67",
                                "19.44",
                                "0.01118466",
                                "55322.4",
                                "9.70",
                                "9.68",
                                "0.00745868",
                                "28538.2"
                            ],
                            "PERIMETER_ZN_4 ZN PSZ-AC-5 GAS BACKUP HTG COIL 31KBTU/HR 0.8 THERMAL EFF": [
                                "COIL:HEATING:FUEL",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5",
                                "PERIMETER_ZN_4 ZN",
                                "Coincident",
                                "HeatingDesignCapacity",
                                "N/A",
                                "Yes",
                                "Yes",
                                "unknown",
                                "No",
                                "8664.576",
                                "8664.576",
                                "-999.0",
                                "-999.0",
                                "-999.000",
                                "-999.0000",
                                "1.00000",
                                "1.00000",
                                "1019.7116",
                                "1004.8586",
                                "0.9651",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5 FAN",
                                "Fan:OnOff",
                                "0.348922",
                                "0.33673862",
                                "",
                                "-999.0000",
                                "-999.0000",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "-999.0000",
                                "-999.0",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "unknown",
                                "unknown",
                                "DENVER-AURORA-BUCKLEY.AFB_CO_USA ANN HTG 99.6% CONDNS DB",
                                "12/21 24:00:00",
                                "Sensible",
                                "8664.58",
                                "8664.58",
                                "1.0000",
                                "0.33673862",
                                "0.348922",
                                "17.86",
                                "10.60",
                                "0.00696021",
                                "35584.4",
                                "50.00",
                                "21.25",
                                "0.00800000",
                                "70993.1",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.00",
                                "0.000",
                                "8664.58",
                                "-17.90",
                                "0.00095524",
                                "-17.93",
                                "0.02906014",
                                "8.3285",
                                "21.11",
                                "0.00750577",
                                "21.11",
                                "0.00750577",
                                "38.6599",
                                "1893.84",
                                "0.00",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.0",
                                "-999.00",
                                "-999.00",
                                "-999.0",
                                "-999.0"
                            ]
                        },
                        "TableName": "Coils"
                    },
                    {
                        "Cols": [
                            "Coil Name",
                            "Coil Type",
                            "Coil Location",
                            "HVAC Type",
                            "HVAC Name",
                            "Zone Name(s)",
                            "Supply Fan Name for HVAC",
                            "Supply Fan Type for HVAC",
                            "Airloop Name",
                            "Plant Name for Coil",
                            "Plant Loop Name"
                        ],
                        "Rows": {
                            "CORE_ZN ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "CORE_ZN ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF",
                                "COIL:HEATING:DX:SINGLESPEED",
                                "AirLoop",
                                "AirLoopHVAC",
                                "CORE_ZN ZN PSZ-AC-1",
                                "CORE_ZN ZN",
                                "CORE_ZN ZN PSZ-AC-1 FAN",
                                "Fan:OnOff",
                                "CORE_ZN ZN PSZ-AC-1",
                                "unknown",
                                "unknown"
                            ],
                            "CORE_ZN ZN PSZ-AC-1 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER": [
                                "CORE_ZN ZN PSZ-AC-1 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER",
                                "Coil:Cooling:DX:SingleSpeed",
                                "AirLoop",
                                "AirLoopHVAC",
                                "CORE_ZN ZN PSZ-AC-1",
                                "CORE_ZN ZN",
                                "CORE_ZN ZN PSZ-AC-1 FAN",
                                "Fan:OnOff",
                                "CORE_ZN ZN PSZ-AC-1",
                                "unknown",
                                "unknown"
                            ],
                            "CORE_ZN ZN PSZ-AC-1 GAS BACKUP HTG COIL 31KBTU/HR 0.8 THERMAL EFF": [
                                "CORE_ZN ZN PSZ-AC-1 GAS BACKUP HTG COIL 31KBTU/HR 0.8 THERMAL EFF",
                                "COIL:HEATING:FUEL",
                                "AirLoop",
                                "AirLoopHVAC",
                                "CORE_ZN ZN PSZ-AC-1",
                                "CORE_ZN ZN",
                                "CORE_ZN ZN PSZ-AC-1 FAN",
                                "Fan:OnOff",
                                "CORE_ZN ZN PSZ-AC-1",
                                "unknown",
                                "unknown"
                            ],
                            "PERIMETER_ZN_1 ZN HP HTG COIL 30 CLG KBTU/HR 8.0HSPF": [
                                "PERIMETER_ZN_1 ZN HP HTG COIL 30 CLG KBTU/HR 8.0HSPF",
                                "COIL:HEATING:DX:SINGLESPEED",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2",
                                "PERIMETER_ZN_1 ZN",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2 FAN",
                                "Fan:OnOff",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2",
                                "unknown",
                                "unknown"
                            ],
                            "PERIMETER_ZN_1 ZN PSZ-AC-2 1SPD DX HP CLG COIL 30KBTU/HR 14.0SEER": [
                                "PERIMETER_ZN_1 ZN PSZ-AC-2 1SPD DX HP CLG COIL 30KBTU/HR 14.0SEER",
                                "Coil:Cooling:DX:SingleSpeed",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2",
                                "PERIMETER_ZN_1 ZN",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2 FAN",
                                "Fan:OnOff",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2",
                                "unknown",
                                "unknown"
                            ],
                            "PERIMETER_ZN_1 ZN PSZ-AC-2 GAS BACKUP HTG COIL 30KBTU/HR 0.8 THERMAL EFF": [
                                "PERIMETER_ZN_1 ZN PSZ-AC-2 GAS BACKUP HTG COIL 30KBTU/HR 0.8 THERMAL EFF",
                                "COIL:HEATING:FUEL",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2",
                                "PERIMETER_ZN_1 ZN",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2 FAN",
                                "Fan:OnOff",
                                "PERIMETER_ZN_1 ZN PSZ-AC-2",
                                "unknown",
                                "unknown"
                            ],
                            "PERIMETER_ZN_2 ZN HP HTG COIL 25 CLG KBTU/HR 8.0HSPF": [
                                "PERIMETER_ZN_2 ZN HP HTG COIL 25 CLG KBTU/HR 8.0HSPF",
                                "COIL:HEATING:DX:SINGLESPEED",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "PERIMETER_ZN_2 ZN",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3 FAN",
                                "Fan:OnOff",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "unknown",
                                "unknown"
                            ],
                            "PERIMETER_ZN_2 ZN PSZ-AC-3 1SPD DX HP CLG COIL 25KBTU/HR 14.0SEER": [
                                "PERIMETER_ZN_2 ZN PSZ-AC-3 1SPD DX HP CLG COIL 25KBTU/HR 14.0SEER",
                                "Coil:Cooling:DX:SingleSpeed",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "PERIMETER_ZN_2 ZN",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3 FAN",
                                "Fan:OnOff",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "unknown",
                                "unknown"
                            ],
                            "PERIMETER_ZN_2 ZN PSZ-AC-3 GAS BACKUP HTG COIL 25KBTU/HR 0.8 THERMAL EFF": [
                                "PERIMETER_ZN_2 ZN PSZ-AC-3 GAS BACKUP HTG COIL 25KBTU/HR 0.8 THERMAL EFF",
                                "COIL:HEATING:FUEL",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "PERIMETER_ZN_2 ZN",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3 FAN",
                                "Fan:OnOff",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "unknown",
                                "unknown"
                            ],
                            "PERIMETER_ZN_3 ZN HP HTG COIL 28 CLG KBTU/HR 8.0HSPF": [
                                "PERIMETER_ZN_3 ZN HP HTG COIL 28 CLG KBTU/HR 8.0HSPF",
                                "COIL:HEATING:DX:SINGLESPEED",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4",
                                "PERIMETER_ZN_3 ZN",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4 FAN",
                                "Fan:OnOff",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4",
                                "unknown",
                                "unknown"
                            ],
                            "PERIMETER_ZN_3 ZN PSZ-AC-4 1SPD DX HP CLG COIL 28KBTU/HR 14.0SEER": [
                                "PERIMETER_ZN_3 ZN PSZ-AC-4 1SPD DX HP CLG COIL 28KBTU/HR 14.0SEER",
                                "Coil:Cooling:DX:SingleSpeed",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4",
                                "PERIMETER_ZN_3 ZN",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4 FAN",
                                "Fan:OnOff",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4",
                                "unknown",
                                "unknown"
                            ],
                            "PERIMETER_ZN_3 ZN PSZ-AC-4 GAS BACKUP HTG COIL 28KBTU/HR 0.8 THERMAL EFF": [
                                "PERIMETER_ZN_3 ZN PSZ-AC-4 GAS BACKUP HTG COIL 28KBTU/HR 0.8 THERMAL EFF",
                                "COIL:HEATING:FUEL",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4",
                                "PERIMETER_ZN_3 ZN",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4 FAN",
                                "Fan:OnOff",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4",
                                "unknown",
                                "unknown"
                            ],
                            "PERIMETER_ZN_4 ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "PERIMETER_ZN_4 ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF",
                                "COIL:HEATING:DX:SINGLESPEED",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5",
                                "PERIMETER_ZN_4 ZN",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5 FAN",
                                "Fan:OnOff",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5",
                                "unknown",
                                "unknown"
                            ],
                            "PERIMETER_ZN_4 ZN PSZ-AC-5 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER": [
                                "PERIMETER_ZN_4 ZN PSZ-AC-5 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER",
                                "Coil:Cooling:DX:SingleSpeed",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5",
                                "PERIMETER_ZN_4 ZN",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5 FAN",
                                "Fan:OnOff",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5",
                                "unknown",
                                "unknown"
                            ],
                            "PERIMETER_ZN_4 ZN PSZ-AC-5 GAS BACKUP HTG COIL 31KBTU/HR 0.8 THERMAL EFF": [
                                "PERIMETER_ZN_4 ZN PSZ-AC-5 GAS BACKUP HTG COIL 31KBTU/HR 0.8 THERMAL EFF",
                                "COIL:HEATING:FUEL",
                                "AirLoop",
                                "AirLoopHVAC",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5",
                                "PERIMETER_ZN_4 ZN",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5 FAN",
                                "Fan:OnOff",
                                "PERIMETER_ZN_4 ZN PSZ-AC-5",
                                "unknown",
                                "unknown"
                            ]
                        },
                        "TableName": "Coil Connections"
                    }
                ]
            },
        ]

        added_hvac_systems, added_terminals_by_zone = t.add_heating_ventilation_system()

        expected_hvac = [{'id': 'CORE_ZN ZN PSZ-AC-1',
                          'heating_system': {'id': 'CORE_ZN ZN PSZ-AC-1-heating', 'design_capacity': 9209.104,
                                             'type': 'HEAT_PUMP', 'energy_source_type': 'ELECTRICITY',
                                             'rated_capacity': 9221.21, 'oversizing_factor': 1.000000434352977,
                                             'is_calculated_size': True, 'heating_coil_setpoint': 46.8,
                                             'efficiency_metric_values': [7.53, 6.84],
                                             'efficiency_metric_types': ['HEATING_SEASONAL_PERFORMANCE_FACTOR',
                                                                         'HEATING_SEASONAL_PERFORMANCE_FACTOR_2'],
                                             'heatpump_low_shutoff_temperature': -12.2},
                          'fan_system': {'id': 'CORE_ZN ZN PSZ-AC-1 FAN-fansystem', 'fan_control': 'CONSTANT',
                                         'supply_fans': [{'id': 'CORE_ZN ZN PSZ-AC-1 FAN', 'design_airflow': 0.37,
                                                          'is_airflow_calculated': True,
                                                          'design_electric_power': 415.54,
                                                          'design_pressure_rise': 622.72, 'total_efficiency': 0.56,
                                                          'motor_efficiency': 0.85,
                                                          'motor_heat_to_airflow_fraction': 1.0,
                                                          'motor_heat_to_zone_fraction': 0.0,
                                                          'motor_location_zone': 'N/A',
                                                          'specification_method': 'SIMPLE'}]}},
                         {'id': 'PERIMETER_ZN_1 ZN PSZ-AC-2',
                          'heating_system': {'id': 'PERIMETER_ZN_1 ZN PSZ-AC-2-heating', 'design_capacity': 8521.475,
                                             'type': 'HEAT_PUMP', 'energy_source_type': 'ELECTRICITY',
                                             'rated_capacity': 8532.67, 'oversizing_factor': 0.9999994132474641,
                                             'is_calculated_size': True, 'heating_coil_setpoint': 46.8,
                                             'efficiency_metric_values': [7.51, 6.84],
                                             'efficiency_metric_types': ['HEATING_SEASONAL_PERFORMANCE_FACTOR',
                                                                         'HEATING_SEASONAL_PERFORMANCE_FACTOR_2'],
                                             'heatpump_low_shutoff_temperature': -12.2},
                          'fan_system': {'id': 'PERIMETER_ZN_1 ZN PSZ-AC-2 FAN-fansystem', 'fan_control': 'CONSTANT',
                                         'supply_fans': [
                                             {'id': 'PERIMETER_ZN_1 ZN PSZ-AC-2 FAN', 'design_airflow': 0.34,
                                              'is_airflow_calculated': True,
                                              'design_electric_power': 384.51, 'design_pressure_rise': 622.72,
                                              'total_efficiency': 0.56, 'motor_efficiency': 0.85,
                                              'motor_heat_to_airflow_fraction': 1.0, 'motor_heat_to_zone_fraction': 0.0,
                                              'motor_location_zone': 'N/A', 'specification_method': 'SIMPLE'}]}},
                         {'id': 'PERIMETER_ZN_2 ZN PSZ-AC-3',
                          'heating_system': {'id': 'PERIMETER_ZN_2 ZN PSZ-AC-3-heating', 'design_capacity': 7154.994,
                                             'type': 'HEAT_PUMP', 'energy_source_type': 'ELECTRICITY',
                                             'rated_capacity': 7164.4, 'oversizing_factor': 1.000000559050397,
                                             'is_calculated_size': True, 'heating_coil_setpoint': 46.8,
                                             'efficiency_metric_values': [7.51, 6.84],
                                             'efficiency_metric_types': ['HEATING_SEASONAL_PERFORMANCE_FACTOR',
                                                                         'HEATING_SEASONAL_PERFORMANCE_FACTOR_2'],
                                             'heatpump_low_shutoff_temperature': -12.2},
                          'fan_system': {'id': 'PERIMETER_ZN_2 ZN PSZ-AC-3 FAN-fansystem', 'fan_control': 'CONSTANT',
                                         'supply_fans': [
                                             {'id': 'PERIMETER_ZN_2 ZN PSZ-AC-3 FAN', 'design_airflow': 0.29,
                                              'is_airflow_calculated': True,
                                              'design_electric_power': 322.85, 'design_pressure_rise': 622.72,
                                              'total_efficiency': 0.56, 'motor_efficiency': 0.85,
                                              'motor_heat_to_airflow_fraction': 1.0, 'motor_heat_to_zone_fraction': 0.0,
                                              'motor_location_zone': 'N/A', 'specification_method': 'SIMPLE'}]}},
                         {'id': 'PERIMETER_ZN_3 ZN PSZ-AC-4',
                          'heating_system': {'id': 'PERIMETER_ZN_3 ZN PSZ-AC-4-heating', 'design_capacity': 7943.433,
                                             'type': 'HEAT_PUMP', 'energy_source_type': 'ELECTRICITY',
                                             'rated_capacity': 7953.87, 'oversizing_factor': 1.0000003776706032,
                                             'is_calculated_size': True, 'heating_coil_setpoint': 46.8,
                                             'efficiency_metric_values': [7.5, 6.84],
                                             'efficiency_metric_types': ['HEATING_SEASONAL_PERFORMANCE_FACTOR',
                                                                         'HEATING_SEASONAL_PERFORMANCE_FACTOR_2'],
                                             'heatpump_low_shutoff_temperature': -12.2},
                          'fan_system': {'id': 'PERIMETER_ZN_3 ZN PSZ-AC-4 FAN-fansystem', 'fan_control': 'CONSTANT',
                                         'supply_fans': [
                                             {'id': 'PERIMETER_ZN_3 ZN PSZ-AC-4 FAN', 'design_airflow': 0.32,
                                              'is_airflow_calculated': True,
                                              'design_electric_power': 358.43, 'design_pressure_rise': 622.72,
                                              'total_efficiency': 0.56, 'motor_efficiency': 0.85,
                                              'motor_heat_to_airflow_fraction': 1.0, 'motor_heat_to_zone_fraction': 0.0,
                                              'motor_location_zone': 'N/A', 'specification_method': 'SIMPLE'}]}},
                         {'id': 'PERIMETER_ZN_4 ZN PSZ-AC-5',
                          'heating_system': {'id': 'PERIMETER_ZN_4 ZN PSZ-AC-5-heating', 'design_capacity': 8664.576,
                                             'type': 'HEAT_PUMP', 'energy_source_type': 'ELECTRICITY',
                                             'rated_capacity': 8675.96, 'oversizing_factor': 0.9999995383503874,
                                             'is_calculated_size': True, 'heating_coil_setpoint': 46.8,
                                             'efficiency_metric_values': [7.52, 6.84],
                                             'efficiency_metric_types': ['HEATING_SEASONAL_PERFORMANCE_FACTOR',
                                                                         'HEATING_SEASONAL_PERFORMANCE_FACTOR_2'],
                                             'heatpump_low_shutoff_temperature': -12.2},
                          'fan_system': {'id': 'PERIMETER_ZN_4 ZN PSZ-AC-5 FAN-fansystem', 'fan_control': 'CONSTANT',
                                         'supply_fans': [
                                             {'id': 'PERIMETER_ZN_4 ZN PSZ-AC-5 FAN', 'design_airflow': 0.35,
                                              'is_airflow_calculated': True,
                                              'design_electric_power': 390.97, 'design_pressure_rise': 622.72,
                                              'total_efficiency': 0.56, 'motor_efficiency': 0.85,
                                              'motor_heat_to_airflow_fraction': 1.0, 'motor_heat_to_zone_fraction': 0.0,
                                              'motor_location_zone': 'N/A', 'specification_method': 'SIMPLE'}]}}]

        expected_terminals = {'CORE_ZN ZN': [
            {'id': 'ADU CORE_ZN ZN PSZ-AC-1 DIFFUSER', 'type': 'CONSTANT_AIR_VOLUME', 'heating_source': 'NONE',
             'cooling_source': 'NONE', 'served_by_heating_ventilating_air_conditioning_system': 'CORE_ZN ZN PSZ-AC-1',
             'primary_airflow': 370.0, 'supply_design_heating_setpoint_temperature': 50.0,
             'supply_design_cooling_setpoint_temperature': 12.78, 'minimum_airflow': 110.0,
             'minimum_outdoor_airflow': 60.0, 'heating_capacity': 1270.47, 'cooling_capacity': 4058.82}],
            'PERIMETER_ZN_1 ZN': [
                {'id': 'ADU PERIMETER_ZN_1 ZN PSZ-AC-2 DIFFUSER', 'type': 'CONSTANT_AIR_VOLUME',
                 'heating_source': 'NONE', 'cooling_source': 'NONE',
                 'served_by_heating_ventilating_air_conditioning_system': 'PERIMETER_ZN_1 ZN PSZ-AC-2',
                 'primary_airflow': 340.0, 'supply_design_heating_setpoint_temperature': 50.0,
                 'supply_design_cooling_setpoint_temperature': 12.78, 'minimum_airflow': 90.0,
                 'minimum_outdoor_airflow': 50.0, 'heating_capacity': 3729.13,
                 'cooling_capacity': 3755.63}], 'PERIMETER_ZN_2 ZN': [
                {'id': 'ADU PERIMETER_ZN_2 ZN PSZ-AC-3 DIFFUSER', 'type': 'CONSTANT_AIR_VOLUME',
                 'heating_source': 'NONE', 'cooling_source': 'NONE',
                 'served_by_heating_ventilating_air_conditioning_system': 'PERIMETER_ZN_2 ZN PSZ-AC-3',
                 'primary_airflow': 290.0, 'supply_design_heating_setpoint_temperature': 50.0,
                 'supply_design_cooling_setpoint_temperature': 12.78, 'minimum_airflow': 50.0,
                 'minimum_outdoor_airflow': 30.0, 'heating_capacity': 2272.61, 'cooling_capacity': 3153.59}],
            'PERIMETER_ZN_3 ZN': [
                {'id': 'ADU PERIMETER_ZN_3 ZN PSZ-AC-4 DIFFUSER', 'type': 'CONSTANT_AIR_VOLUME',
                 'heating_source': 'NONE', 'cooling_source': 'NONE',
                 'served_by_heating_ventilating_air_conditioning_system': 'PERIMETER_ZN_3 ZN PSZ-AC-4',
                 'primary_airflow': 320.0, 'supply_design_heating_setpoint_temperature': 50.0,
                 'supply_design_cooling_setpoint_temperature': 12.78, 'minimum_airflow': 90.0,
                 'minimum_outdoor_airflow': 50.0, 'heating_capacity': 3761.15,
                 'cooling_capacity': 3501.01}], 'PERIMETER_ZN_4 ZN': [
                {'id': 'ADU PERIMETER_ZN_4 ZN PSZ-AC-5 DIFFUSER', 'type': 'CONSTANT_AIR_VOLUME',
                 'heating_source': 'NONE', 'cooling_source': 'NONE',
                 'served_by_heating_ventilating_air_conditioning_system': 'PERIMETER_ZN_4 ZN PSZ-AC-5',
                 'primary_airflow': 350.0, 'supply_design_heating_setpoint_temperature': 50.0,
                 'supply_design_cooling_setpoint_temperature': 12.78, 'minimum_airflow': 50.0,
                 'minimum_outdoor_airflow': 30.0, 'heating_capacity': 2272.61, 'cooling_capacity': 3818.87}]}

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
                     'speed_control': 'FIXED_SPEED', 'design_flow': 66.094, 'is_flow_calculated': True},
                    {'id': '90.1-PRM-2019 WATERCOOLED  ROTARY SCREW CHILLER 0 PRIMARY PUMP',
                     'loop_or_piping': 'CHILLED WATER LOOP_PRIMARY', 'specification_method': 'SIMPLE',
                     'design_electric_power': 4190.42, 'design_head': 44260.44, 'motor_efficiency': 0.9,
                     'speed_control': 'FIXED_SPEED', 'design_flow': 66.094, 'is_flow_calculated': True},
                    {'id': 'CHILLED WATER LOOP PUMP', 'loop_or_piping': 'CHILLED WATER LOOP',
                     'specification_method': 'SIMPLE', 'design_electric_power': 3479.58, 'design_head': 134508.01,
                     'motor_efficiency': 0.9, 'speed_control': 'VARIABLE_SPEED', 'design_flow': 18.16,
                     'is_flow_calculated': True},
                    {'id': 'CONDENSER WATER LOOP CONSTANT PUMP BANK OF 2', 'loop_or_piping': 'CONDENSER WATER LOOP',
                     'specification_method': 'SIMPLE', 'design_electric_power': 63518.6, 'design_head': 219868.07,
                     'motor_efficiency': 0.94, 'speed_control': 'VARIABLE_SPEED', 'design_flow': 210.916,
                     'is_flow_calculated': True},
                    {'id': 'MAIN SERVICE WATER LOOP CIRCULATOR PUMP', 'loop_or_piping': 'SERVICE WATER HEATING LOOP',
                     'specification_method': 'SIMPLE', 'design_electric_power': 20.4, 'design_head': 29891.0,
                     'motor_efficiency': 0.82, 'speed_control': 'FIXED_SPEED', 'design_flow': 0.439,
                     'is_flow_calculated': True}]

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
                     'design_water_flowrate': 20.0, 'leaving_water_setpoint_temperature': 0.0, 'approach': 12.0,
                     'type': 'DRY_COOLER', 'fluid': 'OTHER', 'fan_speed_control': 'TWO_SPEED'}]

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
            {'auxiliary_power': 0.0, 'design_capacity': 1891644.33, 'efficiency_metric_types': ['THERMAL'],
             'efficiency_metric_values': [0.75], 'energy_source_type': 'NATURAL_GAS',
             'id': 'BOILER 5939KBTU/HR 0.75 THERMAL EFF', 'loop': 'HOT WATER LOOP', 'minimum_load_ratio': 0.0,
             'rated_capacity': 1891644.33},
            {'auxiliary_power': 0.0, 'design_capacity': 715840.29, 'efficiency_metric_types': ['THERMAL'],
             'efficiency_metric_values': [0.75], 'energy_source_type': 'NATURAL_GAS',
             'id': 'HEAT PUMP LOOP SUPPLEMENTAL BOILER 2669KBTU/HR 0.75 THERMAL EFF', 'loop': 'HEAT PUMP LOOP',
             'minimum_load_ratio': 0.0, 'rated_capacity': 715840.29}]

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
                     'part_load_efficiency_metric': 'INTEGRATED_PART_LOAD_VALUE',
                     'is_chilled_water_pump_interlocked': False, 'is_condenser_water_pump_interlocked': False},
                    {'id': '90.1-2004 WATERCOOLED  CENTRIFUGAL CHILLER 1 416TONS 0.6KW/TON',
                     'cooling_loop': 'CHILLED WATER LOOP', 'condensing_loop': 'CONDENSER WATER LOOP',
                     'energy_source_type': 'ELECTRICITY', 'design_capacity': 1762283.32, 'rated_capacity': 1762283.32,
                     'rated_entering_condenser_temperature': 35.0, 'rated_leaving_evaporator_temperature': 6.67,
                     'minimum_load_ratio': 0.0, 'design_flow_evaporator': 74.82, 'design_flow_condenser': 87.82,
                     'design_entering_condenser_temperature': 35.0, 'design_leaving_evaporator_temperature': 6.67,
                     'full_load_efficiency': 6.1, 'part_load_efficiency': 6.88,
                     'part_load_efficiency_metric': 'INTEGRATED_PART_LOAD_VALUE',
                     'is_chilled_water_pump_interlocked': False, 'is_condenser_water_pump_interlocked': False,
                     'heat_recovery_loop': 'HeatRecoveryLoop1', 'heat_recovery_fraction': 0.67}]
        self.assertEqual(added_chillers, expected)

    def test_gather_equipment_fans(self):
        t = self.set_minimal_files()

        # example from large_office_cz2-tampa_baseline_final.json
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
                            "Motor Loss Zone Name",
                            "Airloop Name"
                        ],
                        "Rows": {
                            "BASEMENT STORY 0 VAV_PFP_BOXES (SYS8) FAN": [
                                "Fan:VariableVolume",
                                "0.64",
                                "1363.04",
                                "7.69",
                                "16476.98",
                                "2141.35",
                                "1.00",
                                "1.17",
                                "VAV System Fans",
                                "TAMPA-MACDILL.AFB_FL_USA ANN CLG .4% CONDNS DB=>MWB",
                                "8/21 08:20:00",
                                "N/A",
                                "Yes",
                                "0.92",
                                "0.00",
                                "N/A",
                                "BASEMENT STORY 0 VAV_PFP_BOXES (SYS8)"
                            ],
                            "BASEMENT ZN PFP TERM FAN": [
                                "Fan:ConstantVolume",
                                "0.49",
                                "365.09",
                                "7.67",
                                "5688.78",
                                "741.68",
                                "1.00",
                                "1.11",
                                "General",
                                "TAMPA-MACDILL.AFB_FL_USA ANN CLG .4% CONDNS DB=>MWB",
                                "8/21 08:00:00",
                                "N/A",
                                "Yes",
                                "0.90",
                                "0.00",
                                "N/A",
                                "N/A"
                            ],
                            "CORE_BOTTOM ZN PFP TERM FAN": [
                                "Fan:ConstantVolume",
                                "0.49",
                                "365.09",
                                "7.94",
                                "5888.98",
                                "741.68",
                                "1.00",
                                "1.11",
                                "General",
                                "TAMPA-MACDILL.AFB_FL_USA ANN CLG .4% CONDNS DB=>MWB",
                                "8/21 08:00:00",
                                "N/A",
                                "Yes",
                                "0.90",
                                "0.00",
                                "N/A",
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
                                "0.00",
                                "N/A",
                                "DATACENTER_BASEMENT_ZN_6 ZN PSZ-VAV"
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
                                "0.00",
                                "N/A",
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
            {'design_airflow': 7.69, 'is_airflow_calculated': True, 'design_electric_power': 16476.98,
             'design_pressure_rise': 1363.04, 'total_efficiency': 0.64, 'motor_efficiency': 0.92,
             'motor_heat_to_airflow_fraction': 1.0, 'motor_heat_to_zone_fraction': 0.0, 'motor_location_zone': 'N/A'},
            {'type': 'Fan:VariableVolume', 'fan_energy_index': 1.17, 'purpose': 'N/A',
             'airloop_name': 'BASEMENT STORY 0 VAV_PFP_BOXES (SYS8)'}), 'BASEMENT ZN PFP TERM FAN': (
            {'design_airflow': 7.67, 'is_airflow_calculated': True, 'design_electric_power': 5688.78,
             'design_pressure_rise': 365.09, 'total_efficiency': 0.49, 'motor_efficiency': 0.9,
             'motor_heat_to_airflow_fraction': 1.0, 'motor_heat_to_zone_fraction': 0.0, 'motor_location_zone': 'N/A'},
            {'type': 'Fan:ConstantVolume', 'fan_energy_index': 1.11, 'purpose': 'N/A', 'airloop_name': 'N/A'}),
            'CORE_BOTTOM ZN PFP TERM FAN': (
                {'design_airflow': 7.94, 'is_airflow_calculated': True,
                 'design_electric_power': 5888.98, 'design_pressure_rise': 365.09, 'total_efficiency': 0.49,
                 'motor_efficiency': 0.9, 'motor_heat_to_airflow_fraction': 1.0, 'motor_heat_to_zone_fraction': 0.0,
                 'motor_location_zone': 'N/A'},
                {'type': 'Fan:ConstantVolume', 'fan_energy_index': 1.11, 'purpose': 'N/A', 'airloop_name': 'N/A'}),
            'DATACENTER_BASEMENT_ZN_6 ZN PSZ-VAV FAN': (
                {'design_airflow': 30.36, 'is_airflow_calculated': True,
                 'design_electric_power': 0.0, 'design_pressure_rise': 0.0, 'total_efficiency': 0.57,
                 'motor_efficiency': 0.94, 'motor_heat_to_airflow_fraction': 1.0,
                 'motor_heat_to_zone_fraction': 0.0, 'motor_location_zone': 'N/A'},
                {'type': 'Fan:VariableVolume', 'fan_energy_index': 0.0, 'purpose': 'N/A',
                 'airloop_name': 'DATACENTER_BASEMENT_ZN_6 ZN PSZ-VAV'}), 'PERIMETER_BOT_ZN_2 ZN PFP TERM FAN': (
                {'design_airflow': 1.53, 'is_airflow_calculated': True, 'design_electric_power': 1137.67,
                 'design_pressure_rise': 342.66, 'total_efficiency': 0.46, 'motor_efficiency': 0.84,
                 'motor_heat_to_airflow_fraction': 1.0, 'motor_heat_to_zone_fraction': 0.0,
                 'motor_location_zone': 'N/A'},
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

        # test example extracted from SmallOffice-90.1-2013-ASHRAE 169-2013-5B-no_user_data-remove_transformer.json
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
                            "Minimum Outdoor Dry-Bulb Temperature for Compressor Operation [C]",
                            "Supplemental Heat High Shutoff Temperature [C]",
                            "Airloop Name"
                        ],
                        "Rows": {
                            "CORE_ZN ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "9507.0",
                                "5231.3",
                                "7.53",
                                "4",
                                "-12.20",
                                "4.44",
                                "N/A"
                            ],
                            "PERIMETER_ZN_1 ZN HP HTG COIL 30 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8797.2",
                                "4840.7",
                                "7.51",
                                "4",
                                "-12.20",
                                "4.44",
                                "N/A"
                            ],
                            "PERIMETER_ZN_2 ZN HP HTG COIL 25 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "7386.5",
                                "4064.5",
                                "7.51",
                                "4",
                                "-12.20",
                                "4.44",
                                "N/A"
                            ],
                            "PERIMETER_ZN_3 ZN HP HTG COIL 28 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8200.4",
                                "4512.3",
                                "7.50",
                                "4",
                                "-12.20",
                                "4.44",
                                "N/A"
                            ],
                            "PERIMETER_ZN_4 ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8944.9",
                                "4922.0",
                                "7.52",
                                "4",
                                "-12.20",
                                "4.44",
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
                            "Region Number",
                            "Minimum Outdoor Dry-Bulb Temperature for Compressor Operation [C]",
                            "Airloop Name"
                        ],
                        "Rows": {
                            "CORE_ZN ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "9507.0",
                                "5231.3",
                                "6.84",
                                "4",
                                "-12.20",
                                "N/A"
                            ],
                            "PERIMETER_ZN_1 ZN HP HTG COIL 30 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8797.2",
                                "4840.7",
                                "6.84",
                                "4",
                                "-12.20",
                                "N/A"
                            ],
                            "PERIMETER_ZN_2 ZN HP HTG COIL 25 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "7386.5",
                                "4064.5",
                                "6.84",
                                "4",
                                "-12.20",
                                "N/A"
                            ],
                            "PERIMETER_ZN_3 ZN HP HTG COIL 28 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8200.4",
                                "4512.3",
                                "6.84",
                                "4",
                                "-12.20",
                                "N/A"
                            ],
                            "PERIMETER_ZN_4 ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "8944.9",
                                "4922.0",
                                "6.84",
                                "4",
                                "-12.20",
                                "N/A"
                            ]
                        },
                        "TableName": "DX Heating Coils AHRI 2023"
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
                                "9209.10",
                                "3.36",
                                "No",
                                "CORE_ZN ZN PSZ-AC-1",
                                "N/A"
                            ],
                            "CORE_ZN ZN PSZ-AC-1 GAS BACKUP HTG COIL 31KBTU/HR 0.8 THERMAL EFF": [
                                "Coil:Heating:Fuel",
                                "",
                                "9209.10",
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
                                "7154.99",
                                "3.36",
                                "No",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "N/A"
                            ],
                            "PERIMETER_ZN_2 ZN PSZ-AC-3 GAS BACKUP HTG COIL 25KBTU/HR 0.8 THERMAL EFF": [
                                "Coil:Heating:Fuel",
                                "",
                                "7154.99",
                                "0.80",
                                "Yes",
                                "PERIMETER_ZN_2 ZN PSZ-AC-3",
                                "N/A"
                            ],
                            "PERIMETER_ZN_3 ZN HP HTG COIL 28 CLG KBTU/HR 8.0HSPF": [
                                "Coil:Heating:DX:SingleSpeed",
                                "",
                                "7943.43",
                                "3.36",
                                "No",
                                "PERIMETER_ZN_3 ZN PSZ-AC-4",
                                "N/A"
                            ],
                            "PERIMETER_ZN_3 ZN PSZ-AC-4 GAS BACKUP HTG COIL 28KBTU/HR 0.8 THERMAL EFF": [
                                "Coil:Heating:Fuel",
                                "",
                                "7943.43",
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
                                                                      'HSPF2': 6.84, 'Region Number': '4'},
                    'CORE_ZN ZN PSZ-AC-1 GAS BACKUP HTG COIL 31KBTU/HR 0.8 THERMAL EFF': {'type': 'Coil:Heating:Fuel',
                                                                                          'used_as_sup_heat': True,
                                                                                          'nominal_eff': 0.8},
                    'PERIMETER_ZN_1 ZN HP HTG COIL 30 CLG KBTU/HR 8.0HSPF': {'type': 'Coil:Heating:DX:SingleSpeed',
                                                                             'used_as_sup_heat': False,
                                                                             'nominal_eff': 3.36, 'HSPF': 7.51,
                                                                             'HSPF_region': '4',
                                                                             'minimum_temperature_compressor': -12.2,
                                                                             'HSPF2': 6.84, 'Region Number': '4'},
                    'PERIMETER_ZN_1 ZN PSZ-AC-2 GAS BACKUP HTG COIL 30KBTU/HR 0.8 THERMAL EFF': {
                        'type': 'Coil:Heating:Fuel', 'used_as_sup_heat': True, 'nominal_eff': 0.8},
                    'PERIMETER_ZN_2 ZN HP HTG COIL 25 CLG KBTU/HR 8.0HSPF': {'type': 'Coil:Heating:DX:SingleSpeed',
                                                                             'used_as_sup_heat': False,
                                                                             'nominal_eff': 3.36, 'HSPF': 7.51,
                                                                             'HSPF_region': '4',
                                                                             'minimum_temperature_compressor': -12.2,
                                                                             'HSPF2': 6.84, 'Region Number': '4'},
                    'PERIMETER_ZN_2 ZN PSZ-AC-3 GAS BACKUP HTG COIL 25KBTU/HR 0.8 THERMAL EFF': {
                        'type': 'Coil:Heating:Fuel', 'used_as_sup_heat': True, 'nominal_eff': 0.8},
                    'PERIMETER_ZN_3 ZN HP HTG COIL 28 CLG KBTU/HR 8.0HSPF': {'type': 'Coil:Heating:DX:SingleSpeed',
                                                                             'used_as_sup_heat': False,
                                                                             'nominal_eff': 3.36, 'HSPF': 7.5,
                                                                             'HSPF_region': '4',
                                                                             'minimum_temperature_compressor': -12.2,
                                                                             'HSPF2': 6.84, 'Region Number': '4'},
                    'PERIMETER_ZN_3 ZN PSZ-AC-4 GAS BACKUP HTG COIL 28KBTU/HR 0.8 THERMAL EFF': {
                        'type': 'Coil:Heating:Fuel', 'used_as_sup_heat': True, 'nominal_eff': 0.8},
                    'PERIMETER_ZN_4 ZN HP HTG COIL 31 CLG KBTU/HR 8.0HSPF': {'type': 'Coil:Heating:DX:SingleSpeed',
                                                                             'used_as_sup_heat': False,
                                                                             'nominal_eff': 3.36, 'HSPF': 7.52,
                                                                             'HSPF_region': '4',
                                                                             'minimum_temperature_compressor': -12.2,
                                                                             'HSPF2': 6.84, 'Region Number': '4'},
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
                                "9209.10",
                                "6456.35",
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
                                "7154.99",
                                "5016.25",
                                "2138.75",
                                "0.70",
                                "4.12",
                                "",
                                ""
                            ],
                            "PERIMETER_ZN_3 ZN PSZ-AC-4 1SPD DX HP CLG COIL 28KBTU/HR 14.0SEER": [
                                "Coil:Cooling:DX:SingleSpeed",
                                "",
                                "7943.43",
                                "5569.01",
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
                            "Standard Rated Net Cooling Capacity [W][2]",
                            "Standard Rating Net COP [W/W][2]",
                            "EER [Btu/W-h][2]",
                            "SEER User [Btu/W-h][2,3]",
                            "SEER Standard [Btu/W-h][2,3]",
                            "IEER [Btu/W-h][2]"
                        ],
                        "Rows": {
                            "CORE_ZN ZN PSZ-AC-1 1SPD DX HP CLG COIL 31KBTU/HR 14.0SEER": [
                                "",
                                "8916.5",
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
                            "Standard Rated Net Cooling Capacity [W][2]",
                            "Standard Rating Net COP2 [W/W][2,4]",
                            "EER2 [Btu/W-h][2,4]",
                            "SEER User [Btu/W-h][2,3]",
                            "SEER2 Standard [Btu/W-h][2,3]",
                            "IEER [Btu/W-h][2]"
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
                                "7639.5",
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

    def test_gather_coil_connections(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {
                "For": "Entire Facility",
                "ReportName": "CoilSizingDetails",
                "Tables": [
                    {
                        "Cols": [
                            "Coil Name",
                            "Coil Type",
                            "Coil Location",
                            "HVAC Type",
                            "HVAC Name",
                            "Zone Name(s)",
                            "Supply Fan Name for HVAC",
                            "Supply Fan Type for HVAC",
                            "Airloop Name",
                            "Plant Name for Coil",
                            "Plant Loop Name"
                        ],
                        "Rows": {
                            "BASEMENT ZN REHEAT COIL": [
                                "BASEMENT ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU BASEMENT ZN VAV TERMINAL",
                                "BASEMENT ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "CAV_BAS CLG COIL": [
                                "CAV_BAS CLG COIL",
                                "Coil:Cooling:Water",
                                "AirLoop",
                                "AirLoopHVAC",
                                "CAV_BAS",
                                "BASEMENT ZN",
                                "CAV_BAS FAN",
                                "Fan:ConstantVolume",
                                "CAV_BAS",
                                "CHILLED WATER LOOP",
                                "CHILLED WATER LOOP"
                            ],
                            "CAV_BAS MAIN HTG COIL": [
                                "CAV_BAS MAIN HTG COIL",
                                "Coil:Heating:Water",
                                "AirLoop",
                                "AirLoopHVAC",
                                "CAV_BAS",
                                "BASEMENT ZN",
                                "CAV_BAS FAN",
                                "Fan:ConstantVolume",
                                "CAV_BAS",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "CORE_BOTTOM ZN REHEAT COIL": [
                                "CORE_BOTTOM ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU CORE_BOTTOM ZN VAV TERMINAL",
                                "CORE_BOTTOM ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "CORE_MID ZN REHEAT COIL": [
                                "CORE_MID ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU CORE_MID ZN VAV TERMINAL",
                                "CORE_MID ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "CORE_TOP ZN REHEAT COIL": [
                                "CORE_TOP ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU CORE_TOP ZN VAV TERMINAL",
                                "CORE_TOP ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC ELECTRIC BACKUP HTG COIL": [
                                "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC ELECTRIC BACKUP HTG COIL",
                                "COIL:HEATING:ELECTRIC",
                                "AirLoop",
                                "AirLoopHVAC",
                                "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC DATA CENTER",
                                "DATACENTER_BASEMENT_ZN_6 ZN",
                                "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC FAN",
                                "Fan:OnOff",
                                "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC DATA CENTER",
                                "unknown",
                                "unknown"
                            ],
                            "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC WATER-TO-AIR HP CLG COIL": [
                                "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC WATER-TO-AIR HP CLG COIL",
                                "COIL:COOLING:WATERTOAIRHEATPUMP:EQUATIONFIT",
                                "AirLoop",
                                "AirLoopHVAC",
                                "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC DATA CENTER",
                                "DATACENTER_BASEMENT_ZN_6 ZN",
                                "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC FAN",
                                "Fan:OnOff",
                                "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC DATA CENTER",
                                "unknown",
                                "unknown"
                            ],
                            "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC WATER-TO-AIR HP HTG COIL 2215 CLG KBTU/HR 4.2COPH": [
                                "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC WATER-TO-AIR HP HTG COIL 2215 CLG KBTU/HR 4.2COPH",
                                "COIL:HEATING:WATERTOAIRHEATPUMP:EQUATIONFIT",
                                "AirLoop",
                                "AirLoopHVAC",
                                "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC DATA CENTER",
                                "DATACENTER_BASEMENT_ZN_6 ZN",
                                "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC FAN",
                                "Fan:OnOff",
                                "DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC DATA CENTER",
                                "unknown",
                                "unknown"
                            ],
                            "DATACENTER_BOT_ZN_6 ZN PSZ-AC ELECTRIC BACKUP HTG COIL": [
                                "DATACENTER_BOT_ZN_6 ZN PSZ-AC ELECTRIC BACKUP HTG COIL",
                                "COIL:HEATING:ELECTRIC",
                                "AirLoop",
                                "AirLoopHVAC",
                                "DATACENTER_BOT_ZN_6 ZN PSZ-AC DATA CENTER",
                                "DATACENTER_BOT_ZN_6 ZN",
                                "DATACENTER_BOT_ZN_6 ZN PSZ-AC FAN",
                                "Fan:OnOff",
                                "DATACENTER_BOT_ZN_6 ZN PSZ-AC DATA CENTER",
                                "unknown",
                                "unknown"
                            ],
                            "DATACENTER_BOT_ZN_6 ZN PSZ-AC WATER-TO-AIR HP CLG COIL 52KBTU/HR 12.0EER": [
                                "DATACENTER_BOT_ZN_6 ZN PSZ-AC WATER-TO-AIR HP CLG COIL 52KBTU/HR 12.0EER",
                                "COIL:COOLING:WATERTOAIRHEATPUMP:EQUATIONFIT",
                                "AirLoop",
                                "AirLoopHVAC",
                                "DATACENTER_BOT_ZN_6 ZN PSZ-AC DATA CENTER",
                                "DATACENTER_BOT_ZN_6 ZN",
                                "DATACENTER_BOT_ZN_6 ZN PSZ-AC FAN",
                                "Fan:OnOff",
                                "DATACENTER_BOT_ZN_6 ZN PSZ-AC DATA CENTER",
                                "unknown",
                                "unknown"
                            ],
                            "DATACENTER_BOT_ZN_6 ZN PSZ-AC WATER-TO-AIR HP HTG COIL 52 CLG KBTU/HR 4.2COPH": [
                                "DATACENTER_BOT_ZN_6 ZN PSZ-AC WATER-TO-AIR HP HTG COIL 52 CLG KBTU/HR 4.2COPH",
                                "COIL:HEATING:WATERTOAIRHEATPUMP:EQUATIONFIT",
                                "AirLoop",
                                "AirLoopHVAC",
                                "DATACENTER_BOT_ZN_6 ZN PSZ-AC DATA CENTER",
                                "DATACENTER_BOT_ZN_6 ZN",
                                "DATACENTER_BOT_ZN_6 ZN PSZ-AC FAN",
                                "Fan:OnOff",
                                "DATACENTER_BOT_ZN_6 ZN PSZ-AC DATA CENTER",
                                "unknown",
                                "unknown"
                            ],
                            "DATACENTER_MID_ZN_6 ZN PSZ-AC ELECTRIC BACKUP HTG COIL": [
                                "DATACENTER_MID_ZN_6 ZN PSZ-AC ELECTRIC BACKUP HTG COIL",
                                "COIL:HEATING:ELECTRIC",
                                "AirLoop",
                                "AirLoopHVAC",
                                "DATACENTER_MID_ZN_6 ZN PSZ-AC DATA CENTER",
                                "DATACENTER_MID_ZN_6 ZN",
                                "DATACENTER_MID_ZN_6 ZN PSZ-AC FAN",
                                "Fan:OnOff",
                                "DATACENTER_MID_ZN_6 ZN PSZ-AC DATA CENTER",
                                "unknown",
                                "unknown"
                            ],
                            "DATACENTER_MID_ZN_6 ZN PSZ-AC WATER-TO-AIR HP CLG COIL": [
                                "DATACENTER_MID_ZN_6 ZN PSZ-AC WATER-TO-AIR HP CLG COIL",
                                "COIL:COOLING:WATERTOAIRHEATPUMP:EQUATIONFIT",
                                "AirLoop",
                                "AirLoopHVAC",
                                "DATACENTER_MID_ZN_6 ZN PSZ-AC DATA CENTER",
                                "DATACENTER_MID_ZN_6 ZN",
                                "DATACENTER_MID_ZN_6 ZN PSZ-AC FAN",
                                "Fan:OnOff",
                                "DATACENTER_MID_ZN_6 ZN PSZ-AC DATA CENTER",
                                "unknown",
                                "unknown"
                            ],
                            "DATACENTER_MID_ZN_6 ZN PSZ-AC WATER-TO-AIR HP HTG COIL 454 CLG KBTU/HR 4.2COPH": [
                                "DATACENTER_MID_ZN_6 ZN PSZ-AC WATER-TO-AIR HP HTG COIL 454 CLG KBTU/HR 4.2COPH",
                                "COIL:HEATING:WATERTOAIRHEATPUMP:EQUATIONFIT",
                                "AirLoop",
                                "AirLoopHVAC",
                                "DATACENTER_MID_ZN_6 ZN PSZ-AC DATA CENTER",
                                "DATACENTER_MID_ZN_6 ZN",
                                "DATACENTER_MID_ZN_6 ZN PSZ-AC FAN",
                                "Fan:OnOff",
                                "DATACENTER_MID_ZN_6 ZN PSZ-AC DATA CENTER",
                                "unknown",
                                "unknown"
                            ],
                            "DATACENTER_TOP_ZN_6 ZN PSZ-AC ELECTRIC BACKUP HTG COIL": [
                                "DATACENTER_TOP_ZN_6 ZN PSZ-AC ELECTRIC BACKUP HTG COIL",
                                "COIL:HEATING:ELECTRIC",
                                "AirLoop",
                                "AirLoopHVAC",
                                "DATACENTER_TOP_ZN_6 ZN PSZ-AC DATA CENTER",
                                "DATACENTER_TOP_ZN_6 ZN",
                                "DATACENTER_TOP_ZN_6 ZN PSZ-AC FAN",
                                "Fan:OnOff",
                                "DATACENTER_TOP_ZN_6 ZN PSZ-AC DATA CENTER",
                                "unknown",
                                "unknown"
                            ],
                            "DATACENTER_TOP_ZN_6 ZN PSZ-AC WATER-TO-AIR HP CLG COIL 47KBTU/HR 12.0EER": [
                                "DATACENTER_TOP_ZN_6 ZN PSZ-AC WATER-TO-AIR HP CLG COIL 47KBTU/HR 12.0EER",
                                "COIL:COOLING:WATERTOAIRHEATPUMP:EQUATIONFIT",
                                "AirLoop",
                                "AirLoopHVAC",
                                "DATACENTER_TOP_ZN_6 ZN PSZ-AC DATA CENTER",
                                "DATACENTER_TOP_ZN_6 ZN",
                                "DATACENTER_TOP_ZN_6 ZN PSZ-AC FAN",
                                "Fan:OnOff",
                                "DATACENTER_TOP_ZN_6 ZN PSZ-AC DATA CENTER",
                                "unknown",
                                "unknown"
                            ],
                            "DATACENTER_TOP_ZN_6 ZN PSZ-AC WATER-TO-AIR HP HTG COIL 47 CLG KBTU/HR 4.2COPH": [
                                "DATACENTER_TOP_ZN_6 ZN PSZ-AC WATER-TO-AIR HP HTG COIL 47 CLG KBTU/HR 4.2COPH",
                                "COIL:HEATING:WATERTOAIRHEATPUMP:EQUATIONFIT",
                                "AirLoop",
                                "AirLoopHVAC",
                                "DATACENTER_TOP_ZN_6 ZN PSZ-AC DATA CENTER",
                                "DATACENTER_TOP_ZN_6 ZN",
                                "DATACENTER_TOP_ZN_6 ZN PSZ-AC FAN",
                                "Fan:OnOff",
                                "DATACENTER_TOP_ZN_6 ZN PSZ-AC DATA CENTER",
                                "unknown",
                                "unknown"
                            ],
                            "PERIMETER_BOT_ZN_1 ZN REHEAT COIL": [
                                "PERIMETER_BOT_ZN_1 ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU PERIMETER_BOT_ZN_1 ZN VAV TERMINAL",
                                "PERIMETER_BOT_ZN_1 ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "PERIMETER_BOT_ZN_2 ZN REHEAT COIL": [
                                "PERIMETER_BOT_ZN_2 ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU PERIMETER_BOT_ZN_2 ZN VAV TERMINAL",
                                "PERIMETER_BOT_ZN_2 ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "PERIMETER_BOT_ZN_3 ZN REHEAT COIL": [
                                "PERIMETER_BOT_ZN_3 ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU PERIMETER_BOT_ZN_3 ZN VAV TERMINAL",
                                "PERIMETER_BOT_ZN_3 ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "PERIMETER_BOT_ZN_4 ZN REHEAT COIL": [
                                "PERIMETER_BOT_ZN_4 ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU PERIMETER_BOT_ZN_4 ZN VAV TERMINAL",
                                "PERIMETER_BOT_ZN_4 ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "PERIMETER_MID_ZN_1 ZN REHEAT COIL": [
                                "PERIMETER_MID_ZN_1 ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU PERIMETER_MID_ZN_1 ZN VAV TERMINAL",
                                "PERIMETER_MID_ZN_1 ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "PERIMETER_MID_ZN_2 ZN REHEAT COIL": [
                                "PERIMETER_MID_ZN_2 ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU PERIMETER_MID_ZN_2 ZN VAV TERMINAL",
                                "PERIMETER_MID_ZN_2 ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "PERIMETER_MID_ZN_3 ZN REHEAT COIL": [
                                "PERIMETER_MID_ZN_3 ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU PERIMETER_MID_ZN_3 ZN VAV TERMINAL",
                                "PERIMETER_MID_ZN_3 ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "PERIMETER_MID_ZN_4 ZN REHEAT COIL": [
                                "PERIMETER_MID_ZN_4 ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU PERIMETER_MID_ZN_4 ZN VAV TERMINAL",
                                "PERIMETER_MID_ZN_4 ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "PERIMETER_TOP_ZN_1 ZN REHEAT COIL": [
                                "PERIMETER_TOP_ZN_1 ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU PERIMETER_TOP_ZN_1 ZN VAV TERMINAL",
                                "PERIMETER_TOP_ZN_1 ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "PERIMETER_TOP_ZN_2 ZN REHEAT COIL": [
                                "PERIMETER_TOP_ZN_2 ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU PERIMETER_TOP_ZN_2 ZN VAV TERMINAL",
                                "PERIMETER_TOP_ZN_2 ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "PERIMETER_TOP_ZN_3 ZN REHEAT COIL": [
                                "PERIMETER_TOP_ZN_3 ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU PERIMETER_TOP_ZN_3 ZN VAV TERMINAL",
                                "PERIMETER_TOP_ZN_3 ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "PERIMETER_TOP_ZN_4 ZN REHEAT COIL": [
                                "PERIMETER_TOP_ZN_4 ZN REHEAT COIL",
                                "COIL:HEATING:WATER",
                                "Zone Equipment",
                                "ZONEHVAC:AIRDISTRIBUTIONUNIT",
                                "ADU PERIMETER_TOP_ZN_4 ZN VAV TERMINAL",
                                "PERIMETER_TOP_ZN_4 ZN",
                                "unknown",
                                "unknown",
                                "N/A",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "VAV_BOT WITH REHEAT CLG COIL": [
                                "VAV_BOT WITH REHEAT CLG COIL",
                                "Coil:Cooling:Water",
                                "AirLoop",
                                "AirLoopHVAC",
                                "VAV_BOT WITH REHEAT",
                                "PERIMETER_BOT_ZN_1 ZN; PERIMETER_BOT_ZN_2 ZN; PERIMETER_BOT_ZN_3 ZN; "
                                "PERIMETER_BOT_ZN_4 ZN; CORE_BOTTOM ZN;",
                                "VAV_BOT WITH REHEAT FAN",
                                "Fan:VariableVolume",
                                "VAV_BOT WITH REHEAT",
                                "CHILLED WATER LOOP",
                                "CHILLED WATER LOOP"
                            ],
                            "VAV_BOT WITH REHEAT MAIN HTG COIL": [
                                "VAV_BOT WITH REHEAT MAIN HTG COIL",
                                "Coil:Heating:Water",
                                "AirLoop",
                                "AirLoopHVAC",
                                "VAV_BOT WITH REHEAT",
                                "PERIMETER_BOT_ZN_1 ZN; PERIMETER_BOT_ZN_2 ZN; PERIMETER_BOT_ZN_3 ZN; "
                                "PERIMETER_BOT_ZN_4 ZN; CORE_BOTTOM ZN;",
                                "VAV_BOT WITH REHEAT FAN",
                                "Fan:VariableVolume",
                                "VAV_BOT WITH REHEAT",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "VAV_MID WITH REHEAT CLG COIL": [
                                "VAV_MID WITH REHEAT CLG COIL",
                                "Coil:Cooling:Water",
                                "AirLoop",
                                "AirLoopHVAC",
                                "VAV_MID WITH REHEAT",
                                "PERIMETER_MID_ZN_1 ZN; PERIMETER_MID_ZN_2 ZN; PERIMETER_MID_ZN_3 ZN; "
                                "PERIMETER_MID_ZN_4 ZN; CORE_MID ZN;",
                                "VAV_MID WITH REHEAT FAN",
                                "Fan:VariableVolume",
                                "VAV_MID WITH REHEAT",
                                "CHILLED WATER LOOP",
                                "CHILLED WATER LOOP"
                            ],
                            "VAV_MID WITH REHEAT MAIN HTG COIL": [
                                "VAV_MID WITH REHEAT MAIN HTG COIL",
                                "Coil:Heating:Water",
                                "AirLoop",
                                "AirLoopHVAC",
                                "VAV_MID WITH REHEAT",
                                "PERIMETER_MID_ZN_1 ZN; PERIMETER_MID_ZN_2 ZN; PERIMETER_MID_ZN_3 ZN; "
                                "PERIMETER_MID_ZN_4 ZN; CORE_MID ZN;",
                                "VAV_MID WITH REHEAT FAN",
                                "Fan:VariableVolume",
                                "VAV_MID WITH REHEAT",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ],
                            "VAV_TOP WITH REHEAT CLG COIL": [
                                "VAV_TOP WITH REHEAT CLG COIL",
                                "Coil:Cooling:Water",
                                "AirLoop",
                                "AirLoopHVAC",
                                "VAV_TOP WITH REHEAT",
                                "PERIMETER_TOP_ZN_1 ZN; PERIMETER_TOP_ZN_2 ZN; PERIMETER_TOP_ZN_3 ZN; "
                                "PERIMETER_TOP_ZN_4 ZN; CORE_TOP ZN;",
                                "VAV_TOP WITH REHEAT FAN",
                                "Fan:VariableVolume",
                                "VAV_TOP WITH REHEAT",
                                "CHILLED WATER LOOP",
                                "CHILLED WATER LOOP"
                            ],
                            "VAV_TOP WITH REHEAT MAIN HTG COIL": [
                                "VAV_TOP WITH REHEAT MAIN HTG COIL",
                                "Coil:Heating:Water",
                                "AirLoop",
                                "AirLoopHVAC",
                                "VAV_TOP WITH REHEAT",
                                "PERIMETER_TOP_ZN_1 ZN; PERIMETER_TOP_ZN_2 ZN; PERIMETER_TOP_ZN_3 ZN; "
                                "PERIMETER_TOP_ZN_4 ZN; CORE_TOP ZN;",
                                "VAV_TOP WITH REHEAT FAN",
                                "Fan:VariableVolume",
                                "VAV_TOP WITH REHEAT",
                                "HOT WATER LOOP",
                                "HOT WATER LOOP"
                            ]
                        },
                        "TableName": "Coil Connections"
                    }
                ]
            },
        ]

        gathered_coil_connections = t.gather_coil_connections()

        expected = {'BASEMENT ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'CAV_BAS CLG COIL': {'plant_loop_name': 'CHILLED WATER LOOP'},
                    'CAV_BAS MAIN HTG COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'CORE_BOTTOM ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'CORE_MID ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'CORE_TOP ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC ELECTRIC BACKUP HTG COIL': {
                        'plant_loop_name': 'unknown'},
                    'DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC WATER-TO-AIR HP CLG COIL': {
                        'plant_loop_name': 'unknown'},
                    'DATACENTER_BASEMENT_ZN_6 ZN PSZ-AC WATER-TO-AIR HP HTG COIL 2215 CLG KBTU/HR 4.2COPH': {
                        'plant_loop_name': 'unknown'},
                    'DATACENTER_BOT_ZN_6 ZN PSZ-AC ELECTRIC BACKUP HTG COIL': {
                        'plant_loop_name': 'unknown'},
                    'DATACENTER_BOT_ZN_6 ZN PSZ-AC WATER-TO-AIR HP CLG COIL 52KBTU/HR 12.0EER': {
                        'plant_loop_name': 'unknown'},
                    'DATACENTER_BOT_ZN_6 ZN PSZ-AC WATER-TO-AIR HP HTG COIL 52 CLG KBTU/HR 4.2COPH': {
                        'plant_loop_name': 'unknown'},
                    'DATACENTER_MID_ZN_6 ZN PSZ-AC ELECTRIC BACKUP HTG COIL': {
                        'plant_loop_name': 'unknown'},
                    'DATACENTER_MID_ZN_6 ZN PSZ-AC WATER-TO-AIR HP CLG COIL': {
                        'plant_loop_name': 'unknown'},
                    'DATACENTER_MID_ZN_6 ZN PSZ-AC WATER-TO-AIR HP HTG COIL 454 CLG KBTU/HR 4.2COPH': {
                        'plant_loop_name': 'unknown'},
                    'DATACENTER_TOP_ZN_6 ZN PSZ-AC ELECTRIC BACKUP HTG COIL': {
                        'plant_loop_name': 'unknown'},
                    'DATACENTER_TOP_ZN_6 ZN PSZ-AC WATER-TO-AIR HP CLG COIL 47KBTU/HR 12.0EER': {
                        'plant_loop_name': 'unknown'},
                    'DATACENTER_TOP_ZN_6 ZN PSZ-AC WATER-TO-AIR HP HTG COIL 47 CLG KBTU/HR 4.2COPH': {
                        'plant_loop_name': 'unknown'},
                    'PERIMETER_BOT_ZN_1 ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'PERIMETER_BOT_ZN_2 ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'PERIMETER_BOT_ZN_3 ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'PERIMETER_BOT_ZN_4 ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'PERIMETER_MID_ZN_1 ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'PERIMETER_MID_ZN_2 ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'PERIMETER_MID_ZN_3 ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'PERIMETER_MID_ZN_4 ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'PERIMETER_TOP_ZN_1 ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'PERIMETER_TOP_ZN_2 ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'PERIMETER_TOP_ZN_3 ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'PERIMETER_TOP_ZN_4 ZN REHEAT COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'VAV_BOT WITH REHEAT CLG COIL': {'plant_loop_name': 'CHILLED WATER LOOP'},
                    'VAV_BOT WITH REHEAT MAIN HTG COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'VAV_MID WITH REHEAT CLG COIL': {'plant_loop_name': 'CHILLED WATER LOOP'},
                    'VAV_MID WITH REHEAT MAIN HTG COIL': {'plant_loop_name': 'HOT WATER LOOP'},
                    'VAV_TOP WITH REHEAT CLG COIL': {'plant_loop_name': 'CHILLED WATER LOOP'},
                    'VAV_TOP WITH REHEAT MAIN HTG COIL': {'plant_loop_name': 'HOT WATER LOOP'}}

        self.assertEqual(gathered_coil_connections, expected)

    def test_add_simulation_outputs(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [
            {
                "For": "Entire Facility",
                "ReportName": "AnnualBuildingUtilityPerformanceSummary",
                "Tables": [
                    {
                        "Cols": [
                            "Electricity [GJ]",
                            "Natural Gas [GJ]",
                        ],
                        "Rows": {
                            "Cooling": [
                                "12.08",
                                "0.00",
                            ],
                            "Interior Lighting": [
                                "25.61",
                                "0.00",
                            ],
                            "Total End Uses": [
                                "138.47",
                                "4.64",
                            ],
                        },
                        "TableName": "End Uses"
                    },
                ]
            },
            {
                "For": "Entire Facility",
                "ReportName": "DemandEndUseComponentsSummary",
                "Tables": [
                    {
                        "Cols": [
                            "Electricity [W]",
                            "Natural Gas [W]",
                        ],
                        "Rows": {
                            "Cooling": [
                                "42.42",
                                "0.00",
                            ],
                            "Interior Lighting": [
                                "2461.51",
                                "0.00",
                            ],
                            "Total End Uses": [
                                "14959.75",
                                "25029.93",
                            ],
                        },
                        "TableName": "End Uses"
                    },
                ]
            },
            {
                "For": "Entire Facility",
                "ReportName": "EnergyMeters",
                "Tables": [
                    {
                        "Cols": [
                            "Electricity Annual Value [GJ]",
                            "Electricity Minimum Value [W]",
                            "Timestamp of Minimum {TIMESTAMP}",
                            "Electricity Maximum Value [W]",
                            "Timestamp of Maximum {TIMESTAMP}"
                        ],
                        "Rows": {
                            "Cooling:Electricity": [
                                "12.08",
                                "0.00",
                                "01-JAN-00:15",
                                "5318.54",
                                "05-SEP-15:15"
                            ],
                            "InteriorLights:Electricity": [
                                "25.61",
                                "110.04",
                                "01-JAN-00:15",
                                "2461.51",
                                "02-JAN-16:45"
                            ],
                        },
                        "TableName": "Annual and Peak Values - Electricity"
                    },
                    {
                        "Cols": [
                            "Natural Gas Annual Value [GJ]",
                            "Natural Gas Minimum Value [W]",
                            "Timestamp of Minimum {TIMESTAMP}",
                            "Natural Gas Maximum Value [W]",
                            "Timestamp of Maximum {TIMESTAMP}"
                        ],
                        "Rows": {
                            "Heating:NaturalGas": [
                                "4.64",
                                "0.00",
                                "01-JAN-00:15",
                                "25029.93",
                                "02-JAN-06:15"
                            ],
                        },
                        "TableName": "Annual and Peak Values - Natural Gas"
                    },
                ]
            },
            {
                "For": "Entire Facility",
                "ReportName": "LEEDsummary",
                "Tables": [
                    {
                        "Cols": [
                            "Data"
                        ],
                        "Rows": {
                            "Number of hours cooling loads not met": [
                                "31.75"
                            ],
                            "Number of hours heating loads not met": [
                                "33.50"
                            ],
                            "Number of hours not met": [
                                "65.25"
                            ]
                        },
                        "TableName": "EAp2-2. Advisory Messages"
                    },
                ]
            },
            {
                "For": "Entire Facility",
                "ReportName": "SystemSummary",
                "Tables": [
                    {
                        "Cols": [
                            "During Heating [hr]",
                            "During Cooling [hr]",
                            "During Occupied Heating [hr]",
                            "During Occupied Cooling [hr]"
                        ],
                        "Rows": {
                            "CORE_ZN": [
                                "4.00",
                                "10.75",
                                "4.00",
                                "10.75"
                            ],
                            "Facility": [
                                "71.00",
                                "33.75",
                                "33.50",
                                "31.75"
                            ],
                        },
                        "TableName": "Time Setpoint Not Met"
                    }
                ]
            },
        ]

        added_project, added_instance = t.add_simulation_outputs()

        expected_project = {'id': 'output_1',
                            'performance_cost_index': -1.0,
                            'baseline_building_unregulated_energy_cost': -1.0,
                            'baseline_building_regulated_energy_cost': -1.0,
                            'baseline_building_performance_energy_cost': -1.0,
                            'total_area_weighted_building_performance_factor': -1.0,
                            'performance_cost_index_target': -1.0,
                            'total_proposed_building_energy_cost_including_renewable_energy': -1.0,
                            'total_proposed_building_energy_cost_excluding_renewable_energy': -1.0,
                            'percent_renewable_energy_savings': -1.0}

        expected_instance = {'id': 'output_instance_1',
                             'unmet_load_hours': 65.25,
                             'unmet_load_hours_heating': 33.5,
                             'unmet_occupied_load_hours_heating': 33.5,
                             'unmet_load_hours_cooling': 31.75,
                             'unmet_occupied_load_hours_cooling': 31.75,
                             'annual_source_results': [
                                 {'id': 'source_results_ELECTRICITY', 'energy_source': 'ELECTRICITY',
                                  'annual_consumption': 138.47,
                                  'annual_demand': 14959.75, 'annual_cost': -1.0},
                                 {'id': 'source_results_NATURAL_GAS', 'energy_source': 'NATURAL_GAS',
                                  'annual_consumption': 4.64,
                                  'annual_demand': 25029.93, 'annual_cost': -1.0}],
                             'building_peak_cooling_load': -1,
                             'annual_end_use_results': [
                                 {'id': 'end_use_ELECTRICITY-Cooling', 'type': 'SPACE_COOLING',
                                  'energy_source': 'ELECTRICITY',
                                  'annual_site_energy_use': 12.08,
                                  'annual_site_coincident_demand': 42.42,
                                  'annual_site_non_coincident_demand': 5318.54,
                                  'is_regulated': True},
                                 {'id': 'end_use_ELECTRICITY-Interior Lighting',
                                  'type': 'INTERIOR_LIGHTING', 'energy_source': 'ELECTRICITY',
                                  'annual_site_energy_use': 25.61,
                                  'annual_site_coincident_demand': 2461.51,
                                  'annual_site_non_coincident_demand': 2461.51,
                                  'is_regulated': True}]}

        self.assertEqual(added_project, expected_project)
        self.assertEqual(added_instance, expected_instance)

    def test_is_float(self):
        self.assertTrue(is_float('0.09'))
        self.assertTrue(is_float('1'))
        self.assertTrue(is_float('999999.999'))
        self.assertFalse(is_float('1x'))
        self.assertFalse(is_float('y11.1'))

    def test_energy_source_convert(self):
        self.assertEqual(energy_source_convert('ELECTRICITY'), 'ELECTRICITY')
        self.assertEqual(energy_source_convert('FUELOIL2'), 'FUEL_OIL')
        self.assertEqual(energy_source_convert('OTHERFUEL2'), 'OTHER')
        self.assertEqual(energy_source_convert('electricity'), 'ELECTRICITY')

    def test_heating_type_convert(self):
        self.assertEqual(heating_type_convert('COIL:HEATING:WATER'), 'FLUID_LOOP')
        self.assertEqual(heating_type_convert('COIL:HEATING:FUEL'), 'FURNACE')
        self.assertEqual(heating_type_convert('COIL:HEATING:dx:VARIABLESPEED'), 'HEAT_PUMP')

    def test_cooling_type_convert(self):
        self.assertEqual(cooling_type_convert('COIL:COOLING:WATER'), 'FLUID_LOOP')
        self.assertEqual(cooling_type_convert('COIL:COOLING:DX:VARIABLESPEED'), 'DIRECT_EXPANSION')
        self.assertEqual(cooling_type_convert('COIL:cooling:WATERTOAIRHEATPUMP:EQUATIONFIT'), 'DIRECT_EXPANSION')

    def test_source_from_coil(self):
        self.assertEqual(source_from_coil('Coil:Heating:Water'), 'OTHER')
        self.assertEqual(source_from_coil('Coil:Heating:Fuel'), 'NATURAL_GAS')
        self.assertEqual(source_from_coil('Coil:Heating:Electric'), 'ELECTRICITY')

    def test_terminal_option_convert(self):
        self.assertEqual(terminal_option_convert('AirTerminal:SingleDuct:ConstantVolume:Reheat'), 'CONSTANT_AIR_VOLUME')
        self.assertEqual(terminal_option_convert('AirTerminal:SingleDuct:VAV:NoReheat'), 'VARIABLE_AIR_VOLUME')
        self.assertEqual(terminal_option_convert('AirTerminal:SingleDuct:Mixer'), 'OTHER')

    def test_terminal_heating_source_convert(self):
        self.assertEqual(terminal_heating_source_convert('Coil:Heating:Water'), 'HOT_WATER')
        self.assertEqual(terminal_heating_source_convert('Coil:Heating:Electric'), 'ELECTRIC')
        self.assertEqual(terminal_heating_source_convert('Coil:Heating:Steam'), 'NONE')

    def test_terminal_cooling_source_convert(self):
        self.assertEqual(terminal_cooling_source_convert('n/a'), 'NONE')
        self.assertEqual(terminal_cooling_source_convert(''), 'NONE')
        self.assertEqual(terminal_cooling_source_convert('x'), 'CHILLED_WATER')

    def test_terminal_config_convert(self):
        self.assertEqual(terminal_config_convert('AirTerminal:SingleDuct:SeriesPIU:Reheat'), 'SERIES')
        self.assertEqual(terminal_config_convert('AirTerminal:SingleDuct:ParallelPIU:Reheat'), 'PARALLEL')
        self.assertEqual(terminal_config_convert('AirTerminal:SingleDuct:VAV:HeatAndCool:Reheat'), 'OTHER')

    def test_heat_rejection_type_convert(self):
        self.assertEqual(heat_rejection_type_convert('CoolingTower:TwoSpeed'), 'OPEN_CIRCUIT_COOLING_TOWER')
        self.assertEqual(heat_rejection_type_convert('EvaporativeFluidCooler:SingleSpeed'),
                         'CLOSED_CIRCUIT_COOLING_TOWER')
        self.assertEqual(heat_rejection_type_convert('FluidCooler:SingleSpeed'), 'DRY_COOLER')
        self.assertEqual(heat_rejection_type_convert('GroundHeatExchanger:System'), 'OTHER')

    def test_heat_rejection_fan_speed_convert(self):
        self.assertEqual(heat_rejection_fan_speed_convert('CoolingTower:TwoSpeed'), 'TWO_SPEED')
        self.assertEqual(heat_rejection_fan_speed_convert('CoolingTower:VariableSpeed'), 'VARIABLE_SPEED')
        self.assertEqual(heat_rejection_fan_speed_convert('EvaporativeFluidCooler:SingleSpeed'),
                         'CONSTANT')
        self.assertEqual(heat_rejection_fan_speed_convert('FluidCooler:SingleSpeed'), 'CONSTANT')
        self.assertEqual(heat_rejection_fan_speed_convert('GroundHeatExchanger:System'), 'OTHER')

    def test_get_table_single_column(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [{
            'For': 'Entire Facility',
            'ReportName': 'AnnualBuildingUtilityPerformanceSummary',
            'Tables': [
                {
                    "Cols": [
                        "Area [m2]"
                    ],
                    "Rows": {
                        "Net Conditioned Building Area": [
                            "511.16"
                        ],
                        "Total Building Area": [
                            "511.16"
                        ],
                        "Unconditioned Building Area": [
                            "0.00"
                        ]
                    },
                    "TableName": "Building Area"
                },
            ]
        }]

        table = t.get_table('AnnualBuildingUtilityPerformanceSummary', 'Building Area')

        expected = {'Cols': ['Area [m2]'],
                    'Rows': {'Net Conditioned Building Area': ['511.16'], 'Total Building Area': ['511.16'],
                             'Unconditioned Building Area': ['0.00']}, 'TableName': 'Building Area'}

        self.assertEqual(table, expected)

    def test_get_table_multi_column(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [{
            'For': 'Entire Facility',
            'ReportName': 'AnnualBuildingUtilityPerformanceSummary',
            'Tables': [
                {
                    "Cols": [
                        "Total Energy [GJ]",
                        "Energy Per Total Building Area [MJ/m2]",
                        "Energy Per Conditioned Building Area [MJ/m2]"
                    ],
                    "Rows": {
                        "Net Site Energy": [
                            "143.11",
                            "279.97",
                            "279.97"
                        ],
                        "Net Source Energy": [
                            "443.56",
                            "867.76",
                            "867.76"
                        ],
                        "Total Site Energy": [
                            "143.11",
                            "279.97",
                            "279.97"
                        ],
                        "Total Source Energy": [
                            "443.56",
                            "867.76",
                            "867.76"
                        ]
                    },
                    "TableName": "Site and Source Energy"
                },
            ]
        }]

        table = t.get_table('AnnualBuildingUtilityPerformanceSummary', 'Site and Source Energy')

        expected = {'Cols': ['Total Energy [GJ]', 'Energy Per Total Building Area [MJ/m2]',
                             'Energy Per Conditioned Building Area [MJ/m2]'],
                    'Rows': {'Net Site Energy': ['143.11', '279.97', '279.97'],
                             'Net Source Energy': ['443.56', '867.76', '867.76'],
                             'Total Site Energy': ['143.11', '279.97', '279.97'],
                             'Total Source Energy': ['443.56', '867.76', '867.76']},
                    'TableName': 'Site and Source Energy'}

        self.assertEqual(table, expected)

    def test_gather_table_into_list(self):
        t = self.set_minimal_files()

        t.json_results_object['TabularReports'] = [{
            'For': 'Entire Facility',
            'ReportName': 'AnnualBuildingUtilityPerformanceSummary',
            'Tables': [
                {
                    "Cols": [
                        "Total Energy [GJ]",
                        "Energy Per Total Building Area [MJ/m2]",
                        "Energy Per Conditioned Building Area [MJ/m2]"
                    ],
                    "Rows": {
                        "Net Site Energy": [
                            "143.11",
                            "279.97",
                            "279.97"
                        ],
                        "Net Source Energy": [
                            "443.56",
                            "867.76",
                            "867.76"
                        ],
                        "Total Site Energy": [
                            "143.11",
                            "279.97",
                            "279.97"
                        ],
                        "Total Source Energy": [
                            "443.56",
                            "867.76",
                            "867.76"
                        ]
                    },
                    "TableName": "Site and Source Energy"
                },
            ]
        }]

        table = t.gather_table_into_list('AnnualBuildingUtilityPerformanceSummary', 'Site and Source Energy')

        expected = [{'Total Energy [GJ]': '143.11', 'Energy Per Total Building Area [MJ/m2]': '279.97',
                     'Energy Per Conditioned Building Area [MJ/m2]': '279.97', 'first column': 'Net Site Energy'},
                    {'Total Energy [GJ]': '443.56', 'Energy Per Total Building Area [MJ/m2]': '867.76',
                     'Energy Per Conditioned Building Area [MJ/m2]': '867.76', 'first column': 'Net Source Energy'},
                    {'Total Energy [GJ]': '143.11', 'Energy Per Total Building Area [MJ/m2]': '279.97',
                     'Energy Per Conditioned Building Area [MJ/m2]': '279.97', 'first column': 'Total Site Energy'},
                    {'Total Energy [GJ]': '443.56', 'Energy Per Total Building Area [MJ/m2]': '867.76',
                     'Energy Per Conditioned Building Area [MJ/m2]': '867.76', 'first column': 'Total Source Energy'}]

        self.assertEqual(table, expected)

    def test_gather_air_terminal(self):
        t = self.set_minimal_files()

        # example taken from ASHRAE901_OfficeSmall_STD2019_Denver.json
        t.json_results_object['TabularReports'] = [{
            'For': 'Entire Facility',
            'ReportName': 'EquipmentSummary',
            'Tables': [
                {
                    "Cols": [
                        "Zone Name",
                        "Minimum Flow [m3/s]",
                        "Minimum Outdoor Flow [m3/s]",
                        "Supply Cooling Setpoint [C]",
                        "Supply Heating Setpoint [C]",
                        "Heating Capacity [W]",
                        "Cooling Capacity [W]",
                        "Type of Input Object",
                        "Heat/Reheat Coil Object Type",
                        "Chilled Water Coil Object Type",
                        "Fan Object Type",
                        "Fan Name",
                        "Primary Air Flow Rate [m3/s]",
                        "Secondary Air Flow Rate [m3/s]",
                        "Minimum Flow Schedule Name",
                        "Maximum Flow During Reheat [m3/s]",
                        "Minimum Outdoor Flow Schedule Name"
                    ],
                    "Rows": {
                        "CORE_ZN DIRECT AIR ADU": [
                            "CORE_ZN",
                            "0.11",
                            "0.06",
                            "12.80",
                            "40.00",
                            "1231.24",
                            "3830.70",
                            "AirTerminal:SingleDuct:ConstantVolume:NoReheat",
                            "",
                            "n/a",
                            "n/a",
                            "",
                            "0.35",
                            "n/a",
                            "n/a",
                            "0.00",
                            "n/a"
                        ],
                        "PERIMETER_ZN_1 DIRECT AIR ADU": [
                            "PERIMETER_ZN_1",
                            "0.09",
                            "0.05",
                            "12.80",
                            "40.00",
                            "3394.44",
                            "3481.33",
                            "AirTerminal:SingleDuct:ConstantVolume:NoReheat",
                            "",
                            "n/a",
                            "n/a",
                            "",
                            "0.32",
                            "n/a",
                            "n/a",
                            "0.00",
                            "n/a"
                        ],
                        "PERIMETER_ZN_2 DIRECT AIR ADU": [
                            "PERIMETER_ZN_2",
                            "0.05",
                            "0.03",
                            "12.80",
                            "40.00",
                            "2074.14",
                            "2793.42",
                            "AirTerminal:SingleDuct:ConstantVolume:NoReheat",
                            "",
                            "n/a",
                            "n/a",
                            "",
                            "0.26",
                            "n/a",
                            "n/a",
                            "0.00",
                            "n/a"
                        ],
                        "PERIMETER_ZN_3 DIRECT AIR ADU": [
                            "PERIMETER_ZN_3",
                            "0.09",
                            "0.05",
                            "12.80",
                            "40.00",
                            "3327.31",
                            "3188.96",
                            "AirTerminal:SingleDuct:ConstantVolume:NoReheat",
                            "",
                            "n/a",
                            "n/a",
                            "",
                            "0.29",
                            "n/a",
                            "n/a",
                            "0.00",
                            "n/a"
                        ],
                        "PERIMETER_ZN_4 DIRECT AIR ADU": [
                            "PERIMETER_ZN_4",
                            "0.05",
                            "0.03",
                            "12.80",
                            "40.00",
                            "2074.14",
                            "3408.48",
                            "AirTerminal:SingleDuct:ConstantVolume:NoReheat",
                            "",
                            "n/a",
                            "n/a",
                            "",
                            "0.31",
                            "n/a",
                            "n/a",
                            "0.00",
                            "n/a"
                        ]
                    },
                    "TableName": "Air Terminals"
                },
            ]
        }]

        gathered = t.gather_air_terminal()

        expected = {'CORE_ZN': {'terminal_name': 'CORE_ZN DIRECT AIR ADU', 'min_flow': 0.11, 'min_oa_flow': 0.06,
                                'supply_cool_set_point': 12.8, 'supply_heat_set_point': 40.0,
                                'heating_capacity': 1231.24, 'cooling_capacity': 3830.7,
                                'type_input': 'AirTerminal:SingleDuct:ConstantVolume:NoReheat', 'heat_coil_type': '',
                                'chill_coil_type': 'n/a', 'fan_type': 'n/a', 'fan_name': '',
                                'primary_airflow_rate': 0.35, 'min_flow_schedule_name': 'n/a',
                                'min_oa_schedule_name': 'n/a', 'secondary_airflow_rate': 0.0,
                                'max_flow_during_reheat': 0.0},
                    'PERIMETER_ZN_1': {'terminal_name': 'PERIMETER_ZN_1 DIRECT AIR ADU', 'min_flow': 0.09,
                                       'min_oa_flow': 0.05, 'supply_cool_set_point': 12.8,
                                       'supply_heat_set_point': 40.0, 'heating_capacity': 3394.44,
                                       'cooling_capacity': 3481.33,
                                       'type_input': 'AirTerminal:SingleDuct:ConstantVolume:NoReheat',
                                       'heat_coil_type': '', 'chill_coil_type': 'n/a', 'fan_type': 'n/a',
                                       'fan_name': '', 'primary_airflow_rate': 0.32, 'min_flow_schedule_name': 'n/a',
                                       'min_oa_schedule_name': 'n/a', 'secondary_airflow_rate': 0.0,
                                       'max_flow_during_reheat': 0.0},
                    'PERIMETER_ZN_2': {'terminal_name': 'PERIMETER_ZN_2 DIRECT AIR ADU', 'min_flow': 0.05,
                                       'min_oa_flow': 0.03, 'supply_cool_set_point': 12.8,
                                       'supply_heat_set_point': 40.0, 'heating_capacity': 2074.14,
                                       'cooling_capacity': 2793.42,
                                       'type_input': 'AirTerminal:SingleDuct:ConstantVolume:NoReheat',
                                       'heat_coil_type': '', 'chill_coil_type': 'n/a', 'fan_type': 'n/a',
                                       'fan_name': '', 'primary_airflow_rate': 0.26, 'min_flow_schedule_name': 'n/a',
                                       'min_oa_schedule_name': 'n/a', 'secondary_airflow_rate': 0.0,
                                       'max_flow_during_reheat': 0.0},
                    'PERIMETER_ZN_3': {'terminal_name': 'PERIMETER_ZN_3 DIRECT AIR ADU', 'min_flow': 0.09,
                                       'min_oa_flow': 0.05, 'supply_cool_set_point': 12.8,
                                       'supply_heat_set_point': 40.0, 'heating_capacity': 3327.31,
                                       'cooling_capacity': 3188.96,
                                       'type_input': 'AirTerminal:SingleDuct:ConstantVolume:NoReheat',
                                       'heat_coil_type': '', 'chill_coil_type': 'n/a', 'fan_type': 'n/a',
                                       'fan_name': '', 'primary_airflow_rate': 0.29, 'min_flow_schedule_name': 'n/a',
                                       'min_oa_schedule_name': 'n/a', 'secondary_airflow_rate': 0.0,
                                       'max_flow_during_reheat': 0.0},
                    'PERIMETER_ZN_4': {'terminal_name': 'PERIMETER_ZN_4 DIRECT AIR ADU', 'min_flow': 0.05,
                                       'min_oa_flow': 0.03, 'supply_cool_set_point': 12.8,
                                       'supply_heat_set_point': 40.0, 'heating_capacity': 2074.14,
                                       'cooling_capacity': 3408.48,
                                       'type_input': 'AirTerminal:SingleDuct:ConstantVolume:NoReheat',
                                       'heat_coil_type': '', 'chill_coil_type': 'n/a', 'fan_type': 'n/a',
                                       'fan_name': '', 'primary_airflow_rate': 0.31, 'min_flow_schedule_name': 'n/a',
                                       'min_oa_schedule_name': 'n/a', 'secondary_airflow_rate': 0.0,
                                       'max_flow_during_reheat': 0.0}}

        self.assertEqual(gathered, expected)

    def test_gather_airflows_from_62(self):
        t = self.set_minimal_files()

        # example taken from ASHRAE901_OfficeSmall_STD2019_Denver.json
        t.json_results_object['TabularReports'] = [{
            'For': 'Entire Facility',
            'ReportName': 'Standard62.1Summary',
            'Tables': [
                {
                    "Cols": [
                        "Sum of Zone Primary Airflow - Vpz-sum [m3/s]",
                        "System Primary Airflow - Vps [m3/s]",
                        "Sum of Zone Discharge Airflow - Vdz-sum [m3/s]",
                        "Sum of Min Zone Primary Airflow - Vpz-min [m3/s]",
                        "Zone Outdoor Airflow Cooling - Voz-clg [m3/s]",
                        "Zone Ventilation Efficiency - Evz-min"
                    ],
                    "Rows": {
                        "PSZ-AC:1": [
                            "0.3507",
                            "0.3507",
                            "0.3507",
                            "0.3507",
                            "0.0646",
                            "1.0000"
                        ],
                        "PSZ-AC:2": [
                            "0.3187",
                            "0.3187",
                            "0.3187",
                            "0.3187",
                            "0.0490",
                            "1.0000"
                        ],
                        "PSZ-AC:3": [
                            "0.2558",
                            "0.2558",
                            "0.2558",
                            "0.2558",
                            "0.0291",
                            "1.0000"
                        ],
                        "PSZ-AC:4": [
                            "0.2920",
                            "0.2920",
                            "0.2920",
                            "0.2920",
                            "0.0490",
                            "1.0000"
                        ],
                        "PSZ-AC:5": [
                            "0.3121",
                            "0.3121",
                            "0.3121",
                            "0.3121",
                            "0.0291",
                            "1.0000"
                        ]
                    },
                    "TableName": "System Ventilation Calculations for Cooling Design"
                },
                {
                    "Cols": [
                        "Sum of Zone Primary Airflow - Vpz-sum [m3/s]",
                        "System Primary Airflow - Vps [m3/s]",
                        "Sum of Zone Discharge Airflow - Vdz-sum [m3/s]",
                        "Sum of Min Zone Primary Airflow - Vpz-min [m3/s]",
                        "Zone Outdoor Airflow Heating - Voz-htg [m3/s]",
                        "Zone Ventilation Efficiency - Evz-min"
                    ],
                    "Rows": {
                        "PSZ-AC:1": [
                            "0.3507",
                            "0.3507",
                            "0.3507",
                            "0.3507",
                            "0.0646",
                            "1.0000"
                        ],
                        "PSZ-AC:2": [
                            "0.3187",
                            "0.3187",
                            "0.3187",
                            "0.3187",
                            "0.0490",
                            "1.0000"
                        ],
                        "PSZ-AC:3": [
                            "0.2558",
                            "0.2558",
                            "0.2558",
                            "0.2558",
                            "0.0291",
                            "1.0000"
                        ],
                        "PSZ-AC:4": [
                            "0.2920",
                            "0.2920",
                            "0.2920",
                            "0.2920",
                            "0.0490",
                            "1.0000"
                        ],
                        "PSZ-AC:5": [
                            "0.3121",
                            "0.3121",
                            "0.3121",
                            "0.3121",
                            "0.0291",
                            "1.0000"
                        ]
                    },
                    "TableName": "System Ventilation Calculations for Heating Design"
                }
            ]
        }]

        gathered = t.gather_airflows_from_62()

        expected = {'PSZ-AC:1': (350.7, 64.60000000000001),
                    'PSZ-AC:2': (318.7, 49.0),
                    'PSZ-AC:3': (255.80000000000004, 29.1),
                    'PSZ-AC:4': (292.0, 49.0),
                    'PSZ-AC:5': (312.09999999999997, 29.1)}

        self.assertEqual(gathered, expected)

    def test_gather_exhaust_fans_by_airloop(self):
        t = self.set_minimal_files()

        # example taken from ASHRAE901_SchoolPrimary_STD2019_DenverA.json
        t.json_results_object['TabularReports'] = [{
            'For': 'Entire Facility',
            'ReportName': 'HVACTopology',
            'Tables': [
                {
                    "Cols": [
                        "Airloop Name",
                        "Supply Branch Name",
                        "Supply Branch Type",
                        "Supply Path Component Type",
                        "Supply Path Component Name",
                        "Terminal Unit Type",
                        "Terminal Unit Name",
                        "Zone Name",
                        "Return Path Component Type",
                        "Return Path Component Name"
                    ],
                    "Rows": {
                        "31": [
                            "VAV_OTHER",
                            "VAV_OTHER AIR LOOP MAIN BRANCH",
                            "Main",
                            "AIRLOOPHVAC:ZONESPLITTER",
                            "VAV_OTHER SUPPLY AIR SPLITTER",
                            "AIRTERMINAL:SINGLEDUCT:VAV:REHEAT",
                            "BATH_ZN_1_FLR_1 VAV BOX COMPONENT",
                            "BATH_ZN_1_FLR_1",
                            "AIRLOOPHVAC:ZONEMIXER",
                            "VAV_OTHER RETURN AIR MIXER"
                        ],
                        "33": [
                            "VAV_OTHER",
                            "VAV_OTHER AIR LOOP MAIN BRANCH",
                            "Main",
                            "AIRLOOPHVAC:ZONESPLITTER",
                            "VAV_OTHER SUPPLY AIR SPLITTER",
                            "AIRTERMINAL:SINGLEDUCT:VAV:REHEAT",
                            "LIBRARY_MEDIA_CENTER_ZN_1_FLR_1 VAV BOX COMPONENT",
                            "LIBRARY_MEDIA_CENTER_ZN_1_FLR_1",
                            "AIRLOOPHVAC:ZONEMIXER",
                            "VAV_OTHER RETURN AIR MIXER"
                        ],
                        "37": [
                            "PSZ-AC_2:5",
                            "PSZ-AC_2:5 AIR LOOP MAIN BRANCH",
                            "Main",
                            "AIRLOOPHVAC:ZONESPLITTER",
                            "PSZ-AC_2:5 SUPPLY AIR SPLITTER",
                            "AIRTERMINAL:SINGLEDUCT:CONSTANTVOLUME:NOREHEAT",
                            "GYM_ZN_1_FLR_1 DIRECT AIR",
                            "GYM_ZN_1_FLR_1",
                            "AIRLOOPHVAC:ZONEMIXER",
                            "PSZ-AC_2:5 RETURN AIR MIXER"
                        ],
                        "41": [
                            "PSZ-AC_1:6",
                            "PSZ-AC_1:6 AIR LOOP MAIN BRANCH",
                            "Main",
                            "AIRLOOPHVAC:ZONESPLITTER",
                            "PSZ-AC_1:6 SUPPLY AIR SPLITTER",
                            "AIRTERMINAL:SINGLEDUCT:CONSTANTVOLUME:NOREHEAT",
                            "KITCHEN_ZN_1_FLR_1 DIRECT AIR",
                            "KITCHEN_ZN_1_FLR_1",
                            "AIRLOOPHVAC:ZONEMIXER",
                            "PSZ-AC_1:6 RETURN AIR MIXER"
                        ],
                        "45": [
                            "PSZ-AC_2:7",
                            "PSZ-AC_2:7 AIR LOOP MAIN BRANCH",
                            "Main",
                            "AIRLOOPHVAC:ZONESPLITTER",
                            "PSZ-AC_2:7 SUPPLY AIR SPLITTER",
                            "AIRTERMINAL:SINGLEDUCT:CONSTANTVOLUME:NOREHEAT",
                            "CAFETERIA_ZN_1_FLR_1 DIRECT AIR",
                            "CAFETERIA_ZN_1_FLR_1",
                            "AIRLOOPHVAC:ZONEMIXER",
                            "PSZ-AC_2:7 RETURN AIR MIXER"
                        ],
                    },
                    "TableName": "Air Loop Demand Side Component Arrangement"
                },
                {
                    "Cols": [
                        "Zone Name",
                        "Component Type",
                        "Component Name",
                        "Sub-Component Type",
                        "Sub-Component Name",
                        "Sub-Sub-Component Type",
                        "Sub-Sub-Component Name"
                    ],
                    "Rows": {
                        "78": [
                            "BATH_ZN_1_FLR_1",
                            "FAN:ZONEEXHAUST",
                            "BATH_ZN_1_FLR_1 EXHAUST FAN",
                            "",
                            "",
                            "",
                            ""
                        ],
                        "87": [
                            "GYM_ZN_1_FLR_1",
                            "FAN:ZONEEXHAUST",
                            "GYM_ZN_1_FLR_1 DUMMY EXHAUST FAN",
                            "",
                            "",
                            "",
                            ""
                        ],
                        "91": [
                            "KITCHEN_ZN_1_FLR_1",
                            "FAN:ZONEEXHAUST",
                            "KITCHEN_ZN_1_FLR_1 EXHAUST FAN",
                            "",
                            "",
                            "",
                            ""
                        ],
                        "95": [
                            "CAFETERIA_ZN_1_FLR_1",
                            "FAN:ZONEEXHAUST",
                            "CAFETERIA_ZN_1_FLR_1 DUMMY EXHAUST FAN",
                            "",
                            "",
                            "",
                            ""
                        ],
                        "99": [
                            "LIBRARY_MEDIA_CENTER_ZN_1_FLR_1",
                            "FAN:ZONEEXHAUST",
                            "LIBRARY_MEDIA_CENTER_ZN_1_FLR_1 DUMMY EXHAUST FAN",
                            "",
                            "",
                            "",
                            ""
                        ],
                    },
                    "TableName": "Zone Equipment Component Arrangement"
                },
            ]
        }]

        gathered = t.gather_exhaust_fans_by_airloop()

        expected = {'VAV_OTHER': ['BATH_ZN_1_FLR_1 EXHAUST FAN', 'LIBRARY_MEDIA_CENTER_ZN_1_FLR_1 DUMMY EXHAUST FAN'],
                    'PSZ-AC_2:5': ['GYM_ZN_1_FLR_1 DUMMY EXHAUST FAN'],
                    'PSZ-AC_1:6': ['KITCHEN_ZN_1_FLR_1 EXHAUST FAN'],
                    'PSZ-AC_2:7': ['CAFETERIA_ZN_1_FLR_1 DUMMY EXHAUST FAN']}

        self.assertEqual(gathered, expected)

    def test_do_share_branch(self):
        t = self.set_minimal_files()

        # example taken from large_office_cz2-tampa_proposed_final.json
        # but modified to provide a working example
        t.json_results_object['TabularReports'] = [{
            'For': 'Entire Facility',
            'ReportName': 'HVACTopology',
            'Tables': [
                {
                    "Cols": [
                        "Loop Type",
                        "Loop Name",
                        "Side",
                        "Splitter Name",
                        "Branch Name",
                        "Component Type",
                        "Component Name",
                        "Mixer Name"
                    ],
                    "Rows": {
                        "4": [
                            "PlantLoop",
                            "CHILLED WATER LOOP",
                            "Supply",
                            "CHILLED WATER LOOP SUPPLY SPLITTER",
                            "CHILLED WATER LOOP SUPPLY BRANCH",
                            "CHILLER:ELECTRIC:EIR",
                            "90.1-2004 WATERCOOLED  CENTRIFUGAL CHILLER 1 416TONS 0.6KW/TON",
                            "CHILLED WATER LOOP DEMAND INLET"
                        ],
                        "9": [
                            "PlantLoop",
                            "CHILLED WATER LOOP",
                            "Supply",
                            "",
                            "CHILLED WATER LOOP SUPPLY BRANCH",
                            "HeatExchanger:FluidToFluid",
                            "HX1",
                            ""
                        ],
                    },
                    "TableName": "Plant Loop Component Arrangement"
                }
            ]
        }]

        plant_loop_arrangements = t.gather_table_into_list('HVACTopology',
                                                           'Plant Loop Component Arrangement')

        self.assertTrue(do_share_branch('chiller', 'heatexchanger', plant_loop_arrangements))
        self.assertFalse(do_share_branch('chiller', 'tower', plant_loop_arrangements))

    def test_do_chiller_and_pump_share_branch(self):
        t = self.set_minimal_files()

        # example taken from large_office_cz2-tampa_proposed_final.json
        # but modified to provide a working example
        t.json_results_object['TabularReports'] = [{
            'For': 'Entire Facility',
            'ReportName': 'HVACTopology',
            'Tables': [
                {
                    "Cols": [
                        "Loop Type",
                        "Loop Name",
                        "Side",
                        "Splitter Name",
                        "Branch Name",
                        "Component Type",
                        "Component Name",
                        "Mixer Name"
                    ],
                    "Rows": {
                        "4": [
                            "PlantLoop",
                            "CHILLED WATER LOOP",
                            "Supply",
                            "CHILLED WATER LOOP SUPPLY SPLITTER",
                            "CHILLED WATER LOOP SUPPLY BRANCH",
                            "CHILLER:ELECTRIC:EIR",
                            "MainChiller",
                            "CHILLED WATER LOOP DEMAND INLET"
                        ],
                        "9": [
                            "PlantLoop",
                            "CHILLED WATER LOOP",
                            "Supply",
                            "",
                            "CHILLED WATER LOOP SUPPLY BRANCH",
                            "Pump:VariableSpeed",
                            "CHILLED WATER LOOP SECONDARY PUMP",
                            ""
                        ],
                    },
                    "TableName": "Plant Loop Component Arrangement"
                }
            ]
        }]

        plant_loop_arrangements = t.gather_table_into_list('HVACTopology',
                                                           'Plant Loop Component Arrangement')

        self.assertTrue(do_chiller_and_pump_share_branch('MainChiller', plant_loop_arrangements,
                                                         'SUPPLY'))
        self.assertFalse(do_chiller_and_pump_share_branch('Invisible_Chiller', plant_loop_arrangements,
                                                          'SUPPLY'))

        plant_loop_arrangements[1] = {'Loop Type': 'PlantLoop',
                                      'Loop Name': 'CHILLED WATER LOOP',
                                      'Side': 'Supply',
                                      'Splitter Name': '',
                                      'Branch Name': 'CHILLED WATER LOOP SUPPLY BRANCH',
                                      'Component Type': 'PlantComponent:UserDefined',
                                      'Component Name': 'CHILLED WATER LOOP SECONDARY PUMP', 'Mixer Name': '',
                                      'first column': '9'}

        self.assertFalse(do_chiller_and_pump_share_branch('MainChiller', plant_loop_arrangements,
                                                          'SUPPLY'))

    def test_add_fluid_loops(self):
        t = self.set_minimal_files()

        # example taken from large_office_cz2-tampa_proposed_final.json
        t.json_results_object['TabularReports'] = [{
            'For': 'Entire Facility',
            'ReportName': 'HVACTopology',
            'Tables': [
                {
                    "Cols": [
                        "Loop Type",
                        "Loop Name",
                        "Side",
                        "Splitter Name",
                        "Branch Name",
                        "Component Type",
                        "Component Name",
                        "Mixer Name"
                    ],
                    "Rows": {
                        "2": [
                            "PlantLoop",
                            "CHILLED WATER LOOP",
                            "Supply",
                            "",
                            "CHILLED WATER LOOP SUPPLY INLET BRANCH",
                            "PUMP:CONSTANTSPEED",
                            "CHILLED WATER LOOP PRIMARY PUMP",
                            ""
                        ],
                        "3": [
                            "PlantLoop",
                            "CHILLED WATER LOOP",
                            "Supply",
                            "CHILLED WATER LOOP SUPPLY SPLITTER",
                            "CHILLED WATER LOOP SUPPLY BRANCH 1",
                            "CHILLER:ELECTRIC:EIR",
                            "90.1-2004 WATERCOOLED  CENTRIFUGAL CHILLER 0 416TONS 0.6KW/TON",
                            "CHILLED WATER LOOP SUPPLY MIXER"
                        ],
                        "4": [
                            "PlantLoop",
                            "CHILLED WATER LOOP",
                            "Supply",
                            "CHILLED WATER LOOP SUPPLY SPLITTER",
                            "CHILLED WATER LOOP SUPPLY BRANCH 2",
                            "CHILLER:ELECTRIC:EIR",
                            "90.1-2004 WATERCOOLED  CENTRIFUGAL CHILLER 1 416TONS 0.6KW/TON",
                            "CHILLED WATER LOOP SUPPLY MIXER"
                        ],
                        "9": [
                            "PlantLoop",
                            "CHILLED WATER LOOP",
                            "Demand",
                            "",
                            "CHILLED WATER LOOP DEMAND INLET BRANCH",
                            "PUMP:VARIABLESPEED",
                            "CHILLED WATER LOOP SECONDARY PUMP",
                            ""
                        ],
                        "18": [
                            "PlantLoop",
                            "CONDENSER WATER LOOP",
                            "Supply",
                            "",
                            "CONDENSER WATER LOOP SUPPLY INLET BRANCH",
                            "PUMP:CONSTANTSPEED",
                            "CONDENSER WATER LOOP CONSTANT PUMP",
                            ""
                        ],
                        "19": [
                            "PlantLoop",
                            "CONDENSER WATER LOOP",
                            "Supply",
                            "CONDENSER WATER LOOP SUPPLY SPLITTER",
                            "CONDENSER WATER LOOP SUPPLY BRANCH 1",
                            "COOLINGTOWER:VARIABLESPEED",
                            "CENTRIFUGAL VARIABLE SPEED FAN OPEN COOLING TOWER 20.0 GPM/HP",
                            "CONDENSER WATER LOOP SUPPLY MIXER"
                        ],
                        "25": [
                            "PlantLoop",
                            "CONDENSER WATER LOOP",
                            "Demand",
                            "CONDENSER WATER LOOP DEMAND SPLITTER",
                            "CONDENSER WATER LOOP DEMAND BRANCH 2",
                            "CHILLER:ELECTRIC:EIR",
                            "90.1-2004 WATERCOOLED  CENTRIFUGAL CHILLER 0 416TONS 0.6KW/TON",
                            "CONDENSER WATER LOOP DEMAND MIXER"
                        ],
                        "26": [
                            "PlantLoop",
                            "CONDENSER WATER LOOP",
                            "Demand",
                            "CONDENSER WATER LOOP DEMAND SPLITTER",
                            "CONDENSER WATER LOOP DEMAND BRANCH 3",
                            "CHILLER:ELECTRIC:EIR",
                            "90.1-2004 WATERCOOLED  CENTRIFUGAL CHILLER 1 416TONS 0.6KW/TON",
                            "CONDENSER WATER LOOP DEMAND MIXER"
                        ],
                        "30": [
                            "PlantLoop",
                            "HEAT PUMP LOOP",
                            "Supply",
                            "",
                            "HEAT PUMP LOOP SUPPLY INLET BRANCH",
                            "PUMP:CONSTANTSPEED",
                            "HEAT PUMP LOOP PUMP",
                            ""
                        ],
                        "31": [
                            "PlantLoop",
                            "HEAT PUMP LOOP",
                            "Supply",
                            "HEAT PUMP LOOP SUPPLY SPLITTER",
                            "HEAT PUMP LOOP SUPPLY BRANCH 1",
                            "FLUIDCOOLER:TWOSPEED",
                            "HEAT PUMP LOOP FLUIDCOOLERTWOSPEED 4.0 GPM/HP",
                            "HEAT PUMP LOOP SUPPLY MIXER"
                        ],
                        "32": [
                            "PlantLoop",
                            "HEAT PUMP LOOP",
                            "Supply",
                            "HEAT PUMP LOOP SUPPLY SPLITTER",
                            "HEAT PUMP LOOP SUPPLY BRANCH 2",
                            "BOILER:HOTWATER",
                            "HEAT PUMP LOOP SUPPLEMENTAL BOILER 2669KBTU/HR 0.75 THERMAL EFF",
                            "HEAT PUMP LOOP SUPPLY MIXER"
                        ],
                        "49": [
                            "PlantLoop",
                            "HOT WATER LOOP",
                            "Supply",
                            "",
                            "HOT WATER LOOP SUPPLY INLET BRANCH",
                            "PUMP:VARIABLESPEED",
                            "HOT WATER LOOP PUMP",
                            ""
                        ],
                        "50": [
                            "PlantLoop",
                            "HOT WATER LOOP",
                            "Supply",
                            "HOT WATER LOOP SUPPLY SPLITTER",
                            "HOT WATER LOOP SUPPLY BRANCH 1",
                            "BOILER:HOTWATER",
                            "BOILER 5939KBTU/HR 0.75 THERMAL EFF",
                            "HOT WATER LOOP SUPPLY MIXER"
                        ],
                        "79": [
                            "PlantLoop",
                            "MAIN SERVICE WATER LOOP",
                            "Supply",
                            "",
                            "MAIN SERVICE WATER LOOP SUPPLY INLET BRANCH",
                            "PUMP:CONSTANTSPEED",
                            "MAIN SERVICE WATER LOOP CIRCULATOR PUMP",
                            ""
                        ],
                        "80": [
                            "PlantLoop",
                            "MAIN SERVICE WATER LOOP",
                            "Supply",
                            "MAIN SERVICE WATER LOOP SUPPLY SPLITTER",
                            "MAIN SERVICE WATER LOOP SUPPLY BRANCH 1",
                            "WATERHEATER:MIXED",
                            "300GAL NATURAL GAS WATER HEATER - 300KBTU/HR 0.804 THERM EFF",
                            "MAIN SERVICE WATER LOOP SUPPLY MIXER"
                        ],
                    },
                    "TableName": "Plant Loop Component Arrangement"
                }
            ]
        }]

        t.model_description['pumps'] = [
            {'id': 'CHILLED WATER LOOP PRIMARY PUMP', 'loop_or_piping': 'CHILLED WATER LOOP',
             'specification_method': 'SIMPLE', 'design_electric_power': 9611.29, 'design_head': 44836.0,
             'motor_efficiency': 0.9, 'speed_control': 'FIXED_SPEED', 'design_flow': 149.649,
             'is_flow_sized_based_on_design_day': True},
            {'id': 'CHILLED WATER LOOP SECONDARY PUMP', 'loop_or_piping': 'CHILLED WATER LOOP',
             'specification_method': 'SIMPLE', 'design_electric_power': 27928.92, 'design_head': 134508.01,
             'motor_efficiency': 0.92, 'speed_control': 'VARIABLE_SPEED', 'design_flow': 149.649,
             'is_flow_sized_based_on_design_day': True},
            {'id': 'CONDENSER WATER LOOP CONSTANT PUMP', 'loop_or_piping': 'CONDENSER WATER LOOP',
             'specification_method': 'SIMPLE', 'design_electric_power': 37844.02, 'design_head': 148556.63,
             'motor_efficiency': 0.93, 'speed_control': 'FIXED_SPEED', 'design_flow': 184.792,
             'is_flow_sized_based_on_design_day': True},
            {'id': 'HEAT PUMP LOOP PUMP', 'loop_or_piping': 'HEAT PUMP LOOP', 'specification_method': 'SIMPLE',
             'design_electric_power': 4464.57, 'design_head': 179344.02, 'motor_efficiency': 0.9,
             'speed_control': 'FIXED_SPEED', 'design_flow': 17.378, 'is_flow_sized_based_on_design_day': True},
            {'id': 'HOT WATER LOOP PUMP', 'loop_or_piping': 'HOT WATER LOOP', 'specification_method': 'SIMPLE',
             'design_electric_power': 10528.37, 'design_head': 179344.02, 'motor_efficiency': 0.91,
             'speed_control': 'VARIABLE_SPEED', 'design_flow': 41.669, 'is_flow_sized_based_on_design_day': True},
            {'id': 'MAIN SERVICE WATER LOOP CIRCULATOR PUMP', 'loop_or_piping': 'MAIN SERVICE WATER LOOP',
             'specification_method': 'SIMPLE', 'design_electric_power': 20.4, 'design_head': 29891.0,
             'motor_efficiency': 0.82, 'speed_control': 'FIXED_SPEED', 'design_flow': 0.439,
             'is_flow_sized_based_on_design_day': True}]

        t.pump_extra = {'CHILLED WATER LOOP PRIMARY PUMP': {'control': 'Intermittent'},
                        'CHILLED WATER LOOP SECONDARY PUMP': {'control': 'Intermittent'},
                        'CONDENSER WATER LOOP CONSTANT PUMP': {'control': 'Intermittent'},
                        'HEAT PUMP LOOP PUMP': {'control': 'Intermittent'},
                        'HOT WATER LOOP PUMP': {'control': 'Intermittent'},
                        'MAIN SERVICE WATER LOOP CIRCULATOR PUMP': {'control': 'Intermittent'}}

        gathered = t.add_fluid_loops()

        expected = [{'id': 'CHILLED WATER LOOP', 'type': 'COOLING', 'pump_power_per_flow_rate': 250.8550675246744,
                     'cooling_or_condensing_design_and_control': {'id': 'CHILLED WATER LOOP-COOLING',
                                                                  'operation': 'INTERMITTENT',
                                                                  'flow_control': 'VARIABLE_FLOW',
                                                                  'has_integrated_waterside_economizer': False}},
                    {'id': 'CONDENSER WATER LOOP', 'type': 'CONDENSER', 'pump_power_per_flow_rate': 204.79252348586516,
                     'cooling_or_condensing_design_and_control': {'id': 'CONDENSER WATER LOOP-CONDENSER',
                                                                  'operation': 'INTERMITTENT',
                                                                  'flow_control': 'FIXED_FLOW',
                                                                  'has_integrated_waterside_economizer': False}},
                    {'id': 'HEAT PUMP LOOP', 'type': 'HEATING_AND_COOLING',
                     'pump_power_per_flow_rate': 256.90931062262626,
                     'cooling_or_condensing_design_and_control': {'id': 'HEAT PUMP LOOP-HEATING_AND_COOLING',
                                                                  'operation': 'INTERMITTENT',
                                                                  'flow_control': 'FIXED_FLOW',
                                                                  'has_integrated_waterside_economizer': False},
                     'heating_design_and_control': {'id': 'HEAT PUMP LOOP-HEATING_AND_COOLING',
                                                    'operation': 'INTERMITTENT', 'flow_control': 'FIXED_FLOW',
                                                    'has_integrated_waterside_economizer': False}},
                    {'id': 'HOT WATER LOOP', 'type': 'HEATING', 'pump_power_per_flow_rate': 252.66673066308292,
                     'heating_design_and_control': {'id': 'HOT WATER LOOP-HEATING', 'operation': 'INTERMITTENT',
                                                    'flow_control': 'VARIABLE_FLOW'}}]

        self.assertEqual(gathered, expected)

    def test_add_simulation_outputs_b(self):
        t = self.set_minimal_files()

        # example taken from ASHRAE901_OfficeSmall_STD2019_Denver.epJSON
        t.json_results_object['TabularReports'] = [{
            "For": "Entire Facility",
            "ReportName": "AnnualBuildingUtilityPerformanceSummary",
            'Tables': [
                {
                    "Cols": [
                        "Electricity [GJ]",
                        "Natural Gas [GJ]",
                        "Gasoline [GJ]",
                        "Diesel [GJ]",
                        "Coal [GJ]",
                        "Fuel Oil No 1 [GJ]",
                        "Fuel Oil No 2 [GJ]",
                        "Propane [GJ]",
                        "Other Fuel 1 [GJ]",
                        "Other Fuel 2 [GJ]",
                        "District Cooling [GJ]",
                        "District Heating Water [GJ]",
                        "District Heating Steam [GJ]",
                        "Water [m3]"
                    ],
                    "Rows": {
                        "": [
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            ""
                        ],
                        "Cooling": [
                            "12.08",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00"
                        ],
                        "Exterior Equipment": [
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00"
                        ],
                        "Exterior Lighting": [
                            "5.68",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00"
                        ],
                        "Fans": [
                            "19.66",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00"
                        ],
                        "Generators": [
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00"
                        ],
                        "Heat Recovery": [
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00"
                        ],
                        "Heat Rejection": [
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00"
                        ],
                        "Heating": [
                            "9.13",
                            "4.64",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00"
                        ],
                        "Humidification": [
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00"
                        ],
                        "Interior Equipment": [
                            "48.30",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00"
                        ],
                        "Interior Lighting": [
                            "25.61",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00"
                        ],
                        "Pumps": [
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00"
                        ],
                        "Refrigeration": [
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00"
                        ],
                        "Total End Uses": [
                            "138.47",
                            "4.64",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "58.31"
                        ],
                        "Water Systems": [
                            "18.01",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "0.00",
                            "58.31"
                        ]
                    },
                    "TableName": "End Uses"
                },
            ]
        },
            {
                "For": "Entire Facility",
                "ReportName": "DemandEndUseComponentsSummary",
                "Tables": [
                    {
                        "Cols": [
                            "Electricity [W]",
                            "Natural Gas [W]",
                            "Gasoline [W]",
                            "Diesel [W]",
                            "Coal [W]",
                            "Fuel Oil No 1 [W]",
                            "Fuel Oil No 2 [W]",
                            "Propane [W]",
                            "Other Fuel 1 [W]",
                            "Other Fuel 2 [W]",
                            "District Cooling [W]",
                            "District Heating Water [W]",
                            "District Heating Steam [W]",
                            "Water [m3/s]"
                        ],
                        "Rows": {
                            "": [
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                "",
                                ""
                            ],
                            "Cooling": [
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "Exterior Equipment": [
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "Exterior Lighting": [
                                "611.30",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "Fans": [
                                "1712.96",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "Generators": [
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "Heat Recovery": [
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "Heat Rejection": [
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "Heating": [
                                "6277.68",
                                "25029.93",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "Humidification": [
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "Interior Equipment": [
                                "3325.31",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "Interior Lighting": [
                                "2461.51",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "Pumps": [
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "Refrigeration": [
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "Time of Peak": [
                                "02-JAN-17:00",
                                "02-JAN-06:30",
                                "-",
                                "-",
                                "-",
                                "-",
                                "-",
                                "-",
                                "-",
                                "-",
                                "-",
                                "-",
                                "-",
                                "02-JAN-12:30"
                            ],
                            "Total End Uses": [
                                "14959.75",
                                "25029.93",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "Water Systems": [
                                "571.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ]
                        },
                        "TableName": "End Uses"
                    }]
            },
            {
                "For": "Entire Facility",
                "ReportName": "EnergyMeters",
                "Tables": [
                    {
                        "Cols": [
                            "Electricity Annual Value [GJ]",
                            "Electricity Minimum Value [W]",
                            "Timestamp of Minimum {TIMESTAMP}",
                            "Electricity Maximum Value [W]",
                            "Timestamp of Maximum {TIMESTAMP}"
                        ],
                        "Rows": {
                            "Cogeneration:ElectricityNet": [
                                "138.47",
                                "1248.68",
                                "07-JAN-09:30",
                                "14959.75",
                                "02-JAN-16:45"
                            ],
                            "Cogeneration:ElectricityPurchased": [
                                "138.47",
                                "1248.68",
                                "07-JAN-09:30",
                                "14959.75",
                                "02-JAN-16:45"
                            ],
                            "Cogeneration:ElectricitySurplusSold": [
                                "0.00",
                                "0.00",
                                "01-JAN-00:15",
                                "0.00",
                                "01-JAN-00:15"
                            ],
                            "Cooling:Electricity": [
                                "12.08",
                                "0.00",
                                "01-JAN-00:15",
                                "5318.53",
                                "05-SEP-15:15"
                            ],
                            "Electricity:Building": [
                                "73.91",
                                "677.68",
                                "01-JAN-00:15",
                                "5786.82",
                                "02-JAN-16:45"
                            ],
                            "Electricity:Facility": [
                                "138.47",
                                "1248.68",
                                "07-JAN-09:30",
                                "14959.75",
                                "02-JAN-16:45"
                            ],
                            "Electricity:HVAC": [
                                "40.88",
                                "0.00",
                                "05-JAN-03:30",
                                "8764.53",
                                "21-FEB-07:15"
                            ],
                            "Electricity:Plant": [
                                "18.01",
                                "571.00",
                                "02-MAY-02:45",
                                "571.00",
                                "02-JAN-07:15"
                            ],
                            "Electricity:SpaceType:LOBBY_ALL_OTHERS": [
                                "15.94",
                                "150.41",
                                "01-JAN-00:15",
                                "1284.37",
                                "02-JAN-16:45"
                            ],
                            "Electricity:SpaceType:OFFICE_ENCLOSED": [
                                "35.34",
                                "328.86",
                                "01-JAN-00:15",
                                "2808.18",
                                "02-JAN-16:45"
                            ],
                            "Electricity:SpaceType:OFFICE_OPEN_PLAN": [
                                "22.63",
                                "198.41",
                                "01-JAN-00:15",
                                "1694.27",
                                "02-JAN-08:15"
                            ],
                            "Electricity:Zone:CORE_ZN": [
                                "22.63",
                                "198.41",
                                "01-JAN-00:15",
                                "1694.27",
                                "02-JAN-08:15"
                            ],
                            "Electricity:Zone:PERIMETER_ZN_1": [
                                "15.94",
                                "150.41",
                                "01-JAN-00:15",
                                "1284.37",
                                "02-JAN-16:45"
                            ],
                            "Electricity:Zone:PERIMETER_ZN_2": [
                                "9.55",
                                "89.23",
                                "01-JAN-00:15",
                                "761.90",
                                "02-JAN-16:45"
                            ],
                            "Electricity:Zone:PERIMETER_ZN_3": [
                                "16.24",
                                "150.41",
                                "01-JAN-00:15",
                                "1284.37",
                                "02-JAN-16:45"
                            ],
                            "Electricity:Zone:PERIMETER_ZN_4": [
                                "9.55",
                                "89.23",
                                "01-JAN-00:15",
                                "761.90",
                                "02-JAN-16:45"
                            ],
                            "ElectricityNet:Facility": [
                                "138.47",
                                "1248.68",
                                "07-JAN-09:30",
                                "14959.75",
                                "02-JAN-16:45"
                            ],
                            "ElectricityNet:Plant": [
                                "138.47",
                                "1248.68",
                                "07-JAN-09:30",
                                "14959.75",
                                "02-JAN-16:45"
                            ],
                            "ElectricityPurchased:Facility": [
                                "138.47",
                                "1248.68",
                                "07-JAN-09:30",
                                "14959.75",
                                "02-JAN-16:45"
                            ],
                            "ElectricityPurchased:Plant": [
                                "138.47",
                                "1248.68",
                                "07-JAN-09:30",
                                "14959.75",
                                "02-JAN-16:45"
                            ],
                            "ElectricitySurplusSold:Facility": [
                                "0.00",
                                "0.00",
                                "01-JAN-00:15",
                                "0.00",
                                "01-JAN-00:15"
                            ],
                            "ElectricitySurplusSold:Plant": [
                                "0.00",
                                "0.00",
                                "01-JAN-00:15",
                                "0.00",
                                "01-JAN-00:15"
                            ],
                            "ExteriorLights:Electricity": [
                                "5.68",
                                "0.00",
                                "01-JAN-07:30",
                                "611.30",
                                "01-JAN-06:15"
                            ],
                            "Fans:Electricity": [
                                "19.66",
                                "0.00",
                                "01-JAN-08:30",
                                "1712.96",
                                "02-JAN-06:15"
                            ],
                            "General:Cogeneration:ElectricityNet": [
                                "138.47",
                                "1248.68",
                                "07-JAN-09:30",
                                "14959.75",
                                "02-JAN-16:45"
                            ],
                            "General:Cogeneration:ElectricityPurchased": [
                                "138.47",
                                "1248.68",
                                "07-JAN-09:30",
                                "14959.75",
                                "02-JAN-16:45"
                            ],
                            "General:Cogeneration:ElectricitySurplusSold": [
                                "0.00",
                                "0.00",
                                "01-JAN-00:15",
                                "0.00",
                                "01-JAN-00:15"
                            ],
                            "General:Cooling:Electricity": [
                                "12.08",
                                "0.00",
                                "01-JAN-00:15",
                                "5318.53",
                                "05-SEP-15:15"
                            ],
                            "General:ExteriorLights:Electricity": [
                                "5.68",
                                "0.00",
                                "01-JAN-07:30",
                                "611.30",
                                "01-JAN-06:15"
                            ],
                            "General:Fans:Electricity": [
                                "19.66",
                                "0.00",
                                "01-JAN-08:30",
                                "1712.96",
                                "02-JAN-06:15"
                            ],
                            "General:Heating:Electricity": [
                                "9.13",
                                "0.00",
                                "05-JAN-03:30",
                                "7051.57",
                                "21-FEB-07:15"
                            ],
                            "General:Pumps:Electricity": [
                                "0.00",
                                "0.00",
                                "01-JAN-00:15",
                                "0.00",
                                "02-JAN-07:15"
                            ],
                            "Heating:Electricity": [
                                "9.13",
                                "0.00",
                                "05-JAN-03:30",
                                "7051.57",
                                "21-FEB-07:15"
                            ],
                            "InteriorEquipment:Electricity": [
                                "48.30",
                                "567.64",
                                "01-JAN-00:15",
                                "3325.31",
                                "02-JAN-08:15"
                            ],
                            "InteriorEquipment:Electricity:SpaceType:LOBBY_ALL_OTHERS": [
                                "10.72",
                                "125.99",
                                "01-JAN-00:15",
                                "738.04",
                                "02-JAN-08:15"
                            ],
                            "InteriorEquipment:Electricity:SpaceType:OFFICE_ENCLOSED": [
                                "23.44",
                                "275.46",
                                "01-JAN-00:15",
                                "1613.68",
                                "02-JAN-08:15"
                            ],
                            "InteriorEquipment:Electricity:SpaceType:OFFICE_OPEN_PLAN": [
                                "14.14",
                                "166.20",
                                "01-JAN-00:15",
                                "973.59",
                                "02-JAN-08:15"
                            ],
                            "InteriorEquipment:Electricity:Zone:CORE_ZN": [
                                "14.14",
                                "166.20",
                                "01-JAN-00:15",
                                "973.59",
                                "02-JAN-08:15"
                            ],
                            "InteriorEquipment:Electricity:Zone:PERIMETER_ZN_1": [
                                "10.72",
                                "125.99",
                                "01-JAN-00:15",
                                "738.04",
                                "02-JAN-08:15"
                            ],
                            "InteriorEquipment:Electricity:Zone:PERIMETER_ZN_2": [
                                "6.36",
                                "74.74",
                                "01-JAN-00:15",
                                "437.82",
                                "02-JAN-08:15"
                            ],
                            "InteriorEquipment:Electricity:Zone:PERIMETER_ZN_3": [
                                "10.72",
                                "125.99",
                                "01-JAN-00:15",
                                "738.04",
                                "02-JAN-08:15"
                            ],
                            "InteriorEquipment:Electricity:Zone:PERIMETER_ZN_4": [
                                "6.36",
                                "74.74",
                                "01-JAN-00:15",
                                "437.82",
                                "02-JAN-08:15"
                            ],
                            "InteriorLights:Electricity": [
                                "25.61",
                                "110.04",
                                "01-JAN-00:15",
                                "2461.51",
                                "02-JAN-16:45"
                            ],
                            "InteriorLights:Electricity:SpaceType:LOBBY_ALL_OTHERS": [
                                "5.22",
                                "24.42",
                                "01-JAN-00:15",
                                "546.33",
                                "02-JAN-16:45"
                            ],
                            "InteriorLights:Electricity:SpaceType:OFFICE_ENCLOSED": [
                                "11.91",
                                "53.40",
                                "01-JAN-00:15",
                                "1194.50",
                                "02-JAN-16:45"
                            ],
                            "InteriorLights:Electricity:SpaceType:OFFICE_OPEN_PLAN": [
                                "8.49",
                                "32.22",
                                "01-JAN-00:15",
                                "720.68",
                                "02-JAN-08:15"
                            ],
                            "InteriorLights:Electricity:Zone:CORE_ZN": [
                                "8.49",
                                "32.22",
                                "01-JAN-00:15",
                                "720.68",
                                "02-JAN-08:15"
                            ],
                            "InteriorLights:Electricity:Zone:PERIMETER_ZN_1": [
                                "5.22",
                                "24.42",
                                "01-JAN-00:15",
                                "546.33",
                                "02-JAN-16:45"
                            ],
                            "InteriorLights:Electricity:Zone:PERIMETER_ZN_2": [
                                "3.20",
                                "14.49",
                                "01-JAN-00:15",
                                "324.09",
                                "02-JAN-16:45"
                            ],
                            "InteriorLights:Electricity:Zone:PERIMETER_ZN_3": [
                                "5.52",
                                "24.42",
                                "01-JAN-00:15",
                                "546.33",
                                "02-JAN-16:45"
                            ],
                            "InteriorLights:Electricity:Zone:PERIMETER_ZN_4": [
                                "3.19",
                                "14.49",
                                "01-JAN-00:15",
                                "324.09",
                                "02-JAN-16:45"
                            ],
                            "LightsWired:InteriorLights:Electricity": [
                                "25.61",
                                "110.04",
                                "01-JAN-00:15",
                                "2461.51",
                                "02-JAN-16:45"
                            ],
                            "LightsWired:InteriorLights:Electricity:SpaceType:LOBBY_ALL_OTHERS": [
                                "5.22",
                                "24.42",
                                "01-JAN-00:15",
                                "546.33",
                                "02-JAN-16:45"
                            ],
                            "LightsWired:InteriorLights:Electricity:SpaceType:OFFICE_ENCLOSED": [
                                "11.91",
                                "53.40",
                                "01-JAN-00:15",
                                "1194.50",
                                "02-JAN-16:45"
                            ],
                            "LightsWired:InteriorLights:Electricity:SpaceType:OFFICE_OPEN_PLAN": [
                                "8.49",
                                "32.22",
                                "01-JAN-00:15",
                                "720.68",
                                "02-JAN-08:15"
                            ],
                            "LightsWired:InteriorLights:Electricity:Zone:CORE_ZN": [
                                "8.49",
                                "32.22",
                                "01-JAN-00:15",
                                "720.68",
                                "02-JAN-08:15"
                            ],
                            "LightsWired:InteriorLights:Electricity:Zone:PERIMETER_ZN_1": [
                                "5.22",
                                "24.42",
                                "01-JAN-00:15",
                                "546.33",
                                "02-JAN-16:45"
                            ],
                            "LightsWired:InteriorLights:Electricity:Zone:PERIMETER_ZN_2": [
                                "3.20",
                                "14.49",
                                "01-JAN-00:15",
                                "324.09",
                                "02-JAN-16:45"
                            ],
                            "LightsWired:InteriorLights:Electricity:Zone:PERIMETER_ZN_3": [
                                "5.52",
                                "24.42",
                                "01-JAN-00:15",
                                "546.33",
                                "02-JAN-16:45"
                            ],
                            "LightsWired:InteriorLights:Electricity:Zone:PERIMETER_ZN_4": [
                                "3.19",
                                "14.49",
                                "01-JAN-00:15",
                                "324.09",
                                "02-JAN-16:45"
                            ],
                            "MiscPlug:InteriorEquipment:Electricity": [
                                "48.30",
                                "567.64",
                                "01-JAN-00:15",
                                "3325.31",
                                "02-JAN-08:15"
                            ],
                            "MiscPlug:InteriorEquipment:Electricity:SpaceType:LOBBY_ALL_OTHERS": [
                                "10.72",
                                "125.99",
                                "01-JAN-00:15",
                                "738.04",
                                "02-JAN-08:15"
                            ],
                            "MiscPlug:InteriorEquipment:Electricity:SpaceType:OFFICE_ENCLOSED": [
                                "23.44",
                                "275.46",
                                "01-JAN-00:15",
                                "1613.68",
                                "02-JAN-08:15"
                            ],
                            "MiscPlug:InteriorEquipment:Electricity:SpaceType:OFFICE_OPEN_PLAN": [
                                "14.14",
                                "166.20",
                                "01-JAN-00:15",
                                "973.59",
                                "02-JAN-08:15"
                            ],
                            "MiscPlug:InteriorEquipment:Electricity:Zone:CORE_ZN": [
                                "14.14",
                                "166.20",
                                "01-JAN-00:15",
                                "973.59",
                                "02-JAN-08:15"
                            ],
                            "MiscPlug:InteriorEquipment:Electricity:Zone:PERIMETER_ZN_1": [
                                "10.72",
                                "125.99",
                                "01-JAN-00:15",
                                "738.04",
                                "02-JAN-08:15"
                            ],
                            "MiscPlug:InteriorEquipment:Electricity:Zone:PERIMETER_ZN_2": [
                                "6.36",
                                "74.74",
                                "01-JAN-00:15",
                                "437.82",
                                "02-JAN-08:15"
                            ],
                            "MiscPlug:InteriorEquipment:Electricity:Zone:PERIMETER_ZN_3": [
                                "10.72",
                                "125.99",
                                "01-JAN-00:15",
                                "738.04",
                                "02-JAN-08:15"
                            ],
                            "MiscPlug:InteriorEquipment:Electricity:Zone:PERIMETER_ZN_4": [
                                "6.36",
                                "74.74",
                                "01-JAN-00:15",
                                "437.82",
                                "02-JAN-08:15"
                            ],
                            "Pumps:Electricity": [
                                "0.00",
                                "0.00",
                                "01-JAN-00:15",
                                "0.00",
                                "02-JAN-07:15"
                            ],
                            "Water Heater:WaterSystems:Electricity": [
                                "18.01",
                                "571.00",
                                "02-MAY-02:45",
                                "571.00",
                                "14-JAN-04:30"
                            ],
                            "WaterSystems:Electricity": [
                                "18.01",
                                "571.00",
                                "02-MAY-02:45",
                                "571.00",
                                "14-JAN-04:30"
                            ]
                        },
                        "TableName": "Annual and Peak Values - Electricity"
                    },
                    {
                        "Cols": [
                            "Natural Gas Annual Value [GJ]",
                            "Natural Gas Minimum Value [W]",
                            "Timestamp of Minimum {TIMESTAMP}",
                            "Natural Gas Maximum Value [W]",
                            "Timestamp of Maximum {TIMESTAMP}"
                        ],
                        "Rows": {
                            "General:Heating:NaturalGas": [
                                "4.64",
                                "0.00",
                                "01-JAN-00:15",
                                "25029.93",
                                "02-JAN-06:15"
                            ],
                            "Heating:NaturalGas": [
                                "4.64",
                                "0.00",
                                "01-JAN-00:15",
                                "25029.93",
                                "02-JAN-06:15"
                            ],
                            "NaturalGas:Facility": [
                                "4.64",
                                "0.00",
                                "01-JAN-00:15",
                                "25029.93",
                                "02-JAN-06:15"
                            ],
                            "NaturalGas:HVAC": [
                                "4.64",
                                "0.00",
                                "01-JAN-00:15",
                                "25029.93",
                                "02-JAN-06:15"
                            ]
                        },
                        "TableName": "Annual and Peak Values - Natural Gas"
                    }]
            },
            {
                "For": "Entire Facility",
                "ReportName": "LEEDsummary",
                "Tables": [
                    {
                        "Cols": [
                            "Data"
                        ],
                        "Rows": {
                            "Number of hours cooling loads not met": [
                                "31.75"
                            ],
                            "Number of hours heating loads not met": [
                                "33.50"
                            ],
                            "Number of hours not met": [
                                "65.25"
                            ]
                        },
                        "TableName": "EAp2-2. Advisory Messages"
                    }]
            },
            {
                "For": "Entire Facility",
                "ReportName": "SystemSummary",
                "Tables": [
                    {
                        "Cols": [
                            "During Heating [hr]",
                            "During Cooling [hr]",
                            "During Occupied Heating [hr]",
                            "During Occupied Cooling [hr]"
                        ],
                        "Rows": {
                            "ATTIC": [
                                "0.00",
                                "0.00",
                                "0.00",
                                "0.00"
                            ],
                            "CORE_ZN": [
                                "4.00",
                                "10.75",
                                "4.00",
                                "10.75"
                            ],
                            "Facility": [
                                "71.00",
                                "33.75",
                                "33.50",
                                "31.75"
                            ],
                            "PERIMETER_ZN_1": [
                                "29.00",
                                "24.00",
                                "19.00",
                                "22.25"
                            ],
                            "PERIMETER_ZN_2": [
                                "40.50",
                                "3.00",
                                "25.50",
                                "2.75"
                            ],
                            "PERIMETER_ZN_3": [
                                "44.25",
                                "0.25",
                                "24.75",
                                "0.25"
                            ],
                            "PERIMETER_ZN_4": [
                                "42.00",
                                "3.25",
                                "26.00",
                                "3.25"
                            ]
                        },
                        "TableName": "Time Setpoint Not Met"
                    }]
            },
        ]

        added_project, added_instance = t.add_simulation_outputs()

        expected_project = {'id': 'output_1',
                            'performance_cost_index': -1.0,
                            'baseline_building_unregulated_energy_cost': -1.0,
                            'baseline_building_regulated_energy_cost': -1.0,
                            'baseline_building_performance_energy_cost': -1.0,
                            'total_area_weighted_building_performance_factor': -1.0,
                            'performance_cost_index_target': -1.0,
                            'total_proposed_building_energy_cost_including_renewable_energy': -1.0,
                            'total_proposed_building_energy_cost_excluding_renewable_energy': -1.0,
                            'percent_renewable_energy_savings': -1.0}

        expected_instance = {
            'id': 'output_instance_1',
            'unmet_load_hours': 65.25,
            'unmet_load_hours_heating': 33.5,
            'unmet_occupied_load_hours_heating': 33.5,
            'unmet_load_hours_cooling': 31.75,
            'unmet_occupied_load_hours_cooling': 31.75,
            'annual_source_results': [
                {'id': 'source_results_ELECTRICITY',
                 'energy_source': 'ELECTRICITY',
                 'annual_consumption': 138.47,
                 'annual_demand': 14959.75,
                 'annual_cost': -1.0},
                {'id': 'source_results_NATURAL_GAS',
                 'energy_source': 'NATURAL_GAS',
                 'annual_consumption': 4.64,
                 'annual_demand': 25029.93, 'annual_cost': -1.0}],
            'building_peak_cooling_load': -1,
            'annual_end_use_results': [
                {'id': 'end_use_ELECTRICITY-Cooling', 'type': 'SPACE_COOLING',
                 'energy_source': 'ELECTRICITY', 'annual_site_energy_use': 12.08,
                 'annual_site_coincident_demand': 0.0,
                 'annual_site_non_coincident_demand': 5318.53,
                 'is_regulated': True},
                {'id': 'end_use_ELECTRICITY-Exterior Lighting',
                 'type': 'EXTERIOR_LIGHTING', 'energy_source': 'ELECTRICITY',
                 'annual_site_energy_use': 5.68,
                 'annual_site_coincident_demand': 611.3,
                 'annual_site_non_coincident_demand': 611.3,
                 'is_regulated': True},
                {'id': 'end_use_ELECTRICITY-Fans',
                 'type': 'FANS_INTERIOR_VENTILATION',
                 'energy_source': 'ELECTRICITY',
                 'annual_site_energy_use': 19.66,
                 'annual_site_coincident_demand': 1712.96,
                 'annual_site_non_coincident_demand': 1712.96,
                 'is_regulated': True},
                {'id': 'end_use_ELECTRICITY-Heating', 'type': 'SPACE_HEATING',
                 'energy_source': 'ELECTRICITY', 'annual_site_energy_use': 9.13,
                 'annual_site_coincident_demand': 6277.68,
                 'annual_site_non_coincident_demand': 7051.57,
                 'is_regulated': True},
                {'id': 'end_use_ELECTRICITY-Interior Equipment',
                 'type': 'MISC_EQUIPMENT', 'energy_source': 'ELECTRICITY',
                 'annual_site_energy_use': 48.3,
                 'annual_site_coincident_demand': 3325.31,
                 'annual_site_non_coincident_demand': 3325.31,
                 'is_regulated': True},
                {'id': 'end_use_ELECTRICITY-Interior Lighting',
                 'type': 'INTERIOR_LIGHTING', 'energy_source': 'ELECTRICITY',
                 'annual_site_energy_use': 25.61,
                 'annual_site_coincident_demand': 2461.51,
                 'annual_site_non_coincident_demand': 2461.51,
                 'is_regulated': True},
                {'id': 'end_use_NATURAL_GAS-Heating', 'type': 'SPACE_HEATING',
                 'energy_source': 'NATURAL_GAS', 'annual_site_energy_use': 4.64,
                 'annual_site_coincident_demand': 25029.93,
                 'annual_site_non_coincident_demand': 25029.93,
                 'is_regulated': True}]}

        self.assertEqual(added_project, expected_project)
        self.assertEqual(added_instance, expected_instance)
