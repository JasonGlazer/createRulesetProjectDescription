import json
import sys

filename_in = sys.argv[1]
filename_out = filename_in + '_added'

with open(filename_in, "r") as f_in:
    with open(filename_out, 'w') as f_out:
        content = json.load(f_in)

        changes = [
            ('Output:Table:SummaryReports', 'report_name', 'AllSummaryMonthly'),
        ]

        for change in changes:
            obj_name, field_name, field_value = change
            if content[obj_name]:
                ep_object = content[obj_name]
                for obj_name, obj_dict in ep_object.items():
                    pass

        #  Output:Table:SummaryReports
        if 'Output:Table:SummaryReports' in content:
            report = content['Output:Table:SummaryReports']
            if 'Output:Table:SummaryReports 1' in report:
                report_list = report['Output:Table:SummaryReports 1']['reports']
                report_list[0] = {'report_name': 'AllSummaryMonthly', }

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

        json.dump(content, f_out, indent=4)
