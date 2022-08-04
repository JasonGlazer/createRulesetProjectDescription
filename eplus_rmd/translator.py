from pathlib import Path
from typing import Dict

from eplus_rmd.input_file import InputFile
from eplus_rmd.output_file import OutputFile
from eplus_rmd.validator import Validator
from eplus_rmd.status_reporter import StatusReporter


class Translator:
    """This class reads in the input files and does the heavy lifting to write output files"""

    def __init__(self, epjson_file_path: Path):
        print(f"Reading epJSON input file at {str(epjson_file_path)}")
        self.input_file = InputFile(epjson_file_path)
        self.epjson_object = self.input_file.epjson_object
        self.json_results_object = self.input_file.json_results_object
        print(f"Reading EnergyPlus results JSON file: {str(self.input_file.json_results_input_path)}")
        self.json_hourly_results_object = self.input_file.json_hourly_results_object
        print(f"Reading EnergyPlus hourly results JSON file: {str(self.input_file.json_hourly_results_input_path)}")

        self.output_file = OutputFile(epjson_file_path)
        self.rmd_file_path = self.output_file.rmd_file_path
        print(f"Writing output file to {str(self.rmd_file_path)}")

        self.validator = Validator()
        self.status_reporter = StatusReporter(epjson_file_path)

        self.rmd = {}
        self.instance = {}
        self.building = {}
        self.building_segment = {}
        self.surfaces_by_zone = {}
        self.schedules_used_names = []

    @staticmethod
    def validate_input_contents(input_json: Dict):
        if 'Version' not in input_json:
            raise Exception("Did not find Version key in input file epJSON contents, aborting")
        if 'Version 1' not in input_json['Version']:
            raise Exception("Did not find \"Version 1\" key in input epJSON Version value, aborting")
        if "version_identifier" not in input_json['Version']['Version 1']:
            raise Exception("Did not find \"version_identifier\" key in input epJSON Version value, aborting")

    def get_building_name(self):
        building_input = self.epjson_object['Building']
        return list(building_input.keys())[0]

    def get_zone_for_each_surface(self):
        surfaces_to_zone = {}
        if 'BuildingSurface:Detailed' in self.epjson_object:
            building_surface_detailed = self.epjson_object['BuildingSurface:Detailed']
            for surface_name, fields in building_surface_detailed.items():
                if 'zone_name' in fields:
                    surfaces_to_zone[surface_name.upper()] = fields['zone_name'].upper()
        return surfaces_to_zone

    def get_adjacent_surface_for_each_surface(self):
        building_surface_detailed = self.epjson_object['BuildingSurface:Detailed']
        adjacent_by_surface = {}
        for surface_name, fields in building_surface_detailed.items():
            if 'outside_boundary_condition_object' in fields:
                adjacent_by_surface[surface_name.upper()] = fields['outside_boundary_condition_object'].upper()
        return adjacent_by_surface

    def get_constructions_and_materials(self):
        constructions_in = {}
        if 'Construction' in self.epjson_object:
            constructions_in = self.epjson_object['Construction']
        materials_in = {}
        if 'Material' in self.epjson_object:
            materials_in = self.epjson_object['Material']
        materials_no_mass_in = {}
        if 'Material:NoMass' in self.epjson_object:
            materials_no_mass_in = self.epjson_object['Material:NoMass']
        constructions = {}
        for construction_name, layer_dict in constructions_in.items():
            materials = []
            for layer_name, material_name in layer_dict.items():
                if material_name in materials_in:
                    material_in = materials_in[material_name]
                    material = {
                        'id': material_name,
                        'thickness': material_in['thickness'],
                        'thermal_conductivity': material_in['conductivity'],
                        'density': material_in['density'],
                        'specific_heat': material_in['specific_heat']
                    }
                    materials.append(material)
                elif material_name in materials_no_mass_in:
                    material_no_mass_in = materials_no_mass_in[material_name]
                    material = {
                        'id': material_name,
                        'r_value': material_no_mass_in['thermal_resistance']
                    }
                    materials.append(material)
            construction = {'id': construction_name,
                            'surface_construction_input_option': 'LAYERS',
                            'primary_layers': materials
                            }
            constructions[construction_name.upper()] = construction
        return constructions

    def gather_thermostat_setpoint_schedules(self):
        zone_control_thermostats_in = {}
        if 'ZoneControl:Thermostat' in self.epjson_object:
            zone_control_thermostats_in = self.epjson_object['ZoneControl:Thermostat']
        thermostat_setpoint_dual_setpoints_in = {}
        if 'ThermostatSetpoint:DualSetpoint' in self.epjson_object:
            thermostat_setpoint_dual_setpoints_in = self.epjson_object['ThermostatSetpoint:DualSetpoint']
        setpoint_schedules_by_zone = {}
        for zone_control_thermostat_names, zone_control_thermostat_in in zone_control_thermostats_in.items():
            if 'zone_or_zonelist_name' in zone_control_thermostat_in:
                zone_name = zone_control_thermostat_in['zone_or_zonelist_name']
                if zone_control_thermostat_in['control_1_object_type'] == 'ThermostatSetpoint:DualSetpoint':
                    thermostat_setpoint_dual_setpoint = \
                        thermostat_setpoint_dual_setpoints_in[zone_control_thermostat_in['control_1_name']]
                    cooling_schedule = thermostat_setpoint_dual_setpoint['cooling_setpoint_temperature_schedule_name']
                    heating_schedule = thermostat_setpoint_dual_setpoint['heating_setpoint_temperature_schedule_name']
                    setpoint_schedules_by_zone[zone_name.upper()] = {'cool': cooling_schedule,
                                                                     'heat': heating_schedule}
                    self.schedules_used_names.append(cooling_schedule)
                    self.schedules_used_names.append(heating_schedule)
        # print(setpoint_schedules_by_zone)
        return setpoint_schedules_by_zone

    def gather_people_schedule_by_zone(self):
        people_schedule_by_zone = {}
        tabular_reports = self.json_results_object['TabularReports']
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'InitializationSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'People Internal Gains Nominal':
                        rows = table['Rows']
                        row_keys = list(rows.keys())
                        cols = table['Cols']
                        zone_name_column = cols.index('Zone Name')
                        schedule_name_column = cols.index('Schedule Name')
                        for row_key in row_keys:
                            zone_name = rows[row_key][zone_name_column]
                            schedule_name = rows[row_key][schedule_name_column]
                            people_schedule_by_zone[zone_name.upper()] = schedule_name
        # print(people_schedule_by_zone)
        return people_schedule_by_zone

    def create_skeleton(self):
        self.building_segment = {'id': 'segment 1'}

        self.building = {'id': self.get_building_name(),
                         'notes': 'this file contains only a single building',
                         'building_segments': [self.building_segment, ],
                         'building_open_schedule': 'always_1'}

        self.instance = {'id': 'Only instance',
                         'notes': 'this file contains only a single instance',
                         'buildings': [self.building, ]}

        self.rmd = {'id': 'rmd_root',
                    'notes': 'generated by createRulesetModelDescription from EnergyPlus',
                    'ruleset_model_instances': [self.instance, ],
                    }

    def add_weather(self):
        tabular_reports = self.json_results_object['TabularReports']
        weather_file = ''
        climate_zone = ''
        heating_design_day_option = ''
        cooling_design_day_option = ''
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'InputVerificationandResultsSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'General':
                        rows = table['Rows']
                        weather_file = rows['Weather File'][0]
            if tabular_report['ReportName'] == 'ClimaticDataSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'Weather Statistics File':
                        rows = table['Rows']
                        climate_zone = rows['ASHRAE Climate Zone'][0]
                        if climate_zone:
                            climate_zone = 'CZ' + climate_zone
                    if table['TableName'] == 'SizingPeriod:DesignDay':
                        rows = table['Rows']
                        for design_day_names in rows.keys():
                            if '99.6%' in design_day_names:
                                heating_design_day_option = 'HEATING_99_6'
                            elif '99%' in design_day_names or '99.0%' in design_day_names:
                                heating_design_day_option = 'HEATING_99_0'
                            elif '.4%' in design_day_names:
                                cooling_design_day_option = 'COOLING_0_4'
                            elif '1%' in design_day_names or '1.0%' in design_day_names:
                                cooling_design_day_option = 'COOLING_1_0'
                            elif '2%' in design_day_names or '2.0%' in design_day_names:
                                cooling_design_day_option = 'COOLING_2_0'
        weather = {
            'weather_file_name': weather_file,
            'data_source_type': 'OTHER',
            'climate_zone': climate_zone
        }
        if cooling_design_day_option:
            weather['cooling_design_day_type'] = cooling_design_day_option
        if heating_design_day_option:
            weather['heating_design_day_type'] = heating_design_day_option
        self.rmd['weather'] = weather
        return weather

    def add_exterior_lighting(self):
        exterior_lightings = []
        tabular_reports = self.json_results_object['TabularReports']
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'LightingSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'Exterior Lighting':
                        rows = table['Rows']
                        exterior_light_names = list(rows.keys())
                        exterior_light_names.remove('Exterior Lighting Total')
                        cols = table['Cols']
                        total_watt_column = cols.index('Total Watts')
                        schedule_column = cols.index('Schedule Name')
                        type_column = cols.index('Astronomical Clock/Schedule')
                        for exterior_light_name in exterior_light_names:
                            exterior_light = {
                                'id': exterior_light_name,
                                'power': float(rows[exterior_light_name][total_watt_column]),
                            }
                            if rows[exterior_light_name][type_column] == 'AstronomicalClock':
                                exterior_light['multiplier_schedule'] = 'uses_astronomical_clock_not_schedule'
                            else:
                                if rows[exterior_light_name][schedule_column] != '-':
                                    exterior_light['multiplier_schedule'] = rows[exterior_light_name][schedule_column]
                            exterior_lightings.append(exterior_light)
        self.building['exterior_lighting'] = exterior_lightings
        return exterior_lightings

    def add_zones(self):
        tabular_reports = self.json_results_object['TabularReports']
        zones = []
        surfaces_by_surface = self.gather_surfaces()
        setpoint_schedules = self.gather_thermostat_setpoint_schedules()
        infiltration_by_zone = self.gather_infiltration()
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'InputVerificationandResultsSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'Zone Summary':
                        rows = table['Rows']
                        zone_names = list(rows.keys())
                        zone_names.remove('Total')
                        zone_names.remove('Conditioned Total')
                        zone_names.remove('Unconditioned Total')
                        zone_names.remove('Not Part of Total')
                        # print(zone_names)
                        cols = table['Cols']
                        volume_column = cols.index('Volume [m3]')
                        # print(volume_column)
                        for zone_name in zone_names:
                            zone = {'id': zone_name,
                                    'volume': float(rows[zone_name][volume_column]),
                                    }
                            # 'thermostat_cooling_setpoint_schedule': 'always_70',
                            # 'thermostat_heating_setpoint_schedule': 'always_70',
                            # 'minimum_humidity_setpoint_schedule': 'always_0_3',
                            # 'maximum_humidity_setpoint_schedule': 'always_0_8',
                            # 'exhaust_airflow_rate_multiplier_schedule': 'always_1'}
                            zones.append(zone)
                            if zone_name in setpoint_schedules:
                                zone['thermostat_cooling_setpoint_schedule'] = setpoint_schedules[zone_name]['cool']
                                zone['thermostat_heating_setpoint_schedule'] = setpoint_schedules[zone_name]['heat']
                            surfaces = []
                            for key, value in self.surfaces_by_zone.items():
                                if zone_name == value:
                                    if key in surfaces_by_surface:
                                        surfaces.append(surfaces_by_surface[key])
                            zone['surfaces'] = surfaces
                            if zone_name in infiltration_by_zone:
                                zone['infiltration'] = infiltration_by_zone[zone_name]
                break
        self.building_segment['zones'] = zones
        return zones

    def add_spaces(self):
        tabular_reports = self.json_results_object['TabularReports']
        spaces = {}
        lights_by_space = self.gather_interior_lighting()
        people_schedule_by_zone = self.gather_people_schedule_by_zone()
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'InputVerificationandResultsSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'Space Summary':
                        rows = table['Rows']
                        space_names = list(rows.keys())
                        if 'Total' in space_names:
                            space_names.remove('Total')
                        if 'Conditioned Total' in space_names:
                            space_names.remove('Conditioned Total')
                        if 'Unconditioned Total' in space_names:
                            space_names.remove('Unconditioned Total')
                        if 'Not Part of Total' in space_names:
                            space_names.remove('Not Part of Total')
                        # print(space_names)
                        cols = table['Cols']
                        zone_name_column = cols.index('Zone Name')
                        area_column = cols.index('Area [m2]')
                        people_density_column = cols.index('People [m2 per person]')
                        for space_name in space_names:
                            floor_area = float(rows[space_name][area_column])
                            people_density = float(rows[space_name][people_density_column])
                            zone_name = rows[space_name][zone_name_column]
                            if people_density > 0:
                                people = floor_area / people_density
                            else:
                                people = 0
                            space = {'id': space_name, 'floor_area': floor_area,
                                     'number_of_occupants': round(people, 2),
                                     'lighting_space_type': 'OFFICE_ENCLOSED'}
                            if zone_name in people_schedule_by_zone:
                                space['occupant_multiplier_schedule'] = people_schedule_by_zone[zone_name]
                            if space_name in lights_by_space:
                                space['interior_lighting'] = lights_by_space[space_name]
                            # print(space, rows[space_name][zone_name_column])
                            spaces[zone_name] = space
        # insert the space into the corresponding Zone
        for zone in self.building_segment['zones']:
            zone['spaces'] = []
            if zone['id'] in spaces:
                zone['spaces'].append(spaces[zone['id']])
        return spaces

    def gather_interior_lighting(self):
        tabular_reports = self.json_results_object['TabularReports']
        lights = {}  # dictionary by space name containing the lights
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'LightingSummary':
                tables = tabular_report['Tables']

                # gather the daylighting method used by zone name
                daylighting_method_dict = {}
                for table in tables:
                    if table['TableName'] == 'Daylighting':
                        rows = table['Rows']
                        daylighting_names = list(rows.keys())
                        cols = table['Cols']
                        zone_name_column = cols.index('Zone')
                        daylighting_method_column = cols.index('Daylighting Method')
                        for daylighting_name in daylighting_names:
                            zone_name = rows[daylighting_name][zone_name_column]
                            daylighting_method_dict[zone_name] = rows[daylighting_name][daylighting_method_column]

                for table in tables:
                    if table['TableName'] == 'Interior Lighting':
                        rows = table['Rows']
                        int_light_names = list(rows.keys())
                        if 'Interior Lighting Total' in int_light_names:
                            int_light_names.remove('Interior Lighting Total')
                        cols = table['Cols']
                        space_name_column = cols.index('Space Name')
                        zone_name_column = cols.index('Zone Name')
                        schedule_name_column = cols.index('Schedule Name')
                        power_density_column = cols.index('Lighting Power Density [W/m2]')
                        for int_light_name in int_light_names:
                            power_density = float(rows[int_light_name][power_density_column])
                            space_name = rows[int_light_name][space_name_column]
                            zone_name = rows[int_light_name][zone_name_column]
                            schedule_name = rows[int_light_name][schedule_name_column]
                            daylighting_control_type = 'NONE'
                            if zone_name in daylighting_method_dict:
                                native_method = daylighting_method_dict[zone_name]
                                if native_method.find('Continuous'):
                                    daylighting_control_type = 'CONTINUOUS_DIMMING'
                                elif native_method.find('Step'):
                                    daylighting_control_type = 'STEPPED'
                            light = {'id': int_light_name,
                                     'power_per_area': power_density,
                                     'lighting_multiplier_schedule': schedule_name,
                                     'daylighting_control_type': daylighting_control_type,
                                     'are_schedules_used_for_modeling_occupancy_control': True,
                                     'are_schedules_used_for_modeling_daylighting_control': False
                                     }
                            self.schedules_used_names.append(schedule_name)
                            # print(light)
                            if space_name not in lights:
                                lights[space_name] = [light, ]
                            else:
                                lights[space_name].append(light)
        return lights

    # def gather_miscellaneous_equipment(self):
    #     electric_equipments_in = self.epjson_object['ElectricEquipment']
    #     gas_equipments_in = self.epjson_object['GasEquipment']
    #     hot_water_equipments_in = self.epjson_object['HotWaterEquipment']
    #     steam_equipments_in = self.epjson_object['SteamEquipment']
    #     other_equipments_in = self.epjson_object['OtherEquipment']
    #     info_equipments_in = self.epjson_object['ElectricEquipment:ITE:AirCooled']
    #
    #     miscellaneous_equipments_by_zone = {}  # dictionary by zone name containing list of data groups for that zone
    #     for equipment_name, equipment_dict in electric_equipments_in.items():
    #         if 'design_level_calculation_method' in equipment_dict:
    #             method = equipment_dict['design_level_calculation_method'].upper()
    #             if method == 'WATTS/AREA':
    #                 pass
    #             equipment = {'id': equipment_name,
    #                          'energy_type': 'ELECTRICITY'}

    def gather_subsurface(self):
        tabular_reports = self.json_results_object['TabularReports']
        subsurface_by_surface = {}
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'EnvelopeSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'Exterior Fenestration':
                        rows = table['Rows']
                        fenestration_names = list(rows.keys())
                        if 'Non-North Total or Average' in fenestration_names:
                            fenestration_names.remove('Non-North Total or Average')
                        if 'North Total or Average' in fenestration_names:
                            fenestration_names.remove('North Total or Average')
                        if 'Total or Average' in fenestration_names:
                            fenestration_names.remove('Total or Average')
                        cols = table['Cols']
                        glass_area_column = cols.index('Glass Area [m2]')
                        parent_surface_column = cols.index('Parent Surface')
                        frame_area_column = cols.index('Frame Area [m2]')
                        divider_area_column = cols.index('Divider Area [m2]')
                        glass_u_factor_column = cols.index('Glass U-Factor [W/m2-K]')
                        glass_shgc_column = cols.index('Glass SHGC')
                        glass_visible_trans_column = cols.index('Glass Visible Transmittance')
                        assembly_u_factor_column = cols.index('Assembly U-Factor [W/m2-K]')
                        assembly_shgc_column = cols.index('Assembly SHGC')
                        assembly_visible_trans_column = cols.index('Assembly Visible Transmittance')
                        shade_control_column = cols.index('Shade Control')
                        for fenestration_name in fenestration_names:
                            glass_area = float(rows[fenestration_name][glass_area_column])
                            parent_surface_name = rows[fenestration_name][parent_surface_column]
                            frame_area = float(rows[fenestration_name][frame_area_column])
                            divider_area = float(rows[fenestration_name][divider_area_column])
                            glass_u_factor = float(rows[fenestration_name][glass_u_factor_column])
                            glass_shgc = float(rows[fenestration_name][glass_shgc_column])
                            glass_visible_trans = float(rows[fenestration_name][glass_visible_trans_column])
                            assembly_u_factor_str = rows[fenestration_name][assembly_u_factor_column]
                            assembly_shgc_str = rows[fenestration_name][assembly_shgc_column]
                            assembly_visible_trans_str = rows[fenestration_name][assembly_visible_trans_column]
                            if assembly_u_factor_str:
                                u_factor = float(assembly_u_factor_str)
                            else:
                                u_factor = glass_u_factor
                            if assembly_shgc_str:
                                shgc = float(assembly_shgc_str)
                            else:
                                shgc = glass_shgc
                            if assembly_visible_trans_str:
                                visible_trans = float(assembly_visible_trans_str)
                            else:
                                visible_trans = glass_visible_trans
                            shade_control = rows[fenestration_name][shade_control_column]

                            subsurface = {
                                'id': fenestration_name,
                                'classification': 'WINDOW',
                                'glazed_area': glass_area,
                                'opaque_area': frame_area + divider_area,
                                'u_factor': u_factor,
                                'solar_heat_gain_coefficient': shgc,
                                'visible_transmittance': visible_trans,
                                'has_automatic_shades': shade_control == 'Yes'
                            }
                            if parent_surface_name not in subsurface_by_surface:
                                subsurface_by_surface[parent_surface_name] = [subsurface, ]
                            else:
                                subsurface_by_surface[parent_surface_name].append(subsurface)
        # print(subsurface_by_surface)
        return subsurface_by_surface

    def gather_surfaces(self):
        tabular_reports = self.json_results_object['TabularReports']
        surfaces = {}  # dictionary by zone name containing the surface data elements
        constructions = self.get_constructions_and_materials()
        subsurface_by_surface = self.gather_subsurface()
        # print(constructions)
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'EnvelopeSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    is_exterior = table['TableName'] == 'Opaque Exterior'
                    if is_exterior or table['TableName'] == 'Opaque Interior':
                        rows = table['Rows']
                        surface_names = list(rows.keys())
                        cols = table['Cols']
                        construction_name_column = cols.index('Construction')
                        gross_area_column = cols.index('Gross Area [m2]')
                        azimuth_column = cols.index('Azimuth [deg]')
                        tilt_column = cols.index('Tilt [deg]')
                        u_factor_with_film_column = cols.index('U-Factor with Film [W/m2-K]')
                        for surface_name in surface_names:
                            construction_name = rows[surface_name][construction_name_column]
                            gross_area = float(rows[surface_name][gross_area_column])
                            azimuth = float(rows[surface_name][azimuth_column])
                            tilt = float(rows[surface_name][tilt_column])
                            u_factor_with_film_string = rows[surface_name][u_factor_with_film_column]
                            u_factor_with_film = 0
                            if u_factor_with_film_string:
                                u_factor_with_film = float(u_factor_with_film_string)
                            if tilt > 120:
                                surface_classification = 'FLOOR'
                            elif tilt >= 60:
                                surface_classification = 'WALL'
                            else:
                                surface_classification = 'CEILING'
                            if is_exterior:
                                adjacent_to = 'EXTERIOR'
                            else:
                                adjacent_to = 'INTERIOR'
                            surface = {
                                'id': surface_name,
                                'classification': surface_classification,
                                'area': gross_area,
                                'tilt': tilt,
                                'azimuth': azimuth,
                                'adjacent_to': adjacent_to
                            }
                            if not is_exterior:
                                adjacent_surface = self.get_adjacent_surface_for_each_surface()
                                if surface_name in adjacent_surface:
                                    adjacent_surface = adjacent_surface[surface_name]
                                    if adjacent_surface in self.surfaces_by_zone:
                                        surface['adjacent_zone'] = self.surfaces_by_zone[adjacent_surface]
                            if surface_name in subsurface_by_surface:
                                surface['subsurfaces'] = subsurface_by_surface[surface_name]
                            surfaces[surface_name] = surface
                            if construction_name in constructions:
                                surface['construction'] = constructions[construction_name]
                                if u_factor_with_film_string:
                                    surface['construction']['u_factor'] = u_factor_with_film
        # print(surfaces)
        return surfaces

    def gather_infiltration(self):
        infiltration_by_zone = {}
        tabular_reports = self.json_results_object['TabularReports']
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'InitializationSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'ZoneInfiltration Airflow Stats Nominal':
                        rows = table['Rows']
                        row_keys = list(rows.keys())
                        cols = table['Cols']
                        infiltration_name_column = cols.index('Name')
                        zone_name_column = cols.index('Zone Name')
                        design_volume_flow_rate_column = cols.index('Design Volume Flow Rate {m3/s}')
                        schedule_name_column = cols.index('Schedule Name')
                        for row_key in row_keys:
                            infiltration_name = rows[row_key][infiltration_name_column]
                            zone_name = rows[row_key][zone_name_column]
                            design_volumn_flow_rate = float(rows[row_key][design_volume_flow_rate_column])
                            schedule_name = rows[row_key][schedule_name_column]
                            infiltration = {
                                'id': infiltration_name,
                                'modeling_method': 'WEATHER_DRIVEN',
                                'algorithm_name': 'ZoneInfiltration',
                                'infiltration_flow_rate': design_volumn_flow_rate,
                                'multiplier_schedule': schedule_name
                            }
                            self.schedules_used_names.append(schedule_name)
                            # print(infiltration)
                            infiltration_by_zone[zone_name.upper()] = infiltration
        return infiltration_by_zone

    def add_schedules(self):
        unique_schedule_names_used = list(set(self.schedules_used_names))
        unique_schedule_names_used = [name.upper() for name in unique_schedule_names_used]
        output_variables = {}
        if 'Cols' in self.json_hourly_results_object:
            output_variables = self.json_hourly_results_object['Cols']
        selected_names = {}
        for count, output_variable in enumerate(output_variables):
            output_variable_name = output_variable['Variable'].replace(':Schedule Value', '')
            if output_variable_name in unique_schedule_names_used:
                selected_names[output_variable_name] = count
        # print(selected_names)
        rows = {}
        if 'Rows' in self.json_hourly_results_object:
            rows = self.json_hourly_results_object['Rows']
        schedules = []
        for schedule_name, count in selected_names.items():
            hourly = []
            for row in rows:
                timestamp = list(row.keys())[0]
                values_at_time_step = row[timestamp]
                hourly.append(values_at_time_step[count])
            if len(hourly) != 8760:
                print(f'The hourly schedule: {schedule_name} does not have 8760 values as expected. '
                      f'Only {len(hourly)} values found')
            schedule = {
                'id': schedule_name,
                'schedule_sequence_type': 'HOURLY',
                'hourly_values': hourly
            }
            schedules.append(schedule)
        self.instance['schedules'] = schedules

    def process(self):
        epjson = self.epjson_object
        Translator.validate_input_contents(epjson)
        # version_id = epjson['Version']['Version 1']['version_identifier']
        self.create_skeleton()
        self.add_weather()
        self.surfaces_by_zone = self.get_zone_for_each_surface()
        # print(self.surfaces_by_zone)
        self.add_zones()
        self.add_spaces()
        self.add_exterior_lighting()
        self.add_schedules()
        check_validity = self.validator.validate_rmd(self.rmd)
        if not check_validity['passed']:
            print(check_validity['error'])
        self.output_file.write(self.rmd)
        self.status_reporter.generate(self.rmd)