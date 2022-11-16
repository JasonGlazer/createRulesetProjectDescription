from yaml import safe_load
from pathlib import Path
from datetime import datetime


class StatusReporter:
    def __init__(self):
        self.extra_schema = {}
        parent_dir = Path(__file__).parent

        # the extra schema file includes extra tags on fields related to appendix G and energyplus
        # these extra tags are just for internal tracking of what has been fully or partially
        # implemented and is unlikely to be useful to end users.
        extra_schema_file = 'ASHRAE229_extra.schema.yaml'
        extra_schema_path = parent_dir / extra_schema_file
        if extra_schema_path.exists():
            with open(extra_schema_path) as schema_f:
                self.extra_schema = safe_load(schema_f)
        report_file = 'energyplus_implementation_report.txt'
        self.report_file_path = parent_dir / report_file

    def generate(self):  # , rmd_dict):
        if self.extra_schema:
            # if the YAML schema file is not present then don't generate report
            # since the report is just for internal tracking of development
            # it fails gracefully when the file is not present which would only
            # be present for the developer.
            with open(self.report_file_path, 'w') as f:
                print('============= Generated Report ==============', file=f)
                print(f'Updated at: {datetime.now()} \n', file=f)
                for data_group_name, node in self.extra_schema.items():
                    if 'Object Type' in node:
                        if node['Object Type'] == 'Data Group':
                            print(data_group_name, file=f, end='')
                        if 'Data Elements' in node:
                            data_elements = node['Data Elements']
                            counter = {'inout ': 0, 'input ': 0, 'output': 0, 'note  ': 0, 'null  ': 0}
                            status_count = {'DoneUsingInput': 0, 'DoneUsingOutput': 0, 'DoneUsingConstant': 0,
                                            'PartialUsingInput': 0, 'PartialUsingOutput': 0, 'PartialUsingConstant': 0,
                                            'NotRequired': 0, 'NotStarted': 0}
                            print(f'  #elements: {len(data_elements)}', file=f)
                            for data_element in data_elements:
                                fields = data_elements[data_element]
                                _type = self.type_of_ep_field(fields)
                                status = ''
                                if 'EPstatus' in fields:
                                    status = fields['EPstatus']
                                    status_count[status] += 1
                                print('  ' + _type + '  ' + status.ljust(25, ' ') + data_element, file=f)
                                counter[_type] = counter[_type] + 1
                            print(f'  counts:  {counter} {status_count} \n', file=f)

    @staticmethod
    def type_of_ep_field(fields):
        plus_in = False
        plus_out = False
        plus_note = False
        if 'EPin Object' in fields:
            if fields['EPin Object']:
                plus_in = True
        if 'EPin Field' in fields:
            if fields['EPin Field']:
                plus_in = True
        if 'EPout File' in fields:
            if fields['EPout File']:
                plus_out = True
        if 'EPout Report' in fields:
            if fields['EPout Report']:
                plus_out = True
        if 'EPout Table' in fields:
            if fields['EPout Table']:
                plus_out = True
        if 'EPout Column' in fields:
            if fields['EPout Column']:
                plus_out = True
        if 'EP Notes' in fields:
            if fields['EP Notes']:
                plus_note = True
        if plus_in and plus_out:
            return 'inout '
        elif plus_in:
            return 'input '
        elif plus_out:
            return 'output'
        elif plus_note:
            return 'note  '
        else:
            return 'null  '
