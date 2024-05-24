import copy
import jsonpatch
from json import dumps
from pathlib import Path
from typing import Dict


class ComplianceParameterHandler:
    def __init__(self, epjson_file_path: Path):
        self.cp_file_path = epjson_file_path.with_suffix('.cp.patch')
        self.compliance_group_element = {
            # data group: {data element: default value, ...}
            'root': # RulesetProjectDescription
                {'compliance_path': 'CODE_COMPLIANT', },
            'ruleset_model_descriptions':
                {'type': 'PROPOSED',
                 'measured_infiltration_pressure_difference': 0,
                 'is_measured_infiltration_based_on_test': False,
                 'site_zone_type': 'ZONE_4_HIGH_ACTIVITY_COMMERCIAL'},
            'building':
                {'building_open_schedule': ''},
            'building_segments':
                {'is_all_new': True,
                 'area_type_vertical_fenestration': 'OFFICE_MEDIUM',
                 'lighting_building_area_type': 'OFFICE',
                 'area_type_heating_ventilating_air_conditioning_system': 'OTHER_NON_RESIDENTIAL'},
            'zones':
                {'conditioning_type': 'HEATED_AND_COOLED',
                 'aggregation_factor': 1},
            'spaces':
                {'status_type': 'NEW',
                 'function': 'OTHER',
                 'lighting_space_type': '',
                 'ventilation_space_type': '',
                 'service_water_heating_space_type': ''},
            'infiltration':
                {'measured_air_leakage_rate': 0},
            'surfaces':
                {'status_type': 'NEW'},
            'construction':
                {'classification': 'STEEL_FRAMED'},
            'subsurfaces':
                {'subclassification': 'OTHER',
                 'is_operable': False,
                 'has_open_sensor': False,
                 'framing_type': 'ALUMINUM_WITH_BREAK',
                 'has_manual_interior_shades': False,
                 'status_type': 'NEW'},
            'interior_lighting':
                {'purpose_type': 'GENERAL',
                 'occupancy_control_type': 'NONE'},
            'miscellaneous_equipment':
                {'type': 'PLUG',
                 'has_automatic_control': False},
            'transformers':
                {'type': 'DRY_TYPE'},
            'schedules':
                {'prescribed_type': 'NOT_APPLICABLE',
                 'is_modified_for_workaround': False},
            'weather':
                {'data_source_type': 'HISTORIC_AGGREGATION'},
            'heating_ventilating_air_conditioning_systems':
                {'status_type': 'NEW'},
            'fan_systems':
                {'air_filter_merv_rating': 8,
                 'has_fully_ducted_return': False},
            'air_energy_recovery':
                {'enthalpy_recovery_ratio':0.3},
            'fans':
                {'motor_nameplate_power': 0.0,
                 'shaft_power': 0.0,
                 'status_type': 'NEW'},
            'terminals':
                {'is_supply_ducted': False},
            'pumps':
                {'motor_nameplate_power': 0.0,
                 'impeller_efficiency': 0.0},
            'boilers':
                {'draft_type': 'NATURAL'},
            'chillers':
                {'compressor_type': 'POSITIVE_DISPLACEMENT'},
            'heat_rejections':
                {'fan_type': 'AXIAL',
                 'fan_shaft_power': 0.0,
                 'fan_motor_efficiency': 0.5,
                 'rated_water_flowrate': 0.0},
            'exterior_lightings':
                {'type': 'MISCELLANEOUS_NON_TRADABLE',
                 'area': 0.0,
                 'length': 0.0,
                 'fixture_height': 0.0,
                 'is_exempt': False}
        }


    def create_empty_patch(self, json_dict: Dict):
        with_new = copy.deepcopy(json_dict)
        # calendar = with_new['calendar']
        # calendar['fictional1'] = '-'
        # calendar['fictional2'] = '-'
        with_new['compliance_path'] = 'CODE_COMPLIANT'
        model_descriptions = with_new['ruleset_model_descriptions']
        for model_description in model_descriptions:
            model_description['type'] = 'PROPOSED'
            model_description['measured_infiltration_pressure_difference'] = 0
            model_description['is_measured_infiltration_based_on_test'] = False
            model_description['site_zone_type'] = 'ZONE_4_HIGH_ACTIVITY_COMMERCIAL'
            buildings = model_description['buildings']
            for building in buildings:
                building_segments = building['building_segments']
                for building_segment in building_segments:
                    building_segment['is_all_new'] = True
                    building_segment['area_type_vertical_fenestration'] = 'OFFICE_MEDIUM'
                    building_segment['lighting_building_area_type'] = 'OFFICE'
                    building_segment['area_type_heating_ventilating_air_conditioning_system'] = 'OTHER_NON_RESIDENTIAL'
                    zones = building_segment['zones']
                    for zone in zones:
                        zone['conditioning_type'] = 'HEATED_AND_COOLED'
                        zone['aggregation_factor'] = 1
                        spaces = zone['spaces']
                        for space in spaces:
                            space['status_type'] = 'NEW'
                            space['function'] = 'OTHER'
                        if 'infiltration' in zone:
                            infiltration = zone['infiltration']
                            infiltration['measured_air_leakage_rate'] = 0

        patch = jsonpatch.JsonPatch.from_diff(json_dict, with_new)
        print('[')
        for item in patch:
            print('  ', item)
        print(']')

    def create_empty_cp(self, json_dict: Dict):
        compliance = {}
        compliance['id'] = json_dict['id']
        compliance['notes'] = 'contains only the compliance parameters'
        compliance['compliance_path'] = 'CODE_COMPLIANT'
        model_descriptions = json_dict['ruleset_model_descriptions']
        compliance_model_descriptions = []
        for model_description in model_descriptions:
            compliance_model_description = {}
            compliance_model_description['id'] = model_description['id']
            compliance_model_description['notes'] = model_description['notes']
            compliance_model_description['type'] = 'PROPOSED'
            compliance_model_description['measured_infiltration_pressure_difference'] = 0
            compliance_model_description['is_measured_infiltration_based_on_test'] = False
            compliance_model_description['site_zone_type'] = 'ZONE_4_HIGH_ACTIVITY_COMMERCIAL'
            buildings = model_description['buildings']
            compliance_buildings = []
            for building in buildings:
                compliance_building = {}
                compliance_building['id'] = building['id']
                compliance_building['notes'] = building['notes']
                building_segments = building['building_segments']
                compliance_building_segments = []
                for building_segment in building_segments:
                    compliance_building_segment = {}
                    compliance_building_segment['id'] = building_segment['id']
                    # compliance_building_segment['notes'] = building_segment['notes']
                    compliance_building_segment['is_all_new'] = True
                    compliance_building_segment['area_type_vertical_fenestration'] = 'OFFICE_MEDIUM'
                    compliance_building_segment['lighting_building_area_type'] = 'OFFICE'
                    compliance_building_segment['area_type_heating_ventilating_air_conditioning_system'] = 'OTHER_NON_RESIDENTIAL'
                    zones = building_segment['zones']
                    compliance_zones = []
                    for zone in zones:
                        compliance_zone = {}
                        compliance_zone['id'] = zone['id']
                        compliance_zone['conditioning_type'] = 'HEATED_AND_COOLED'
                        compliance_zone['aggregation_factor'] = 1
                        spaces = zone['spaces']
                        compliance_spaces = []
                        for space in spaces:
                            compliance_space = {}
                            compliance_space['id'] = space['id']
                            compliance_space['status_type'] = 'NEW'
                            compliance_space['function'] = 'OTHER'
                            compliance_spaces.append(compliance_space)
                        # if 'infiltration' in zone:
                        #    infiltration = zone['infiltration']
                        #    infiltration['measured_air_leakage_rate'] = 0
                        compliance_zone['spaces'] =  compliance_spaces
                        compliance_zones.append(compliance_zone)
                    compliance_building_segment['zones'] = compliance_zones
                    compliance_building_segments.append(compliance_building_segment)
                compliance_building['building_segments'] = compliance_building_segments
                compliance_buildings.append(compliance_building)
            compliance_model_description['buildings'] = compliance_buildings
            compliance_model_descriptions.append(compliance_model_description)
        compliance['ruleset_model_descriptions'] = compliance_model_descriptions

        # note: this could be redone with using a file that contains just one instance of everything and merging it using a more generic approach rather than so specific that this is doing.

        print(dumps(compliance, indent=2))


    def create_empty_cp2(self, json_dict: Dict):
        # self.find_data_groups_nested_org(json_dict)
        for group in self.find_data_groups_nested(json_dict):
            parent, out_dict = group
            if isinstance(out_dict, dict):
                if 'id' in out_dict:
                    print(f'parent: {parent}  dictionary id: {out_dict["id"]}')
                    # print('x')
                else:
                    # the only data groups weather and calendar with no id's
                    print(f'parent: {parent}  dictionary size: {len(out_dict)}')
                if parent in self.compliance_group_element:
                    print('  parent found')
            else:
                print(f'parent: {parent} but no dictionary')

    def find_data_groups_nested_orig(self, in_dict):
        for k, v in in_dict.items():
            if isinstance(v, dict):
                print(f'data group: {k}')
                self.find_data_groups_nested(v)
            if isinstance(v, list):
                print(f'data group: {k}')
                for o in v:
                    if isinstance(o,dict):
                        self.find_data_groups_nested(o)

    def find_data_groups_nested(self, in_dict):
        for k, v in in_dict.items():
            if isinstance(v, dict):
                yield k, v
                yield from self.find_data_groups_nested(v)
            if isinstance(v, list):
                for o in v:
                    if isinstance(o, dict):
                        yield k, o
                        yield from self.find_data_groups_nested(o)

## maybe make a deepcopy and delete the elements of each dictionary that are not id or notes and then add the new items.
## or else reconstruct a JSON dictionary in the image as it is being created and just copy the id and notes and the new items

    def create_compliance_json(self, json_dict: Dict):
        #cp_dict = copy.deepcopy(json_dict)
        #self.delete_and_add_compliance(cp_dict)
        # print(dumps(cp_dict, indent=2))
        created_dict = {}
        self.mirror_nested(json_dict, created_dict)
        print(dumps(created_dict, indent=2))
        out_path = Path("test.json")
        out_path.write_text(dumps(created_dict, indent=2))

    def delete_and_add_compliance(self, in_dict: Dict):
        for k, v in in_dict.items():
            if isinstance(v, dict):
                if 'id' in in_dict:
                    print(f'data group:  {k} - {in_dict["id"]}')
                self.delete_and_add_compliance(v)
            if isinstance(v, list):
                for o in v:
                    if isinstance(o, dict):
                        if 'id' in in_dict:
                            print(f'data group:  {k} - {in_dict["id"]}')
                        self.delete_and_add_compliance(o)

    def mirror_nested(self, in_dict: Dict, out_dict: Dict):
        for key_in, value_in in in_dict.items():
            if key_in == 'id':
                out_dict['id'] = value_in
            if isinstance(value_in, dict):
                new_dict = {}
                out_dict[key_in] = new_dict
                self.add_compliance_parameters(key_in, new_dict)
                self.mirror_nested(value_in, new_dict)
            if isinstance(value_in, list):
                list_out = []
                found = False
                for item_in in value_in:
                    if isinstance(item_in, dict):
                        found = True
                        new_dict = {}
                        self.add_compliance_parameters(key_in, new_dict)
                        list_out.append(new_dict)
                        self.mirror_nested(item_in, new_dict)
                if found:
                    out_dict[key_in] = list_out

    def add_compliance_parameters(self, in_key, dict_new):
        if in_key in self.compliance_group_element:
            dict_new.update(self.compliance_group_element[in_key])

