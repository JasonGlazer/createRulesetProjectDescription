from json import loads
from pathlib import Path
from typing import Tuple

import jsonschema


class Validator:

    def __init__(self):
        parent_dir = Path(__file__).resolve().parent

        # approach from
        # https://stackoverflow.com/questions/53968770/how-to-set-up-local-file-references-in-python-jsonschema-document

        main_schema_path = parent_dir / 'ASHRAE229.schema.json'
        enum_901_path = parent_dir / 'Enumerations2019ASHRAE901.schema.json'
        enum_resnet_path = parent_dir / 'EnumerationsRESNET.schema.json'
        enum_t24_path = parent_dir / 'Enumerations2019T24.schema.json'
        output_901_path = parent_dir / 'Output2019ASHRAE901.schema.json'

        self.main_schema = loads(main_schema_path.read_text())
        self.enum_901 = loads(enum_901_path.read_text())
        self.enum_resnet = loads(enum_resnet_path.read_text())
        self.enum_t24 = loads(enum_t24_path.read_text())
        self.output_901 = loads(output_901_path.read_text())

        schema_store = {
            main_schema_path.name: self.main_schema,
            enum_901_path.name: self.enum_901,
            enum_resnet_path.name: self.enum_resnet,
            enum_t24_path.name: self.enum_t24,
            output_901_path.name: self.output_901
        }

        resolver = jsonschema.RefResolver.from_schema(self.main_schema, store=schema_store)
        validator_class_type = jsonschema.validators.validator_for(self.main_schema)
        self.validator = validator_class_type(self.main_schema, resolver=resolver)

    def validate_rmd(self, rmd_dict: dict) -> Tuple[bool, str]:
        try:
            self.validator.validate(rmd_dict)
            return True, ''
        except jsonschema.exceptions.ValidationError as err:
            return False, f"invalid: {err.message}"

    def is_in_901_enumeration(self, enumeration_list_name: str, search_string: str) -> bool:
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
