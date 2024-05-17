import copy
import jsonpatch
from json import dumps
from pathlib import Path
from typing import Dict


class ComplianceParameterHandler:
    def __init__(self, epjson_file_path: Path):
        self.cp_file_path = epjson_file_path.with_suffix('.cp.patch')

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
