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

## Other Lessons

## 
