# Creating ASHRAE Standard 229 Ruleset Project Description Files for EnergyPlus 

[![Test/Package Status](https://github.com/JasonGlazer/createRulesetProjectDescription/actions/workflows/flake8.yml/badge.svg)](https://github.com/JasonGlazer/createRulesetProjectDescription/actions/workflows/flake8.yml)
[![Build Package and Run Tests](https://github.com/JasonGlazer/createRulesetProjectDescription/actions/workflows/build_and_test.yml/badge.svg?branch=main)](https://github.com/JasonGlazer/createRulesetProjectDescription/actions/workflows/build_and_test.yml)

An EnergyPlus utility that creates a Ruleset Project Description (RPD) file based on output (and some input) from a simulation. 

## Background

The RPD file is based on a schema being developed as part of the writing of ASHRAE Standard 229P:

Title:

 - Protocols for Evaluating Ruleset Implementation in Building Performance Modeling Software

Purpose:

 - This standard establishes tests and acceptance criteria for implementation of rulesets (e.g., modeling rules) and related reporting in building performance modeling software.

Scope:

 - This standard applies to building performance modeling software that implements rulesets.
 - This standard applies to rulesets associated with new or existing buildings and their systems, system controls, their sites, and other aspects of buildings described by the ruleset implementation being evaluated.

The development of the RPD schema to support the standard is going on here:

https://github.com/open229/ruleset-model-description-schema

## Overview

The utility is intended to be used at a command line prompt:

```
  createRulesetProjectDescription in.epJSON
```

where in.epJSON is the name of the EnergyPlus input file with the file path, in the epJSON format. 

EnergyPlus version 24.2.0 or newer is required to use the utility.

An [overview video](https://youtu.be/p1vHqsraR8g) is also available.

## Command Line Options

To create an RPD file using the same name as the .epJSON file but with the .rpd extension, call 

```
  createRulesetProjectDescription filename.epJSON
```

Since many compliance parameters are needed, to create an JSON file with the correct fields for each corresponding EnergyPlus object call with the --create_empty_cp or -c parameter

```
  createRulesetProjectDescription --create_empty_cp filename.epJSON
```

That will create a file named filename.comp-param-empty.json that is like an RPD file but only contains compliance parameters. The user should then rename the file to filename.comp-param.json and edit the file with the correct compliance parameters in each field. When that is complete the command with --add_cp or -a will merge the compliance parameters provided by the user with the data elements populated from EnergyPlus. Here is an example:

```
  createRulesetProjectDescription --add_cp filename.epJSON
```

For help with the command line options use the parameter -h or --help without a filename.

```
  createRulesetProjectDescription --help
```

## epJSON Format

To create an epJSON file from an EnergyPlus IDF file, use ConvertInputFormat.exe that comes with EnergyPlus. 

To convert files, at the command prompt type:

```
 ConvertInputFormat in.idf
```

Where in.idf is the name of the EnergyPlus input file with the file path, in the IDF format. The utility will convert the file into a file with the same name
but with the extension .epJSON in the JSON format. 

For additional help with ConvertInputFormat at the command prompt in the directory with the EnergyPlus application, type:

```
 ConvertInputFormat --help
```

## Required Input File Changes

The EnergyPlus input file has some added requirements to be used with the createRulesetProjectDescription utility.

 - many tabular output reports are used, so the Output:Table:SummaryReports should be set to AllSummary, AllSummaryMonthly, or AllSummaryMonthlyAndSizingPeriod:

``` 
  Output:Table:SummaryReports,
    AllSummaryMonthly;    !- Report 1 Name
``` 

Additional warning messages may appear when including the monthly predefined reports.

 - the JSON output format is used, so that should be enabled for both time series and tabular output:

```    
  Output:JSON,
    TimeSeriesAndTabular,    !- Option Type
    Yes,                     !- Output JSON
    No,                      !- Output CBOR
    No;                      !- Output MessagePack
```

This will create filename_out.json files when EnergyPlus is run at the command line. 

Note: This utility was designed to work with files produced using EnergyPlus at the command line. Some file renaming might be necessary if using EP-Launch. 
If using EP-Launch, the eplusout.json and eplusout_hourly.json files may be found in the EPTEMP directory without the specific file name.

 - SI units should be used so

``` 
   OutputControl:Table:Style,
    HTML,            !- Column Separator
    None;            !- Unit Conversion
```
 - hourly output for each schedule needs to be created using the following
 
```
   Output:Variable,
    *,
    schedule value,
    hourly;
```

This will create filenameout_hourly.json files when EnergyPlus is run at the command line. If using EP-Launch, this files may be found in the EPTEMP directory without the specific file name.

 - add output schedules reports
 
```
  Output:Schedules,
    Hourly;
```

This produces a summary report in the EIO file and the Initialization Summary related to schedules. While it is not currently used by the script it probably will be used 
in the future.


 - add space type tags by using the Space input object

```
  Space,
    core_space,              !- Name
    Core_ZN,                 !- Zone Name
    autocalculate,           !- Ceiling Height
    autocalculate,           !- Volume
    autocalculate,           !- Floor Area {m2}
    OFFICE_OPEN_PLAN,        !- Space Type
    OFFICE_BUILDINGS_OFFICE_SPACE, !- Tag 1
    OFFICE;                  !- Tag 2
```

The fields should be completed as described below:

 - the Space Type field should be set to the appropriate option for lighting_space_type see LightingSpaceOptions2019ASHRAE901TG37 for the list of options.
 - the Tag 1 field should be set to the the appropriate option for ventilations_space_type see VentilationSpaceOptions2019ASHRAE901 for the list of options.
 - the Tag 2 field should be set to the the appropriate option for service_water_heating_space_type see ServiceWaterHeatingSpaceOptions2019ASHRAE901 for the list of options.

These enumerated lists are found here:

https://github.com/open229/ruleset-model-description-schema/blob/master/docs229/Enumerations2019ASHRAE901.schema.md

If you have not been using the Space input object before, set the numeric inputs to 'autocalculate'.

It is usually easier to make these changes prior to converting the file into the epJSON format.

## Weather File

When selecting the EPW weather file, make sure the STAT file is present in the same directory. This file is needed to fully populate the Climatic Data Summary tabular 
report, which is used to identify the ASHRAE climate zone.

## Output

The resulting Ruleset Project Description file will be created in the same directory as the epJSON file with the same name and the file extension .rpd

The Ruleset Project Description file is not complete but can be used to test many aspects of the building model transformation due to the ruleset. 
The data groups that are partially populated include:

 - RulesetProjectDescription
 - RulesetModelDescription
 - Building
 - BuildingSegment
 - Zone
 - Space
 - Infiltration
 - Surface
 - Construction
 - Material
 - Subsurface
 - InteriorLighting
 - MiscellaneousEquipment
 - Schedule
 - Calendar
 - Weather
 - HeatingVentilatingAirConditioningSystem
 - HeatingSystem
 - CoolingSystem
 - FanSystem
 - Fan
 - Terminal
 - FluidLoop
 - FluidLoopDesignAndControl
 - Pump
 - Boiler
 - Chiller
 - HeatRejection
 - ExteriorLighting


Please note that all data groups listed above still have some data elements that are not implemented and, in many cases, many data elements that are not implemented. The ones that 
were implemented often because they were easy to implement and not necessarily based on the need for the data element. 

Data groups that have not started to be implemented are:

 - SurfaceOpticalProperties
 - Transformer
 - Elevator
 - AirEconomizer
 - AirEnergyRecovery
 - FanOutputValidationPoint
 - PumpOutputValidationPoint
 - BoilerOutputValidationPoint
 - ChillerCapacityValidationPoint
 - ChillerPowerValidationPoint
 - ExternalFluidSource
 - ServiceWaterHeatingDistributionSystem
 - ServiceWaterPiping
 - SolarThermal
 - ServiceWaterHeatingEquipment
 - ServiceWaterHeaterValidationPoint
 - HeatPumpWaterHeaterCapacityValidationPoint
 - HeatPumpWaterHeaterPowerValidationPoint
 - Tank
 - ServiceWaterHeatingUse
 - RefrigeratedCase

If the the ASHRAE229_extra.schema.yaml with extra EnergyPlus tags are included in the energyplus_rpd folder, then an energyplus_implementation_report.txt file is generated which provides additional details. An example of the extra tags is shown here:

https://github.com/open229/ruleset-model-description-schema/blob/EPtags/schema-source/ASHRAE229_extra.schema.yaml

