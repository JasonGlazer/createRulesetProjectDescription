import jsonschema
import os
import posixpath

from json import load


class Validator:

    def __init__(self):
        schema_path = './ASHRAE229.schema.json'
        with open(schema_path ,'r') as schema_file:
            uri_path = os.path.abspath(os.path.dirname(schema_path))
            if os.sep != posixpath.sep:
                uri_path = posixpath.sep + uri_path
            self.resolver = jsonschema.RefResolver(f'file://{uri_path}/', schema_path)
            self.schema = load(schema_file)
            print(f"Validation based on {uri_path} {schema_path}")

    def validate_rmd(self, rmd_dict):
            jsonschema.validate(instance=rmd_dict, schema=self.schema, resolver=self.resolver)
