import json
import sys
from pathlib import Path

filename_in = sys.argv[1]
filename_out = Path(filename_in).with_suffix(".added.epjson")


def get_tags_by_name(name):
    tagging = {
        'off': ('OFFICE_OPEN_PLAN',
                'OFFICE_BUILDINGS_OFFICE_SPACE',
                'OFFICE'),
        'din': ('DINING_AREA_CAFETERIA_OR_FAST_FOOD_DINING',
                'FOOD_AND_BEVERAGE_SERVICE_RESTAURANT_DINING_ROOMS',
                'DINING_CAFETERIA_FAST_FOOD'),
        'dorm': ('GUEST_ROOM',
                 'HOTELS_MOTELS_RESORTS_DORMITORIES_BEDROOM_LIVING_ROOM',
                 'DORMITORY'),
        'guest': ('GUEST_ROOM',
                  'HOTELS_MOTELS_RESORTS_DORMITORIES_BEDROOM_LIVING_ROOM',
                  'HOTEL'),
        'ret': ('RETAIL_FACILITIES_MALL_CONCOURSE',
                'RETAIL_SALES_EXCEPT_OTHER_SPECIFIC_RETAIL',
                'RETAIL'),
        'exer': ('GYMNASIUM_FITNESS_CENTER_EXERCISE_AREA',
                 'SPORTS_AND_ENTERTAINMENT_HEALTH_CLUB_AEROBICS_ROOM',
                 'EXERCISE_CENTER'),
        'gym': ('GYMNASIUM_FITNESS_CENTER_PLAYING_AREA',
                'SPORTS_AND_ENTERTAINMENT_GYM_SPORTS_ARENA_PLAY_AREA',
                'GYMNASIUM'),
        'health': ('HEALTHCARE_FACILITY_EXAM_TREATMENT_ROOM',
                   'OUTPATIENT_HEALTH_CARE_FACILITIES_GENERAL_EXAMINATION_ROOM',
                   'HEALTH_CARE_CLINIC'),
        'hosp': ('HEALTHCARE_FACILITY_EXAM_TREATMENT_ROOM',
                 'OUTPATIENT_HEALTH_CARE_FACILITIES_URGENT_CARE_EXAMINATION_ROOM',
                 'HOSPITAL_AND_OUTPATIENT_SURGERY'),
        'otel': ('DWELLING_UNIT',
                 'HOTELS_MOTELS_RESORTS_DORMITORIES_BEDROOM_LIVING_ROOM',
                 'HOTEL'),
        'lib': ('LIBRARY_STACKS',
                'PUBLIC_ASSEMBLY_SPACES_LIBRARIES',
                'LIBRARY'),
        'manu': ('MANUFACTURING_FACILITY_LOW_BAY_AREA',
                 'MISCELLANEOUS_SPACES_MANUFACTURING_WHERE_HAZARDOUS_MATERIALS_ARE_NOT_USED',
                 'MANUFACTURING_FACILITY'),
        'apart': ('DWELLING_UNIT',
                  'HOTELS_MOTELS_RESORTS_DORMITORIES_BEDROOM_LIVING_ROOM',
                  'MULTIFAMILY'),
        'museum': ('MUSEUM_GENERAL_EXHIBITION_AREA',
                   'PUBLIC_ASSEMBLY_SPACES_MUSEUMS_GALLERIES',
                   'MUSEUM'),
        'class': ('CLASSROOM_LECTURE_HALL_TRAINING_ROOM_SCHOOL',
                  'EDUCATIONAL_FACILITIES_CLASSROOMS_AGES_5_TO_8',
                  'SCHOOL_UNIVERSITY'),
        'ware': ('WAREHOUSE_STORAGE_AREA_MEDIUM_TO_BULKY_PALLETIZED_ITEMS',
                 'MISCELLANEOUS_SPACES_WAREHOUSES',
                 'WAREHOUSE'),
        'aud': ('AUDIENCE_SEATING_AREA_AUDITORIUM',
                'PUBLIC_ASSEMBLY_SPACES_AUDITORIUM_SEATING_AREA',
                'TOWN_HALL'),
        'corr': ('CORRIDOR_ALL_OTHERS',
                 'TRANSIENT_RESIDENTIAL_COMMON_CORRIDORS',
                 'ALL_OTHERS'),
        'lob': ('LOBBY_ALL_OTHERS',
                'OFFICE_BUILDINGS_MAIN_ENTRY_LOBBIES',
                'ALL_OTHERS'),
        'stor': ('STORAGE_ROOM_SMALL',
                 'MISCELLANEOUS_SPACES_WAREHOUSES',
                 'WAREHOUSE'),
    }
    name_lower = name.lower()
    found = 'off'  # default to office if can't find anything else
    for search_string in tagging.keys():
        if search_string in name_lower:
            found = search_string
    return tagging[found]


with open(filename_in, "r") as f_in:
    with open(filename_out, 'w') as f_out:
        content = json.load(f_in)

        #  Output:Table:SummaryReports
        if 'Output:Table:SummaryReports' in content:
            report = content['Output:Table:SummaryReports']
            if 'Output:Table:SummaryReports 1' in report:
                report_list = report['Output:Table:SummaryReports 1']['reports']
                report_list[0] = {'report_name': 'AllSummaryAndMonthly', }

        # Output:JSON
        field_dict = {
            "option_type": "TimeSeriesAndTabular",
            "output_cbor": "No",
            "output_json": "Yes",
            "output_messagepack": "No"
        }
        if 'Output:JSON' in content:
            input_obj = content['Output:JSON']
            if 'Output:JSON 1' in input_obj:
                input_obj['Output:JSON 1'] = field_dict
        else:
            content['Output:JSON'] = {'Output:JSON 1': field_dict}

        # OutputControl:Table:Style
        field_dict = {
            "column_separator": "HTML",
            "unit_conversion": "None"
        }
        if 'OutputControl:Table:Style' in content:
            input_obj = content['OutputControl:Table:Style']
            if 'OutputControl:Table:Style 1' in input_obj:
                input_obj['OutputControl:Table:Style 1'] = field_dict
        else:
            content['OutputControl:Table:Style'] = {'OutputControl:Table:Style 1': field_dict}

        # Output:Variable
        field_dict = {
            "key_value": "*",
            "reporting_frequency": "Hourly",
            "variable_name": "schedule value"
        }
        if 'Output:Variable' in content:
            input_obj = content['Output:Variable']
            input_obj['Output:Variable ADDED'] = field_dict
        else:
            content['Output:Variable'] = {'Output:Variable ADDED': field_dict}

        # Output:Schedules
        field_dict = {
            "key_field": "Hourly"
        }
        if 'Output:Schedules' in content:
            input_obj = content['Output:Schedules']
            input_obj['Output:Schedules 1'] = field_dict
        else:
            content['Output:Schedules'] = {'Output:Schedules 1': field_dict}

        # Output:Constructions
        field_dict = {
            "details_type_1": "Constructions",
            "details_type_2": "Materials"
        }
        if 'Output:Constructions' in content:
            input_obj = content['Output:Constructions']
            input_obj['Output:Constructions 1'] = field_dict
        else:
            content['Output:Constructions'] = {'Output:Constructions 1': field_dict}

        # Space
        zones = {}
        spaces = {}
        default_space_dict = {
            "ceiling_height": "Autocalculate",
            "floor_area": "Autocalculate",
            "space_type": "OFFICE_OPEN_PLAN",
            "tags": [
                {
                    "tag": "OFFICE_BUILDINGS_OFFICE_SPACE"
                },
                {
                    "tag": "OFFICE"
                }
            ],
            "zone_name": "Core_ZN ZN"
        }
        if 'Zone' in content:
            zones = content['Zone']
        if 'Space' in content:
            spaces = content['Space']
        if zones and not spaces:  # no spaces need to create them for each zone
            for zone_name, zone_fields in zones.items():
                space_name = zone_name + '_space'
                space_type, tag1, tag2 = get_tags_by_name(zone_name)
                tags = [
                    {
                        "tag": tag1
                    },
                    {
                        "tag": tag2
                    }
                ]
                space = {
                    "ceiling_height": "Autocalculate",
                    "floor_area": "Autocalculate",
                    "volume": "Autocalculate",
                    "zone_name": zone_name,
                    "space_type": space_type,
                    "tags": tags
                }
                spaces[space_name] = space
            content['Space'] = spaces
        elif spaces:  # spaces exist so just need to add tags
            for space_name, space_fields in spaces.items():
                space_type, tag1, tag2 = get_tags_by_name(space_name)
                space_fields['space_type'] = space_type
                tags = [
                    {
                        "tag": tag1
                    },
                    {
                        "tag": tag2
                    }
                ]
                space_fields['tags'] = tags

        json.dump(content, f_out, indent=4)
