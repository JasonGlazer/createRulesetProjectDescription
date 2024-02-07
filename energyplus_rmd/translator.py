from pathlib import Path
from typing import Dict
from copy import deepcopy
from datetime import datetime
from datetime import timezone

from energyplus_rmd.input_file import InputFile
from energyplus_rmd.output_file import OutputFile
from energyplus_rmd.validator import Validator
from energyplus_rmd.status_reporter import StatusReporter


def energy_source_convert(energy_name_input):
    energy_source_map = {'ELECTRICITY': 'ELECTRICITY',
                         'NATURALGAS': 'NATURAL_GAS',
                         'PROPANE': 'PROPANE',
                         'FUELOIL1': 'FUEL_OIL',
                         'FUELOIL2': 'FUEL_OIL',
                         'DIESEL': 'OTHER',
                         'GASOLINE': 'OTHER',
                         'COAL': 'OTHER',
                         'OTHERFUEL1': 'OTHER',
                         'OTHERFUEL2': 'OTHER'}
    energy_type = energy_name_input.upper().replace(' ', '_')
    return energy_source_map[energy_type]


def heating_type_convert(coil_type):
    coil_map = {'COIL:HEATING:WATER': 'FLUID_LOOP',
                'COIL:HEATING:STEAM': 'FLUID_LOOP',
                'COIL:HEATING:ELECTRIC': 'ELECTRIC_RESISTANCE',
                'COIL:HEATING:ELECTRIC:MULTISTAGE': 'ELECTRIC_RESISTANCE',
                'COIL:HEATING:FUEL': 'FURNACE',
                'COIL:HEATING:GAS:MULTISTAGE': 'FURNACE',
                'COIL:HEATING:DX:SINGLESPEED': 'HEAT_PUMP',
                'COIL:HEATING:DX:MULTISPEED': 'HEAT_PUMP',
                'COIL:HEATING:DX:VARIABLESPEED': 'HEAT_PUMP',
                'COIL:HEATING:WATERTOAIRHEATPUMP:EQUATIONFIT': 'FLUID_LOOP'}
    return coil_map[coil_type.upper()]


def cooling_type_convert(coil_type):
    coil_map = {'COIL:COOLING:WATER': 'FLUID_LOOP',
                'COIL:COOLING:WATER:DETAILEDGEOMETRY': 'FLUID_LOOP',
                'COILSYSTEM:COOLING:WATER': 'FLUID_LOOP',
                'COILSYSTEM:COOLING:WATER:HEATEXCHANGERASSISTED': 'FLUID_LOOP',
                'COIL:COOLING:DX': 'DIRECT_EXPANSION',
                'COIL:COOLING:DX:SINGLESPEED': 'DIRECT_EXPANSION',
                'COIL:COOLING:DX:TWOSPEED': 'DIRECT_EXPANSION',
                'COIL:COOLING:DX:MULTISPEED': 'DIRECT_EXPANSION',
                'COIL:COOLING:DX:VARIABLESPEED': 'DIRECT_EXPANSION',
                'COIL:COOLING:DX:TWOSTAGEWITHHUMIDITYCONTROLMODE': 'DIRECT_EXPANSION',
                'COIL:COOLING:DX:VARIABLEREFRIGERANTFLOW': 'DIRECT_EXPANSION',
                'COIL:COOLING:WATERTOAIRHEATPUMP:PARAMETERESTIMATION': 'DIRECT_EXPANSION',
                'COIL:COOLING:WATERTOAIRHEATPUMP:EQUATIONFIT': 'DIRECT_EXPANSION',
                'COIL:COOLING:WATERTOAIRHEATPUMP:VARIABLESPEEDEQUATIONFIT': 'DIRECT_EXPANSION',
                'COILSYSTEM:COOLING:DX:HEATEXCHANGERASSISTED': 'DIRECT_EXPANSION',
                'COIL:COOLING:DX:SINGLESPEED:THERMALSTORAGE': 'DIRECT_EXPANSION'}
    return coil_map[coil_type.upper()]


def source_from_coil(coil_type):
    source = 'OTHER'
    if 'ELECTRIC' in coil_type.upper() or 'DX' in coil_type.upper():
        source = 'ELECTRICITY'
    elif 'GAS' in coil_type.upper() or 'FUEL' in coil_type.upper():
        source = 'NATURAL_GAS'
    return source


def is_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False


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
                                    'data_version': 1,
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
            for row in rows:
                timestamp = list(row.keys())[0]
                values_at_time_step = row[timestamp]
                hourly.append(values_at_time_step[count])
            if len(hourly) < 8760:
                print(f'The hourly schedule: {schedule_name} has less than the 8760 values expected. '
                      f'{len(hourly)} values found')
            schedule = {
                'id': schedule_name,
                'sequence_type': 'HOURLY',
                'hourly_values': hourly
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

    def add_heating_ventilation_system(self):
        # only handles adding the heating and cooling capacities for the small office and medium office DOE prototypes
        hvac_systems = []
        coil_connections = self.gather_coil_connections()
        cooling_coil_efficiencies = self.gather_cooling_coil_efficiencies()
        heating_coil_efficiencies = self.gather_heating_coil_efficiencies()
        equipment_fans = self.gather_equipment_fans()
        coils_table = self.get_table('CoilSizingDetails', 'Coils')
        if not coils_table:
            return hvac_systems
        rows = coils_table['Rows']
        row_keys = list(rows.keys())
        cols = coils_table['Cols']
        coil_type_column = cols.index('Coil Type')
        hvac_type_column = cols.index('HVAC Type')
        hvac_name_column = cols.index('HVAC Name')
        zone_names_column = cols.index('Zone Name(s)')
        total_capacity_column = cols.index('Coil Final Gross Total Capacity [W]')
        sensible_capacity_column = cols.index('Coil Final Gross Sensible Capacity [W]')
        rated_capacity_column = cols.index('Coil Total Capacity at Rating Conditions [W]')
        rated_sensible_capacity_column = cols.index('Coil Sensible Capacity at Rating Conditions [W]')
        ideal_load_peak_column = cols.index('Coil Total Capacity at Ideal Loads Peak [W]')
        is_autosized_coil_column = cols.index('Autosized Coil Capacity?')
        leaving_drybulb_column = cols.index('Coil Leaving Air Drybulb at Rating Conditions [C]')
        supply_fan_name_for_coil_column = cols.index('Supply Fan Name for Coil')
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
            rated_capacity = float(rows[row_key][rated_capacity_column])
            rated_sensible_capacity = float(rows[row_key][rated_sensible_capacity_column])
            ideal_load_peak = float(rows[row_key][ideal_load_peak_column])
            is_autosized_coil = rows[row_key][is_autosized_coil_column]
            leaving_drybulb = float(rows[row_key][leaving_drybulb_column])
            supply_fan_name_for_coil = rows[row_key][supply_fan_name_for_coil_column]
            if sensible_capacity == -999:
                sensible_capacity = 0  # removes error but not sure if this makes sense
            oversize_ratio = 1.
            if ideal_load_peak != -999 and ideal_load_peak != 0.:
                oversize_ratio = total_capacity / ideal_load_peak
            heating_system = {}
            cooling_system = {}
            if hvac_type == 'AirLoopHVAC':
                if 'HEATING' in coil_type.upper():
                    heating_system['id'] = hvac_name + '-heating'
                    heating_system['design_capacity'] = total_capacity
                    heating_system['type'] = heating_type_convert(coil_type)
                    heating_system['energy_source_type'] = source_from_coil(coil_type)
                    if 'WATER' in coil_type.upper():
                        heating_system['hot_water_loop'] = coil_connections[row_key]['plant_loop_name']
                    if rated_capacity != -999:
                        heating_system['rated_capacity'] = rated_capacity
                    heating_system['oversizing_factor'] = oversize_ratio
                    heating_system['is_autosized'] = is_autosized_coil == 'Yes'
                    if leaving_drybulb != -999:
                        heating_system['heating_coil_setpoint'] = leaving_drybulb
                    metric_types, metric_values = self.process_heating_metrics(row_key, heating_coil_efficiencies)
                    if metric_values:
                        heating_system['efficiency_metric_values'] = metric_values
                        heating_system['efficiency_metric_types'] = metric_types
                    if 'minimum_temperature_compressor' in heating_coil_efficiencies[row_key]:
                        heating_system['heatpump_low_shutoff_temperature'] = heating_coil_efficiencies[row_key][
                            'minimum_temperature_compressor']
                elif 'COOLING' in coil_type.upper():
                    cooling_system['id'] = hvac_name + '-cooling'
                    cooling_system['design_total_cool_capacity'] = total_capacity
                    cooling_system['design_sensible_cool_capacity'] = sensible_capacity
                    cooling_system['type'] = cooling_type_convert(coil_type)
                    if rated_capacity != -999:
                        cooling_system['rated_total_cool_capacity'] = rated_capacity
                    if rated_sensible_capacity != -999:
                        cooling_system['rated_sensible_cool_capacity'] = rated_sensible_capacity
                    cooling_system['oversizing_factor'] = oversize_ratio
                    cooling_system['is_autosized'] = is_autosized_coil == 'Yes'
                    if 'WATER' in coil_type.upper():
                        cooling_system['chilled_water_loop'] = coil_connections[row_key]['plant_loop_name']
                    metric_types, metric_values = self.process_cooling_metrics(row_key, cooling_coil_efficiencies)
                    if metric_values:
                        cooling_system['efficiency_metric_values'] = metric_values
                        cooling_system['efficiency_metric_types'] = metric_types
                hvac_system_list = list(filter(lambda x: (x['id'] == hvac_name), hvac_systems))
                if hvac_system_list:
                    hvac_system = hvac_system_list[0]
                else:
                    hvac_system = {'id': hvac_name}
#                hvac_system = {'id': hvac_name}
                if heating_system:
                    hvac_system['heating_system'] = heating_system
                if cooling_system:
                    hvac_system['cooling_system'] = cooling_system
                # add the fansystem
                if supply_fan_name_for_coil != 'unknown':
                    if supply_fan_name_for_coil in equipment_fans:
                        fan = {'id': supply_fan_name_for_coil}
                        equipment_fan, equipment_fan_extra = equipment_fans[supply_fan_name_for_coil]
                        fan.update(equipment_fan)
                        fan['specification_method'] = 'SIMPLE'
                        fans = [fan, ]
                        fan_system = {'id': supply_fan_name_for_coil + '-fansystem',
                                      'supply_fans': fans}
                        # note cannot differentiate between different types of variables flow fan (INLET_VANE,
                        # DISCHARGE_DAMPER, or VARIABLE_SPEED_DRIVE) so can only see if constant or not
                        if 'type' in equipment_fan_extra:
                            if 'variable' not in equipment_fan_extra['type'].lower():
                                fan_system['fan_control'] = 'CONSTANT'
                        hvac_system['fan_system'] = fan_system
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

    def get_table(self, report_name, table_name):
        tabular_reports = self.json_results_object['TabularReports']
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == report_name:
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == table_name:
                        return table
        return []

    def gather_coil_connections(self):
        connection_by_coil = {}
        table = self.get_table('CoilSizingDetails', 'Coil Connections')
        if not table:
            return connection_by_coil
        rows = table['Rows']
        row_keys = list(rows.keys())
        cols = table['Cols']
        plant_loop_name_column = cols.index('Plant Loop Name')
        for row_key in row_keys:
            plant_loop_name = rows[row_key][plant_loop_name_column]
            connection = {'plant_loop_name': plant_loop_name}
            connection_by_coil[row_key] = connection
        # print(connection_by_coil)
        return connection_by_coil

    def gather_cooling_coil_efficiencies(self):
        coil_efficiencies = {}
        cooling_coils_table = self.get_table('EquipmentSummary', 'Cooling Coils')
        if not cooling_coils_table:
            return coil_efficiencies
        cooling_coils_rows = cooling_coils_table['Rows']
        row_keys = list(cooling_coils_rows.keys())
        cooling_coils_cols = cooling_coils_table['Cols']
        type_column = cooling_coils_cols.index('Type')
        nominal_efficiency_column = cooling_coils_cols.index('Nominal Efficiency [W/W]')
        for row_key in row_keys:
            coil_type = cooling_coils_rows[row_key][type_column]
            coil_efficiency = {'type': coil_type}
            nominal_efficiency_string = cooling_coils_rows[row_key][nominal_efficiency_column]
            if is_float(nominal_efficiency_string):
                nominal_efficiency = float(nominal_efficiency_string)
                coil_efficiency['nominal_eff'] = nominal_efficiency
            coil_efficiencies[row_key] = coil_efficiency
        dx_2017_table = self.get_table('EquipmentSummary', 'DX Cooling Coil Standard Ratings 2017')
        dx_2017_rows = dx_2017_table['Rows']
        dx_2017_row_keys = list(dx_2017_rows.keys())
        dx_2017_cols = dx_2017_table['Cols']
        net_cop_2017_column = dx_2017_cols.index('Standard Rated Net COP [W/W] #2')
        eer_2017_column = dx_2017_cols.index('EER [Btu/W-h] #2')
        seer_2017_column = dx_2017_cols.index('SEER Standard [Btu/W-h] #2,3')
        ieer_2017_column = dx_2017_cols.index('IEER [Btu/W-h] #2')
        for row_key in row_keys:
            if row_key in dx_2017_row_keys:
                coil_efficiencies[row_key]['StandardRatedNetCOP2017'] = float(
                    dx_2017_rows[row_key][net_cop_2017_column])
                coil_efficiencies[row_key]['EER2017'] = float(dx_2017_rows[row_key][eer_2017_column])
                seer2017_string = dx_2017_rows[row_key][seer_2017_column]
                if seer2017_string != 'N/A':
                    coil_efficiencies[row_key]['SEER2017'] = float(seer2017_string)
                coil_efficiencies[row_key]['IEER2017'] = float(dx_2017_rows[row_key][ieer_2017_column])
        dx_2023_table = self.get_table('EquipmentSummary', 'DX Cooling Coil Standard Ratings 2023')
        dx_2023_rows = dx_2023_table['Rows']
        dx_2023_row_keys = list(dx_2023_rows.keys())
        dx_2023_cols = dx_2023_table['Cols']
        net_cop_2023_column = dx_2023_cols.index('Standard Rated Net COP [W/W] #2,4')
        eer_2023_column = dx_2023_cols.index('EER [Btu/W-h] #2,4')
        seer_2023_column = dx_2023_cols.index('SEER Standard [Btu/W-h] #2,3')
        ieer_2023_column = dx_2023_cols.index('IEER [Btu/W-h] #2')
        for row_key in row_keys:
            if row_key in dx_2023_row_keys:
                coil_efficiencies[row_key]['StandardRatedNetCOP2023'] = float(
                    dx_2023_rows[row_key][net_cop_2023_column])
                coil_efficiencies[row_key]['EER2023'] = float(dx_2023_rows[row_key][eer_2023_column])
                seer2023_string = dx_2023_rows[row_key][seer_2023_column]
                if seer2023_string != 'N/A':
                    coil_efficiencies[row_key]['SEER2023'] = float(seer2023_string)
                coil_efficiencies[row_key]['IEER2023'] = float(dx_2023_rows[row_key][ieer_2023_column])
        return coil_efficiencies

    def process_cooling_metrics(self, coil_name, coil_efficiencies):
        metric_types = []
        metric_values = []
        if coil_name in coil_efficiencies:
            coil_efficiency = coil_efficiencies[coil_name]
            if 'StandardRatedNetCOP2017' in coil_efficiency:
                metric_types.append('FULL_LOAD_COEFFICIENT_OF_PERFORMANCE')
                metric_values.append(coil_efficiency['StandardRatedNetCOP2017'])
            if 'EER2017' in coil_efficiency:
                metric_types.append('ENERGY_EFFICIENCY_RATIO')
                metric_values.append(coil_efficiency['EER2017'])
            if 'SEER2017' in coil_efficiency:
                metric_types.append('SEASONAL_ENERGY_EFFICIENCY_RATIO')
                metric_values.append(coil_efficiency['SEER2017'])
            if 'IEER2023' in coil_efficiency:
                metric_types.append('INTEGRATED_ENERGY_EFFICIENCY_RATIO')
                metric_values.append(coil_efficiency['IEER2023'])
        return metric_types, metric_values

    def gather_heating_coil_efficiencies(self):
        coil_efficiencies = {}
        heating_coils_table = self.get_table('EquipmentSummary', 'Heating Coils')
        if not heating_coils_table:
            return coil_efficiencies
        heating_coils_rows = heating_coils_table['Rows']
        coil_row_keys = list(heating_coils_rows.keys())
        heating_coils_cols = heating_coils_table['Cols']
        type_column = heating_coils_cols.index('Type')
        nominal_efficiency_column = heating_coils_cols.index('Nominal Efficiency [W/W]')
        used_as_sup_heat_column = heating_coils_cols.index('Used as Supplementary Heat')
        for row_key in coil_row_keys:
            coil_type = heating_coils_rows[row_key][type_column]
            used_as_sup_heat = 'Y' in heating_coils_rows[row_key][used_as_sup_heat_column]
            coil_efficiency = {'type': coil_type,
                               'used_as_sup_heat': used_as_sup_heat}
            nominal_efficiency_string = heating_coils_rows[row_key][nominal_efficiency_column]
            if is_float(nominal_efficiency_string):
                nominal_efficiency = float(nominal_efficiency_string)
                coil_efficiency['nominal_eff'] = nominal_efficiency
            coil_efficiencies[row_key] = coil_efficiency
        dx_table = self.get_table('EquipmentSummary', 'DX Heating Coils')
        dx_rows = dx_table['Rows']
        dx_row_keys = list(dx_rows.keys())
        dx_cols = dx_table['Cols']
        hspf_column = dx_cols.index('HSPF [Btu/W-h]')
        hspf_region_column = dx_cols.index('Region Number')
        minimum_temperature_column = dx_cols.index('Minimum Outdoor Dry-Bulb Temperature for Compressor Operation')
        for row_key in dx_row_keys:
            if row_key in coil_row_keys:
                coil_efficiencies[row_key]['HSPF'] = float(dx_rows[row_key][hspf_column])
                coil_efficiencies[row_key]['HSPF_region'] = dx_rows[row_key][hspf_region_column]
                coil_efficiencies[row_key]['minimum_temperature_compressor'] = float(
                    dx_rows[row_key][minimum_temperature_column])
        dx2_table = self.get_table('EquipmentSummary', 'DX Heating Coils [ HSPF2 ]')
        dx2_rows = dx2_table['Rows']
        dx2_row_keys = list(dx2_rows.keys())
        dx2_cols = dx2_table['Cols']
        hspf2_column = dx2_cols.index('HSPF2 [Btu/W-h]')
        hspf2_region_column = dx2_cols.index('Region Number')
        for row_key in dx2_row_keys:
            if row_key in coil_row_keys:
                coil_efficiencies[row_key]['HSPF2'] = float(dx2_rows[row_key][hspf2_column])
                coil_efficiencies[row_key]['HSPF2_region'] = dx2_rows[row_key][hspf2_region_column]
        return coil_efficiencies

    def process_heating_metrics(self, coil_name, coil_efficiencies):
        metric_types = []
        metric_values = []
        if coil_name in coil_efficiencies:
            coil_efficiency = coil_efficiencies[coil_name]
            if 'HSPF' in coil_efficiency:
                metric_types.append('HEATING_SEASONAL_PERFORMANCE_FACTOR')
                metric_values.append(coil_efficiency['HSPF'])
            if 'HSPF2' in coil_efficiency:
                metric_types.append('HEATING_SEASONAL_PERFORMANCE_FACTOR_2')
                metric_values.append(coil_efficiency['HSPF2'])
            if 'type' in coil_efficiency:
                if coil_efficiency['type'] == 'Coil:Heating:Fuel':
                    metric_types.append('THERMAL_EFFICIENCY')
                    metric_values.append(coil_efficiency['nominal_eff'])
        return metric_types, metric_values

    def gather_equipment_fans(self):
        equipment_fans = {}
        table = self.get_table('EquipmentSummary', 'Fans')
        if not table:
            return equipment_fans
        rows = table['Rows']
        coil_row_keys = list(rows.keys())
        cols = table['Cols']
        type_column = cols.index('Type')
        total_efficiency_column = cols.index('Total Efficiency [W/W]')
        delta_pressure_column = cols.index('Delta Pressure [pa]')
        max_air_flow_rate_column = cols.index('Max Air Flow Rate [m3/s]')
        rated_electricity_rate_column = cols.index('Rated Electricity Rate [W]')
        motor_heat_in_air_column = cols.index('Motor Heat In Air Fraction')
        fan_energy_index_column = cols.index('Fan Energy Index')
        purpose_column = cols.index('Purpose')
        is_autosized_column = cols.index('Is Autosized')
        motor_eff_column = cols.index('Motor Efficiency')
        motor_heat_to_zone_column = cols.index('Motor Heat to Zone Fraction')
        airloop_name_column = cols.index('Airloop Name')
        for row_key in coil_row_keys:
            max_air_flow_rate = float(rows[row_key][max_air_flow_rate_column])
            is_autosized = 'Y' in rows[row_key][is_autosized_column]
            rated_electricity_rate = float(rows[row_key][rated_electricity_rate_column])
            delta_pressure = float(rows[row_key][delta_pressure_column])
            total_efficiency = float(rows[row_key][total_efficiency_column])
            motor_eff = float(rows[row_key][motor_eff_column])
            motor_heat_in_air = float(rows[row_key][motor_heat_in_air_column])
            motor_heat_to_zone = float(rows[row_key][motor_heat_to_zone_column])
            # extra columns of data not necessarily used now
            type = rows[row_key][type_column]
            fan_energy_index = float(rows[row_key][fan_energy_index_column])
            purpose = rows[row_key][purpose_column]
            airloop_name = rows[row_key][airloop_name_column]
            equipment_fan = {'design_airflow': max_air_flow_rate,
                             'is_airflow_autosized': is_autosized,
                             'design_electric_power': rated_electricity_rate,
                             'design_pressure_rise': delta_pressure,
                             'total_efficiency': total_efficiency,
                             'motor_efficiency': motor_eff,
                             'motor_heat_to_airflow_fraction': motor_heat_in_air,
                             'motor_heat_to_zone_fraction': motor_heat_to_zone}
            fan_extra = {'type': type,
                         'fan_energy_index': fan_energy_index,
                         'purpose': purpose,
                         'airloop_name': airloop_name}
            equipment_fans[row_key] = (equipment_fan, fan_extra)
        return equipment_fans

    def add_chillers(self):
        chillers = []
        tabular_reports = self.json_results_object['TabularReports']
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'EquipmentSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'Chillers':
                        rows = table['Rows']
                        chiller_names = list(rows.keys())
                        cols = table['Cols']
                        plant_loop_name_column = cols.index('Plantloop Name')
                        condenser_loop_name_column = cols.index('Condenser Loop Name')
                        fuel_type_column = cols.index('Fuel Type')
                        reference_capacity_column = cols.index('Reference Capacity[W]')
                        rated_capacity_column = cols.index('Rated Capacity [W]')
                        rated_enter_temp_column = cols.index('Rated Entering Condenser Temperature [C]')
                        rated_leave_temp_column = cols.index('Rated Leaving Evaporator Temperature [C]')
                        min_plr_column = cols.index('Minimum Part Load Ratio')
                        chilled_water_rate_column = cols.index('Design Size Reference Chilled Water Flow Rate [kg/s]')
                        condenser_water_rate_column = cols.index(
                            'Design Size Reference Condenser Fluid Flow Rate [kg/s]')
                        ref_enter_temp_column = cols.index('Reference Entering Condenser Temperature [C]')
                        ref_leave_temp_column = cols.index('Reference Leaving Evaporator Temperature [C]')
                        rated_efficiency_column = cols.index('Rated Efficiency [W/W]')
                        part_load_efficiency_column = cols.index('IPLV in SI Units [W/W]')
                        heat_recovery_loop_name_column = cols.index('Heat Recovery Plantloop Name')
                        heat_recovery_fraction_column = cols.index('Recovery Relative Capacity Fraction')
                        for chiller_name in chiller_names:
                            if chiller_name != 'None':
                                fuel_type = rows[chiller_name][fuel_type_column].upper().replace(' ', '_')
                                chiller = {
                                    'id': chiller_name,
                                    'cooling_loop': rows[chiller_name][plant_loop_name_column],
                                    'condensing_loop': rows[chiller_name][condenser_loop_name_column],
                                    'energy_source_type': fuel_type,
                                    'design_capacity': float(rows[chiller_name][reference_capacity_column]),
                                    'rated_capacity': float(rows[chiller_name][rated_capacity_column]),
                                    'rated_entering_condenser_temperature':
                                        float(rows[chiller_name][rated_enter_temp_column]),
                                    'rated_leaving_evaporator_temperature':
                                        float(rows[chiller_name][rated_leave_temp_column]),
                                    'minimum_load_ratio': float(rows[chiller_name][min_plr_column]),
                                    'design_flow_evaporator': float(rows[chiller_name][chilled_water_rate_column]),
                                    'design_flow_condenser': float(rows[chiller_name][condenser_water_rate_column]),
                                    'design_entering_condenser_temperature':
                                        float(rows[chiller_name][ref_enter_temp_column]),
                                    'design_leaving_evaporator_temperature':
                                        float(rows[chiller_name][ref_leave_temp_column]),
                                    'full_load_efficiency': float(rows[chiller_name][rated_efficiency_column]),
                                    'part_load_efficiency': float(rows[chiller_name][part_load_efficiency_column]),
                                    'part_load_efficiency_metric': 'INTEGRATED_PART_LOAD_VALUE',
                                }
                                if rows[chiller_name][heat_recovery_loop_name_column] != 'N/A':
                                    chiller['heat_recovery_loop'] = rows[chiller_name][heat_recovery_loop_name_column]
                                    chiller['heat_recovery_fraction'] = (
                                        float(rows[chiller_name][heat_recovery_fraction_column]))
                                chillers.append(chiller)
        self.model_description['chillers'] = chillers
        return chillers

    def add_boilers(self):
        boilers = []
        tabular_reports = self.json_results_object['TabularReports']
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'EquipmentSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'Boilers':
                        rows = table['Rows']
                        boiler_names = list(rows.keys())
                        cols = table['Cols']
                        plant_loop_name_column = cols.index('Plantloop Name')
                        reference_capacity_column = cols.index('Reference Capacity [W]')
                        rated_capacity_column = cols.index('Rated Capacity [W]')
                        min_plr_column = cols.index('Minimum Part Load Ratio')
                        fuel_type_column = cols.index('Fuel Type')
                        reference_efficiency_column = cols.index('Reference Efficiency[W/W]')
                        parasitic_load_column = cols.index('Parasitic Electric Load [W]')
                        for boiler_name in boiler_names:
                            if boiler_name != 'None':
                                fuel_type = energy_source_convert(rows[boiler_name][fuel_type_column])
                                boiler = {
                                    'id': boiler_name,
                                    'loop': rows[boiler_name][plant_loop_name_column],
                                    'design_capacity': float(rows[boiler_name][reference_capacity_column]),
                                    'rated_capacity': float(rows[boiler_name][rated_capacity_column]),
                                    'minimum_load_ratio': float(rows[boiler_name][min_plr_column]),
                                    'energy_source_type': fuel_type,
                                    'efficiency_metric': 'THERMAL',
                                    'efficiency': float(rows[boiler_name][reference_efficiency_column]),
                                    'auxiliary_power': float(rows[boiler_name][parasitic_load_column]),
                                }
                                boilers.append(boiler)
        self.model_description['boilers'] = boilers
        return boilers

    def add_heat_rejection(self):
        heat_rejections = []
        tabular_reports = self.json_results_object['TabularReports']
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'EquipmentSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'Cooling Towers and Fluid Coolers':
                        rows = table['Rows']
                        heat_rejection_names = list(rows.keys())
                        cols = table['Cols']
                        loop_name_column = cols.index('Condenser Loop Name')
                        range_column = cols.index('Range [C]')
                        approach_column = cols.index('Approach [C]')
                        fan_power_column = cols.index('Design Fan Power [W]')
                        wet_bulb_column = cols.index('Design Inlet Air Wet-Bulb Temperature [C]')
                        flow_rate_column = cols.index('Design Water Flow Rate [m3/s]')
                        leaving_setpoint_column = cols.index('Leaving Water Setpoint Temperature [C]')
                        for heat_rejection_name in heat_rejection_names:
                            if heat_rejection_name != 'None':
                                heat_rejection = {
                                    'id': heat_rejection_name,
                                    'loop': rows[heat_rejection_name][loop_name_column],
                                    'range': float(rows[heat_rejection_name][range_column]),
                                    'fan_motor_nameplate_power': float(rows[heat_rejection_name][fan_power_column]),
                                    'design_wetbulb_temperature': float(rows[heat_rejection_name][wet_bulb_column]),
                                    'design_water_flowrate': float(rows[heat_rejection_name][flow_rate_column]) * 1000,
                                    'leaving_water_setpoint_temperature':
                                        float(rows[heat_rejection_name][leaving_setpoint_column]),
                                }
                                approach_str = rows[heat_rejection_name][approach_column]
                                if approach_str:
                                    heat_rejection['approach'] = float(approach_str)
                                heat_rejections.append(heat_rejection)
        self.model_description['heat_rejections'] = heat_rejections
        return heat_rejections

    def add_pumps(self):
        pumps = []
        tabular_reports = self.json_results_object['TabularReports']
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == 'EquipmentSummary':
                tables = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == 'Pumps':
                        rows = table['Rows']
                        pump_names = list(rows.keys())
                        cols = table['Cols']
                        plant_loop_name_column = cols.index('Plantloop Name')
                        electricity_column = cols.index('Electricity Rate [W]')
                        head_column = cols.index('Head [pa]')
                        motor_efficiency_column = cols.index('Motor Efficiency [W/W]')
                        type_column = cols.index('Type')
                        water_flow_column = cols.index('Water Flow [m3/s]')
                        is_autosized_column = cols.index('Is Autosized')
                        for pump_name in pump_names:
                            type_str = rows[pump_name][type_column]
                            speed_control = 'FIXED_SPEED'
                            if 'vari' in type_str.lower():
                                speed_control = 'VARIABLE_SPEED'
                            is_autosized = False
                            if 'Y' in rows[pump_name][is_autosized_column]:
                                is_autosized = True
                            pump = {
                                'id': pump_name,
                                'loop_or_piping': rows[pump_name][plant_loop_name_column],
                                'specification_method': 'SIMPLE',
                                'design_electric_power': float(rows[pump_name][electricity_column]),
                                'design_head': float(rows[pump_name][head_column]),
                                'motor_efficiency': float(rows[pump_name][motor_efficiency_column]),
                                'speed_control': speed_control,
                                'design_flow': float(rows[pump_name][water_flow_column]) * 1000,
                                'is_flow_autosized': is_autosized
                            }
                            pumps.append(pump)
        self.model_description['pumps'] = pumps
        return pumps

    def add_simulation_outputs(self):
        source_map = {'Electricity': 'ELECTRICITY',
                      'Natural Gas': 'NATURAL_GAS',
                      'Gasoline': 'OTHER',
                      'Diesel': 'OTHER',
                      'Coal': 'OTHER',
                      'Fuel Oil No 1': 'FUEL_OIL',
                      'Fuel Oil No 2': 'FUEL_OIL',
                      'Propane': 'PROPANE',
                      'Other Fuel 1': 'OTHER',
                      'Other Fuel 2': 'OTHER',
                      'District Cooling': 'OTHER',
                      'District Heating Water': 'OTHER',
                      'District Heating Steam': 'OTHER',
                      'Water': 'OTHER'}
        enduse_map = {'Heating': 'SPACE_HEATING',
                      'Cooling': 'SPACE_COOLING',
                      'Interior Lighting': 'INTERIOR_LIGHTING',
                      'Exterior Lighting': 'EXTERIOR_LIGHTING',
                      'Interior Equipment': 'MISC_EQUIPMENT',
                      'Exterior Equipment': 'OTHER',
                      'Fans': 'FANS_INTERIOR_VENTILATION',
                      'Pumps': 'PUMPS',
                      'Heat Rejection': 'HEAT_REJECTION',
                      'Humidification': 'HUMIDIFICATION',
                      'Heat Recovery': 'HEAT_RECOVERY',
                      'Water Systems': 'SERVICE_WATER_HEATING',
                      'Refrigeration': 'REFRIGERATION_EQUIPMENT',
                      'Generators': 'OTHER'}
        meter_map = {'Heating': 'Heating',
                     'Cooling': 'Cooling',
                     'Interior Lighting': 'InteriorLights',
                     'Exterior Lighting': 'ExteriorLights',
                     'Interior Equipment': 'InteriorEquipment',
                     'Exterior Equipment': 'OTHER',
                     'Fans': 'Fans',
                     'Pumps': 'Pumps',
                     'Heat Rejection': 'HeatRejection',
                     'Humidification': 'Humidification',
                     'Heat Recovery': 'HeatRecovery',
                     'Water Systems': 'WaterSystem',
                     'Refrigeration': 'Refrigeration',
                     'Generators': 'Generators'}
        simulation_output = {}
        abups_enduse_table = self.get_table('AnnualBuildingUtilityPerformanceSummary', 'End Uses')
        if not abups_enduse_table:
            return simulation_output
        abups_enduse_rows = abups_enduse_table['Rows']
        abups_enduse_cols = abups_enduse_table['Cols']
        demand_enduse_table = self.get_table('DemandEndUseComponentsSummary', 'End Uses')
        if not demand_enduse_table:
            return simulation_output
        demand_enduse_rows = demand_enduse_table['Rows']
        #  demand_enduse_cols = demand_enduse_table['Cols']
        meters_elec_table = self.get_table('EnergyMeters', 'Annual and Peak Values - Electricity')
        if not meters_elec_table:
            return simulation_output
        meters_elec_rows = meters_elec_table['Rows']
        meters_elec_cols = meters_elec_table['Cols']
        meters_elec_max_col = meters_elec_cols.index('Electricity Maximum Value [W]')
        meters_gas_table = self.get_table('EnergyMeters', 'Annual and Peak Values - Natural Gas')
        if not meters_gas_table:
            return simulation_output
        meters_gas_rows = meters_gas_table['Rows']
        meters_gas_cols = meters_gas_table['Cols']
        meters_gas_max_col = meters_gas_cols.index('Natural Gas Maximum Value [W]')

        source_results = []
        end_use_results = []
        for col in abups_enduse_cols:
            consumption = float(abups_enduse_rows['Total End Uses'][abups_enduse_cols.index(col)])
            demand = float(demand_enduse_rows['Total End Uses'][abups_enduse_cols.index(col)])  # must be same order
            source = source_map[col.split(' [', 1)[0]]
            if consumption > 0 and 'Water' not in col:
                source_result = {
                    'id': 'source_results_' + source,
                    'energy_source': source,
                    'annual_consumption': consumption,
                    'annual_demand': demand,
                    'annual_cost': -1.,
                }
                source_results.append(source_result)

            for row in abups_enduse_rows:
                if row != 'Total End Uses' and row != '':
                    consumption = float(abups_enduse_rows[row][abups_enduse_cols.index(col)])
                    conincident_demand = float(demand_enduse_rows[row][abups_enduse_cols.index(col)])
                    if consumption > 0 and 'Water' not in row:
                        end_use_result = {
                            'id': 'end_use_' + source + '-' + row,
                            'type': enduse_map[row],
                            'energy_source': source,
                            'annual_site_energy_use': consumption,
                            'annual_site_coincident_demand': conincident_demand,
                            'annual_site_non_coincident_demand': -1.,
                            'is_regulated': True
                        }
                        if source == 'ELECTRICITY':
                            end_use_meter_name = meter_map[row] + ':Electricity'
                            if end_use_meter_name in meters_elec_rows:
                                noncoincident_demand = float(meters_elec_rows[end_use_meter_name][meters_elec_max_col])
                                end_use_result['annual_site_non_coincident_demand'] = noncoincident_demand
                        elif source == 'NATURAL_GAS':
                            end_use_meter_name = meter_map[row] + ':NaturalGas'
                            if end_use_meter_name in meters_gas_rows:
                                noncoincident_demand = float(meters_gas_rows[end_use_meter_name][meters_gas_max_col])
                                end_use_result['annual_site_non_coincident_demand'] = noncoincident_demand

                        end_use_results.append(end_use_result)

        ea_advisory_messages_table = self.get_table('LEEDsummary', 'EAp2-2. Advisory Messages')
        if not ea_advisory_messages_table:
            return simulation_output
        ea_rows = ea_advisory_messages_table['Rows']
        ea_cols = ea_advisory_messages_table['Cols']
        ea_data_column = ea_cols.index('Data')

        time_setpoint_not_met_table = self.get_table('SystemSummary', 'Time Setpoint Not Met')
        if not time_setpoint_not_met_table:
            return simulation_output
        time_rows = time_setpoint_not_met_table['Rows']
        time_cols = time_setpoint_not_met_table['Cols']
        time_heat_occupied_column = time_cols.index('During Occupied Heating [hr]')
        time_cool_occupied_column = time_cols.index('During Occupied Cooling [hr]')

        output_instance = {}
        if ea_advisory_messages_table and time_setpoint_not_met_table:
            output_instance = {
                'id': 'output_instance_1',
                'ruleset_model_type': 'PROPOSED',
                'rotation_angle': 0,
                'unmet_load_hours': float(ea_rows['Number of hours not met'][ea_data_column]),
                'unmet_load_hours_heating': float(ea_rows['Number of hours heating loads not met'][ea_data_column]),
                'unmet_occupied_load_hours_heating': float(time_rows['Facility'][time_heat_occupied_column]),
                'unmet_load_hours_cooling': float(ea_rows['Number of hours cooling loads not met'][ea_data_column]),
                'unmet_occupied_load_hours_cooling': float(time_rows['Facility'][time_cool_occupied_column]),
                'annual_source_results': source_results,
                'building_peak_cooling_load': -1,
                'annual_end_use_results': end_use_results
            }

        simulation_output = {
            'id': 'output_1',
            'output_instance': output_instance,
            'performance_cost_index': -1.,
            'baseline_building_unregulated_energy_cost': -1.,
            'baseline_building_regulated_energy_cost': -1.,
            'baseline_building_performance_energy_cost': -1.,
            'total_area_weighted_building_performance_factor': -1.,
            'performance_cost_index_target': -1.,
            'total_proposed_building_energy_cost_including_renewable_energy': -1.,
            'total_proposed_building_energy_cost_excluding_renewable_energy': -1.,
            'percent_renewable_energy_savings': -1.
        }
        self.model_description['output'] = simulation_output
        return simulation_output

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
        self.gather_coil_connections()
        self.add_heating_ventilation_system()
        self.add_chillers()
        self.add_boilers()
        self.add_heat_rejection()
        self.add_pumps()
        self.add_zones()
        self.add_spaces()
        self.add_exterior_lighting()
        self.add_simulation_outputs()
        self.add_schedules()
        self.ensure_all_id_unique()
        passed, message = self.validator.validate_rmd(self.project_description)
        if not passed:
            print(message)
        self.output_file.write(self.project_description)
        self.status_reporter.generate()
