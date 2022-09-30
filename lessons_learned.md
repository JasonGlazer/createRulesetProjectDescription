# Lessons Learned During createRulesetModelDescription Development

An initial effort to implement an RMD generation script for EnergyPlus took place from 
March through September 2022. The NFP is here:

https://github.com/NREL/EnergyPlus/blob/develop/design/FY2022/NFP-InitialRulesetModelDescription.md

While the developmet took place:

https://github.com/JasonGlazer/createRulesetModelDescription

in the "initial_development" branch.

Overall, the project was successful in demonstrating that an output file could be generated that is 
consistent with the schema defined here:

https://github.com/open229/ruleset-model-description-schema

As a demonstration focused on non-HVAC items that were easiest to implement, many different
data groups and data elements were included. Tracking of the specific data elements implemented is 
based on additional attributes in the schema:

https://github.com/open229/ruleset-model-description-schema/blob/EPtags/schema-source/ASHRAE229_extra.schema.yaml

The additional attributes were:

 - EPin Object
 - EPin Field
 - EPout File
 - EPout Report
 - EPout Table
 - EPout Column
 - EPstatus
 - EP Notes

Most of these tags describe where in EnergyPlus input (epJSON or IDF files) or EnergyPlus output (tabular reports 
or other files) that the data element could be populated. The EPstatus tags indicate overall status of the implementation:

 - DoneUsingInput
 - DoneUsingOutput
 - DoneUsingConstant
 - PartialUsingInput
 - PartialUsingOutput
 - PartialUsingConstant
 - NotRequired
 - NotStarted

These tags are are specifically summarized in the script and 

https://github.com/JasonGlazer/createRulesetModelDescription/blob/initial_development/eplus_rmd/energyplus_implementation_report.txt

The 'counts' at the bottom of each data group summarize the implementation for that data group. This file is regenerated each time the 
script is run if the ASHRAE229_extra.schema.yaml is in folder with the script.

## Personal Bias

While this document is trying to focus on the lessons learned while implementing the createRulesetModelDescription.py script, some 
personal bias in the lessons learned are possible since I also serve as the chair of the Schema workgroup of SPC 229 and am the 
vice-chair of SPC 229.

## Goals

The development of the createRulesetModelDescription.py script for EnergyPlus always has multiple goals:

 - Demonstrate an initial implementation of producing an RMD
 - Uncover problems with RMD schema
 - Show feasibility of implementation
 - Implement as many stable data groups as possible
 - Skip complicated data elements
 - Skip “Compliance Parameters”

## Separate Python Utility Focused on Output

The original expectation for how to implement the functionality of creating an RMD file was to include it directly in the EnergyPlus
C++ engine as an additional report option. After a presentation of this original plan, the EnergyPlus development team recognized
the value of keeping it outside the EnergyPlus engine and instead making it a separate Python utility. This kept the EnergyPlus 
engine from having an additional non-core feature as well as separating the utility to make its use more flexible and less tied 
to executing a specific simulation. 

In addition, the development team decided that the Python utility should favor the use of EnergyPlus outputs and only use input
files if absolutely necessary. The reasons for this were 

 - stability: since output changes less often than input
 - summary: since output is already often a summary rather than a echo of input
 - value to others: adding additional output which will be required will also help users debug files and understand their simulations 
 even if completely unrelated to compliance and this utility
 - no syncronizing with input: if no input is ever used then the question of a revised input file being paired with the results of 
 an older, stale, output file would not occur

## All JSON Approach 

To simplify the script, it was decided leverage JSON files whenever possible. The RMD file is already in JSON format and EnergyPlus
has a JSON formatted input file called epJSON that is equivalent to an IDF file. In addition, EnergyPlus has a way to produce the 
tabular output files in JSON format. While the JSON output format and epJSON input format are not as commonly used, they are easy
for users to create. In the case of epJSON, a utility is included with EnergyPlus to produce an epJSON file from an IDF file. One 
disadvantage of this all JSON approach is that the JSON output file format is not supported by two utilities that are common ways
to run EnergyPlus called EP-Launch 2 and EP-Launch 3. The addition of supporting this output format will not be difficult and is
described in Issue #9403:

https://github.com/NREL/EnergyPlus/issues/9403

During the development of the script, a bug was found in the way the Intialization Summary report was generated. This report 
produces in the tabular output file (usually HTML but for this script JSON) the contents of the EIO file that EnergyPlus
historically uses to summarize input, issue #9419 

https://github.com/NREL/EnergyPlus/issues/9419

Resolving this issue was important to this effort and it was fixed during the time of development so that additional data 
from the Intialization Summary could be utilized.

## New Input Requirements

In order to create all the outputs required by the script, several additional inputs are needed in the EnergyPlus input file
to trigger the production of certain reports or files. These are described in the README.MD file are include:

 - Output:Table:SummaryReports
 - Output:JSON
 - OutputControl:Table:Style
 - Output:Variable,\*,schedule value,hourly;
 - Output:Schedules
 - Space
    
The main issue for users will be adding the appropriate Space input objects. This is a recent addition to EnergyPlus appearing
first in version 9.6.0 released in September 2021 and many users do not use the input object. A Space input object needs to be 
added for each Zone for files that do not have them and this could greatly reduce the adoption of this script.

## Version Nightmares

Many separate software pieces were going through simulatenous development during this effort including EnergyPlus, the RMD Schema,
the PNNL RCT tool and the version of the RMD Schema it was using, OpenStudio Standards and the version of EnergyPlus it was using.
This is the nature of software components being developed in to be used with other software that has its own priorities and deadlines
and is nothing new. Hopefully, as the RMD Schema gets published as part of Standard 229, it will undergo no changes or at least 
fewer changes and that will allow all other software components to be integrated without as much concern for versions. 

## Validation

The initial version of the script did not validate the RMD files that were being produced but this oversight was quickly changed and
now the Python package jsonschema is used to validate the RMD file being produced by the script. It add very little overhead and 
has caught numerous problems.

## Unit Testing

The current line coverage for unit testing is at 91% which is good but not 100%. The development of unit tests provides the developer
confidence while making changes and updates that they are not breaking other code and was critical to the development of the script.

## IDs

## Level

For example outputs that are categories by zone but are needed by space like misce elec 

## Schedules

Large portion of RMD

## Infiltration

Every zone instead of driven by presense of data

## Tracking Implementation

Custom tags in schema. Needs to be kept merged.

## New Output Reports

An early decision by the EnergyPlus development team is to favor the use of output reports for the source of data for the data elements. 
While a good approach, it does mean that the addition of many new reports are probably required in order to fully populate the schema.
This is needed for the data groups implemented so far but is expected to be even more important when HVAC oriented data groups are 
implemented. These new output reports while critical to the future implementation of this script will also provide users with the 
benefit of summarizing the input from EnergyPlus which is quite valuable in the process of debugging input files no matter what user
interface is used. This effort did not include any additional output reports but future efforts should include the development of 
at least a targeted number of output reports to reduce the need to depend directly on the input file (epJSON is read by the script). To
see which data elements used input, see data elements with the EPstatus of DoneUsingInput or PartialUsingInput. Do not underestimate the
effort to create new tabular report especially those related to HVAC topology.

## Specific New Outputs Needed

## Topology of HVAC

Challenge to loosely connected simulation programs like EnergyPlus and TRNSYS

## More testing with variety of files

## Reasons not done

Too complicated
Compliance parameter
Reference to other data group
Uses input instead of output
In InitializationSummary
Does not apply to EnergyPlus
Upper hierarchy skeleton 
In development
Not started yet


## Compliance Parameters

Many data elements are not reflected in an EnergyPlus input or output files and many of them are related to categorization used in
compliance. In general these were not implemented but some system to facilitate input from users would make sense. For interfaces
using EnergyPlus, they might be added as fields from the user interface or they might be infered from the use of a particular library
element. For users of EnergyPlus directly, a system to merge parameters that are compliance parameters with the RMD created by the
script would be useful. One possible approach would be to have a RMD-like file that only includes only the compliance parameters but 
follows the structure of the RMD file for zones and other data groupsl. that could be read by the script and a RMD with values from 
EnergyPlus and this RMD-like file would be merged together and created. Given the iterative nature of 
input file creation and debugging, this would be a good approach. The script itself could help create a "blank" RMD-like file that has
all the places that need to be completed by the user. This could simply be a JSON based file with fields for all the compliance parameters
organized by zone and by other data groups with such parameters.

Alternatively, this could take the form of a special epJSON or IDF file that could together with a 
special Energy+.idd or Energy+.schema.epJSON file that includes all the lists of choices that the user would pick from based on the 
enumerations from the schema. This would allow the user to use IDF Editor or epJSON Editor (hopefully available soon) to complete the 
compliance parameters and then the script could merge them. Generally the compliance parameters will probably be updated less often 
during the development of an input file.

For the current initial script, some compliance parameters were implemented for lighting space type, ventilation space type, and service
water heating space type since the new EnergyPlus Space input object has three fields for entering such information (Space Type, Tag 1 
and Tag 2).

Kludge of using enumeration names in simulation input naming.

## Future Changes to the Schema

At point this was done, most data groups approved by Schema WG but many fewer approved by SPC 229. Had focused on stable "approved" portions but expect changes. More in public review...
Possibly using completely different format for schedules based on BDE.

## Problems In Schema

Too many non-required fields, imply that all fields are required.

## Challenge of Decisions Still Being Made and Not Formally Required in Standard Yet

Such as infiltration for every zone, u-factor vs layers

## Continual Validation Against Schema

## docstrings

## Only works in 22.2.0

## Other Lessons

## Other future tasks

Incorporate RMD files into RunEPlus.bat, EPLaunch Classic, EPLaunch New

Greater integration with OpenStudio and OpenStudio standards and other interfaces

## Summary



