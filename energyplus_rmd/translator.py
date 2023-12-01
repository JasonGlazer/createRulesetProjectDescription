from pathlib import Path
from typing import Dict
from copy import deepcopy
from datetime import datetime
from datetime import timezone

from energyplus_rmd.input_file import InputFile
from energyplus_rmd.output_file import OutputFile
from energyplus_rmd.validator import Validator
from energyplus_rmd.status_reporter import StatusReporter


class Translator:
    """This class reads in the input files and does the heavy lifting to write output files"""

    def __init__(self, epjson_file_path: Path, rmd_name=None):
        print(f"Reading epJSON input file at {epjson_file_path}")
        self.input_file = InputFile(epjson_file_path)
        self.epjson_object = self.input_file.epjson_object
        self.json_results_object = self.input_file.json_results_object
        print(f"Reading EnergyPlus results JSON file: {self.input_file.json_results_input_path}")
        self.json_hourly_results_object = self.input_file.json_hourly_results_object
        print(f"Reading EnergyPlus hourly results JSON file: {self.input_file.json_hourly_results_input_path}")

        # Modify export name - to avoid long execution line set by windows
        output_path = Path(str(epjson_file_path.parent.absolute()) + "\\" + rmd_name) if rmd_name else epjson_file_path
        self.output_file = OutputFile(output_path)
        self.rmd_file_path = self.output_file.rmd_file_path
        print(f"Writing output file to {self.rmd_file_path}")

        self.validator = Validator()
        self.status_reporter = StatusReporter()

        self.project_description = {}
        self.model_description = {}
        self.building = {}
        self.building_segment = {}
        self.surfaces_by_zone = {}
        self.schedules_used_names = []
        self.terminals_by_zone = {}
        self.serial_number = 0
        self.id_used = set()

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
        if 'Construction:FfactorGroundFloor' in self.epjson_object:
            constructions_in.update(self.epjson_object['Construction:FfactorGroundFloor'])
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
                    materials.append(deepcopy(material))
                elif material_name in materials_no_mass_in:
                    material_no_mass_in = materials_no_mass_in[material_name]
                    material = {
                        'id': material_name,
                        'r_value': material_no_mass_in['thermal_resistance']
                    }
                    materials.append(deepcopy(material))
            construction = {'id': construction_name,
                            'surface_construction_input_option': 'LAYERS',
                            'primary_layers': materials
                            }
            constructions[construction_name.upper()] = deepcopy(construction)
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
                         'building_open_schedule': 'always_1',
                         'has_site_shading': self.is_site_shaded(),
                         'building_segments': [self.building_segment, ]}

        self.model_description = {'id': 'Only model description',
                                  'notes': 'this file contains only a single model description',
                                  'buildings': [self.building, ]}

        time_stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
        self.project_description = {'id': 'project description root',
                                    'notes': 'generated by createRulesetModelDescription from EnergyPlus',
                                    'output_format_type': 'OUTPUT_SCHEMA_ASHRAE901_2019',
                                    'data_timestamp': time_stamp,
                                    'ruleset_model_descriptions': [self.model_description, ],
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
            'file_name': weather_file,
            'data_source_type': 'OTHER',
            'climate_zone': climate_zone
        }
        if cooling_design_day_option:
            weather['cooling_design_day_type'] = cooling_design_day_option
        if heating_design_day_option:
            weather['heating_design_day_type'] = heating_design_day_option
        self.project_description['weather'] = weather
        return weather

    def add_calendar(self):
        tabular_reports = self.json_results_object['TabularReports']
        calendar = {}
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'InitializationSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'Environment':
                        rows = table['Rows']
                        row_keys = list(rows.keys())
                        cols = table['Cols']
                        environment_name_column = cols.index('Environment Name')
                        start_date_column = cols.index('Start Date')
                        start_day_of_week_column = cols.index('Start DayOfWeek')
                        duration_column = cols.index('Duration {#days}')
                        for row_key in row_keys:
                            environment_name = rows[row_key][environment_name_column]
                            start_date = rows[row_key][start_date_column]
                            duration = float(rows[row_key][duration_column])
                            calendar['notes'] = 'name environment: ' + environment_name
                            # add day of week for january 1 only if the start date is 01/01/xxxx
                            start_date_parts = start_date.split('/')
                            if start_date_parts[0] == '01' and start_date_parts[1] == '01':
                                start_day_of_week = rows[row_key][start_day_of_week_column]
                                calendar['day_of_week_for_january_1'] = start_day_of_week.upper()
                            if duration == 365:
                                calendar['is_leap_year'] = False
                            elif duration == 366:
                                calendar['is_leap_year'] = True
                            self.project_description['calendar'] = calendar
                    if table['TableName'] == 'Environment:Daylight Saving':
                        rows = table['Rows']
                        row_keys = list(rows.keys())
                        cols = table['Cols']
                        daylight_savings_column = cols.index('Daylight Saving Indicator')
                        for row_key in row_keys:
                            daylight_savings = rows[row_key][daylight_savings_column]
                            calendar['has_daylight_saving_time'] = daylight_savings == 'Yes'
        return calendar

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
                            if zone_name.upper() in self.terminals_by_zone:
                                zone['terminals'] = self.terminals_by_zone[zone_name.upper()]
                break
        self.building_segment['zones'] = zones
        return zones

    def add_spaces(self):
        tabular_reports = self.json_results_object['TabularReports']
        spaces = {}
        lights_by_space = self.gather_interior_lighting()
        people_schedule_by_zone = self.gather_people_schedule_by_zone()
        equipment_by_zone = self.gather_miscellaneous_equipment()
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
                        space_type_column = cols.index('Space Type')
                        tags_column = cols.index('Tags')
                        for space_name in space_names:
                            floor_area = float(rows[space_name][area_column])
                            people_density = float(rows[space_name][people_density_column])
                            zone_name = rows[space_name][zone_name_column]
                            space_type = rows[space_name][space_type_column]
                            tags = rows[space_name][tags_column]

                            if people_density > 0:
                                people = floor_area / people_density
                            else:
                                people = 0
                            space = {'id': space_name, 'floor_area': floor_area,
                                     'number_of_occupants': round(people, 2)}
                            if zone_name in people_schedule_by_zone:
                                space['occupant_multiplier_schedule'] = people_schedule_by_zone[zone_name]
                            if space_name in lights_by_space:
                                space['interior_lighting'] = lights_by_space[space_name]
                            if space_type:
                                if self.validator.is_in_901_enumeration('LightingSpaceOptions2019ASHRAE901TG37',
                                                                        space_type.upper()):
                                    space['lighting_space_type'] = space_type
                                # print(space, rows[space_name][zone_name_column])
                            if zone_name in equipment_by_zone:
                                misc_equipments = equipment_by_zone[zone_name]
                                # remove power density and replace with power
                                for misc_equipment in misc_equipments:
                                    power_density = misc_equipment.pop('POWER DENSITY')
                                    power = power_density * floor_area
                                    misc_equipment['power'] = power
                                    space['miscellaneous_equipment'] = misc_equipments
                            tag_list = []
                            if tags:
                                if ',' in tags:
                                    tag_list = tags.split(', ')
                                else:
                                    tag_list.append(tags)
                            if tag_list:
                                first_tag = tag_list.pop(0)
                                if self.validator.is_in_901_enumeration('VentilationSpaceOptions2019ASHRAE901',
                                                                        first_tag.upper()):
                                    space['ventilation_space_type'] = first_tag
                            if tag_list:
                                second_tag = tag_list.pop(0)
                                if self.validator.is_in_901_enumeration('ServiceWaterHeatingSpaceOptions2019ASHRAE901',
                                                                        second_tag.upper()):
                                    space['service_water_heating_space_type'] = second_tag
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

    def gather_miscellaneous_equipment(self):
        miscellaneous_equipments_by_zone = {}  # dictionary by space name containing list of data elements
        tabular_reports = self.json_results_object['TabularReports']
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'InitializationSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'ElectricEquipment Internal Gains Nominal':
                        rows = table['Rows']
                        row_keys = list(rows.keys())
                        cols = table['Cols']
                        equipment_name_column = cols.index('Name')
                        zone_name_column = cols.index('Zone Name')
                        power_density_column = cols.index('Equipment/Floor Area {W/m2}')
                        schedule_name_column = cols.index('Schedule Name')
                        latent_column = cols.index('Fraction Latent')
                        lost_column = cols.index('Fraction Lost')
                        for row_key in row_keys:
                            equipment_name = rows[row_key][equipment_name_column]
                            zone_name = rows[row_key][zone_name_column]
                            power_density = float(rows[row_key][power_density_column])
                            schedule_name = rows[row_key][schedule_name_column]
                            latent = float(rows[row_key][latent_column])
                            lost = float(rows[row_key][lost_column])
                            sensible = 1 - (latent + lost)
                            equipment = {
                                'id': equipment_name,
                                'energy_type': 'ELECTRICITY',
                                'multiplier_schedule': schedule_name,
                                'sensible_fraction': sensible,
                                'latent_fraction': latent,
                                'POWER DENSITY': power_density
                            }
                            self.schedules_used_names.append(schedule_name)
                            # print(equipment)
                            if zone_name.upper() not in miscellaneous_equipments_by_zone:
                                miscellaneous_equipments_by_zone[zone_name.upper()] = [equipment, ]
                            else:
                                miscellaneous_equipments_by_zone[zone_name.upper()].append(equipment)
        return miscellaneous_equipments_by_zone

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
        do_surfaces_cast_shadows = self.are_shadows_cast_from_surfaces()
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
                                'adjacent_to': adjacent_to,
                                'does_cast_shade': do_surfaces_cast_shadows
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
                                surface['construction'] = deepcopy(constructions[construction_name])
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
                            design_volume_flow_rate = float(rows[row_key][design_volume_flow_rate_column])
                            schedule_name = rows[row_key][schedule_name_column]
                            infiltration = {
                                'id': infiltration_name,
                                'modeling_method': 'WEATHER_DRIVEN',
                                'algorithm_name': 'ZoneInfiltration',
                                'flow_rate': design_volume_flow_rate,
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
            design_heating_hourly = []
            design_cooling_hourly = []
            for row in rows:
                timestamp = list(row.keys())[0]
                values_at_time_step = row[timestamp]
                hourly.append(values_at_time_step[count])
            if len(hourly) < 8760:
                print(f'The hourly schedule: {schedule_name} has less than the 8760 values expected. '
                      f'{len(hourly)} values found')
            if len(hourly) == 8808:
                # In this scenario, we have two sizing day data in the schedule. Take them out.
                design_cooling_hourly = hourly[:24]
                design_heating_hourly = hourly[24:48]
                hourly = hourly[48:]
            schedule = {
                'id': schedule_name,
                'sequence_type': 'HOURLY',
                'hourly_values': hourly,
                'hourly_heating_design_day': design_heating_hourly,
                'hourly_cooling_design_day': design_cooling_hourly,
            }
            schedules.append(schedule)
        self.model_description['schedules'] = schedules

    def is_site_shaded(self):
        tabular_reports = self.json_results_object['TabularReports']
        total_detached = 0  # assume no shading surfaces
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'ObjectCountSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'Surfaces by Class':
                        rows = table['Rows']
                        cols = table['Cols']
                        total_column = cols.index('Total')
                        building_detached = rows['Building Detached Shading'][total_column]
                        fixed_detached = rows['Fixed Detached Shading'][total_column]
                        try:
                            total_detached = float(building_detached) + float(fixed_detached)
                        except ValueError:
                            print('non-numeric value found in ObjectCountSummary:Surfaces by Class:* Detached Shading')
        return total_detached > 0

    def are_shadows_cast_from_surfaces(self):
        tabular_reports = self.json_results_object['TabularReports']
        shadows_cast = True  # assume shadows are cast
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'InitializationSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'Building Information':
                        rows = table['Rows']
                        cols = table['Cols']
                        solar_distribution_column = cols.index('Solar Distribution')
                        solar_distribution = rows['1'][solar_distribution_column]
                        # shadows are always cast unless Solar Distribution is set to MinimalShadowing
                        shadows_cast = solar_distribution != 'MinimalShadowing'
        return shadows_cast

    def add_simple_hvac(self):
        # only handles adding the heating and cooling capacities for the small office and medium office DOE prototypes
        hvac_systems = []
        tabular_reports = self.json_results_object['TabularReports']
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'CoilSizingDetails':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'Coils':
                        rows = table['Rows']
                        row_keys = list(rows.keys())
                        cols = table['Cols']
                        coil_type_column = cols.index('Coil Type')
                        hvac_type_column = cols.index('HVAC Type')
                        hvac_name_column = cols.index('HVAC Name')
                        zone_names_column = cols.index('Zone Name(s)')
                        total_capacity_column = cols.index('Coil Final Gross Total Capacity [W]')
                        sensible_capacity_column = cols.index('Coil Final Gross Sensible Capacity [W]')
                        terminal_capacity_by_zone = dict()
                        for row_key in row_keys:
                            hvac_type = rows[row_key][hvac_type_column]
                            zone_name = rows[row_key][zone_names_column]
                            total_capacity = float(rows[row_key][total_capacity_column])
                            if hvac_type == 'ZONEHVAC:AIRDISTRIBUTIONUNIT':
                                terminal_capacity_by_zone[zone_name] = total_capacity
                        for row_key in row_keys:
                            coil_type = rows[row_key][coil_type_column]
                            hvac_type = rows[row_key][hvac_type_column]
                            hvac_name = rows[row_key][hvac_name_column]
                            zone_names = rows[row_key][zone_names_column]
                            if ';' in zone_names:
                                zone_name_list = zone_names.split(';')
                            else:
                                zone_name_list = [zone_names, ]
                            zone_name_list = [name.strip() for name in zone_name_list if name]
                            # print(zone_name_list)
                            total_capacity = float(rows[row_key][total_capacity_column])
                            sensible_capacity = float(rows[row_key][sensible_capacity_column])
                            heating_system = {}
                            cooling_system = {}
                            if hvac_type == 'AirLoopHVAC':
                                if 'HEATING' in coil_type.upper():
                                    heating_system['id'] = hvac_name + '-heating'
                                    heating_system['design_capacity'] = total_capacity
                                elif 'COOLING' in coil_type.upper():
                                    cooling_system['id'] = hvac_name + '-cooling'
                                    cooling_system['design_total_cool_capacity'] = total_capacity
                                    cooling_system['design_sensible_cool_capacity'] = sensible_capacity
                                hvac_system_list = list(filter(lambda x: (x['id'] == hvac_name), hvac_systems))
                                if hvac_system_list:
                                    hvac_system = hvac_system_list[0]
                                else:
                                    hvac_system = {'id': hvac_name}
                                if heating_system:
                                    hvac_system['heating_system'] = heating_system
                                if cooling_system:
                                    hvac_system['cooling_system'] = cooling_system
                                # print(hvac_system)
                                hvac_systems.append(hvac_system)
                                for zone in zone_name_list:
                                    terminal = {
                                        'id': zone + '-terminal',
                                        'served_by_heating_ventilating_air_conditioning_system': hvac_name
                                    }
                                    if zone in terminal_capacity_by_zone:
                                        terminal['heating_capacity'] = terminal_capacity_by_zone[zone]
                                    self.terminals_by_zone[zone.upper()] = [terminal, ]
        self.building_segment['heating_ventilating_air_conditioning_systems'] = hvac_systems
        # print(self.terminals_by_zone)
        return hvac_systems, self.terminals_by_zone

    def ensure_all_id_unique(self):
        self.add_serial_number_nested(self.model_description, 'id')

    def add_serial_number_nested(self, in_dict, key):
        for k, v in in_dict.items():
            if key == k:
                in_dict[k] = self.replace_serial_number(v)
            elif isinstance(v, dict):
                self.add_serial_number_nested(v, key)
            elif isinstance(v, list):
                for o in v:
                    if isinstance(o, dict):
                        self.add_serial_number_nested(o, key)

    def replace_serial_number(self, original_id):
        index = original_id.rfind('~~~')
        if index == -1:
            if original_id in self.id_used:
                self.serial_number += 1
                new_id = original_id + '~~~' + str(self.serial_number).zfill(8)
                self.id_used.add(new_id)
                return new_id
            else:
                self.id_used.add(original_id)
                return original_id
        else:
            self.serial_number += 1
            root_id = original_id[:index]
            new_id = root_id + '~~~' + str(self.serial_number).zfill(8)
            self.id_used.add(new_id)
            return new_id

    def process(self):
        epjson = self.epjson_object
        Translator.validate_input_contents(epjson)
        self.create_skeleton()
        self.add_weather()
        self.add_calendar()
        self.surfaces_by_zone = self.get_zone_for_each_surface()
        self.add_simple_hvac()
        self.add_zones()
        self.add_spaces()
        self.add_exterior_lighting()
        self.add_schedules()
        self.ensure_all_id_unique()
        passed, message = self.validator.validate_rmd(self.project_description)
        if not passed:
            print(message)
        self.output_file.write(self.project_description)
        self.status_reporter.generate()
