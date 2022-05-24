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

        main_schema_path = Path(parent_dir).joinpath(main_schema_file)
        enum_901_path = Path(parent_dir).joinpath(enum_901_file)
        enum_resnet_path = Path(parent_dir).joinpath(enum_resnet_file)
        enum_t24_path = Path(parent_dir).joinpath(enum_t24_file)
        output_901_path = Path(parent_dir).joinpath(output_901_file)

        with open(main_schema_path) as schema_f:
            main_schema = load(schema_f)
        with open(enum_901_path) as enum_901_f:
            enum_901 = load(enum_901_f)
        with open(enum_resnet_path) as enum_resnet_f:
            enum_resnet = load(enum_resnet_f)
        with open(enum_t24_path) as enum_t24_f:
            enum_t24 = load(enum_t24_f)
        with open(output_901_path) as output_901_f:
            output_901 = load(output_901_f)

        schema_store = {
            main_schema_file: main_schema,
            enum_901_file: enum_901,
            enum_resnet_file: enum_resnet,
            enum_t24_file: enum_t24,
            output_901_file: output_901
        }

        resolver = jsonschema.RefResolver.from_schema(main_schema, store=schema_store)

        Validator = jsonschema.validators.validator_for(main_schema)
        self.validator = Validator(main_schema, resolver=resolver)

    def validate_rmd(self, rmd_dict):
        try:
            self.validator.validate(rmd_dict)
            return {"passed": True, "error": None}
        except jsonschema.exceptions.ValidationError as err:
            return {"passed": False, "error": "invalid: " + err.message}
