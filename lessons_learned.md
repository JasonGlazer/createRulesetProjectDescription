# Lessons Learned During createRulesetModelDescription Development

An initial effort to implement an RMD generation script for EnergyPlus took place from March through September 2022. The
NFP is here:

https://github.com/NREL/EnergyPlus/blob/develop/design/FY2022/NFP-InitialRulesetModelDescription.md

The repository for the development was here:

https://github.com/JasonGlazer/createRulesetModelDescription

Overall, the project was successful in demonstrating that an output file could be generated that is consistent with the
draft ruleset model description (RMD) schema defined for ASHRAE 229 here:

https://github.com/open229/ruleset-model-description-schema

As a demonstration, the effort focused on non-HVAC items that were easiest to implement. Many different data groups and
data elements were included. Tracking of the specific data elements implemented is based on additional attributes in the
schema:

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

Most of these tags describe where in EnergyPlus input (epJSON or IDF files) or EnergyPlus output (tabular reports or
other files) that the data element could be populated. The EPstatus tags indicated an overall status of the implementation
for each data element and were one of the following:

 - DoneUsingInput
 - DoneUsingOutput
 - DoneUsingConstant
 - PartialUsingInput
 - PartialUsingOutput
 - PartialUsingConstant
 - NotRequired
 - NotStarted

If the ASHRAE229_extra.schema.yaml is present in the same directory as the script, these tags are read and summarized in
the script, and a report is generated each time it is run

https://github.com/JasonGlazer/createRulesetModelDescription/blob/initial_development/eplus_rmd/energyplus_implementation_report.txt

The 'counts' at the bottom of each data group summarize the implementation for that data group. This file is regenerated
each time the script is run if the ASHRAE229_extra.schema.yaml is in the folder with the script.

## Goals

The development of the createRulesetModelDescription.py script for EnergyPlus always has multiple goals:

 - Demonstrate an initial implementation of producing an RMD
 - Uncover problems with RMD schema
 - Show feasibility of implementation
 - Implement as many stable data groups as possible

As part of this plan, we decided to skip complicated data elements and “Compliance Parameters” (explained below)

## Separate Python Utility Focused on Output

The original expectation for how to implement the functionality of creating an RMD file was to include it directly in
the EnergyPlus C++ engine as an additional report option. After a presentation of this original plan, the EnergyPlus
development team recognized the value of keeping it outside the EnergyPlus engine and instead made it a separate
Python utility. This kept the EnergyPlus engine from having an additional non-core feature as well as separating the
utility to make its use more flexible and less tied to executing a specific simulation.

In addition, the development team decided that the Python utility should favor the use of EnergyPlus outputs and only
use input files if absolutely necessary. The reasons for this were:

 - increased stability since output changes less often than the input
 - many output reports already provide a summary similar to what is needed rather than needing to reinterpret the input
 - adding additional output tables also benefits users in debugging files and understanding their simulations 
 - if no input is used, then no synchronization is needed between reading input and output files, and whether the output files are stale 

## All JSON Approach 

To simplify the script and include fewer libraries, we decided leverage to JSON files whenever possible. The RMD file is
already in JSON format, and EnergyPlus has a JSON formatted input file called epJSON that is equivalent to an IDF file.
In addition, EnergyPlus can produce tabular output files in JSON format. While the JSON output format and epJSON
input format are not as commonly used, they are easy for users to create. In the case of epJSON, a utility is included
with EnergyPlus to produce an epJSON file from an IDF file. One disadvantage of this all JSON approach is that the JSON
output file format is not supported by two utilities that are common ways to run EnergyPlus called EP- Launch 2 and EP-
Launch 3. The addition of supporting this output format will not be difficult and is described in Issue #9403:

https://github.com/NREL/EnergyPlus/issues/9403

During the development of the script, a bug was found in the way the Initialization Summary report was generated. This
report produces in the tabular output file (usually HTML but for this script JSON) the contents of the EIO file that
EnergyPlus historically uses to summarize input, issue #9419

https://github.com/NREL/EnergyPlus/issues/9419

Resolving this issue was important to this effort, and it was fixed during the time of development so that additional
data from the Initialization Summary could be utilized.

## New Input Requirements

In order to create all the outputs required by the script, several additional inputs are needed in the EnergyPlus input file
to trigger the production of certain reports or files. These are described in the README.MD file and include:

 - Output:Table:SummaryReports
 - Output:JSON
 - OutputControl:Table:Style
 - Output:Variable,\*,schedule value,hourly;
 - Output:Schedules
 - Space
    
The main issue for users will be adding the appropriate Space input objects. This is a recent addition to EnergyPlus
appearing first in version 9.6.0, released in September 2021, and many users do not use the input object. A Space input
object needs to be added for each Zone for files that do not have them and this could greatly reduce the adoption of
this script.

## Version Nightmares

Many separate software pieces were going through simultaneous development during this effort, including EnergyPlus, the
RMD Schema, the PNNL RCT tool and the version of the RMD Schema it was using, and OpenStudio Standards and the version
of EnergyPlus it was using. This is the nature of software components being developed to be used with other software
that has its own priorities and deadlines and is nothing new. Hopefully, as the RMD Schema gets published as part of
Standard 229, it will undergo no changes or at least fewer changes, and that will allow all other software components to
be integrated without as much concern for versions.

## Validation

The initial version of the script did not validate the RMD files that were being produced, but this oversight was quickly
changed, and now the Python package jsonschema is used to validate the RMD file being produced by the script. It adds very
little overhead and has caught numerous problems.

## Unit Testing

The current line coverage for unit testing is at 91% which is good but not 100%. The development of unit tests provided
the developer confidence while making changes and updates that they were not breaking other code and were critical to the
development of the script.

## IDs

The schema file has the following note:

- All IDs within a RulesetModelInstance should be unique for each type of data group. Between Ruleset ModelInstances,
  IDs should be the same for the same component.

This has proven to be a challenge. The strategy that is currently used to use the name of the input object from
EnergyPlus does not meet this criterion since EnergyPlus allows the same name to be used for different input objects. An
approach of using a combination of the names of the input object and the name of its "parent" might be better. In
addition, since many Python dictionaries are used and re-used in the schema, additional uses "deepcopy" need to be added
to make sure separate subdictionary elements are named uniquely.

## Level

The inherent hierarchy of EnergyPlus and the inherent hierarchy of the RMD schema do not always match, and this can be a
challenge. For example, modeling plug loads in EnergyPlus is done with ElectricEquipment, which most commonly references
the Zone, but in the RMD schema, the MiscellaneousEquipment data group is a child of the Space data group, which is a child
of Zone. This disconnect in the level of the hierarchy can be difficult to properly map and allocate.

## Schedules

A very large portion of RMD files ends up being the schedules since they are represented in the schema as 8760 hourly
values. This makes them almost impossible to debug if they are being done correctly. Since we were echoing the values
from an hourly output from EnergyPlus, no debugging was performed other than to see that they were the same.

## Data Groups for each Parent

The methodology used throughout the script was to create data groups for each row of the appropriate table found in the
EnergyPlus output. This was identified as not as expected for the Infiltration data group, which wanted the data group to
exist even for zones with no infiltration defined.

## New Output Reports

An early decision by the EnergyPlus development team is to favor the use of output reports for the source of data for
the data elements. While a good approach, it does mean that the addition of many new reports are probably required in
order to fully populate the schema. This is needed for the data groups implemented so far but is expected to be even
more important when HVAC-oriented data groups are implemented. These new output reports, while critical to the future
implementation of this script, will also provide users with the benefit of summarizing the input from EnergyPlus, which is
quite valuable in the process of debugging input files no matter what user interface is used. This effort did not
include any additional output reports, but future efforts should include the development of at least a targeted number of
output reports to reduce the need to depend directly on the input file (epJSON is read by the script). To see which data
elements used input, see data elements with the EPstatus of DoneUsingInput or PartialUsingInput. Do not underestimate
the effort to create new tabular reports, especially those related to HVAC topology.

## Topology of HVAC

EnergyPlus does not have any output reports that directly represent the topology of the HVAC system. A graphical
representation is available using the HVAC-Diagram utility that reads the BND file (essentially a list of different types
of links between components) and creates an SVG file (this will soon be replaced with a Python script to provide the same
function), but no explicit reports of topology exist in EnergyPlus. Adding such reports of branches and how they connect
into loops would be necessary. These types of reports may not be strictly tabular or maybe a combination of hierarchy
and tabular layouts, which is currently not being used in EnergyPlus. Creating the proper reporting may be a challenge for
any simulation program with loosely connected components used to define HVAC systems.

## Compliance Parameters

Many data elements are not reflected in an EnergyPlus input or output files, and many of them are related to
categorization used in compliance. In general, these data elements were not implemented, but some system to facilitate
input from users would make sense. For interfaces using EnergyPlus, they might be added as fields from the user
interface, or they might be inferred from the use of a particular library element. For users of EnergyPlus directly, a
system to merge parameters that are compliance parameters with the RMD created by the script would be useful. One
possible approach would be to have an RMD-like file that only includes only the compliance parameters but follows the
structure of the RMD file for zones and other data groups. This file could be read by the script and merged together to
provide a complete RMD file. Given the iterative nature of input file creation and debugging, this would be a good
approach. The script itself could help create a "blank" RMD-like file that has all the places that need to be completed
by the user. This could simply be a JSON-based file with fields for all the compliance parameters organized by zone and
by other data groups with such parameters.

To leverage the ability for IDF Editor (or soon the epJSON Editor), this approach could be extended to provide special
IDF or epJSON files that could be used with those editors to complete them. In many cases, the compliance parameters are
selections from a list of enumerations, something that the IDF Editor does well.

For the current initial script, some compliance parameters were implemented for lighting space type, ventilation space
type, and service water heating space type since the new EnergyPlus Space input object has fields for entering such 
information (Space Type, Tag 1, Tag 2, etc.). Only three compliance parameters in the Space data group were implemented
using these fields but more could be implemented in the future.

## Summary

The most important considerations for completing the createRulesetModelDescription are:

- identification and classification of all data groups using the special tags in the schema
- adding necessary output reports in EnergyPlus
- improving the generation of unique but consistent IDs
- develop a strategy for handling compliance parameters





