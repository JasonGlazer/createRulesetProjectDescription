from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from datetime import timezone

from energyplus_rpd.input_file import InputFile
from energyplus_rpd.output_file import OutputFile
from energyplus_rpd.validator import Validator
from energyplus_rpd.status_reporter import StatusReporter
from energyplus_rpd.compliance_parameter_handler import ComplianceParameterHandler

JsonDict = Dict[str, Any]
JsonList = List[Any]
TableRows = Dict[str, JsonList]


def energy_source_convert(energy_name_input: str) -> str:
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


def heating_type_convert(coil_type: str) -> str:
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


def cooling_type_convert(coil_type: str) -> str:
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


def source_from_coil(coil_type: str) -> str:
    source = 'OTHER'
    if 'ELECTRIC' in coil_type.upper() or 'DX' in coil_type.upper():
        source = 'ELECTRICITY'
    elif 'GAS' in coil_type.upper() or 'FUEL' in coil_type.upper():
        source = 'NATURAL_GAS'
    return source


def is_float(string: str) -> bool:
    try:
        float(string)
        return True
    except ValueError:
        return False


def to_float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    value_string = str(value).strip()
    if not value_string or value_string.upper() in {'N/A', 'NA'}:
        return None
    if is_float(value_string):
        return float(value_string)
    return None


def non_empty_string(value: Any) -> str:
    if value is None:
        return ''
    value_string = str(value).strip()
    if value_string.upper() in {'N/A', 'NA'}:
        return ''
    return value_string


def terminal_heating_source_convert(heat_coil_type):
    if 'WATER' in heat_coil_type.upper():
        option = 'HOT_WATER'
    elif 'ELECTRIC' in heat_coil_type.upper():
        option = 'ELECTRIC'
    else:
        option = 'NONE'
    return option


def terminal_cooling_source_convert(cool_coil_type):
    if 'N/A' in cool_coil_type.upper():
        option = 'NONE'
    elif cool_coil_type == '':
        option = 'NONE'
    else:
        option = 'CHILLED_WATER'
    return option


def terminal_config_convert(type_input_obj):
    if 'series' in type_input_obj.lower():
        option = 'SERIES'
    elif 'parallel' in type_input_obj.lower():
        option = 'PARALLEL'
    else:
        option = "OTHER"
    return option


def heat_rejection_type_convert(type_input_obj):
    lower_case_obj = type_input_obj.lower()
    if 'tower' in lower_case_obj:
        option = 'OPEN_CIRCUIT_COOLING_TOWER'
    elif 'evaporative' in lower_case_obj:
        option = 'CLOSED_CIRCUIT_COOLING_TOWER'
    elif 'fluidcooler' in lower_case_obj:
        option = 'DRY_COOLER'
    else:
        option = 'OTHER'
    return option


def heat_rejection_fan_speed_convert(type_input_obj):
    lower_case_obj = type_input_obj.lower()
    if 'two' in lower_case_obj:
        option = 'TWO_SPEED'
    elif 'variable' in lower_case_obj:
        option = 'VARIABLE_SPEED'
    elif 'single' in lower_case_obj:
        option = 'CONSTANT'
    else:
        option = 'OTHER'
    return option


def do_chiller_and_pump_share_branch(chiller_name, list_of_dict, side_of_loop):
    answer = False
    chiller_branch_name = ''
    # find the branch used by the chiller
    for row in list_of_dict:
        if row['Side'].lower() == side_of_loop.lower():
            if chiller_name.lower() == row['Component Name'].lower():
                chiller_branch_name = row['Branch Name']
                break
    # find if a pump is on the same branch
    if chiller_branch_name:
        for row in list_of_dict:
            if chiller_branch_name == row['Branch Name']:
                if 'pump' in row['Component Type'].lower():
                    answer = True
                    break
    return answer


def do_share_branch(comp_a, comp_b, list_of_dict):
    answer = False
    comp_a_branch_names = []
    # find the branches used by the component type A
    for row in list_of_dict:
        if comp_a.lower() in row['Component Type'].lower():
            comp_a_branch_names.append(row['Branch Name'])
    # find if component type B is on the same branch
    if comp_a_branch_names:
        for row in list_of_dict:
            if (row['Branch Name']
                    in comp_a_branch_names):
                if comp_b in row['Component Type'].lower():
                    answer = True
                    break
    return answer


class Translator:
    """This class reads in the input files and does the heavy lifting to write output files"""

    def __init__(self, epjson_file_path: Path, rpd_name=None, add_cp=False, empty_cp=False):
        print(f"Reading epJSON input file at {epjson_file_path}")
        self.input_file = InputFile(epjson_file_path)
        self.epjson_object = self.input_file.epjson_object
        self.json_results_object = self.input_file.json_results_object
        print(f"Reading EnergyPlus results JSON file: {self.input_file.json_results_input_path}")
        self.json_hourly_results_object = self.input_file.json_hourly_results_object
        print(f"Reading EnergyPlus hourly results JSON file: {self.input_file.json_hourly_results_input_path}")

        # Modify export name - to avoid long execution line set by windows
        output_path = Path(str(epjson_file_path.parent.absolute()) + "\\" + rpd_name) if rpd_name else epjson_file_path
        self.output_file = OutputFile(output_path)
        self.rpd_file_path = self.output_file.rpd_file_path
        print(f"Writing output file to {self.rpd_file_path}")

        self.validator = Validator()
        self.status_reporter = StatusReporter()

        self.do_use_compliance_parameters = add_cp
        self.do_create_empty_compliance_parameters = empty_cp

        self.compliance_parameter = ComplianceParameterHandler(epjson_file_path)
        if self.do_use_compliance_parameters or self.do_create_empty_compliance_parameters:
            print(f"File with compliance parameter information is: {self.compliance_parameter.cp_empty_file_path}")

        self.project_description = {}
        self.model_description = {}
        self.building = {}
        self.building_segment = {}
        self.metadata = {}
        self.surfaces_by_zone = {}
        self.schedules_used_names = []
        self.terminals_by_zone = {}
        self.serial_number = 0
        self.id_used = set()
        self.pump_extra = {}

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

    def get_dynamic_fenestration(self):
        dynamic_fenestrations = []
        if 'WindowShadingControl' in self.epjson_object:
            window_shading_control = self.epjson_object['WindowShadingControl']
            for name, fields in window_shading_control.items():
                if "shading_type" in fields:
                    if fields["shading_type"] == "SwitchableGlazing":
                        surfaces = fields['fenestration_surfaces']
                        for surface in surfaces:
                            named_surface = surface['fenestration_surface_name']
                            if named_surface not in dynamic_fenestrations:
                                dynamic_fenestrations.append(named_surface.lower())
        return dynamic_fenestrations

    def find_window_overhangs(self):
        windows_with_overhangs = []
        if 'Shading:Overhang' in self.epjson_object:
            shading = self.epjson_object['Shading:Overhang']
            for shading_name, fields in shading.items():
                if 'window_or_door_name' in fields:
                    named_shading = fields['window_or_door_name']
                    if named_shading not in windows_with_overhangs:
                        windows_with_overhangs.append(named_shading.lower())
        if 'Shading:Overhang:Projection' in self.epjson_object:
            shading = self.epjson_object['Shading:Overhang:Projection']
            for shading_name, fields in shading.items():
                if 'window_or_door_name' in fields:
                    named_shading = fields['window_or_door_name']
                    if named_shading not in windows_with_overhangs:
                        windows_with_overhangs.append(named_shading.lower())
        return windows_with_overhangs

    def find_window_fins(self):
        windows_with_fins = []
        if 'Shading:Fin' in self.epjson_object:
            shading = self.epjson_object['Shading:Fin']
            for shading_name, fields in shading.items():
                if 'window_or_door_name' in fields:
                    named_shading = fields['window_or_door_name']
                    if named_shading not in windows_with_fins:
                        windows_with_fins.append(named_shading.lower())
        if 'Shading:Fin:Projection' in self.epjson_object:
            shading = self.epjson_object['Shading:Fin:Projection']
            for shading_name, fields in shading.items():
                if 'window_or_door_name' in fields:
                    named_shading = fields['window_or_door_name']
                    if named_shading not in windows_with_fins:
                        windows_with_fins.append(named_shading.lower())
        return windows_with_fins

    def get_adjacent_surface_for_each_surface(self):
        adjacent_by_surface = {}
        if 'BuildingSurface:Detailed' in self.epjson_object:
            building_surface_detailed = self.epjson_object['BuildingSurface:Detailed']
            for surface_name, fields in building_surface_detailed.items():
                if 'outside_boundary_condition_object' in fields:
                    adjacent_by_surface[surface_name.upper()] = fields['outside_boundary_condition_object'].upper()
        return adjacent_by_surface

    def get_outside_boundary_condition_for_each_surface(self):
        boundary_by_surface = {}
        if 'BuildingSurface:Detailed' in self.epjson_object:
            building_surface_detailed = self.epjson_object['BuildingSurface:Detailed']
            for surface_name, fields in building_surface_detailed.items():
                if 'outside_boundary_condition' in fields:
                    boundary_by_surface[surface_name.upper()] = fields['outside_boundary_condition'].upper()
        return boundary_by_surface

    @staticmethod
    def should_emit_surface(surface_name, surfaces_by_surface, adjacent_surfaces):
        if surface_name not in surfaces_by_surface:
            return False
        surface = surfaces_by_surface[surface_name]
        if surface.get('adjacent_to') != 'INTERIOR':
            return True

        adjacent_surface = adjacent_surfaces.get(surface_name)
        if adjacent_surface not in surfaces_by_surface:
            return True

        return surface_name <= adjacent_surface

    def add_materials(self):
        materials = []
        if 'Material' in self.epjson_object:
            materials_in = self.epjson_object['Material']
            for material_name, material_dict in materials_in.items():
                material = {
                    'id': material_name,
                    'thickness': material_dict['thickness'],
                    'thermal_conductivity': material_dict['conductivity'],
                    'density': material_dict['density'],
                    'specific_heat': material_dict['specific_heat']
                }
                materials.append(material)
        if 'Material:NoMass' in self.epjson_object:
            materials_no_mass_in = self.epjson_object['Material:NoMass']
            for material_name, material_dict in materials_no_mass_in.items():
                material = {
                    'id': material_name,
                    'r_value': material_dict['thermal_resistance']
                }
                materials.append(material)
        self.model_description['materials'] = materials
        return materials

    def add_constructions(self):
        constructions = []
        u_by_construction = self.gather_ufactor_by_construction()
        if 'Construction' in self.epjson_object:
            constructions_in = self.epjson_object['Construction']
            for construction_name, layer_dict in constructions_in.items():
                # fix the order of the dictionary because the use of 'outside_layer' messes it up
                if 'outside_layer' in layer_dict and 'layer_1' not in layer_dict:
                    layer_dict['layer_1'] = layer_dict.pop('outside_layer')
                sorted_layer_dict = dict(sorted(layer_dict.items()))
                construction = {'id': construction_name.upper(),
                                'primary_layers': list(sorted_layer_dict.values())
                                }
                if construction_name.upper() in u_by_construction:
                    construction['u_factor'] = u_by_construction[construction_name.upper()]
                constructions.append(construction)
        self.model_description['constructions'] = constructions
        return constructions

    def gather_ufactor_by_construction(self):
        u_by_construction = {}
        for table_name in ['Opaque Exterior', 'Opaque Interior']:
            opaque_table = self.get_table_dictionary("EnvelopeSummary", table_name)
            for row in opaque_table.values():
                if row['Construction'] not in u_by_construction:
                    if is_float(row['U-Factor with Film [W/m2-K]']):
                        u_by_construction[row['Construction']] = float(row['U-Factor with Film [W/m2-K]'])
        return u_by_construction

    def gather_surface_optical(self):
        optical_by_construction = {}
        # return a dictionary of optical SurfaceOpticalProperties by construction
        material_dict = self.get_table_dictionary('InitializationSummary', "Material Details", ignore_first_column=True)
        opaque_layers_dict = self.get_table_dictionary('EnvelopeSummary', "Opaque Construction Layers")
        for construction_name, layers in opaque_layers_dict.items():
            first_layer, last_layer = self.first_last_layer(layers)
            if first_layer in material_dict and last_layer in material_dict:
                optical = {
                    'id': construction_name + '-SurfaceOpticalProperties',
                    'absorptance_thermal_exterior': float(material_dict[last_layer]['Absorptance:Thermal']),
                    'absorptance_solar_exterior': float(material_dict[last_layer]['Absorptance:Solar']),
                    'absorptance_visible_exterior': float(material_dict[last_layer]['Absorptance:Visible']),
                    'absorptance_thermal_interior': float(material_dict[first_layer]['Absorptance:Thermal']),
                    'absorptance_solar_interior': float(material_dict[first_layer]['Absorptance:Solar']),
                    'absorptance_visible_interior': float(material_dict[first_layer]['Absorptance:Visible'])
                }
                optical_by_construction[construction_name] = optical
        return optical_by_construction

    @staticmethod
    def first_last_layer(layer_dict):
        first_layer = ''
        last_layer = ''
        layer_names = [f'Layer {x}' for x in range(10, 1, -1)]  # list of layers in reverse order
        if 'Layer 1' in layer_dict:
            first_layer = layer_dict['Layer 1']
        for layer_name in layer_names:
            if layer_name in layer_dict:
                if layer_dict[layer_name]:
                    last_layer = layer_dict[layer_name]
                    break
        return first_layer, last_layer

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
                            if row_key == 'None':
                                continue
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
                                  'type': 'PROPOSED',
                                  'buildings': [self.building, ]}

        time_stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')

        self.metadata = {
            'id': 'metadata id 1',
            'schema_author': 'ASHRAE SPC 229 Schema Working Group',
            'schema_name': 'Ruleset Evaluation Schema',
            'schema_version': '0.1.7',
            'schema_url': 'https://github.com/open229/ruleset-model-description-schema',
            'time_of_creation': time_stamp,
            'version': '1.0.0',
            'author': 'The createRulesetProjectDescription script written primarily by Jason Glazer '
                      'of GARD Analytics, Inc. as part of NREL EnergyPlus Development Team as funded by USDOE.',
            'description': '',
            'source': 'created by createRulesetProjectDescription script'
        }

        self.project_description = {'id': 'project description root',
                                    'notes': 'generated by createRulesetProjectDescription from EnergyPlus',
                                    'output_format_type': 'OUTPUT_SCHEMA_ASHRAE901_2019',
                                    'metadata': self.metadata,
                                    'ruleset_model_descriptions': [self.model_description, ],
                                    }

    def add_external_fluid_source(self):
        external_fluid_sources = []
        plant_loop_arrangements = self.gather_table_into_list('HVACTopology', 'Plant Loop Component Arrangement')
        for arrangement_row in plant_loop_arrangements:
            comp_type = arrangement_row['Component Type']
            if comp_type == 'DISTRICTCOOLING':
                external_fluid = {
                    "id": arrangement_row['Component Name'],
                    "loop": arrangement_row['Loop Name'],
                    "type": "CHILLED_WATER",
                }
                external_fluid_sources.append(external_fluid)
            elif comp_type == 'DISTRICTHEATING:STEAM':
                external_fluid = {
                    "id": arrangement_row['Component Name'],
                    "loop": arrangement_row['Loop Name'],
                    "type": "STEAM",
                }
                external_fluid_sources.append(external_fluid)
            elif comp_type == 'DISTRICTHEATING:WATER':
                external_fluid = {
                    "id": arrangement_row['Component Name'],
                    "loop": arrangement_row['Loop Name'],
                    "type": "HOT_WATER",
                }
                external_fluid_sources.append(external_fluid)
        if external_fluid_sources:
            self.model_description['external_fluid_sources'] = external_fluid_sources
        return external_fluid_sources

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
                        if 'ASHRAE Climate Zone' in rows:
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
        }
        if climate_zone:
            weather['climate_zone'] = climate_zone
        if cooling_design_day_option:
            weather['cooling_dry_bulb_design_day_type'] = cooling_design_day_option
        if heating_design_day_option:
            weather['heating_dry_bulb_design_day_type'] = heating_design_day_option
        self.model_description['weather'] = weather
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
                        for row_key in row_keys:
                            if row_key == 'None':
                                continue
                            environment_name = rows[row_key][environment_name_column]
                            start_date = rows[row_key][start_date_column]
                            calendar['notes'] = 'name environment: ' + environment_name
                            # add day of week for january 1 only if the start date is 01/01/xxxx
                            start_date_parts = start_date.split('/')
                            if start_date_parts[0] == '01' and start_date_parts[1] == '01':
                                start_day_of_week = rows[row_key][start_day_of_week_column]
                                calendar['day_of_week_for_january_1'] = start_day_of_week.upper()
                            self.model_description['calendar'] = calendar
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
                            if exterior_light_name == 'None':
                                continue
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
        adjacent_surfaces = self.get_adjacent_surface_for_each_surface()
        setpoint_schedules = self.gather_thermostat_setpoint_schedules()
        humid_sch_name_by_zone = self.gather_humidity_schedules()
        effective_by_zone = self.gather_air_dist_effectiveness()
        zone_info_init_summary = self.get_table_dictionary('InitializationSummary', 'Zone Information',
                                                           ignore_first_column=True)
        setpoint_by_zone = self.gather_thermostat_setpoints()
        infiltration_by_zone = self.gather_infiltration()
        exhaust_fans_by_zone = self.gather_exhaust_fans_by_zone()
        equipment_fans = self.gather_equipment_fans()
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
                            if zone_name == 'None':
                                continue
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
                            if zone_name in setpoint_by_zone:
                                heat_setpoint, cool_setpoint = setpoint_by_zone[zone_name]
                                zone['design_thermostat_heating_setpoint'] = heat_setpoint
                                zone['design_thermostat_cooling_setpoint'] = cool_setpoint
                            if zone_name.upper() in humid_sch_name_by_zone:
                                humid_sch, dehumid_sch = humid_sch_name_by_zone[zone_name]
                                zone['minimum_humidity_setpoint_schedule'] = humid_sch
                                zone['maximum_humidity_setpoint_schedule'] = dehumid_sch
                            if zone_name in effective_by_zone:
                                zone['air_distribution_effectiveness'] = effective_by_zone[zone_name]
                            surfaces = []
                            for key, value in self.surfaces_by_zone.items():
                                if zone_name == value:
                                    if self.should_emit_surface(key, surfaces_by_surface, adjacent_surfaces):
                                        surfaces.append(surfaces_by_surface[key])
                            zone['surfaces'] = surfaces
                            if zone_name in infiltration_by_zone:
                                zone['infiltration'] = infiltration_by_zone[zone_name]
                            else:
                                infiltration_zero = {
                                    'id': 'infiltration-' + zone_name,
                                    'modeling_method': 'WEATHER_DRIVEN',
                                    'algorithm_name': 'ZoneInfiltration',
                                    'flow_rate': 0.0,
                                    'multiplier_schedule': 'always_1'
                                }
                                zone['infiltration'] = infiltration_zero
                            if zone_name.upper() in self.terminals_by_zone:
                                zone['terminals'] = self.terminals_by_zone[zone_name.upper()]
                            if zone_name.upper() in zone_info_init_summary:
                                zone['floor_name'] = 'Floor at Height ' + zone_info_init_summary[zone_name.upper()][
                                    'Minimum Z {m}']
                            if zone_name.upper() in exhaust_fans_by_zone:
                                zone['zonal_exhaust_fans'] = [
                                    {
                                        "id": f"{zone_name} exhaust_fan",
                                        **equipment_fans[exhaust_fans_by_zone[zone_name.upper()]][0],
                                    }
                                ]
                break
        self.building_segment['zones'] = zones
        return zones

    def gather_thermostat_setpoints(self):
        setpoint_by_zone = {}
        zone_sensible_cooling_table = self.get_table_dictionary('HVACSizingSummary', 'Zone Sensible Cooling')
        zone_sensible_heating_table = self.get_table_dictionary('HVACSizingSummary', 'Zone Sensible Heating')
        for zone_name, table in zone_sensible_heating_table.items():
            heat_setpoint = float(zone_sensible_heating_table[zone_name]
                                  ['Thermostat Setpoint Temperature at Peak Load [C]'])
            cool_setpoint = heat_setpoint
            if zone_name in zone_sensible_cooling_table:
                cool_setpoint = float(zone_sensible_cooling_table[zone_name]
                                      ['Thermostat Setpoint Temperature at Peak Load [C]'])
            setpoint_by_zone[zone_name] = (heat_setpoint, cool_setpoint)
        return setpoint_by_zone

    def gather_humidity_schedules(self):
        humid_sch_name_by_zone = {}
        if 'ZoneControl:Humidistat' in self.epjson_object:
            zone_control_humidistats = self.epjson_object['ZoneControl:Humidistat']
            for stat_name, fields in zone_control_humidistats.items():
                if fields['zone_name']:
                    humid_schedule = fields['humidifying_relative_humidity_setpoint_schedule_name']
                    dehumid_schedule = fields['dehumidifying_relative_humidity_setpoint_schedule_name']
                    humid_sch_name_by_zone[fields['zone_name'].upper()] = (humid_schedule, dehumid_schedule)
        return humid_sch_name_by_zone

    def gather_air_dist_effectiveness(self):
        effective_by_zone = {}
        zone_vent_param_table = self.get_table_dictionary('Standard62.1Summary', 'Zone Ventilation Parameters')
        for zone_name, row in zone_vent_param_table.items():
            cooling_eff = row['Cooling Zone Air Distribution Effectiveness - Ez-clg']
            heating_eff = row['Cooling Zone Air Distribution Effectiveness - Ez-clg']
            if is_float(cooling_eff) and is_float(heating_eff):
                eff = min(float(cooling_eff), float(heating_eff))
                effective_by_zone[zone_name] = eff
        return effective_by_zone

    def add_spaces(self):
        tabular_reports = self.json_results_object['TabularReports']
        spaces: Dict[str, List[JsonDict]] = {}
        lights_by_space = self.gather_interior_lighting()
        people_schedule_by_zone = self.gather_people_schedule_by_zone()
        equipment_by_zone = self.gather_miscellaneous_equipment()
        people_annual_list = self.gather_table_into_list("PEOPLE INTERNAL GAIN ANNUAL", "Custom Annual Report")
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
                            if space_name == 'None':
                                continue
                            floor_area = float(rows[space_name][area_column])
                            people_density = float(rows[space_name][people_density_column])
                            zone_name = rows[space_name][zone_name_column]
                            space_type = rows[space_name][space_type_column]
                            tags = rows[space_name][tags_column]

                            if people_density > 0:
                                people = floor_area / people_density
                            else:
                                people = 0

                            space = {'id': space_name,
                                     'floor_area': floor_area,
                                     'number_of_occupants': round(people, 2),
                                     }
                            if zone_name in people_schedule_by_zone:
                                space['occupant_multiplier_schedule'] = people_schedule_by_zone[zone_name]

                            # get the sensible and latent from annual
                            # this only works if space name is subset of people input object name
                            sensible = 0
                            latent = 0
                            for people_annual_row in people_annual_list:
                                if space_name in people_annual_row['first column']:
                                    people_count = float(people_annual_row['People Occupant Count {AT MAX/MIN} []'])
                                    if people_count > 0:
                                        sens = float(people_annual_row['People Sensible Heating Rate {AT MAX/MIN} [W]'])
                                        sensible = sens / people_count
                                        lat = float(people_annual_row['People Latent Gain Rate {AT MAX/MIN} [W]'])
                                        latent = lat / people_count
                                    break
                            if sensible > 0:
                                space['occupant_sensible_heat_gain'] = sensible
                            if latent > 0:
                                space['occupant_latent_heat_gain'] = latent

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
                                    space['service_water_heating_area_type'] = second_tag
                            zone_key = zone_name.upper()
                            if zone_key not in spaces:
                                spaces[zone_key] = [space]
                            else:
                                spaces[zone_key].append(space)
        # insert the space into the corresponding Zone
        for zone in self.building_segment['zones']:
            zone['spaces'] = spaces.get(zone['id'].upper(), [])
        legacy_spaces = {}
        for zone_name, zone_spaces in spaces.items():
            if len(zone_spaces) == 1:
                legacy_spaces[zone_name] = zone_spaces[0]
            else:
                legacy_spaces[zone_name] = zone_spaces
        return legacy_spaces

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
                            if daylighting_name == 'None':
                                continue
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
                            if int_light_name == 'None':
                                continue
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
                            if row_key == 'None':
                                continue
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
        classification_by_subsurface = self.get_subsurface_classification()
        dynamic_fenestrations = self.get_dynamic_fenestration()
        windows_with_overhangs = self.find_window_overhangs()
        windows_with_fins = self.find_window_fins()
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
                            if fenestration_name == 'None':
                                continue
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
                                'glazed_area': glass_area,
                                'opaque_area': frame_area + divider_area,
                                'u_factor': u_factor,
                                'solar_heat_gain_coefficient': shgc,
                                'visible_transmittance': visible_trans,
                                'has_automatic_shades': shade_control == 'Yes'
                            }
                            if fenestration_name in classification_by_subsurface:
                                subsurface['classification'] = classification_by_subsurface[fenestration_name]
                            else:
                                subsurface['classification'] = 'WINDOW'
                            if fenestration_name.lower() in dynamic_fenestrations:
                                subsurface['dynamic_glazing_type'] = 'AUTOMATIC_DYNAMIC'
                            else:
                                subsurface['dynamic_glazing_type'] = 'NOT_DYNAMIC'
                            subsurface['has_shading_overhang'] = fenestration_name.lower() in windows_with_overhangs
                            subsurface['has_shading_sidefins'] = fenestration_name.lower() in windows_with_fins
                            if parent_surface_name not in subsurface_by_surface:
                                subsurface_by_surface[parent_surface_name] = [subsurface, ]
                            else:
                                subsurface_by_surface[parent_surface_name].append(subsurface)
        # print(subsurface_by_surface)
        return subsurface_by_surface

    def get_subsurface_classification(self):
        classification_by_subsurface = {}
        heat_transfer_surfaces_table = self.gather_table_into_list('InitializationSummary', 'HeatTransfer Surface')
        for table_row in heat_transfer_surfaces_table:
            if table_row['Surface Class'] == 'Door':
                classification_by_subsurface[table_row['Surface Name']] = 'DOOR'
            elif table_row['Surface Class'] == 'Window':
                tilt = float(table_row['Tilt {deg}'])
                if tilt > 60:  # based on 90.1 definition of wall.
                    classification_by_subsurface[table_row['Surface Name']] = 'WINDOW'
                else:
                    classification_by_subsurface[table_row['Surface Name']] = 'SKYLIGHT'
        return classification_by_subsurface

    def gather_surfaces(self):
        tabular_reports = self.json_results_object['TabularReports']
        surfaces = {}  # dictionary by zone name containing the surface data elements
        subsurface_by_surface = self.gather_subsurface()
        do_surfaces_cast_shadows = self.are_shadows_cast_from_surfaces()
        adjacent_surfaces = self.get_adjacent_surface_for_each_surface()
        outside_boundary_conditions = self.get_outside_boundary_condition_for_each_surface()
        optical_by_construction = self.gather_surface_optical()
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
                        for surface_name in surface_names:
                            if surface_name == 'None':
                                continue
                            construction_name = rows[surface_name][construction_name_column]
                            gross_area = float(rows[surface_name][gross_area_column])
                            azimuth = float(rows[surface_name][azimuth_column])
                            tilt = float(rows[surface_name][tilt_column])
                            if tilt > 120:
                                surface_classification = 'FLOOR'
                            elif tilt >= 60:
                                surface_classification = 'WALL'
                            else:
                                surface_classification = 'CEILING'
                            if is_exterior:
                                adjacent_to = 'EXTERIOR'
                                if surface_name in outside_boundary_conditions:
                                    outside_boundary_condition = outside_boundary_conditions[surface_name]
                                    if 'GROUND' in outside_boundary_condition:
                                        adjacent_to = 'GROUND'
                            else:
                                adjacent_to = 'INTERIOR'
                            surface = {
                                'id': surface_name,
                                'classification': surface_classification,
                                'area': gross_area,
                                'tilt': tilt,
                                'azimuth': azimuth,
                                'adjacent_to': adjacent_to,
                                'does_cast_shade': do_surfaces_cast_shadows,
                                'construction': construction_name
                            }
                            if not is_exterior:
                                if surface_name in adjacent_surfaces:
                                    adjacent_surface = adjacent_surfaces[surface_name]
                                    if adjacent_surface in self.surfaces_by_zone:
                                        surface['adjacent_zone'] = self.surfaces_by_zone[adjacent_surface]
                            if surface_name in subsurface_by_surface:
                                surface['subsurfaces'] = subsurface_by_surface[surface_name]
                            surfaces[surface_name] = surface
                            if construction_name in optical_by_construction:
                                surface['optical_properties'] = optical_by_construction[construction_name]
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
                            if row_key == 'None':
                                continue
                            infiltration_name = rows[row_key][infiltration_name_column]
                            zone_name = rows[row_key][zone_name_column]
                            design_volume_flow_rate = 1000 * float(rows[row_key][design_volume_flow_rate_column])
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
        air_flow_network_annual = self.get_table_dictionary('AFN ZONE INFILTRATION ANNUAL', 'Custom Annual Report')
        for name, afn in air_flow_network_annual.items():
            if name == 'Annual Sum or Average' or name == 'Maximum of Rows' or name == 'Minimum of Rows' or name == '':
                continue
            infiltration = {
                'id': name + 'AFN Infiltration',
                'modeling_method': 'PRESSURE_BASED',
                'algorithm_name': 'Air Flow Network',
                'flow_rate': float(afn['AFN Zone Infiltration Volume {MAXIMUM} [m3/s]'])
            }
            infiltration_by_zone[name.upper()] = infiltration
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
        type_by_name = self.gather_schedule_type()
        rows = {}
        if 'Rows' in self.json_hourly_results_object:
            rows = self.json_hourly_results_object['Rows']
        schedules = []

        init_week_schedules = self.get_table_dictionary('InitializationSummary', 'WeekSchedule - Hourly', True)
        init_day_schedules = self.get_table_dictionary('InitializationSummary', 'DaySchedule - Hourly', True)
        init_schedules = self.get_table_dictionary('InitializationSummary', 'Schedule - Hourly', True)

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
            else:
                #  the Hourly JSON file does not contain the summer and winter design days
                #  assume that weekschedule1 or 2 contains both
                if schedule_name in init_schedules:
                    week1_name = init_schedules[schedule_name]['WeekSchedule 1']
                    summer_day = None
                    winter_day = None
                    if week1_name in init_week_schedules:
                        summer_day = init_week_schedules[week1_name]['SummerDesignDay']
                        winter_day = init_week_schedules[week1_name]['WinterDesignDay']
                    if not summer_day or not winter_day:
                        week2_name = init_schedules[schedule_name]['WeekSchedule 2']
                        if week2_name:
                            if week2_name in init_week_schedules:
                                summer_day = init_week_schedules[week1_name]['SummerDesignDay']
                                winter_day = init_week_schedules[week1_name]['WinterDesignDay']
                    if summer_day:
                        if summer_day in init_day_schedules:
                            day = init_day_schedules[summer_day]
                            design_cooling_hourly = [float(day[f"{x:02d}:00"]) for x in range(1, 24)]
                    if winter_day:
                        if winter_day in init_day_schedules:
                            day = init_day_schedules[winter_day]
                            design_heating_hourly = [float(day[f"{x:02d}:00"]) for x in range(1, 24)]
            schedule = {
                'id': schedule_name,
                'sequence_type': 'HOURLY',
                'hourly_values': hourly,
                'hourly_heating_design_day': design_heating_hourly,
                'hourly_cooling_design_day': design_cooling_hourly,
            }
            if schedule_name in type_by_name:
                if type_by_name[schedule_name]:
                    schedule['type'] = type_by_name[schedule_name]
            schedules.append(schedule)
        self.model_description['schedules'] = schedules

    def gather_schedule_type(self):
        raw_to_final_map = {
            'FRACTIONAL': 'MULTIPLIER_DIMENSIONLESS',
            'DIMENSIONLESS': 'MULTIPLIER_DIMENSIONLESS',
            'TEMPERATURE': 'TEMPERATURE',
            'DELTATEMPERATURE': 'TEMPERATURE',
            'POWER': 'POWER',
            'CAPACITY': 'POWER'
        }
        type_by_name = {}
        init_schedule_table = self.get_table_dictionary('InitializationSummary', 'Schedule - Hourly', True)
        for name, row in init_schedule_table.items():
            raw_type = row['ScheduleType']
            if raw_type in raw_to_final_map:
                type_by_name[name] = raw_to_final_map[raw_type]
            elif 'TEMPERATURE' in raw_type:
                type_by_name[name] = 'TEMPERATURE'
            elif 'THERMOSTAT' in raw_type:
                type_by_name[name] = 'TEMPERATURE'
            else:
                type_by_name[name] = ''
        return type_by_name

    def add_ground_schedule(self):
        ground_schedule = {}
        empty_list = []
        monthly_table = self.get_table_dictionary('InitializationSummary', 'Site:GroundTemperature:BuildingSurface')
        # for debugging purposes the following has difference values for each month for the SmallOffice
        # monthly_table = self.get_table_dictionary('InitializationSummary', 'Site:GroundTemperature:FCfactorMethod')
        if '1' in monthly_table:
            monthly_table_dict = monthly_table['1']
            monthly_table_numbers = [float(x) for _, x in monthly_table_dict.items()]
            ground_temps = self.twelve_to_8760(monthly_table_numbers)
            ground_schedule = {
                'id': 'schedule_of_ground_temperatures',
                'sequence_type': 'HOURLY',
                'hourly_heating_design_day': empty_list,
                'hourly_cooling_design_day': empty_list,
                'type': 'TEMPERATURE',
                'hourly_values': ground_temps,
            }
            self.model_description['schedules'].append(ground_schedule)
            self.model_description['weather']['ground_temperature_schedule'] = 'schedule_of_ground_temperatures'
        return ground_schedule

    @staticmethod
    def twelve_to_8760(list_of_twelve):
        list_of_8760 = []
        number_of_days_in_month = [31,  # January
                                   28,  # February
                                   31,  # March
                                   30,  # April
                                   31,  # May
                                   30,  # June
                                   31,  # July
                                   31,  # August
                                   30,  # September
                                   31,  # October
                                   30,  # November
                                   31]  # December
        for indx, item in enumerate(list_of_twelve):
            list_of_8760.extend([item] * number_of_days_in_month[indx] * 24)
        return list_of_8760

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

    def add_airloop_heating_ventilation_ac_system(self):
        hvac_systems = []
        supply_topology_by_airloop = self.analyze_supply_topology_by_airloop()
        humid_option_by_airloop = self.gather_humid_option_by_airloop()

        coils_table = self.get_table_dictionary("CoilSizingDetails", "Coils")
        coil_connections = self.gather_coil_connections()
        heating_coil_efficiencies = self.gather_heating_coil_efficiencies()
        cooling_coil_efficiencies = self.gather_cooling_coil_efficiencies()
        coil_connections = self.gather_coil_connections()
        dehumid_option_by_airloop = self.gather_dehumid_option_by_airloop()

        air_flows_62 = self.gather_airflows_from_62()
        exhaust_fan_names = self.gather_exhaust_fans_by_airloop()
        equipment_fans = self.gather_equipment_fans()
        economizer_by_airloop = self.gather_economizer_by_airloop()

        for airloop, supply_top in supply_topology_by_airloop.items():
            hvac = {"id": airloop}

            if airloop in humid_option_by_airloop:
                hvac['humidification_type'] = humid_option_by_airloop[airloop]

            hvac_systems.append(hvac)

            heating_system = self.get_airloop_heating_system(airloop, supply_top, coils_table,
                                                             heating_coil_efficiencies, coil_connections)
            if heating_system:
                hvac["heating_system"] = heating_system

            cooling_system = self.get_airloop_cooling_system(airloop, supply_top, coils_table,
                                                             cooling_coil_efficiencies,
                                                             coil_connections, dehumid_option_by_airloop)
            if cooling_system:
                hvac["cooling_system"] = cooling_system

            fan_system = self.get_airloop_fan_system(airloop, supply_top, equipment_fans, air_flows_62,
                                                     exhaust_fan_names, economizer_by_airloop)
            if fan_system:
                hvac["fan_system"] = fan_system

        self.building_segment["heating_ventilating_air_conditioning_systems"] = hvac_systems
        return hvac_systems

    def get_airloop_heating_system(self, airloop, supply_top, coils_table, heating_coil_efficiencies, coil_connections):
        hs = {}
        if 'main_heating_coil' in supply_top:
            heat_coil_name = supply_top['main_heating_coil']
            heat_coil = coils_table[heat_coil_name]
            current_coil_efficiencies = heating_coil_efficiencies[heat_coil_name]

            coil_type = heat_coil["Coil Type"]
            total_capacity = float(heat_coil["Coil Final Gross Total Capacity [W]"])
            sensible_capacity = float(heat_coil["Coil Final Gross Sensible Capacity [W]"])
            rated_capacity = float(heat_coil["Coil Total Capacity at Rating Conditions [W]"])
            ideal_load_peak = float(heat_coil["Coil Total Capacity at Ideal Loads Peak [W]"])
            is_autosized = heat_coil["Autosized Coil Capacity?"]
            leaving_db = float(heat_coil["Coil Leaving Air Drybulb at Rating Conditions [C]"])

            if sensible_capacity < 0:
                sensible_capacity = 0
            if total_capacity < 0:
                total_capacity = sensible_capacity
            oversize = 1.0
            if ideal_load_peak > 0:
                oversize = total_capacity / ideal_load_peak
            hs = {
                "id": f"{airloop}-heating",
                "design_capacity": total_capacity,
                "type": heating_type_convert(coil_type),
                "energy_source_type": source_from_coil(coil_type),
                "oversizing_factor": oversize,
                "is_calculated_size": is_autosized == "Yes",
            }
            if rated_capacity != -999:
                hs["rated_capacity"] = rated_capacity
            if leaving_db != -999:
                hs["heating_coil_setpoint"] = leaving_db

            mt, mv = self.process_heating_metrics(heat_coil_name, heating_coil_efficiencies)
            if mv:
                hs["efficiency_metric_types"] = mt
                hs["efficiency_metric_values"] = mv

            if "minimum_temperature_compressor" in current_coil_efficiencies:
                min_temp = current_coil_efficiencies["minimum_temperature_compressor"]
                if min_temp is not None:
                    hs["heatpump_low_shutoff_temperature"] = min_temp

            if "max_temperature_supplement" in current_coil_efficiencies:
                max_supplement_temp = current_coil_efficiencies["max_temperature_supplement"]
                if max_supplement_temp is not None:
                    hs['heatpump_auxiliary_heat_high_shutoff_temperature'] = max_supplement_temp

            # Combined loop mapping logic (water-to-air HP vs generic water)
            if "WATERTOAIRHEATPUMP" in coil_type.upper() and heat_coil_name in coil_connections:
                hs["water_source_heat_pump_loop"] = coil_connections[heat_coil_name]["plant_loop_name"]
            elif "WATER" in coil_type.upper() and heat_coil_name in coil_connections:
                hs["hot_water_loop"] = coil_connections[heat_coil_name]["plant_loop_name"]

            if "backup_heating_coil" in supply_top:
                backup_coil_name = supply_top['backup_heating_coil']
                backup_coil = coils_table[backup_coil_name]
                backup_type = backup_coil["Coil Type"]
                hs['heatpump_auxiliary_heat_type'] = heating_type_convert(backup_type)
        return hs

    def get_airloop_cooling_system(self, airloop, supply_top, coils_table, cooling_coil_efficiencies,
                                   coil_connections, dehumid_option_by_airloop):
        cs = {}
        if 'cooling_coil' in supply_top:
            cool_coil_name = supply_top['cooling_coil']
            cool_coil = coils_table[cool_coil_name]
            coil_type = cool_coil["Coil Type"]
            total_capacity = float(cool_coil["Coil Final Gross Total Capacity [W]"])
            sensible_capacity = float(cool_coil["Coil Final Gross Sensible Capacity [W]"])
            rated_capacity = float(cool_coil["Coil Total Capacity at Rating Conditions [W]"])
            rated_sensible_capacity = float(cool_coil["Coil Sensible Capacity at Rating Conditions [W]"])
            ideal_load_peak = float(cool_coil["Coil Total Capacity at Ideal Loads Peak [W]"])
            is_autosized = cool_coil["Autosized Coil Capacity?"]

            if sensible_capacity < 0:
                sensible_capacity = 0
            if total_capacity < 0:
                total_capacity = sensible_capacity
            oversize = 1.0
            if ideal_load_peak > 0:
                oversize = total_capacity / ideal_load_peak

            cs = {
                "id": f"{airloop}-cooling",
                "design_total_cool_capacity": total_capacity,
                "design_sensible_cool_capacity": sensible_capacity,
                "type": cooling_type_convert(coil_type),
                "oversizing_factor": oversize,
                "is_calculated_size": is_autosized == "Yes",
            }

            if rated_capacity != -999:
                cs["rated_total_cool_capacity"] = rated_capacity
            if rated_sensible_capacity != -999:
                cs["rated_sensible_cool_capacity"] = rated_sensible_capacity

            # Combined loop mapping logic (water-to-air HP vs generic water)
            # if "WATERTOAIRHEATPUMP" in coil_type.upper() and cool_coil_name in coil_connections:
            #    cs["water_source_heat_pump_loop"] = coil_connections[cool_coil_name]["plant_loop_name"]
            # elif "WATER" in coil_type.upper() and cool_coil_name in coil_connections:
            #    cs["hot_water_loop"] = coil_connections[cool_coil_name]["plant_loop_name"]

            mt, mv = self.process_cooling_metrics(cool_coil_name, cooling_coil_efficiencies)
            if mv:
                cs["efficiency_metric_types"] = mt
                cs["efficiency_metric_values"] = mv

            if airloop in dehumid_option_by_airloop:
                cs['dehumidification_type'] = dehumid_option_by_airloop[airloop]
        return cs

    def get_airloop_fan_system(self, airloop, supply_top, equipment_fans, air_flows_62, exhaust_fan_names,
                               economizer_by_airloop):
        fs = {}
        if 'supply_fan' in supply_top:
            supply_fan_name = supply_top['supply_fan']
            supply_fan, supply_fan_extra = equipment_fans[supply_fan_name]

            fs = {"id": f"{supply_fan_name}-fansystem"}
            if supply_fan:
                fan = {
                    "id": supply_fan_name,
                    "specification_method": "SIMPLE"
                }
                fan.update(supply_fan)
                fs["supply_fans"] = [fan,]

                if airloop in air_flows_62:
                    fs["minimum_airflow"], fs["minimum_outdoor_airflow"] = air_flows_62[airloop]

                if supply_fan_extra["type"] == "Fan:SystemModel":
                    if (supply_fan_extra["speed_control_method"] == "Discrete" and
                            supply_fan_extra["number_of_speeds"] == 1):
                        fs["fan_control"] = "CONSTANT"
                elif "variable" not in supply_fan_extra["type"].lower():
                    fs["fan_control"] = "CONSTANT"

                if "air_energy_recovery" in supply_fan_extra:
                    fs["air_energy_recovery"] = supply_fan_extra["air_energy_recovery"]

                if airloop in exhaust_fan_names:
                    fs["exhaust_fans"] = [{"id": n, **equipment_fans[n][0]} for n in exhaust_fan_names[airloop]]

                if airloop in economizer_by_airloop:
                    econo = economizer_by_airloop[airloop]
                    if 'XTRA-Maxair' in econo:
                        fs['maximum_outdoor_airflow'] = 1000 * econo['XTRA-Maxair']
                        del econo['XTRA-Maxair']
                    fs['air_economizer'] = economizer_by_airloop[airloop]

                if 'speed_control_method' in supply_fan_extra:
                    method = supply_fan_extra["speed_control_method"]
                    if method == 'Discrete':
                        fs['operation_during_occupied'] = 'CYCLING'
                    elif method == 'Continuous':
                        fs['operation_during_occupied'] = 'CONTINUOUS'

                if 'return_fan' in supply_top:
                    return_fan_name = supply_top['return_fan']
                    return_fan, return_fan_extra = equipment_fans[return_fan_name]
                    fs['return_fans'] = [{"id": return_fan_name, **return_fan, "specification_method": "SIMPLE"}, ]
        return fs

    def add_terminal_hvac_system(self):
        zones_by_airloop, zone_by_terminal, airloop_by_zone = self.analyze_demand_topology_by_airloop()
        equip_topology_by_zone = self.analyze_zone_equipment()
        coils_table = self.get_table_dictionary("CoilSizingDetails", "Coils")
        air_terminals = self.gather_air_terminal()
        equipment_fans = self.gather_equipment_fans()

        # The following is from the schema description of the Terminal.Type:
        #
        # System configurations that typically are at the zone and include a compressor (such as packaged terminal air
        # conditioning, packaged terminal heat pumps, window air conditioning units, and water loop heat pumps) should
        # be reported in the schema using HeatingSystem and CoolingSystem. Systems that include gas or electric
        # furnaces should be reported in the schema using HeatingSystem. Distributed systems where each zone is
        # individually served by dedicated fans and/or coils (such as four-pipe fan coil, two-pipe fan coil, radiant
        # systems, baseboards, chilled beams, and variable refrigerant flow indoor units) should be reported in the
        # schema using Terminal with the cooling and heating described in the cooling_source and heating_source data
        # elements (and any other relevant Terminal Data elements). Evaporative cooling systems should be described
        # in CoolingSystem. Passive diffusers with no coil or fan should be described in Terminal.

        for zone, topology in equip_topology_by_zone.items():
            for ze in topology:
                if self.does_zone_equip_have_compressor(ze, coils_table):
                    pass
                else:
                    if zone in airloop_by_zone:
                        airloop_name = airloop_by_zone[zone]
                    else:
                        airloop_name = ''
                    if 'has_ADU' in ze and zone in air_terminals:
                        if 'has_vav' in ze:
                            primary_terminal_option = 'VARIABLE_AIR_VOLUME'
                        else:
                            primary_terminal_option = 'CONSTANT_AIR_VOLUME'
                        at = air_terminals[zone]
                        t = {
                            "id": at["terminal_name"],
                            "type": primary_terminal_option,
                            "heating_source": terminal_heating_source_convert(at["heat_coil_type"]),
                            "cooling_source": terminal_cooling_source_convert(at["chill_coil_type"]),
                            "served_by_heating_ventilating_air_conditioning_system": airloop_name,
                            "primary_airflow": at["primary_airflow_rate"] * 1000,
                            "supply_design_heating_setpoint_temperature": at["supply_heat_set_point"],
                            "supply_design_cooling_setpoint_temperature": at["supply_cool_set_point"],
                            "minimum_airflow": at["min_flow"] * 1000,
                            "minimum_outdoor_airflow": at["min_oa_flow"] * 1000,
                            "heating_capacity": at["heating_capacity"],
                            "cooling_capacity": at["cooling_capacity"],
                        }
                        if 'main_heating_coil' in ze:
                            main_heating_coil_name = ze['main_heating_coil']
                            if main_heating_coil_name in coils_table:
                                coils_detail = coils_table[main_heating_coil_name]
                                if coils_detail["HVAC Type"] == "ZONEHVAC:AIRDISTRIBUTIONUNIT":
                                    t["heating_capacity"] = float(coils_detail['Coil Final Gross Total Capacity [W]'])
                        if at.get("fan_name"):
                            if at["fan_name"] in equipment_fans:
                                tfan, _ = equipment_fans[at["fan_name"]]
                                t["fan"] = {"id": at["fan_name"], **tfan}
                                t["fan_configuration"] = terminal_config_convert(at["type_input"])
                        if at.get("secondary_airflow_rate", 0) > 0:
                            t["secondary_airflow"] = at["secondary_airflow_rate"] * 1000
                        if at.get("max_flow_during_reheat", 0) > 0:
                            t["maximum_heating_airflow"] = at["max_flow_during_reheat"] * 1000
                        if at.get("min_oa_schedule_name") and at["min_oa_schedule_name"] != "n/a":
                            t["minimum_outdoor_airflow_multiplier_schedule"] = at["min_oa_schedule_name"]
                        self.merge_into_terminal_list(zone, t)  # append to self.terminals_by_zone
                    elif 'has_baseboard' in ze:
                        for (type_of_component, obj_name) in ze['component_group_list']:
                            if 'BASEBOARD' in type_of_component:
                                obj_name_uc = obj_name.upper()
                                zone_baseboards = self.epjson_object.get(type_of_component, {})
                                t = {
                                    "id": f"{obj_name_uc}-terminal",
                                    "type": "BASEBOARD",
                                    "is_supply_ducted": False,
                                }
                                if "ELECTRIC" in type_of_component:
                                    t['heating_source'] = 'ELECTRIC'
                                else:
                                    t['heating_source'] = 'HOT_WATER'
                                if obj_name in zone_baseboards:
                                    bb = zone_baseboards[obj_name]
                                    cap = bb.get("heating_design_capacity")
                                    if is_float(cap):
                                        t["heating_capacity"] = float(cap)
                                self.merge_into_terminal_list(zone, t)
                    elif 'has_radiant' in ze:
                        for (type_of_component, obj_name) in ze['component_group_list']:
                            if 'RADIANT' in type_of_component:
                                t = {
                                    "id": f"{obj_name}-terminal",
                                    "type": "RADIANT",
                                    "is_supply_ducted": False,
                                }
                                if "ELECTRIC" in type_of_component:
                                    t['heating_source'] = 'ELECTRIC'
                                else:
                                    t['heating_source'] = 'HOT_WATER'
                                self.merge_into_terminal_list(zone, t)
                    elif 'has_vrf' in ze:
                        for (type_of_component, obj_name) in ze['component_group_list']:
                            if 'RADIANT' in type_of_component:
                                t = {
                                    "id": f"{obj_name}-terminal",
                                    "type": "VARIABLE_REFRIGERANT_FLOW",
                                    "is_supply_ducted": False,
                                    'heating_source': 'OTHER'
                                }
                            self.merge_into_terminal_list(zone, t)
        return self.terminals_by_zone

    def merge_into_terminal_list(self, zone_name, terminal):
        zone_key = zone_name.upper()
        if zone_key not in self.terminals_by_zone:
            self.terminals_by_zone[zone_key] = [terminal]
            return
        for existing in self.terminals_by_zone[zone_key]:
            if existing.get("id") == terminal.get("id"):
                existing.update(terminal)
                return
        self.terminals_by_zone[zone_key].append(terminal)

    def does_zone_equip_have_compressor(self, zone_equip_topology, coils_table):
        has_cooling_compressor = False
        has_heating_compressor = False
        if 'cooling_coil' in zone_equip_topology:
            cooling_coil_name = zone_equip_topology['cooling_coil']
            if cooling_coil_name in coils_table:
                coil_details = coils_table[cooling_coil_name]
                if 'DX' in coil_details['Coil Type']:
                    has_cooling_compressor = True
                elif 'WATERTOAIRHEATPUMP' in coil_details['Coil Type']:
                    has_cooling_compressor = True
        if 'main_heating_coil' in zone_equip_topology:
            heating_coil_name = zone_equip_topology['main_heating_coil']
            if heating_coil_name in coils_table:
                coil_details = coils_table[heating_coil_name]
                if 'DX' in coil_details['Coil Type']:
                    has_heating_compressor = True
                elif 'WATERTOAIRHEATPUMP' in coil_details['Coil Type']:
                    has_heating_compressor = True
        if not has_heating_compressor:
            if 'backup_heating_coil' in zone_equip_topology:
                heating_coil_name = zone_equip_topology['backup_heating_coil']
                if heating_coil_name in coils_table:
                    coil_details = coils_table[heating_coil_name]
                    if 'DX' in coil_details['Coil Type']:
                        has_heating_compressor = True
                    elif 'WATERTOAIRHEATPUMP' in coil_details['Coil Type']:
                        has_heating_compressor = True
        return has_cooling_compressor or has_heating_compressor

    def analyze_supply_topology_by_airloop(self):
        tops = {}  # nested dictionary with inner dictionary having predefined terms such as "supply-fan"
        airloop_supplies = self.gather_table_into_list('HVACTopology',
                                                       "Air Loop Supply Side Component Arrangement")
        top = {}
        oa_found = False
        heat_coil_found = False

        for row_count, airloop_supply in enumerate(airloop_supplies):
            current_airloop_name = airloop_supply['Airloop Name']

            # find outside air system
            if (airloop_supply['Component Type'] == 'AIRLOOPHVAC:OUTDOORAIRSYSTEM' or
                    airloop_supply['Sub-Component Type'] == 'AIRLOOPHVAC:OUTDOORAIRSYSTEM' or
                    airloop_supply['Sub-Sub-Component Type'] == 'AIRLOOPHVAC:OUTDOORAIRSYSTEM'):
                oa_found = True

            # find fan(s)
            found = False
            if 'FAN:' in airloop_supply['Component Type']:
                name = airloop_supply['Component Name']
                found = True
            elif 'FAN:' in airloop_supply['Sub-Component Type']:
                name = airloop_supply['Sub-Component Name']
                found = True
            elif 'FAN:' in airloop_supply['Sub-Sub-Component Type']:
                name = airloop_supply['Sub-Sub-Component Name']
                found = True
            if found:
                if oa_found:
                    top['supply_fan'] = name
                else:
                    top['return_fan'] = name

            # find cooling coils
            found = False
            if 'COIL:COOLING:' in airloop_supply['Component Type']:
                name = airloop_supply['Component Name']
                found = True
            elif 'COIL:COOLING:' in airloop_supply['Sub-Component Type']:
                name = airloop_supply['Sub-Component Name']
                found = True
            elif 'COIL:COOLING:' in airloop_supply['Sub-Sub-Component Type']:
                name = airloop_supply['Sub-Sub-Component Name']
                found = True
            if found:
                top['cooling_coil'] = name

            # find heating coil(s)
            found = False
            if 'COIL:HEATING:' in airloop_supply['Component Type']:
                name = airloop_supply['Component Name']
                found = True
            elif 'COIL:HEATING:' in airloop_supply['Sub-Component Type']:
                name = airloop_supply['Sub-Component Name']
                found = True
            elif 'COIL:HEATING:' in airloop_supply['Sub-Sub-Component Type']:
                name = airloop_supply['Sub-Sub-Component Name']
                found = True
            if found:
                if heat_coil_found:
                    top['backup_heating_coil'] = name
                else:
                    top['main_heating_coil'] = name
                heat_coil_found = True

            if (row_count == len(airloop_supplies) - 1) or ((row_count < len(airloop_supplies) - 1) and (
                    current_airloop_name != airloop_supplies[row_count + 1]['Airloop Name'])):
                oa_found = False
                heat_coil_found = False
                if top:  # add the current airloop topology unless empty (first iteration)

                    # if no supply fan ever found but return fan was, assume classified wrong
                    if 'supply_fan' not in top and 'return_fan' in top:
                        top['supply_fan'] = top['return_fan']
                        del top['return_fan']

                    # add to dictionary across all airloops
                    tops[current_airloop_name] = top
                    top = {}
        return tops

    def analyze_demand_topology_by_airloop(self):
        zones_by_airloop = {}
        zone_by_terminal = {}
        airloop_by_zone = {}
        airloop_demands = self.gather_table_into_list('HVACTopology',
                                                      "Air Loop Demand Side Component Arrangement")
        for airloop_demand in airloop_demands:
            if airloop_demand['Zone Name'] and airloop_demand['Terminal Unit Name']:
                current_air_loop = airloop_demand['Airloop Name']
                zone_name = airloop_demand['Zone Name']
                zone_by_terminal[airloop_demand['Terminal Unit Name']] = zone_name
                airloop_by_zone[zone_name] = current_air_loop
                if current_air_loop in zones_by_airloop:
                    zones_by_airloop[current_air_loop].append(zone_name)
                else:
                    zones_by_airloop[current_air_loop] = [zone_name,]
        return zones_by_airloop, zone_by_terminal, airloop_by_zone

    def analyze_zone_equipment(self):
        # dictionary that is returned has zone names as the keys and for each is a list
        # that contains dictionsary for each zone equipment (usually ZoneHVAC:*)
        # each of these subdictionaries has fan, heating coil, cooling coil

        zone_equipments = self.gather_table_into_list('HVACTopology',
                                                      "Zone Equipment Component Arrangement")
        tops = {}
        ze = {}
        heat_coil_found = False
        component_group_list = []

        for row_count, zone_equipment in enumerate(zone_equipments):
            zone_name = zone_equipment['Zone Name']
            component_name = zone_equipment['Component Name']

            if 'ZONEHVAC:AIRDISTRIBUTIONUNIT' in zone_equipment['Component Type']:
                ze['has_ADU'] = True

            if 'FAN:' in zone_equipment['Sub-Component Type']:
                ze['fan'] = zone_equipment['Sub-Component Name']
            elif 'FAN:' in zone_equipment['Sub-Sub-Component Type']:
                ze['fan'] = zone_equipment['Sub-Sub-Component Name']

            found = False
            if 'COIL:HEATING:' in zone_equipment['Sub-Component Type']:
                name = zone_equipment['Sub-Component Name']
                found = True
            elif 'COIL:HEATING:' in zone_equipment['Sub-Sub-Component Type']:
                name = zone_equipment['Sub-Sub-Component Name']
                found = True
            if found:
                if heat_coil_found:
                    ze['backup_heating_coil'] = name
                else:
                    ze['main_heating_coil'] = name
                heat_coil_found = True

            if 'COIL:COOLING:' in zone_equipment['Sub-Component Type']:
                ze['cooling_coil'] = zone_equipment['Sub-Component Name']
            elif 'COIL:COOLING:' in zone_equipment['Sub-Sub-Component Type']:
                ze['cooling_coil'] = zone_equipment['Sub-Sub-Component Name']

            if 'VAV:' in zone_equipment['Sub-Component Type']:
                ze['has_vav'] = True
            elif 'VAV:' in zone_equipment['Sub-Sub-Component Type']:
                ze['has_vav'] = True

            if 'PIU:' in zone_equipment['Sub-Component Type']:
                ze['has_vav'] = True
            elif 'PIU:' in zone_equipment['Sub-Sub-Component Type']:
                ze['has_vav'] = True

            if 'BASEBOARD:' in zone_equipment['Component Type']:
                ze['has_baseboard'] = True
            elif 'BASEBOARD:' in zone_equipment['Sub-Component Type']:
                ze['has_baseboard'] = True
            elif 'BASEBOARD:' in zone_equipment['Sub-Sub-Component Type']:
                ze['has_baseboard'] = True
            # use elif here since some baseboards also use term radiant
            elif 'RADIANT' in zone_equipment['Component Type']:
                ze['has_radiant'] = True
            elif 'RADIANT' in zone_equipment['Sub-Component Type']:
                ze['has_radiant'] = True
            elif 'RADIANT' in zone_equipment['Sub-Sub-Component Type']:
                ze['has_radiant'] = True

            if 'VARIABLEREFRIGERANTFLOW' in zone_equipment['Component Type']:
                ze['has_vrf'] = True
            elif 'VARIABLEREFRIGERANTFLOW' in zone_equipment['Sub-Component Type']:
                ze['has_vrf'] = True
            elif 'VARIABLEREFRIGERANTFLOW' in zone_equipment['Sub-Sub-Component Type']:
                ze['has_vrf'] = True

            type_of_component = zone_equipment['Component Type']
            name = zone_equipment['Component Name']
            component_group = (type_of_component, name)
            if component_group not in component_group_list and component_group != ('', ''):
                component_group_list.append(component_group)

            type_of_component = zone_equipment['Sub-Component Type']
            name = zone_equipment['Sub-Component Name']
            component_group = (type_of_component, name)
            if component_group not in component_group_list and component_group != ('', ''):
                component_group_list.append(component_group)

            type_of_component = zone_equipment['Sub-Sub-Component Type']
            name = zone_equipment['Sub-Sub-Component Name']
            component_group = (type_of_component, name)
            if component_group not in component_group_list and component_group != ('', ''):
                component_group_list.append(component_group)

            #  when new zone equipment component name or end of list
            if (row_count == len(zone_equipments) - 1) or ((row_count < len(zone_equipments) - 1) and (
                    component_name != zone_equipments[row_count + 1]['Component Name'])):
                heat_coil_found = False
                if component_group_list:
                    ze['component_group_list'] = component_group_list
                    component_group_list = []
                    if zone_name in tops:
                        tops[zone_name].append(ze)
                    else:
                        tops[zone_name] = [ze,]
                ze = {}
        return tops

    def gather_economizer_by_airloop(self):
        economizers = {}
        sys_econo_reps = self.gather_table_into_list('SystemSummary', 'Economizer')
        airloop_supplies = self.gather_table_into_list('HVACTopology',
                                                       "Air Loop Supply Side Component Arrangement")
        ep_control_type_map = {
            'FixedDryBulb': 'TEMPERATURE',
            'FixedEnthalpy': 'ENTHALPY',
            'DifferentialDryBulb': 'DIFFERENTIAL_TEMPERATURE',
            'DifferentialEnthalpy': 'DIFFERENTIAL_ENTHALPY',
            'FixedDewPointAndDryBulb': 'OTHER',
            'ElectronicEnthalpy': 'OTHER',
            'DifferentialDryBulbAndEnthalpy': 'OTHER',
            'NoEconomizer': 'FIXED_FRACTION'
        }
        airloop_by_oa_sys = {}
        for airloop_supply in airloop_supplies:
            if (airloop_supply['Component Type'] == 'AIRLOOPHVAC:OUTDOORAIRSYSTEM' and
                    airloop_supply['Sub-Component Type'] == ''):
                airloop_by_oa_sys[airloop_supply['Component Name']] = airloop_supply['Airloop Name']
        for sys_econo_rep in sys_econo_reps:
            if sys_econo_rep['AirLoopHVAC:OutdoorAirSystem Name'] in airloop_by_oa_sys:
                economizer = {'id': sys_econo_rep['first column'], }
                if sys_econo_rep['High Limit Shutoff Control'] in ep_control_type_map:
                    economizer['type'] = ep_control_type_map[sys_econo_rep['High Limit Shutoff Control']]
                if sys_econo_rep['Outdoor Air Temperature Limit [C]']:
                    economizer['high_limit_shutoff_temperature'] = float(
                        sys_econo_rep['Outdoor Air Temperature Limit [C]'])
                if sys_econo_rep['Maximum Outdoor Air [m3/s]']:
                    # not used in economizer but just carried along in data structure
                    economizer['XTRA-Maxair'] = float(sys_econo_rep['Maximum Outdoor Air [m3/s]'])
                economizers[airloop_by_oa_sys[sys_econo_rep['AirLoopHVAC:OutdoorAirSystem Name']]] = economizer
        return economizers

    def gather_dehumid_option_by_airloop(self):
        dehumid_options = {}
        airloop_supplies = self.gather_table_into_list('HVACTopology',
                                                       "Air Loop Supply Side Component Arrangement")
        for airloop_supply in airloop_supplies:
            if ('desiccant' in (airloop_supply['Component Type']).lower() or
                    'desiccant' in (airloop_supply['Sub-Component Type']).lower() or
                    'desiccant' in (airloop_supply['Sub-Sub-Component Type']).lower()):
                dehumid_options[airloop_supply['Airloop Name']] = 'DESICCANT'
            elif 'coilsystem:cooling:water:heatexchangerassisted ' in (airloop_supply['Component Type']).lower():
                dehumid_options[airloop_supply['Airloop Name']] = 'SERIES_HEAT_RECOVERY'
        # note that determining if it is MECHANICAL_COOLING would require output reporting that does not exist
        # to determine if the controls are present to control it that way
        return dehumid_options

    def gather_humid_option_by_airloop(self):
        humid_options = {}
        airloop_supplies = self.gather_table_into_list('HVACTopology',
                                                       "Air Loop Supply Side Component Arrangement")
        for airloop_supply in airloop_supplies:
            if ('humidifier:steam:' in (airloop_supply['Component Type']).lower() or
                    'humidifier:steam:' in (airloop_supply['Sub-Component Type']).lower() or
                    'humidifier:steam:' in (airloop_supply['Sub-Sub-Component Type']).lower()):
                humid_options[airloop_supply['Airloop Name']] = 'OTHER'
        return humid_options

    def get_table(self, report_name: str, table_name: str) -> JsonDict:
        tabular_reports: List[JsonDict] = self.json_results_object['TabularReports']
        for tabular_report in tabular_reports:
            if tabular_report['ReportName'] == report_name:
                tables: List[JsonDict] = tabular_report['Tables']
                for table in tables:
                    if table['TableName'] == table_name:
                        return table
        return {}

    def gather_coil_connections(self) -> Dict[str, Dict[str, str]]:
        connection_by_coil: Dict[str, Dict[str, str]] = {}
        table: JsonDict = self.get_table('CoilSizingDetails', 'Coil Connections')
        if not table:
            return connection_by_coil
        rows: TableRows = table['Rows']
        row_keys: List[str] = list(rows.keys())
        cols: List[str] = table['Cols']
        plant_loop_name_column: int = cols.index('Plant Loop Name')
        for row_key in row_keys:
            if row_key == 'None':
                continue
            plant_loop_name: str = str(rows[row_key][plant_loop_name_column])
            connection: Dict[str, str] = {'plant_loop_name': plant_loop_name}
            connection_by_coil[row_key] = connection
        # print(connection_by_coil)
        return connection_by_coil

    def gather_supply_fan_names_by_coil_connection(self):
        supply_fan_name_by_coil = {}
        table = self.get_table('CoilSizingDetails', 'Coil Connections')
        if not table:
            return supply_fan_name_by_coil
        rows = table['Rows']
        row_keys: List[str] = list(rows.keys())
        cols: List[str] = table['Cols']
        supply_fan_name_column = -1
        if 'Supply Fan Name for HVAC' in cols:
            supply_fan_name_column = cols.index('Supply Fan Name for HVAC')
        elif 'Supply Fan Name for Coil' in cols:
            supply_fan_name_column = cols.index('Supply Fan Name for Coil')
        if supply_fan_name_column == -1:
            return supply_fan_name_by_coil
        for row_key in row_keys:
            if row_key == 'None':
                continue
            supply_fan_name = rows[row_key][supply_fan_name_column]
            if not supply_fan_name:
                continue
            if supply_fan_name.lower() == 'unknown':
                continue
            supply_fan_name_by_coil[row_key] = supply_fan_name
        return supply_fan_name_by_coil

    def gather_table_into_list(self, report_name: str, table_name: str) -> List[JsonDict]:
        # transform the rows and columns format into a list of dictionaries
        list_of_dict: List[JsonDict] = []
        table: JsonDict = self.get_table(report_name, table_name)
        if not table:
            return list_of_dict
        rows: TableRows = table['Rows']
        row_keys: List[str] = list(rows.keys())
        cols: List[str] = table['Cols']
        for row_key in row_keys:
            arrangement: JsonDict = {}
            for col in cols:
                col_index: int = cols.index(col)
                arrangement[col] = rows[row_key][col_index]
            arrangement["first column"] = row_key
            list_of_dict.append(arrangement)
#        for item in list_of_dict:
#            print(item)
        return list_of_dict

    def get_table_dictionary(
            self,
            report_name: str,
            table_name: str,
            ignore_first_column: bool = False
    ) -> Dict[str, JsonDict]:
        # transform the rows and columns format into a dictionary of dictionaries
        dict_of_dict: Dict[str, JsonDict] = {}
        table: JsonDict = self.get_table(report_name, table_name)
        if not table:
            return dict_of_dict
        rows: TableRows = table['Rows']
        row_keys: List[str] = list(rows.keys())
        cols: List[str] = table['Cols']
        if not ignore_first_column:
            for row_key in row_keys:
                arrangement: JsonDict = {}
                for col in cols:
                    col_index: int = cols.index(col)
                    arrangement[col] = rows[row_key][col_index]
                dict_of_dict[row_key] = arrangement
        else:
            if cols:
                for row_key in row_keys:
                    arrangement: JsonDict = {}
                    for col in cols[1:]:
                        col_index: int = cols.index(col)
                        arrangement[col] = rows[row_key][col_index]
                    dict_of_dict[str(rows[row_key][0])] = arrangement
#        for item in dict_of_dict.items():
#            print(item)
        return dict_of_dict

    def gather_exhaust_fans_by_zone(self):
        exh_fan_by_zone = {}
        topology_zone_equips = self.gather_table_into_list('HVACTopology', "Zone Equipment Component Arrangement")
        for topology_zone_equip in topology_zone_equips:
            current_zone_name = topology_zone_equip['Zone Name']
            if topology_zone_equip['Component Type'] == 'FAN:ZONEEXHAUST':
                exh_fan_by_zone[current_zone_name] = topology_zone_equip['Component Name']
        return exh_fan_by_zone

    def gather_possible_return_fans_by_airloop(self):
        return_fans = {}
        airloop_supplies = self.gather_table_into_list('HVACTopology',
                                                       "Air Loop Supply Side Component Arrangement")
        blank_row = False
        for supply_row in airloop_supplies:
            if supply_row['Supply Branch Name']:
                if blank_row:
                    if 'FAN:' in supply_row['Component Type']:
                        return_fans[supply_row['Airloop Name']] = supply_row['Component Name']
                    elif 'FAN:' in supply_row['Sub-Component Type']:
                        return_fans[supply_row['Airloop Name']] = supply_row['Sub-Component Name']
                blank_row = False
            else:
                # if empty string then the row is blank except for airloop name
                blank_row = True
                continue
        return return_fans

    def gather_exhaust_fans_by_airloop(self):
        exh_fan_by_airloop = {}  # for each airloop name contains a list of exhaust fans
        topology_zone_equips = self.gather_table_into_list('HVACTopology', "Zone Equipment Component Arrangement")
        zone_name_exh_fan = []  # list of tuples of zone name and exhaust fans
        for topology_zone_equip in topology_zone_equips:
            current_zone_name = topology_zone_equip['Zone Name']
            # only look in nested sub and sub-sub components
            if topology_zone_equip['Sub-Component Type'] == 'FAN:ZONEEXHAUST':
                zone_name_exh_fan.append((current_zone_name, topology_zone_equip['Sub-Component Name']))
            elif topology_zone_equip['Sub-Sub-Component Type'] == 'FAN:ZONEEXHAUST':
                zone_name_exh_fan.append((current_zone_name, topology_zone_equip['Sub-Sub-Component Name']))
        topology_airloop_demands = self.gather_table_into_list('HVACTopology',
                                                               "Air Loop Demand Side Component Arrangement")
        airloop_by_zone = {}
        for topology_airloop_demand in topology_airloop_demands:
            if not topology_airloop_demands[0]['first column'] == 'None':
                if topology_airloop_demand['Zone Name']:
                    airloop_by_zone[topology_airloop_demand['Zone Name']] = topology_airloop_demand['Airloop Name']
        if zone_name_exh_fan and airloop_by_zone:
            for (zone_name, fan_name) in zone_name_exh_fan:
                if zone_name in airloop_by_zone:
                    airloop = airloop_by_zone[zone_name]
                    if airloop not in exh_fan_by_airloop:
                        exh_fan_by_airloop[airloop] = [fan_name, ]
                        exh_fan_by_airloop[airloop] = [fan_name, ]
                    else:
                        exh_fan_by_airloop[airloop].append(fan_name)
        return exh_fan_by_airloop

    def gather_airflows_from_62(self):
        airflows_by_sys = {}
        cool_airflows_by_sys = {}
        cool_table = self.gather_table_into_list('Standard62.1Summary',
                                                 'System Ventilation Calculations for Cooling Design')
        heat_table = self.gather_table_into_list('Standard62.1Summary',
                                                 'System Ventilation Calculations for Heating Design')
        if not cool_table and heat_table:
            return airflows_by_sys

        if cool_table:
            if not cool_table[0]['first column'] == 'None':
                for row in cool_table:
                    cool_min_primary = float(row['Sum of Min Zone Primary Airflow - Vpz-min [m3/s]']) * 1000
                    cool_outdoor = float(row['Zone Outdoor Airflow Cooling - Voz-clg [m3/s]']) * 1000
                    cool_airflows_by_sys[row['first column']] = (cool_min_primary, cool_outdoor)
        # now use the values in the heating table if they are lower
        if heat_table:
            if not heat_table[0]['first column'] == 'None':
                for row in heat_table:
                    cool_min_primary, cool_outdoor = cool_airflows_by_sys[row['first column']]
                    min_primary = min(float(row['Sum of Min Zone Primary Airflow - Vpz-min [m3/s]']) * 1000,
                                      cool_min_primary)
                    outdoor = min(float(row['Zone Outdoor Airflow Heating - Voz-htg [m3/s]']) * 1000, cool_outdoor)
                    airflows_by_sys[row['first column']] = (min_primary, outdoor)

        return airflows_by_sys

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
            if row_key == 'None':
                continue
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
        net_cop_2017_column = dx_2017_cols.index('Standard Rating Net COP [W/W][2]')
        eer_2017_column = dx_2017_cols.index('EER [Btu/W-h][2]')
        seer_2017_column = dx_2017_cols.index('SEER Standard [Btu/W-h][2,3]')
        ieer_2017_column = dx_2017_cols.index('IEER [Btu/W-h][2]')
        for row_key in row_keys:
            if row_key == 'None':
                continue
            if row_key in dx_2017_row_keys:
                coil_efficiencies[row_key]['StandardRatedNetCOP2017'] = float(
                    dx_2017_rows[row_key][net_cop_2017_column])
                coil_efficiencies[row_key]['EER2017'] = float(dx_2017_rows[row_key][eer_2017_column])
                seer2017_string = dx_2017_rows[row_key][seer_2017_column]
                if seer2017_string != 'N/A':
                    coil_efficiencies[row_key]['SEER2017'] = float(seer2017_string)
                ieer2017_string = dx_2017_rows[row_key][ieer_2017_column]
                if ieer2017_string != 'N/A':
                    coil_efficiencies[row_key]['IEER2017'] = float(ieer2017_string)
        dx_2023_table = self.get_table('EquipmentSummary', 'DX Cooling Coil Standard Ratings 2023')
        dx_2023_rows = dx_2023_table['Rows']
        dx_2023_row_keys = list(dx_2023_rows.keys())
        dx_2023_cols = dx_2023_table['Cols']
        net_cop_2023_column = dx_2023_cols.index('Standard Rating Net COP2 [W/W][2,4]')
        eer_2023_column = dx_2023_cols.index('EER2 [Btu/W-h][2,4]')
        seer_2023_column = dx_2023_cols.index('SEER2 Standard [Btu/W-h][2,3]')
        ieer_2023_column = dx_2023_cols.index('IEER [Btu/W-h][2]')
        for row_key in row_keys:
            if row_key in dx_2023_row_keys:
                if row_key == 'None':
                    continue
                coil_efficiencies[row_key]['StandardRatedNetCOP2023'] = float(
                    dx_2023_rows[row_key][net_cop_2023_column])
                coil_efficiencies[row_key]['EER2023'] = float(dx_2023_rows[row_key][eer_2023_column])
                seer2023_string = dx_2023_rows[row_key][seer_2023_column]
                if seer2023_string != 'N/A':
                    coil_efficiencies[row_key]['SEER2023'] = float(seer2023_string)
                coil_efficiencies[row_key]['IEER2023'] = float(dx_2023_rows[row_key][ieer_2023_column])
        return coil_efficiencies

    @staticmethod
    def process_cooling_metrics(coil_name, coil_efficiencies):
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
            if row_key == 'None':
                continue
            coil_type = heating_coils_rows[row_key][type_column]
            used_as_sup_heat = 'Y' in heating_coils_rows[row_key][used_as_sup_heat_column]
            coil_efficiency: JsonDict = {'type': coil_type,
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
        minimum_temperature_column = dx_cols.index('Minimum Outdoor Dry-Bulb Temperature for Compressor Operation [C]')
        supplement_high_temp_column = dx_cols.index('Supplemental Heat High Shutoff Temperature [C]')
        for row_key in dx_row_keys:
            if row_key == 'None':
                continue
            if row_key in coil_row_keys:
                try:
                    coil_efficiencies[row_key]['HSPF'] = float(dx_rows[row_key][hspf_column])
                except ValueError:
                    pass
                coil_efficiencies[row_key]['HSPF_region'] = dx_rows[row_key][hspf_region_column]
                try:
                    coil_efficiencies[row_key]['minimum_temperature_compressor'] = float(
                        dx_rows[row_key][minimum_temperature_column])
                except ValueError:
                    pass
                try:
                    coil_efficiencies[row_key]['max_temperature_supplement'] = float(
                        dx_rows[row_key][supplement_high_temp_column])
                except ValueError:
                    pass

        dx2_table = self.get_table('EquipmentSummary', 'DX Heating Coils AHRI 2023')
        dx2_rows = dx2_table['Rows']
        dx2_row_keys = list(dx2_rows.keys())
        dx2_cols = dx2_table['Cols']
        hspf2_column = dx2_cols.index('HSPF2 [Btu/W-h]')
        hspf2_region_column = dx2_cols.index('Region Number')
        for row_key in dx2_row_keys:
            if row_key == 'None':
                continue
            if row_key in coil_row_keys:
                coil_efficiencies[row_key]['HSPF2'] = float(dx2_rows[row_key][hspf2_column])
                coil_efficiencies[row_key]['Region Number'] = dx2_rows[row_key][hspf2_region_column]
        return coil_efficiencies

    @staticmethod
    def process_heating_metrics(coil_name, coil_efficiencies):
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
        motor_heat_to_zone_frac_column = cols.index('Motor Heat to Zone Fraction')
        speed_control_method_column = cols.index('Speed Control Method')
        motor_loss_zone_name_column = cols.index('Motor Loss Zone Name')
        airloop_name_column = cols.index('Airloop Name')
        for row_key in coil_row_keys:
            if row_key == 'None':
                continue
            max_air_flow_rate = float(rows[row_key][max_air_flow_rate_column])
            is_autosized = 'Y' in rows[row_key][is_autosized_column]
            rated_electricity_rate = float(rows[row_key][rated_electricity_rate_column])
            delta_pressure = float(rows[row_key][delta_pressure_column])
            total_efficiency = float(rows[row_key][total_efficiency_column])
            motor_eff = float(rows[row_key][motor_eff_column])
            motor_heat_in_air = float(rows[row_key][motor_heat_in_air_column])
            motor_heat_to_zone_frac = float(rows[row_key][motor_heat_to_zone_frac_column])
            motor_loss_zone_name = rows[row_key][motor_loss_zone_name_column]
            # extra columns of data not necessarily used now
            extra_type = rows[row_key][type_column]
            fan_energy_index = float(rows[row_key][fan_energy_index_column])
            purpose = rows[row_key][purpose_column]
            speed_control_method = rows[row_key][speed_control_method_column]
            airloop_name = rows[row_key][airloop_name_column]
            equipment_fan = {'design_airflow': max_air_flow_rate,
                             'is_airflow_calculated': is_autosized,
                             'design_electric_power': rated_electricity_rate,
                             'design_pressure_rise': delta_pressure,
                             'total_efficiency': total_efficiency,
                             'motor_efficiency': motor_eff,
                             'motor_heat_to_airflow_fraction': motor_heat_in_air,
                             'motor_heat_to_zone_fraction': motor_heat_to_zone_frac,
                             'motor_location_zone': motor_loss_zone_name}
            fan_extra = {'type': extra_type,
                         'fan_energy_index': fan_energy_index,
                         'purpose': purpose,
                         'speed_control_method': speed_control_method,
                         'airloop_name': airloop_name}
            #  for Fan:SystemModel need to add some additional fields to understand later if variable speed or not
            equipment_fan['operating_points'] = self.gather_fan_operating_points(row_key, max_air_flow_rate,
                                                                                 rated_electricity_rate)
            if airloop_name != 'N/A':
                air_energy_recovery = self.gather_air_heat_recovery(airloop_name)
                if air_energy_recovery:
                    fan_extra['air_energy_recovery'] = air_energy_recovery
            if extra_type == 'Fan:SystemModel':
                fan_system_model = self.get_epjson_by_uc_name('Fan:SystemModel', row_key)
                if 'speed_control_method' in fan_system_model:
                    fan_extra['speed_control_method'] = fan_system_model['speed_control_method']
                if 'number_of_speeds' in fan_system_model:
                    fan_extra['number_of_speeds'] = fan_system_model['number_of_speeds']
            equipment_fans[row_key] = (equipment_fan, fan_extra)
        return equipment_fans

    def gather_air_heat_recovery(self, airloop_name):
        heat_recovery = {}
        table_in = self.gather_table_into_list('EquipmentSummary', 'Air Heat Recovery')
        active_map = {
            'WhenFansOn': 'WHEN_FANS_ON',
            'Scheduled': 'SCHEDULED',
            'WhenOutsideEconomizerLimits': 'OTHER',
            'WhenMinimumOutdoorAir': 'WHEN_MINIMUM_OUTSIDE_AIR'
        }
        for row_in in table_in:
            if airloop_name == row_in['Airloop Name']:
                if row_in['Type'] == 'HeatExchanger:AirToAir:SensibleAndLatent':
                    if float(row_in['Latent Effectiveness at 100% Heating Air Flow']) > 0:
                        option = 'ENTHALPY'
                    else:
                        option = 'ENTHALPY'
                    if row_in['Plate/Rotary'] == 'Rotary':
                        option += '_HEAT_WHEEL'
                    else:
                        option += '_HEAT_EXCHANGE'
                else:
                    option = 'SENSIBLE_HEAT_EXCHANGE'
                sensible_effectiveness = max(float(row_in['Sensible Effectiveness at 100% Heating Air Flow']),
                                             float(row_in['Sensible Effectiveness at 100% Cooling Air Flow']))
                latent_effectiveness = max(float(row_in['Latent Effectiveness at 100% Heating Air Flow']),
                                           float(row_in['Latent Effectiveness at 100% Cooling Air Flow']))
                heat_recovery = {
                    'id': row_in['first column'],
                    'type': option,
                    'design_sensible_effectiveness': sensible_effectiveness,
                    'design_latent_effectiveness': latent_effectiveness,
                    'outdoor_airflow': float(row_in['Supply Air Flow Rate [m3/s]']),
                    'exhaust_airflow': float(row_in['Exhaust Air Flow Rate [m3/s]']),
                }
                active = row_in['Heat Recovery Active']
                if active in active_map:
                    heat_recovery['energy_recovery_operation'] = active_map[active]
        return heat_recovery

    def gather_fan_operating_points(self, fan_name, max_flow, max_elec):
        operating_points = []
        fractions = self.get_table_dictionary('EquipmentSummary', 'Fan Power Fractions')
        column_headings = ['Flow Frac 0.0',
                           'Flow Frac 0.1',
                           'Flow Frac 0.2',
                           'Flow Frac 0.3',
                           'Flow Frac 0.4',
                           'Flow Frac 0.5',
                           'Flow Frac 0.6',
                           'Flow Frac 0.7',
                           'Flow Frac 0.8',
                           'Flow Frac 0.9',
                           'Flow Frac 1.0']
        if fan_name in fractions:
            for count, heading in enumerate(column_headings):
                operating_point = {
                    'airflow': max_flow * count / 10.,
                    'power': max_elec * float(fractions[fan_name][heading])
                }
                operating_points.append(operating_point)
        return operating_points

    def gather_air_terminal(self):
        air_terminal_by_zone = {}
        table = self.get_table('EquipmentSummary', 'Air Terminals')
        if not table:
            return air_terminal_by_zone
        rows = table['Rows']
        row_keys = list(rows.keys())
        cols = table['Cols']
        zone_name_column = cols.index('Zone Name')
        min_flow_column = cols.index('Minimum Flow [m3/s]')
        min_oa_flow_column = cols.index('Minimum Outdoor Flow [m3/s]')
        supply_cool_set_point_column = cols.index('Supply Cooling Setpoint [C]')
        supply_heat_set_point_column = cols.index('Supply Heating Setpoint [C]')
        heating_capacity_column = cols.index('Heating Capacity [W]')
        cooling_capacity_column = cols.index('Cooling Capacity [W]')
        type_input_column = cols.index('Type of Input Object')
        heat_coil_type_column = cols.index('Heat/Reheat Coil Object Type')
        chill_coil_type_column = cols.index('Chilled Water Coil Object Type')
        fan_type_column = cols.index('Fan Object Type')
        fan_name_column = cols.index('Fan Name')
        primary_airflow_rate_column = cols.index('Primary Air Flow Rate [m3/s]')
        secondary_airflow_rate_column = cols.index('Secondary Air Flow Rate [m3/s]')
        min_flow_schedule_name_column = cols.index('Minimum Flow Schedule Name')
        max_flow_during_reheat_column = cols.index('Maximum Flow During Reheat [m3/s]')
        min_oa_schedule_name_column = cols.index('Minimum Outdoor Flow Schedule Name')
        for row_key in row_keys:
            if row_key == 'None':
                continue
            zone_name = rows[row_key][zone_name_column].upper()
            min_flow = rows[row_key][min_flow_column]
            min_oa_flow = rows[row_key][min_oa_flow_column]
            supply_cool_set_point = rows[row_key][supply_cool_set_point_column]
            supply_heat_set_point = rows[row_key][supply_heat_set_point_column]
            heating_capacity = rows[row_key][heating_capacity_column]
            cooling_capacity = rows[row_key][cooling_capacity_column]
            type_input = rows[row_key][type_input_column]
            heat_coil_type = rows[row_key][heat_coil_type_column]
            chill_coil_type = rows[row_key][chill_coil_type_column]
            fan_type = rows[row_key][fan_type_column]
            fan_name = rows[row_key][fan_name_column]
            primary_airflow_rate = rows[row_key][primary_airflow_rate_column]
            secondary_airflow_rate = rows[row_key][secondary_airflow_rate_column]
            min_flow_schedule_name = rows[row_key][min_flow_schedule_name_column]
            max_flow_during_reheat = rows[row_key][max_flow_during_reheat_column]
            min_oa_schedule_name = rows[row_key][min_oa_schedule_name_column]
            terminal = {'terminal_name': row_key,
                        'min_flow': float(min_flow),
                        'min_oa_flow': float(min_oa_flow),
                        'supply_cool_set_point': float(supply_cool_set_point),
                        'supply_heat_set_point': float(supply_heat_set_point),
                        'heating_capacity': float(heating_capacity),
                        'cooling_capacity': float(cooling_capacity),
                        'type_input': type_input,
                        'heat_coil_type': heat_coil_type,
                        'chill_coil_type': chill_coil_type,
                        'fan_type': fan_type,
                        'fan_name': fan_name,
                        'primary_airflow_rate': float(primary_airflow_rate),
                        'min_flow_schedule_name': min_flow_schedule_name,
                        'min_oa_schedule_name': min_oa_schedule_name}
            if is_float(secondary_airflow_rate):
                terminal['secondary_airflow_rate'] = float(secondary_airflow_rate)
            else:
                terminal['secondary_airflow_rate'] = 0.
            if is_float(max_flow_during_reheat):
                terminal['max_flow_during_reheat'] = float(max_flow_during_reheat)
            else:
                terminal['max_flow_during_reheat'] = 0.
            air_terminal_by_zone[zone_name] = terminal
        # print(air_terminal_by_zone)
        return air_terminal_by_zone

    def gather_zone_hvac_equipment_by_zone(self):
        # dictionary: zone name -> list of tuples(object_type, object_name)
        zone_equipment_by_zone = {}
        equipment_connections = self.epjson_object.get('ZoneHVAC:EquipmentConnections', {})
        equipment_lists = self.epjson_object.get('ZoneHVAC:EquipmentList', {})
        for equipment_connection in equipment_connections.values():
            zone_name = equipment_connection.get('zone_name', '').upper()
            equipment_list_name = equipment_connection.get('zone_conditioning_equipment_list_name')
            if not zone_name or equipment_list_name not in equipment_lists:
                continue
            equipment_list = equipment_lists[equipment_list_name]
            equipment = []
            if 'equipment' in equipment_list and isinstance(equipment_list['equipment'], list):
                for equipment_item in equipment_list['equipment']:
                    object_type = equipment_item.get('zone_equipment_object_type')
                    object_name = equipment_item.get('zone_equipment_name')
                    if object_type and object_name:
                        equipment.append((object_type, object_name))
            else:
                # backward compatibility with older epJSON variants
                for index in range(1, 21):
                    object_type = equipment_list.get(f'zone_equipment_{index}_object_type')
                    object_name = equipment_list.get(f'zone_equipment_{index}_name')
                    if object_type and object_name:
                        equipment.append((object_type, object_name))
            zone_equipment_by_zone[zone_name] = equipment
        return zone_equipment_by_zone

    def add_chillers(self):
        chillers = []
        tabular_reports = self.json_results_object['TabularReports']
        plant_loop_arrangement = self.gather_table_into_list('HVACTopology', 'Plant Loop Component Arrangement')
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
                                metric_types = ['FULL_LOAD_EFFICIENCY_RATED',
                                                'INTEGRATED_PART_LOAD_VALUE']
                                metric_values = [float(rows[chiller_name][rated_efficiency_column]),
                                                 float(rows[chiller_name][part_load_efficiency_column])]
                                chiller = {'id': chiller_name,
                                           'cooling_loop': rows[chiller_name][plant_loop_name_column],
                                           'condensing_loop': rows[chiller_name][condenser_loop_name_column],
                                           'energy_source_type': fuel_type,
                                           'chiller_function': 'CHILLED_WATER_ONLY',
                                           'design_capacity': float(rows[chiller_name][reference_capacity_column]),
                                           'rated_capacity': float(rows[chiller_name][rated_capacity_column]),
                                           'rated_entering_condenser_temperature': float(
                                               rows[chiller_name][rated_enter_temp_column]),
                                           'rated_leaving_evaporator_temperature': float(
                                               rows[chiller_name][rated_leave_temp_column]),
                                           'minimum_load_ratio': float(rows[chiller_name][min_plr_column]),
                                           'design_flow_evaporator': float(
                                               rows[chiller_name][chilled_water_rate_column]),
                                           'design_flow_condenser': float(
                                               rows[chiller_name][condenser_water_rate_column]),
                                           'design_entering_condenser_temperature': float(
                                               rows[chiller_name][ref_enter_temp_column]),
                                           'design_leaving_evaporator_temperature': float(
                                               rows[chiller_name][ref_leave_temp_column]),
                                           'efficiency_metric_values': metric_values,
                                           'efficiency_metric_types': metric_types,
                                           'is_chilled_water_pump_interlocked': do_chiller_and_pump_share_branch(
                                               chiller_name, plant_loop_arrangement, 'Supply'),
                                           'is_condenser_water_pump_interlocked': do_chiller_and_pump_share_branch(
                                               chiller_name, plant_loop_arrangement, 'Demand')}
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
        operation_load_based = self.gather_table_into_list('ControlSummary', 'PlantEquipmentOperation Load Based')
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
                                    'efficiency_metric_types': ['THERMAL', ],
                                    'efficiency_metric_values':
                                        [float(rows[boiler_name][reference_efficiency_column]), ],
                                    'auxiliary_power': float(rows[boiler_name][parasitic_load_column]),
                                }
                                for operation_row in operation_load_based:
                                    if boiler_name == operation_row['Equipment']:
                                        boiler['operation_lower_limit'] = float(operation_row['Lower Limit [W]'])
                                        boiler['operation_upper_limit'] = float(operation_row['Upper Limit [W]'])
                                        break
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
                        type_column = cols.index('Type')
                        fluid_type_column = cols.index('Fluid Type')
                        loop_name_column = cols.index('Condenser Loop Name')
                        range_column = cols.index('Range [C]')
                        approach_column = cols.index('Approach [C]')
                        fan_power_column = cols.index('Design Fan Power [W]')
                        wet_bulb_column = cols.index('Design Inlet Air Wet-Bulb Temperature [C]')
                        flow_rate_column = cols.index('Design Water Flow Rate [m3/s]')
                        leaving_setpoint_column = cols.index('Leaving Water Setpoint Temperature [C]')
                        for heat_rejection_name in heat_rejection_names:
                            if heat_rejection_name != 'None':
                                fan = {
                                    'id': heat_rejection_name + '_fan',
                                    'motor_nameplate_power': float(rows[heat_rejection_name][fan_power_column])
                                }
                                heat_rejection = {
                                    'id': heat_rejection_name,
                                    'loop': rows[heat_rejection_name][loop_name_column],
                                    'range': float(rows[heat_rejection_name][range_column]),
                                    'fan': fan,
                                    'design_wetbulb_temperature': float(rows[heat_rejection_name][wet_bulb_column]),
                                    'design_water_flowrate': float(rows[heat_rejection_name][flow_rate_column]) * 1000,
                                    'leaving_water_setpoint_temperature':
                                        float(rows[heat_rejection_name][leaving_setpoint_column]),
                                }
                                approach_str = rows[heat_rejection_name][approach_column]
                                type_of_object = rows[heat_rejection_name][type_column]
                                if approach_str:
                                    heat_rejection['approach'] = float(approach_str)
                                heat_rejection['type'] = heat_rejection_type_convert(type_of_object)
                                fluid_type_str = rows[heat_rejection_name][fluid_type_column].lower()
                                if fluid_type_str == 'water':
                                    heat_rejection['fluid'] = 'WATER'
                                else:
                                    heat_rejection['fluid'] = 'OTHER'
                                heat_rejection['fan_speed_control'] = heat_rejection_fan_speed_convert(type_of_object)
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
                        control_column = cols.index('Control')
                        for pump_name in pump_names:
                            if pump_name == 'None':
                                continue
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
                                'is_flow_calculated': is_autosized
                            }
                            pump_extra = {
                                'control': rows[pump_name][control_column]
                            }
                            self.pump_extra[pump_name] = pump_extra
                            pumps.append(pump)
        self.model_description['pumps'] = pumps
        return pumps

    def add_fluid_loops(self):
        fluid_loops = []
        plant_loop_arrangements = self.gather_table_into_list('HVACTopology', 'Plant Loop Component Arrangement')
        loop_equip_summaries = self.get_table_dictionary('EquipmentSummary', 'PlantLoop or CondenserLoop')
        loop_comp_summaries = self.get_table_dictionary('ComponentSizingSummary', 'PlantLoop')
        oa_reset_control_summaries = self.gather_table_into_list('ControlSummary', 'SetpointManager:OutdoorAirReset')
        return_control_summaries = self.gather_table_into_list('ControlSummary', 'SetpointManager:ReturnTemperature')
        loop_types = {}
        if plant_loop_arrangements:
            if plant_loop_arrangements[0]['first column'] == 'None':
                return fluid_loops
        for arrangement_row in plant_loop_arrangements:
            name = arrangement_row['Loop Name']
            likely_type = ''
            if arrangement_row['Side'] == 'Supply':
                if 'CHILLER' in arrangement_row['Component Type']:
                    likely_type = 'COOLING'
                elif 'BOILER' in arrangement_row['Component Type']:
                    likely_type = 'HEATING'
                elif 'TOWER' in arrangement_row['Component Type']:
                    likely_type = 'CONDENSER'
                elif 'FLUIDCOOLER' in arrangement_row['Component Type']:
                    likely_type = 'CONDENSER'
            if likely_type:
                if name in loop_types:
                    prev_type = loop_types[name]
                    type_tuple = (likely_type, prev_type)
                    if type_tuple == ('COOLING', 'HEATING') or type_tuple == ('HEATING', 'COOLING'):
                        loop_types[name] = 'HEATING_AND_COOLING'
                    elif type_tuple == ('CONDENSER', 'HEATING') or type_tuple == ('HEATING', 'CONDENSER'):
                        loop_types[name] = 'HEATING_AND_COOLING'
                else:
                    loop_types[name] = likely_type
        for loop_name, loop_type in loop_types.items():
            fluid_loop = {
                'id': loop_name,
                'type': loop_type
            }
            # go through and get all the pumps
            pump_power = 0
            pump_flow_rate = 0
            current_pump_control = ''
            current_pump_speed = ''
            pumps_from_rmd = self.model_description['pumps']
            for arrangement_row in plant_loop_arrangements:
                if loop_name == arrangement_row['Loop Name']:
                    if 'PUMP' in arrangement_row['Component Type']:
                        pump_name = arrangement_row['Component Name']
                        for pump_from_rmd in pumps_from_rmd:
                            if pump_name == pump_from_rmd['id']:
                                pump_power = pump_power + pump_from_rmd['design_electric_power']
                                if pump_from_rmd['design_flow'] > pump_flow_rate:
                                    pump_flow_rate = pump_from_rmd['design_flow']
                                current_pump_speed = pump_from_rmd['speed_control']
                        if pump_name in self.pump_extra:
                            current_pump_control = self.pump_extra[pump_name]['control']
            if pump_flow_rate > 0:
                fluid_loop['pump_power_per_flow_rate'] = pump_power / pump_flow_rate
            design_control = {
                'id': loop_name + '-' + loop_type,
                'operation': current_pump_control.upper()
            }
            if current_pump_speed == 'VARIABLE_SPEED':
                design_control['flow_control'] = 'VARIABLE_FLOW'
            else:
                design_control['flow_control'] = 'FIXED_FLOW'
            if loop_name in loop_equip_summaries:
                temperature_string = loop_equip_summaries[loop_name]['Design Supply Temperature [C]']
                if is_float(temperature_string):
                    design_control['design_supply_temperature'] = float(temperature_string)
                temperature_string = loop_equip_summaries[loop_name]['Design Return Temperature [C]']
                if is_float(temperature_string):
                    design_control['design_return_temperature'] = float(temperature_string)
            if loop_name in loop_comp_summaries:
                if 'Sizing Option' in loop_comp_summaries[loop_name]:
                    sizing_option = loop_comp_summaries[loop_name]['Sizing Option']
                    if sizing_option == 'NonCoincident':
                        design_control['is_sized_using_coincident_load'] = False
                    elif sizing_option == 'Coincident':
                        design_control['is_sized_using_coincident_load'] = True
                if 'Maximum Loop Flow Rate [m3/s]' in loop_comp_summaries[loop_name]:
                    max_flow = float(loop_comp_summaries[loop_name]['Maximum Loop Flow Rate [m3/s]'])
                    if max_flow > 0 and 'Minimum Loop Flow Rate [m3/s]' in loop_comp_summaries[loop_name]:
                        min_flow = float(loop_comp_summaries[loop_name]['Minimum Loop Flow Rate [m3/s]'])
                        design_control['minimum_flow_fraction'] = min_flow / max_flow
            for oa_reset_control in oa_reset_control_summaries:
                if loop_name == oa_reset_control['Setpoint Node PlantLoop Name']:
                    design_control['temperature_reset_type'] = 'OUTSIDE_AIR_RESET'
                    design_control['outdoor_high_for_loop_supply_reset_temperature'] = float(
                        oa_reset_control['Outdoor High Temperature [C]'])
                    design_control['outdoor_low_for_loop_supply_reset_temperature'] = float(
                        oa_reset_control['Outdoor Low Temperature [C]'])
                    design_control['loop_supply_temperature_at_outdoor_high'] = float(
                        oa_reset_control['Setpoint at Outdoor High Temperature [C]'])
                    design_control['loop_supply_temperature_at_outdoor_low'] = float(
                        oa_reset_control['Setpoint at Outdoor Low Temperature [C]'])
            for return_control in return_control_summaries:
                if loop_name == return_control['PlantLoop Name']:
                    if 'COOLING' in loop_type or 'CONDENSER' == loop_type:
                        design_control['temperature_reset_type'] = 'LOAD_RESET'
                        design_control['loop_supply_temperature_at_low_load'] = float(
                            oa_reset_control['Maximum Supply Temperature Setpoint [C]'])
                    elif 'HEATING' in loop_type:
                        design_control['temperature_reset_type'] = 'LOAD_RESET'
                        design_control['loop_supply_temperature_at_low_load'] = float(
                            oa_reset_control['Minimum Supply Temperature Setpoint [C]'])
            if 'COOLING' in loop_type or 'CONDENSER' == loop_type:
                fluid_loop['cooling_or_condensing_design_and_control'] = design_control
                design_control['has_integrated_waterside_economizer'] = do_share_branch('chiller',
                                                                                        'heatexchanger',
                                                                                        plant_loop_arrangements)
            if 'HEATING' in loop_type:
                fluid_loop['heating_design_and_control'] = design_control

            fluid_loops.append(fluid_loop)
        self.model_description['fluid_loops'] = fluid_loops
        return fluid_loops

    def gather_service_water_heater_loops(self) -> Dict[str, str]:
        loop_by_heater: Dict[str, str] = {}
        plant_loop_arrangements: List[JsonDict] = self.gather_table_into_list(
            'HVACTopology',
            'Plant Loop Component Arrangement'
        )
        for arrangement_row in plant_loop_arrangements:
            component_type: str = non_empty_string(arrangement_row.get('Component Type'))
            if 'WATERHEATER' in component_type.upper():
                component_name: str = non_empty_string(arrangement_row.get('Component Name'))
                loop_name: str = non_empty_string(arrangement_row.get('Loop Name'))
                if component_name and loop_name:
                    loop_by_heater[component_name] = loop_name
        return loop_by_heater

    def gather_mains_schedule(self) -> Tuple[str, Optional[bool]]:
        mains_schedule: str = ''
        is_ground_based: Optional[bool] = None
        mains_info_table: Dict[str, JsonDict] = self.get_table_dictionary(
            'InitializationSummary',
            'Site Water Mains Temperature Information'
        )
        for row in mains_info_table.values():
            schedule_name: str = non_empty_string(row.get('Water Mains Temperature Schedule Name{}'))
            if schedule_name:
                mains_schedule = schedule_name
                self.schedules_used_names.append(schedule_name)
            method: str = non_empty_string(row.get('Calculation Method{}')).upper()
            if method:
                is_ground_based = method == 'CORRELATION'
            break
        return mains_schedule, is_ground_based

    def gather_service_water_heater_metadata(self) -> Dict[str, JsonDict]:
        metadata_by_name: Dict[str, JsonDict] = {}
        tank_metadata_by_name: Dict[str, JsonDict] = {}
        tank_object_sections = ('WaterHeater:Mixed', 'WaterHeater:Stratified')

        for object_type in tank_object_sections:
            for heater_name, heater_object in self.epjson_object.get(object_type, {}).items():
                heater_key = heater_name.upper()
                heater_metadata: JsonDict = {
                    'object_type': object_type,
                    'peak_use_flow_rate': heater_object.get('peak_use_flow_rate'),
                    'use_flow_rate_fraction_schedule_name': heater_object.get('use_flow_rate_fraction_schedule_name'),
                    'ambient_temperature_zone_name': heater_object.get('ambient_temperature_zone_name'),
                    'end_use_subcategory': heater_object.get('end_use_subcategory')
                }
                if object_type == 'WaterHeater:Mixed':
                    heater_metadata['setpoint_temperature_schedule_name'] = heater_object.get(
                        'setpoint_temperature_schedule_name'
                    )
                else:
                    heater_metadata['setpoint_temperature_schedule_name'] = (
                        heater_object.get('heater_1_setpoint_temperature_schedule_name')
                        or heater_object.get('heater_2_setpoint_temperature_schedule_name')
                    )
                metadata_by_name[heater_key] = heater_metadata
                tank_metadata_by_name[heater_key] = heater_metadata

        heat_pump_object_sections = (
            'WaterHeater:HeatPump:PumpedCondenser',
            'WaterHeater:HeatPump:WrappedCondenser'
        )
        for object_type in heat_pump_object_sections:
            for heater_name, heater_object in self.epjson_object.get(object_type, {}).items():
                heater_key = heater_name.upper()
                tank_name: str = non_empty_string(heater_object.get('tank_name'))
                tank_key = tank_name.upper()
                heater_metadata: JsonDict = {
                    'object_type': object_type,
                    'tank_name': tank_name,
                    'setpoint_temperature_schedule_name': heater_object.get(
                        'compressor_setpoint_temperature_schedule_name'
                    )
                }
                tank_metadata = tank_metadata_by_name.get(tank_key, {})
                for key in (
                        'peak_use_flow_rate',
                        'use_flow_rate_fraction_schedule_name',
                        'ambient_temperature_zone_name',
                        'end_use_subcategory'
                ):
                    if key in tank_metadata:
                        heater_metadata[key] = tank_metadata[key]
                metadata_by_name[heater_key] = heater_metadata
                if tank_key and tank_key in metadata_by_name:
                    metadata_by_name[tank_key]['heat_pump_water_heater_name'] = heater_name

        return metadata_by_name

    def gather_branch_names_from_branch_list(self, branch_list_name: str) -> List[str]:
        if not branch_list_name:
            return []
        branch_list = self.epjson_object.get('BranchList', {}).get(branch_list_name, {})
        branches = branch_list.get('branches', [])
        branch_names: List[str] = []
        for branch in branches:
            branch_name = non_empty_string(branch.get('branch_name'))
            if branch_name:
                branch_names.append(branch_name)
        return branch_names

    def gather_service_water_loop_pipe_children(self, loop_name: str) -> List[JsonDict]:
        loop_object = self.epjson_object.get('PlantLoop', {}).get(loop_name, {})
        if not loop_object:
            return []
        branch_names: List[str] = []
        branch_names.extend(
            self.gather_branch_names_from_branch_list(non_empty_string(loop_object.get('plant_side_branch_list_name')))
        )
        branch_names.extend(
            self.gather_branch_names_from_branch_list(non_empty_string(loop_object.get('demand_side_branch_list_name')))
        )
        pipe_children: List[JsonDict] = []
        pipe_object_types = ('Pipe:Adiabatic', 'Pipe:Indoor', 'Pipe:Outdoor', 'Pipe:Underground')
        for branch_name in branch_names:
            branch_object = self.epjson_object.get('Branch', {}).get(branch_name, {})
            for component in branch_object.get('components', []):
                component_type = non_empty_string(component.get('component_object_type'))
                component_name = non_empty_string(component.get('component_name'))
                if component_type not in pipe_object_types or not component_name:
                    continue
                pipe_object = self.epjson_object.get(component_type, {}).get(component_name, {})
                pipe_child: JsonDict = {
                    'id': component_name,
                    'are_thermal_losses_modeled': component_type != 'Pipe:Adiabatic'
                }
                if component_type == 'Pipe:Indoor':
                    pipe_child['loop_pipe_location'] = 'CONDITIONED'
                    location_zone = non_empty_string(pipe_object.get('ambient_temperature_zone_name'))
                    if location_zone:
                        pipe_child['location_zone'] = location_zone
                elif component_type == 'Pipe:Outdoor':
                    pipe_child['loop_pipe_location'] = 'OUTSIDE'
                elif component_type == 'Pipe:Underground':
                    pipe_child['loop_pipe_location'] = 'UNDERGROUND'
                if 'pipe_length' in pipe_object:
                    length = to_float_or_none(pipe_object.get('pipe_length'))
                    if length is not None:
                        pipe_child['length'] = length
                if 'pipe_inside_diameter' in pipe_object:
                    diameter = to_float_or_none(pipe_object.get('pipe_inside_diameter'))
                    if diameter is not None:
                        pipe_child['diameter'] = diameter
                pipe_children.append(pipe_child)
        return pipe_children

    def is_service_water_recirculation_loop(self, loop_name: str) -> bool:
        loop_object = self.epjson_object.get('PlantLoop', {}).get(loop_name, {})
        if not loop_object:
            return False

        demand_branch_names = self.gather_branch_names_from_branch_list(
            non_empty_string(loop_object.get('demand_side_branch_list_name'))
        )
        if not demand_branch_names:
            return False

        has_water_use_connections = False
        has_demand_side_pump = False
        has_demand_side_pipe = False
        has_inlet_branch = False
        has_outlet_branch = False

        demand_inlet_node = non_empty_string(loop_object.get('demand_side_inlet_node_name'))
        demand_outlet_node = non_empty_string(loop_object.get('demand_side_outlet_node_name'))

        for branch_name in demand_branch_names:
            branch_object = self.epjson_object.get('Branch', {}).get(branch_name, {})
            for component in branch_object.get('components', []):
                component_type = non_empty_string(component.get('component_object_type'))
                if not component_type:
                    continue
                component_type_upper = component_type.upper()
                if component_type == 'WaterUse:Connections':
                    has_water_use_connections = True
                elif 'PUMP' in component_type_upper:
                    has_demand_side_pump = True
                elif component_type.startswith('Pipe:'):
                    has_demand_side_pipe = True

                component_inlet_node = non_empty_string(component.get('component_inlet_node_name'))
                component_outlet_node = non_empty_string(component.get('component_outlet_node_name'))
                if demand_inlet_node and component_inlet_node == demand_inlet_node:
                    has_inlet_branch = True
                if demand_outlet_node and component_outlet_node == demand_outlet_node:
                    has_outlet_branch = True

        if not has_water_use_connections:
            return False

        has_closed_loop_path = bool(demand_inlet_node and demand_outlet_node and has_inlet_branch and has_outlet_branch)
        if not has_closed_loop_path:
            return False

        if has_demand_side_pump:
            return True

        connector_list_name = non_empty_string(loop_object.get('demand_side_connector_list_name'))
        if not connector_list_name:
            return False

        connector_list = self.epjson_object.get('ConnectorList', {}).get(connector_list_name, {})
        splitter_name = ''
        mixer_name = ''
        for index in range(1, 11):
            connector_type = non_empty_string(connector_list.get(f'connector_{index}_object_type'))
            connector_name = non_empty_string(connector_list.get(f'connector_{index}_name'))
            if connector_type == 'Connector:Splitter' and connector_name:
                splitter_name = connector_name
            elif connector_type == 'Connector:Mixer' and connector_name:
                mixer_name = connector_name

        if not splitter_name or not mixer_name:
            return False

        splitter_object = self.epjson_object.get('Connector:Splitter', {}).get(splitter_name, {})
        mixer_object = self.epjson_object.get('Connector:Mixer', {}).get(mixer_name, {})
        if not splitter_object or not mixer_object:
            return False

        splitter_inlet_branch = non_empty_string(splitter_object.get('inlet_branch_name'))
        mixer_outlet_branch = non_empty_string(mixer_object.get('outlet_branch_name'))
        if not splitter_inlet_branch or not mixer_outlet_branch:
            return False

        return has_demand_side_pipe

    def make_service_water_piping(self, loop_name: str, system_id: str) -> Optional[JsonDict]:
        if not loop_name:
            return None
        pipe_children = self.gather_service_water_loop_pipe_children(loop_name)
        piping: JsonDict = {
            'id': system_id + ' piping',
            'are_thermal_losses_modeled': any(
                child.get('are_thermal_losses_modeled', False) for child in pipe_children
            )
        }
        if self.is_service_water_recirculation_loop(loop_name):
            piping['is_recirculation_loop'] = True
        if pipe_children:
            piping['child'] = pipe_children
        return piping

    def assign_service_water_heating_uses_to_spaces(self, use_zone_by_id: Dict[str, str]) -> None:
        assigned_use_ids = set()
        use_object_by_id = {
            item['id']: item for item in self.model_description.get('service_water_heating_uses', [])
        }
        zones = self.building_segment.get('zones', [])
        for zone in zones:
            zone_id = non_empty_string(zone.get('id')).upper()
            if not zone_id:
                continue
            zone_use_ids = [use_id for use_id, use_zone in use_zone_by_id.items() if use_zone == zone_id]
            if not zone_use_ids:
                continue
            spaces = zone.get('spaces', [])
            if not spaces:
                continue
            if len(spaces) > 1:
                total_occupants = sum(to_float_or_none(space.get('number_of_occupants')) or 0.0 for space in spaces)
                total_floor_area = sum(to_float_or_none(space.get('floor_area')) or 0.0 for space in spaces)
                for use_id in zone_use_ids:
                    use_object = use_object_by_id.get(use_id)
                    if not use_object:
                        continue
                    use_units = use_object.get('use_units')
                    use_value = to_float_or_none(use_object.get('use'))
                    if use_value is None or use_units not in {'POWER', 'VOLUME'}:
                        continue
                    if total_occupants > 0:
                        use_object['use'] = use_value / total_occupants
                        use_object['use_units'] = f'{use_units}_PER_PERSON'
                    elif total_floor_area > 0:
                        use_object['use'] = use_value / total_floor_area
                        use_object['use_units'] = f'{use_units}_PER_AREA'
            for space in spaces:
                space['service_water_heating_uses'] = zone_use_ids
            assigned_use_ids.update(zone_use_ids)

        if 'service_water_heating_uses' not in self.model_description:
            return
        remaining_use_ids = [
            item['id']
            for item in self.model_description['service_water_heating_uses']
            if item['id'] not in assigned_use_ids
        ]
        if remaining_use_ids:
            self.building_segment['service_water_heating_uses'] = remaining_use_ids
        elif 'service_water_heating_uses' in self.building_segment:
            del self.building_segment['service_water_heating_uses']

    def add_service_water_heating_distribution_systems(
            self
    ) -> Tuple[List[JsonDict], Dict[str, str], Dict[str, str], Dict[str, str]]:
        systems: List[JsonDict] = []
        system_id_by_connection: Dict[str, str] = {}
        system_id_by_loop: Dict[str, str] = {}
        system_id_by_heater: Dict[str, str] = {}
        mains_schedule, is_ground_based = self.gather_mains_schedule()
        connection_table: Dict[str, JsonDict] = self.get_table_dictionary('EquipmentSummary', 'WaterUse Connections')
        for connection_name, row in connection_table.items():
            connection_name = non_empty_string(connection_name)
            if not connection_name or connection_name.upper() == 'NONE':
                continue
            system: JsonDict = {'id': connection_name}
            loop_name: str = non_empty_string(row.get('PlantLoop Name'))
            if loop_name:
                system_id_by_loop[loop_name] = connection_name
                system['is_central_system'] = True
                piping = self.make_service_water_piping(loop_name, connection_name)
                if piping:
                    system['service_water_piping'] = piping
            design_supply_temperature: Optional[float] = to_float_or_none(
                row.get('Hot Water Supply Temperature Schedule Maximum [C]')
            )
            if design_supply_temperature is not None:
                system['design_supply_temperature'] = design_supply_temperature
            if mains_schedule:
                system['entering_water_mains_temperature_schedule'] = mains_schedule
            if is_ground_based is not None:
                system['is_ground_temperature_used_for_entering_water'] = is_ground_based
            systems.append(system)
            system_id_by_connection[connection_name] = connection_name

        loop_by_heater: Dict[str, str] = self.gather_service_water_heater_loops()
        for _, loop_name in loop_by_heater.items():
            if loop_name and loop_name not in system_id_by_loop:
                system = {'id': loop_name}
                piping = self.make_service_water_piping(loop_name, loop_name)
                if piping:
                    system['service_water_piping'] = piping
                if mains_schedule:
                    system['entering_water_mains_temperature_schedule'] = mains_schedule
                if is_ground_based is not None:
                    system['is_ground_temperature_used_for_entering_water'] = is_ground_based
                systems.append(system)
                system_id_by_loop[loop_name] = loop_name

        service_water_table: Dict[str, JsonDict] = self.get_table_dictionary(
            'EquipmentSummary',
            'Service Water Heating'
        )
        for heater_name in service_water_table.keys():
            heater_name = non_empty_string(heater_name)
            if not heater_name or heater_name.upper() == 'NONE':
                continue
            loop_name = loop_by_heater.get(heater_name, '')
            if loop_name and loop_name in system_id_by_loop:
                system_id_by_heater[heater_name] = system_id_by_loop[loop_name]

        if not system_id_by_connection and not system_id_by_loop:
            for heater_name, row in service_water_table.items():
                heater_name = non_empty_string(heater_name)
                if not heater_name or heater_name.upper() == 'NONE':
                    continue
                system_id = heater_name + ' distribution system'
                system: JsonDict = {'id': system_id, 'is_central_system': False}
                design_supply_temperature = to_float_or_none(
                    row.get('Set Point at 11am First Wednesday for Heater 1 [C]')
                )
                if design_supply_temperature is not None:
                    system['design_supply_temperature'] = design_supply_temperature
                if mains_schedule:
                    system['entering_water_mains_temperature_schedule'] = mains_schedule
                if is_ground_based is not None:
                    system['is_ground_temperature_used_for_entering_water'] = is_ground_based
                systems.append(system)
                system_id_by_heater[heater_name] = system_id

        if systems:
            self.model_description['service_water_heating_distribution_systems'] = systems
        return systems, system_id_by_connection, system_id_by_loop, system_id_by_heater

    def add_service_water_heating_equipment(
            self,
            system_id_by_loop: Dict[str, str],
            system_id_by_heater: Dict[str, str],
            default_system_id: str
    ) -> List[JsonDict]:
        equipment_list: List[JsonDict] = []
        service_water_table: Dict[str, JsonDict] = self.get_table_dictionary(
            'EquipmentSummary',
            'Service Water Heating'
        )
        loop_by_heater: Dict[str, str] = self.gather_service_water_heater_loops()
        for heater_name, row in service_water_table.items():
            heater_name = non_empty_string(heater_name)
            if not heater_name or heater_name.upper() == 'NONE':
                continue
            loop_name: str = loop_by_heater.get(heater_name, '')
            distribution_system: str = ''
            if loop_name in system_id_by_loop:
                distribution_system = system_id_by_loop[loop_name]
            elif heater_name in system_id_by_heater:
                distribution_system = system_id_by_heater[heater_name]
            elif default_system_id:
                distribution_system = default_system_id
            if not distribution_system:
                continue
            equipment: JsonDict = {
                'id': heater_name,
                'distribution_system': distribution_system
            }
            fuel_type: str = non_empty_string(row.get('Fuel Type'))
            if fuel_type:
                try:
                    equipment['heater_fuel_type'] = energy_source_convert(fuel_type)
                except KeyError:
                    if fuel_type.upper() in {'ELECTRICITY', 'NATURAL_GAS', 'PROPANE', 'FUEL_OIL', 'STEAM'}:
                        equipment['heater_fuel_type'] = fuel_type.upper()
                    else:
                        equipment['heater_fuel_type'] = 'OTHER'

            metric_types: List[str] = []
            metric_values: List[float] = []
            thermal_efficiency: Optional[float] = to_float_or_none(row.get('Thermal Efficiency [W/W]'))
            if thermal_efficiency is not None:
                metric_types.append('THERMAL_EFFICIENCY')
                metric_values.append(thermal_efficiency)
            energy_factor: Optional[float] = to_float_or_none(row.get('Energy Factor'))
            if energy_factor is not None:
                metric_types.append('ENERGY_FACTOR')
                metric_values.append(energy_factor)
            if metric_types:
                equipment['efficiency_metric_types'] = metric_types
                equipment['efficiency_metric_values'] = metric_values

            input_power: Optional[float] = to_float_or_none(row.get('Input [W]'))
            if input_power is not None:
                equipment['input_power'] = input_power
            recovery_efficiency: Optional[float] = to_float_or_none(row.get('Recovery Efficiency [W/W]'))
            if recovery_efficiency is not None:
                equipment['recovery_efficiency'] = recovery_efficiency
            setpoint_temperature: Optional[float] = to_float_or_none(
                row.get('Set Point at 11am First Wednesday for Heater 1 [C]')
            )
            if setpoint_temperature is not None:
                equipment['setpoint_temperature'] = setpoint_temperature

            storage_volume: Optional[float] = to_float_or_none(row.get('Storage Volume [m3]'))
            if storage_volume is not None and storage_volume > 0:
                tank_type: str = 'COMMERCIAL_STORAGE'
                heater_type: str = non_empty_string(row.get('Type')).upper()
                if 'INSTANTANEOUS' in heater_type:
                    tank_type = 'COMMERCIAL_INSTANTANEOUS'
                equipment['tank'] = {
                    'id': heater_name + '-tank',
                    'storage_capacity': storage_volume * 1000,
                    'type': tank_type
                }

            if loop_name:
                equipment['hot_water_loop'] = loop_name
            equipment_list.append(equipment)
        if equipment_list:
            self.model_description['service_water_heating_equipment'] = equipment_list
        return equipment_list

    def add_service_water_heating_uses(
            self,
            system_id_by_connection: Dict[str, str],
            system_id_by_heater: Dict[str, str],
            default_system_id: str
    ) -> List[JsonDict]:
        uses: List[JsonDict] = []
        use_zone_by_id: Dict[str, str] = {}
        water_use_table: Dict[str, JsonDict] = self.get_table_dictionary('EquipmentSummary', 'Water Use')
        service_water_table: Dict[str, JsonDict] = self.get_table_dictionary(
            'EquipmentSummary',
            'Service Water Heating'
        )
        heater_metadata_by_name = self.gather_service_water_heater_metadata()
        serves_type_map: Dict[str, str] = {
            'SHOWER': 'SHOWER',
            'BATH': 'BATH',
            'RESTROOM': 'RESTROOM_SINK',
            'DISHWASHER': 'DISHWASHER',
            'KITCHEN': 'KITCHEN_SINK',
            'WASH': 'WASH_SINK',
            'CLOTHES': 'CLOTHES_WASHER'
        }
        for use_name, row in water_use_table.items():
            use_name = non_empty_string(use_name)
            if not use_name or use_name.upper() == 'NONE':
                continue
            connection_name: str = non_empty_string(row.get('WaterUse Connection Name'))
            served_by: str = system_id_by_connection.get(connection_name, default_system_id)
            if not served_by:
                continue
            use: JsonDict = {
                'id': use_name,
                'served_by_distribution_system': served_by
            }
            zone_name = non_empty_string(row.get('Zone')).upper()
            if zone_name:
                use_zone_by_id[use_name] = zone_name
            peak_flow: Optional[float] = to_float_or_none(row.get('Peak Water Flow Rate [m3/s]'))
            if peak_flow is not None:
                use['use'] = peak_flow * 60000
                use['use_units'] = 'VOLUME'
            flow_schedule: str = non_empty_string(row.get('Peak Flow Multipler Schedule'))
            if flow_schedule:
                use['use_multiplier_schedule'] = flow_schedule
                self.schedules_used_names.append(flow_schedule)
            target_temperature: Optional[float] = to_float_or_none(row.get('Target Temperature  Schedule Maximum [C]'))
            if target_temperature is not None:
                use['temperature_at_fixture'] = target_temperature
            end_use_subcategory: str = non_empty_string(row.get('End-Use Subcategory')).upper()
            for key, value in serves_type_map.items():
                if key in end_use_subcategory:
                    use['water_serves_type'] = value
                    break
            uses.append(use)

        if uses:
            self.model_description['service_water_heating_uses'] = uses
            self.building_segment['service_water_heating_uses'] = [item['id'] for item in uses]
            self.assign_service_water_heating_uses_to_spaces(use_zone_by_id)
            return uses

        for heater_name, row in service_water_table.items():
            heater_name = non_empty_string(heater_name)
            if not heater_name or heater_name.upper() == 'NONE':
                continue
            served_by: str = system_id_by_heater.get(heater_name, default_system_id)
            if not served_by:
                continue
            heater_key = heater_name.upper()
            use: JsonDict = {
                'id': heater_name + ' use',
                'served_by_distribution_system': served_by
            }
            zone_name = non_empty_string(
                heater_metadata_by_name.get(heater_key, {}).get('ambient_temperature_zone_name')
            ).upper()
            if zone_name:
                use_zone_by_id[use['id']] = zone_name
            peak_flow = to_float_or_none(row.get('Peak Use Water Flow Rate [m3/s]'))
            if peak_flow is None:
                peak_flow = to_float_or_none(
                    heater_metadata_by_name.get(heater_key, {}).get('peak_use_flow_rate')
                )
            if peak_flow is not None:
                use['use'] = peak_flow * 60000
                use['use_units'] = 'VOLUME'

            flow_schedule = non_empty_string(row.get('Use Flow Rate Fraction Schedule Name'))
            if not flow_schedule:
                flow_schedule = non_empty_string(
                    heater_metadata_by_name.get(heater_key, {}).get('use_flow_rate_fraction_schedule_name')
                )
            if flow_schedule:
                use['use_multiplier_schedule'] = flow_schedule
                self.schedules_used_names.append(flow_schedule)

            temperature_at_fixture = to_float_or_none(
                row.get('Set Point at 11am First Wednesday for Heater 1 [C]')
            )
            if temperature_at_fixture is not None:
                use['temperature_at_fixture'] = temperature_at_fixture

            end_use_subcategory = non_empty_string(
                heater_metadata_by_name.get(heater_key, {}).get('end_use_subcategory')
            ).upper()
            for key, value in serves_type_map.items():
                if key in end_use_subcategory:
                    use['water_serves_type'] = value
                    break
            uses.append(use)

        if uses:
            self.model_description['service_water_heating_uses'] = uses
            self.building_segment['service_water_heating_uses'] = [item['id'] for item in uses]
            self.assign_service_water_heating_uses_to_spaces(use_zone_by_id)
        return uses

    def add_service_water_heating(self) -> Tuple[List[JsonDict], List[JsonDict], List[JsonDict]]:
        systems, system_id_by_connection, system_id_by_loop, system_id_by_heater = (
            self.add_service_water_heating_distribution_systems()
        )
        default_system_id = systems[0]['id'] if systems else ''
        equipment = self.add_service_water_heating_equipment(
            system_id_by_loop,
            system_id_by_heater,
            default_system_id
        )
        uses = self.add_service_water_heating_uses(
            system_id_by_connection,
            system_id_by_heater,
            default_system_id
        )
        return systems, equipment, uses

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
                'unmet_load_hours': float(ea_rows['Number of hours not met'][ea_data_column]),
                'unmet_load_hours_heating': float(ea_rows['Number of hours heating loads not met'][ea_data_column]),
                'unmet_occupied_load_hours_heating': float(time_rows['Facility'][time_heat_occupied_column]),
                'unmet_load_hours_cooling': float(ea_rows['Number of hours cooling loads not met'][ea_data_column]),
                'unmet_occupied_load_hours_cooling': float(time_rows['Facility'][time_cool_occupied_column]),
                'annual_source_results': source_results,
                'building_peak_cooling_load': -1,
                'annual_end_use_results': end_use_results
            }

        project_output = {
            'id': 'output_1',
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
        self.model_description['model_output'] = output_instance
        self.project_description['output'] = project_output
        return project_output, output_instance

    def get_epjson_by_uc_name(self, epjson_object_name, specific_name_uc):
        specific_epjson_input_object = {}
        if epjson_object_name in self.epjson_object:
            if specific_name_uc in self.epjson_object[epjson_object_name]:
                specific_epjson_input_object = self.epjson_object[specific_name_uc]
            else:
                for key, val in self.epjson_object[epjson_object_name].items():
                    if key.upper() == specific_name_uc:
                        specific_epjson_input_object = val
                        break
        return specific_epjson_input_object

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
        self.add_external_fluid_source()
        self.add_weather()
        self.add_calendar()
        self.add_materials()
        self.add_constructions()
        self.surfaces_by_zone = self.get_zone_for_each_surface()
        self.gather_coil_connections()
        self.add_airloop_heating_ventilation_ac_system()
        self.add_terminal_hvac_system()
        self.add_chillers()
        self.add_boilers()
        self.add_heat_rejection()
        self.add_pumps()
        self.add_fluid_loops()
        self.add_zones()
        self.add_spaces()
        self.add_service_water_heating()
        self.add_exterior_lighting()
        self.add_simulation_outputs()
        self.add_schedules()
        self.add_ground_schedule()
        self.ensure_all_id_unique()

        if self.do_use_compliance_parameters:
            self.compliance_parameter.merge_in_compliance_parameters(self.project_description)
        elif self.do_create_empty_compliance_parameters:
            self.compliance_parameter.create_empty_compliance_json(self.project_description)
        passed, message = self.validator.validate_rpd(self.project_description)
        if not passed:
            print(message)
        self.output_file.write(self.project_description)
        self.status_reporter.generate()
