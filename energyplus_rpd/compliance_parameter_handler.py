from json import dumps, loads
from pathlib import Path
from typing import Dict


class ComplianceParameterHandler:
    def __init__(self, epjson_file_path: Path):
        self.cp_empty_file_path = epjson_file_path.with_suffix('.comp-param-empty.json')
        self.cp_file_path = epjson_file_path.with_suffix('.comp-param.json')
        self.cp_file = {}
        self.compliance_group_element = {
            # data group: {data element: default value, ...}
            'root':
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
                 'function': 'OTHER'},
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
                {'enthalpy_recovery_ratio': 0.3},
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

    def create_empty_compliance_json(self, json_dict: Dict):
        # this is one of the main entry points
        created_dict = {}
        self.mirror_nested(json_dict, created_dict)
        self.cp_empty_file_path.write_text(dumps(created_dict, indent=2))
        return created_dict

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
        return out_dict

    def add_compliance_parameters(self, in_key, dict_new):
        if in_key in self.compliance_group_element:
            dict_new.update(self.compliance_group_element[in_key])
        return dict_new

    def merge_in_compliance_parameters(self, rpd_dict):
        # this is one of the main entry points
        self._load_cp_file()
        rpd_dict = self.update_dict(rpd_dict, self.cp_file)
        return rpd_dict

    def _load_cp_file(self):
        if not self.cp_file_path.exists():
            raise Exception(f"Could not find input file at path: {self.cp_file_path}")
        try:
            cp_contents = self.cp_file_path.read_text()
            self.cp_file = loads(cp_contents)
        except Exception as e:
            print(f"Could not process compliance file into JSON object; error: {e}")
            raise

    # https://stackoverflow.com/questions/66383920/merge-deep-json-files-in-python
    def update_dict(self, original, update):
        for key, value in update.items():
            # Add new key values
            if key not in original:
                original[key] = update[key]
                continue
            # Update the old key values with the new key values
            if key in original:
                if isinstance(value, dict):
                    self.update_dict(original[key], update[key])
                if isinstance(value, list):
                    self.update_list(original[key], update[key])
                if isinstance(value, (str, int, float)):
                    original[key] = update[key]
        return original

    def update_list(self, original, update):
        # Make sure the order is equal, otherwise it is hard to compare the items.
        assert len(original) == len(update), "Can only handle equal length lists."
        for idx, (val_original, val_update) in enumerate(zip(original, update)):
            if not isinstance(val_original, type(val_update)):
                raise ValueError(f"Different types! {type(val_original)}, {type(val_update)}")
            if isinstance(val_original, dict):
                original[idx] = self.update_dict(original[idx], update[idx])
            if isinstance(val_original, (tuple, list)):
                original[idx] = self.update_list(original[idx], update[idx])
            if isinstance(val_original, (str, int, float)):
                original[idx] = val_update
        return original
