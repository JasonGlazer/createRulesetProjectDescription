import jsonschema

from pathlib import Path
from json import load


class Validator:

    def __init__(self):
        parent_dir = Path(__file__).parent

        # approach from
        # https://stackoverflow.com/questions/53968770/how-to-set-up-local-file-references-in-python-jsonschema-document

        main_schema_file = 'ASHRAE229.schema.json'
        enum_901_file = 'Enumerations2019ASHRAE901.schema.json'
        enum_resnet_file = 'EnumerationsRESNET.schema.json'
        enum_t24_file = 'Enumerations2019T24.schema.json'
        output_901_file = 'Output2019ASHRAE901.schema.json'

        main_schema_path = parent_dir / main_schema_file
        enum_901_path = parent_dir / enum_901_file
        enum_resnet_path = parent_dir / enum_resnet_file
        enum_t24_path = parent_dir / enum_t24_file
        output_901_path = parent_dir / output_901_file

        self.main_schema = {}
        self.enum_901 = {}
        self.enum_resnet = {}
        self.enum_t24 = {}
        self.output_901 = {}

        with open(main_schema_path) as schema_f:
            self.main_schema = load(schema_f)
        with open(enum_901_path) as enum_901_f:
            self.enum_901 = load(enum_901_f)
        with open(enum_resnet_path) as enum_resnet_f:
            self.enum_resnet = load(enum_resnet_f)
        with open(enum_t24_path) as enum_t24_f:
            self.enum_t24 = load(enum_t24_f)
        with open(output_901_path) as output_901_f:
            self.output_901 = load(output_901_f)

        schema_store = {
            main_schema_file: self.main_schema,
            enum_901_file: self.enum_901,
            enum_resnet_file: self.enum_resnet,
            enum_t24_file: self.enum_t24,
            output_901_file: self.output_901
        }

        resolver = jsonschema.RefResolver.from_schema(self.main_schema, store=schema_store)

        validator_class_type = jsonschema.validators.validator_for(self.main_schema)
        self.validator = validator_class_type(self.main_schema, resolver=resolver)

    def validate_rmd(self, rmd_dict):
        try:
            self.validator.validate(rmd_dict)
            return {"passed": True, "error": None}
        except jsonschema.exceptions.ValidationError as err:
            return {"passed": False, "error": "invalid: " + err.message}

    def is_in_901_enumeration(self, enumeration_list_name, search_string):
        if self.enum_901:
            if 'definitions' in self.enum_901:
                dict_of_enumerations = self.enum_901['definitions']
                if enumeration_list_name in dict_of_enumerations:
                    enumeration_holder = dict_of_enumerations[enumeration_list_name]
                    if 'enum' in enumeration_holder:
                        enumerations = enumeration_holder['enum']
                        if search_string in enumerations:
                            return True
        return False
